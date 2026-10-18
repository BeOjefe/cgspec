"""The individual checks doctor.py runs. Each yields Finding objects; none writes anything."""

from __future__ import annotations

import json
import os
import re
import stat
from pathlib import Path
from typing import Iterator
from urllib.parse import unquote

from . import layout as L
from .common import ENGINE_DIR, MEMLOG_FILE, STATE_DIR, sha256_file
from .globs import match_any
from .mdlinks import link_targets
from .findings import Finding, rel as _rel
from .doctor_layout import layout  # noqa: F401  (re-exported for doctor.py)
from .schema import validate_named

STATUS = re.compile(r"^\s*[-*]?\s*\*{0,2}Status:?\*{0,2}:?\s*(.+?)\s*$", re.M | re.I)
URL_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:", re.I)


def read_text(path: Path, root: Path, sink: list[Finding]) -> str | None:
    """Read UTF-8 text; on failure record a finding and return None so other checks continue."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        sink.append(Finding("E-ENCODING", _rel(path, root), "not valid UTF-8"))
    except OSError as exc:
        sink.append(Finding("E-READ", _rel(path, root), f"cannot read: {exc.strerror}"))
    return None


def load_json(path: Path, root: Path, schema: str | None) -> tuple[object | None, list[Finding]]:
    sink: list[Finding] = []
    text = read_text(path, root, sink)
    if text is None:
        return None, sink
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, [Finding("E-SCHEMA", _rel(path, root), f"invalid JSON: line {exc.lineno}: {exc.msg}")]
    if schema is None:
        return data, []
    return data, [Finding("E-SCHEMA", _rel(path, root), e) for e in validate_named(data, schema)]


def inside(root: Path, rel: str) -> Path | None:
    """Path under root, or None when rel escapes it."""
    try:
        target = (root / rel).resolve()
        target.relative_to(root.resolve())
        return target
    except (ValueError, OSError):
        return None


def project(root: Path, data: dict | None) -> Iterator[Finding]:
    if data is None:
        yield Finding("E-LAYOUT-MISSING", "docs/_cgspec/project.json", "version marker missing or unreadable")
        return
    for error in validate_named(data, "project"):
        yield Finding("E-SCHEMA", "docs/_cgspec/project.json", error)


def symlinks(root: Path) -> Iterator[Finding]:
    for path in (root / "docs", root / "AGENTS.md", root / "CLAUDE.md"):
        if path.is_symlink():
            yield Finding("E-SYMLINK", _rel(path, root), "symlinks are not allowed")
    if (root / "docs").is_dir() and not (root / "docs").is_symlink():
        for dirpath, dirnames, filenames in os.walk(root / "docs"):
            for name in dirnames + filenames:
                full = Path(dirpath) / name
                if full.is_symlink():
                    yield Finding("E-SYMLINK", _rel(full, root), "symlinks are not allowed")


def state_files(root: Path) -> Iterator[Finding]:
    for name, schema in L.ALLOWED_STATE_FILES.items():
        path = root / STATE_DIR / name
        if path.is_file() and schema:
            yield from load_json(path, root, schema)[1]
    manifest = root / "docs/_cgspec/04-checks/manifest.json"
    if manifest.is_file():
        yield from load_json(manifest, root, "checks-manifest")[1]
    runs = root / "docs/_cgspec/05-runs"
    if not runs.is_dir():
        return
    for run in sorted(p for p in runs.iterdir() if p.is_dir()):
        if not re.match(L.RUN_NAME, run.name):
            yield Finding("E-NAME", _rel(run, root), "run folder must be named R-YYYYMMDD-xxxx")
        run_json = run / "run.json"
        if not run_json.is_file():
            yield Finding("E-LAYOUT-MISSING", _rel(run_json, root), "run folder without run.json")
            continue
        data, findings = load_json(run_json, root, "run")
        yield from findings
        if not findings and isinstance(data, dict) and data.get("run_id") != run.name:
            yield Finding("E-SCHEMA", _rel(run_json, root), "run_id does not match folder name")


def _real_content(text: str, spine: str) -> bool:
    template = L.SPINE_TEMPLATE_TEXT.get(spine, "")
    words = 0
    for line in text.splitlines():
        stripped = line.strip()
        if (not stripped or stripped.startswith("#") or L.EMPTY_MARKER in stripped or stripped == template
                or re.match(L.PLACEHOLDER_LINE, stripped, re.I)):
            continue
        words += len(re.findall(r"[^\W_]{2,}", stripped))
    return words >= L.MIN_SPINE_WORDS


def spines(root: Path, stages: dict) -> Iterator[Finding]:
    reached = max((L.STAGES.index(s) for s in stages.values() if s in L.STAGES), default=0)
    sink: list[Finding] = []
    for spine in L.SPINES:
        path = root / f"docs/spines/{spine}.md"
        if not path.is_file():
            path = root / f"docs/spines/{spine}/INDEX.md"
        text = read_text(path, root, sink) if path.is_file() else None
        if text is None or _real_content(text, spine):
            continue
        if reached >= L.STAGES.index(L.SPINE_REQUIRED_FROM[spine]):
            yield Finding("E-SPINE-EMPTY", _rel(path, root), f"empty, but a part has reached {L.STAGES[reached]}")
        else:
            yield Finding("W-SPINE-EMPTY", _rel(path, root), "still empty (fine at this stage)")
    yield from sink


def _markdown_files(root: Path) -> list[Path]:
    files = [root / "AGENTS.md", root / "CLAUDE.md"]
    docs = root / "docs"
    if docs.is_dir():
        engine = root / ENGINE_DIR
        files += [p for p in docs.rglob("*.md") if engine not in p.parents]
    return [p for p in files if p.is_file() and not p.is_symlink()]


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
    yield from sink


def records(root: Path) -> Iterator[Finding]:
    sink: list[Finding] = []
    groups = [("docs/adrs", L.ADR_NAME, L.DECISION_STATUSES), ("docs/slices", L.SLICE_NAME, L.SLICE_STATUSES)]
    for folder, pattern, statuses in groups:
        base = root / folder
        numbers: dict[str, str] = {}
        for path in sorted(base.iterdir()) if base.is_dir() else []:
            if path.name == ".gitkeep" or not path.is_file():
                continue
            name = re.match(pattern, path.name)
            if not name:
                yield Finding("E-NAME", _rel(path, root), f"name must match {pattern}")
                continue
            if name.group(1) != "draft":
                if name.group(1) in numbers:
                    yield Finding("E-ID-DUP", _rel(path, root), f"number {name.group(1)} also used by {numbers[name.group(1)]}")
                numbers[name.group(1)] = path.name
            text = read_text(path, root, sink)
            status = STATUS.search(text) if text is not None else None
            if text is not None and not status:
                yield Finding("E-STATUS", _rel(path, root), "no Status line")
            elif status and status.group(1).strip("* ") not in statuses:
                yield Finding("E-STATUS", _rel(path, root), f"status '{status.group(1)}' not in {statuses}")
    for folder, pattern, want_dir in (("docs/_cgspec/02-research", L.RES_NAME, False),
                                      ("docs/_cgspec/03-councils", L.COUNCIL_NAME, True)):
        base = root / folder
        for path in base.iterdir() if base.is_dir() else []:
            if path.name != ".gitkeep" and not (path.is_dir() == want_dir and re.match(pattern, path.name)):
                yield Finding("E-NAME", _rel(path, root), f"name must match {pattern}")
    yield from sink


def indexed_records(root: Path) -> list[str]:
    """Paths (relative to docs/) that the index must list."""
    out = []
    for folder in ("adrs", "slices", "_cgspec/02-research"):
        base = root / "docs" / folder
        if base.is_dir():
            out += [f"{folder}/{p.name}" for p in sorted(base.iterdir()) if p.is_file() and p.suffix == ".md"]
    councils = root / "docs/_cgspec/03-councils"
    if councils.is_dir():
        out += [f"_cgspec/03-councils/{p.name}/" for p in sorted(councils.iterdir()) if p.is_dir()]
    return out


def index(root: Path) -> Iterator[Finding]:
    path = root / "docs/00-INDEX.md"
    sink: list[Finding] = []
    text = read_text(path, root, sink) if path.is_file() else None
    yield from sink
    if text is None:
        return
    targets = {unquote(t.split("#")[0]) for t in link_targets(text)}
    for rel in indexed_records(root):
        if rel not in targets and rel.rstrip("/") not in targets:
            yield Finding("E-INDEX-MISSING", f"docs/{rel}", "not listed in docs/00-INDEX.md (doctor --fix adds it)")
    for target in sorted(targets):
        if target and not URL_SCHEME.match(target) and not (root / "docs" / target).exists():
            yield Finding("E-INDEX-ORPHAN", "docs/00-INDEX.md", f"lists {target}, which does not exist")


def frozen_entries(root: Path) -> tuple[list[dict], list[Finding]]:
    path = root / STATE_DIR / "frozen.json"
    if not path.is_file():
        return [], []
    data, findings = load_json(path, root, "frozen")
    if findings or not isinstance(data, dict):
        return [], []  # schema errors are reported by state_files
    return data["entries"], []


def frozen(root: Path) -> Iterator[Finding]:
    entries, _ = frozen_entries(root)
    listed = set()
    for entry in entries:
        target = inside(root, entry["path"])
        if target is None:
            yield Finding("E-FROZEN-PATH", entry["path"], "frozen path leaves the project")
            continue
        listed.add(target)
        if not target.is_file():
            yield Finding("E-FROZEN-MISSING", entry["path"], "frozen file is gone")
        elif sha256_file(target) != entry["sha256"]:
            yield Finding("E-FROZEN-HASH", entry["path"], "frozen file was changed")
        elif target.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
            yield Finding("W-FROZEN-WRITABLE", entry["path"], "frozen file is writable; doctor --fix makes it read-only")
    snaps = root / "docs/prototypes/_snapshots"
    for snap in sorted(snaps.glob("*.html")) if snaps.is_dir() else []:
        if snap.resolve() not in listed:
            yield Finding("E-FROZEN-UNLISTED", _rel(snap, root), "snapshot not recorded in frozen.json (only the bundler makes snapshots)")


def _has_shebang(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(2) == b"#!"
    except OSError:
        return False


def _is_script(path: Path) -> bool:
    # The exec bit alone is noise (WSL, exFAT, core.fileMode=false); a shebang is not.
    return path.suffix.lower() in L.SCRIPT_SUFFIXES or _has_shebang(path)


def _browser_asset(path: Path, prototypes: Path) -> bool:
    """Browser code inside a screen folder or the vision board, with no Node usage."""
    if prototypes not in path.parents or path.parent == prototypes or "_snapshots" in path.parts:
        return False
    if path.suffix.lower() not in L.PROTOTYPE_ASSET_SUFFIXES or _has_shebang(path):
        return False
    try:
        return not re.search(L.NODE_MARKERS, path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return False


def _registered_checks(root: Path) -> dict[str, str]:
    manifest = root / "docs/_cgspec/04-checks/manifest.json"
    if not manifest.is_file():
        return {}
    data, findings = load_json(manifest, root, "checks-manifest")
    return {c["path"]: c["sha256"] for c in data["checks"]} if not findings and isinstance(data, dict) else {}


def scripts(root: Path, path_classes: dict, legacy: set[str]) -> Iterator[Finding]:
    registered = _registered_checks(root)
    for rel, digest in registered.items():
        target = inside(root, rel)
        if target is None or not target.is_file():
            yield Finding("E-CHECK-MISSING", rel, "registered check is missing")
        elif sha256_file(target) != digest:
            yield Finding("E-CHECK-HASH", rel, "registered check changed since approval")
    engine, prototypes = root / ENGINE_DIR, root / "docs/prototypes"
    allowed_outside = path_classes.get("code", []) + path_classes.get("tests", []) + L.CONFIG_GLOBS
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in L.SKIP_WALK]
        here = Path(dirpath)
        if here == engine or engine in here.parents:
            continue
        for name in filenames:
            path = here / name
            if path.is_symlink() or name == ".gitkeep" or not _is_script(path):
                continue
            rel = _rel(path, root)
            if rel.startswith("docs/"):
                if rel in registered or _browser_asset(path, prototypes):
                    continue
                yield Finding("E-SCRIPT-UNREGISTERED", rel, "scripts in docs/ must be registered checks (spec 8)")
            elif rel not in legacy and not match_any(rel, allowed_outside):
                yield Finding("W-SCRIPT-OUTSIDE", rel, "script outside src/, tests or registered checks; the commit hook refuses new ones")


def engine_integrity(root: Path, verify) -> Iterator[Finding]:
    if not (root / ENGINE_DIR / "manifest.json").is_file():
        return
    try:
        problems = verify(root)
    except Exception as exc:  # malformed manifest: report, keep going
        problems = [f"engine manifest unusable: {exc}"]
    for problem in problems:
        yield Finding("E-ENGINE-HASH", ENGINE_DIR.as_posix(), problem)


def memlog(root: Path, parse) -> Iterator[Finding]:
    path = root / MEMLOG_FILE
    sink: list[Finding] = []
    text = read_text(path, root, sink) if path.is_file() else None
    yield from sink
    seen: set[str] = set()
    for entry in parse(text) if text is not None else []:
        if not entry.header_ok:
            yield Finding("E-MEMLOG", MEMLOG_FILE.as_posix(), f"line {entry.line}: malformed header [{entry.id}]")
        if entry.id in seen:
            yield Finding("E-MEMLOG", MEMLOG_FILE.as_posix(), f"line {entry.line}: duplicate id {entry.id}")
        seen.add(entry.id)


def blocked(root: Path) -> Iterator[Finding]:
    evidence = root / "docs/_cgspec/06-evidence"
    count = 0
    for path in sorted(evidence.rglob("*.json")) if evidence.is_dir() else []:
        data, findings = load_json(path, root, "test-pair" if path.parent.name == "tests" else "evidence")
        yield from findings
        if isinstance(data, dict) and data.get("verdict") in ("BLOCKED", "PARTIAL") and data.get("state") != "Stale":
            count += 1
    if count:
        yield Finding("W-BLOCKED", "docs/_cgspec/06-evidence", f"{count} unresolved BLOCKED or PARTIAL results")
