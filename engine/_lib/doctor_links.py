"""Markdown link and bare path checking for doctor.py."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterator
from urllib.parse import unquote

from .common import ENGINE_DIR
from .findings import Finding, rel as _rel
from .mdlinks import link_targets

URL_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:", re.I)
DOC_EXTENSIONS = (".md", ".json", ".yaml", ".yml", ".toml")
KNOWN_REFS = re.compile(r"^(ADR|SLICE|RES|COUNCIL|CHK|M|CAP)-(?:NNN|[A-Za-z0-9_-]+)(?:\.md)?$", re.I)
GITHUB_REF = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:#\d+)?$")
INLINE_CODE = re.compile(r"(`+)([^`\n]+)\1")
FENCE = re.compile(r"^[ \t]*```.*?^[ \t]*```", re.S | re.M)


def read_text(path: Path, root: Path, sink: list[Finding]) -> str | None:
    """Read UTF-8 text; on failure record a finding and return None so other checks continue."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        sink.append(Finding("E-ENCODING", _rel(path, root), "not valid UTF-8"))
    except OSError as exc:
        sink.append(Finding("E-READ", _rel(path, root), f"cannot read: {exc.strerror}"))
    return None


def inside(root: Path, rel: str) -> Path | None:
    """Path under root, or None when rel escapes it."""
    try:
        target = (root / rel).resolve()
        target.relative_to(root.resolve())
        return target
    except (ValueError, OSError):
        return None


def _markdown_files(root: Path) -> list[Path]:
    files = [root / "AGENTS.md", root / "CLAUDE.md"]
    docs = root / "docs"
    if docs.is_dir():
        engine = root / ENGINE_DIR
        files += [p for p in docs.rglob("*.md") if engine not in p.parents and root / "docs/_cgspec/_archive/agent-skills" not in p.parents]
    return [p for p in files if p.is_file() and not p.is_symlink()]


def _is_bare_path_candidate(span: str) -> tuple[str, bool] | None:
    if not span or any(ch.isspace() for ch in span):
        return None
    if any(ch in span for ch in ("<", ">", "*", "$", "{", "}", "%")) or "..." in span or "…" in span:
        return None
    if span.startswith(("//", "/*")) or (span.startswith("[") and "](" in span):
        return None
    if URL_SCHEME.match(span) and not span.startswith("file:"):
        return None
    if KNOWN_REFS.match(span) or span.startswith(("refs/", "origin/")) or span in ("HEAD", "FETCH_HEAD", "#"):
        return None

    cand = span
    if cand.startswith("file://"):
        cand = cand[7:]
        if cand.startswith("localhost/"):
            cand = cand[9:]
    cand = cand.split("#", 1)[0]
    cand = re.sub(r":\d+(?:[-:]\d+)?$", "", cand).strip()
    if not cand or KNOWN_REFS.match(cand):
        return None
    if cand.startswith("/") and not cand.startswith("//") and "/" not in cand[1:] and not any(cand.endswith(ext) for ext in DOC_EXTENSIONS):
        return None

    is_abs = cand.startswith(("/", "~"))
    is_rel = cand.startswith(("./", "../"))
    has_doc = any(cand.endswith(ext) for ext in DOC_EXTENSIONS)
    has_slash = "/" in cand
    looks_like_path = is_abs or is_rel or has_doc or (has_slash and (cand.endswith("/") or "." in Path(cand).name))
    if not looks_like_path:
        return None
    return cand, is_abs


def _bare_paths(path: Path, root: Path, text: str) -> Iterator[Finding]:
    stripped = FENCE.sub("", text)
    seen: set[str] = set()
    for m in INLINE_CODE.finditer(stripped):
        span = m.group(2).strip()
        if not span or span in seen:
            continue
        parsed = _is_bare_path_candidate(span)
        if parsed is None:
            continue
        cand, is_abs = parsed
        has_slash = "/" in cand
        has_doc = any(cand.endswith(ext) for ext in DOC_EXTENSIONS)
        if has_slash and not is_abs and not cand.startswith(("./", "../")) and not has_doc and GITHUB_REF.match(span):
            if not inside(root, cand) and not inside(root, str(path.parent / cand)):
                continue

        seen.add(span)
        if is_abs:
            try:
                target_str = os.path.expanduser(cand)
            except Exception:
                target_str = cand
            target = inside(root, target_str)
            if target is None or not target.exists():
                yield Finding("W-BARE-PATH", _rel(path, root), f"dangling bare path: {span}")
        else:
            t_doc = inside(root, str(path.parent / cand))
            t_root = inside(root, cand)
            if not ((t_doc is not None and t_doc.exists()) or (t_root is not None and t_root.exists())):
                yield Finding("W-BARE-PATH", _rel(path, root), f"dangling bare path: {span}")


def links(root: Path) -> Iterator[Finding]:
    archive = root / "docs/_cgspec/_archive"
    sink: list[Finding] = []
    for path in _markdown_files(root):
        text = read_text(path, root, sink)
        if text is None:
            continue
        for target in sorted(set(link_targets(text))):
            if URL_SCHEME.match(target) or target.startswith("#"):
                continue
            file_part = unquote(target.split("#", 1)[0])
            if file_part and not (path.parent / file_part).exists():
                code = "W-LINK" if archive in path.parents else "E-LINK"
                yield Finding(code, _rel(path, root), f"broken link: {target}")
        yield from _bare_paths(path, root, text)
    yield from sink
