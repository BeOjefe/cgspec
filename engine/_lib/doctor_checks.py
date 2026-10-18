"""The individual checks doctor.py runs. Each yields Finding objects; none writes anything."""

from __future__ import annotations

import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from . import layout as L
from .common import ENGINE_DIR, MEMLOG_FILE, STATE_DIR, sha256_file
from .schema import validate_named

LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
CODE_SPAN = re.compile(r"`[^`\n]*`")
FENCE = re.compile(r"^```.*?^```", re.S | re.M)
STATUS = re.compile(r"^\s*[-*]?\s*\*{0,2}Status:?\*{0,2}:?\s*(.+?)\s*$", re.M | re.I)


@dataclass
class Finding:
    code: str
    path: str
    message: str

    @property
    def is_error(self) -> bool:
        return self.code.startswith("E-")


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _load_json(path: Path, root: Path, schema: str | None) -> tuple[object | None, list[Finding]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [Finding("E-SCHEMA", _rel(path, root), f"unreadable JSON: {exc}")]
    if schema is None:
        return data, []
    errors = validate_named(data, schema)
    return data, [Finding("E-SCHEMA", _rel(path, root), e) for e in errors]


def project(root: Path, data: dict | None) -> Iterator[Finding]:
    if data is None:
        yield Finding("E-LAYOUT-MISSING", "docs/_cgspec/project.json", "version marker missing")
        return
    for error in validate_named(data, "project"):
        yield Finding("E-SCHEMA", "docs/_cgspec/project.json", error)


def layout(root: Path, profile: str) -> Iterator[Finding]:
    for rel in L.REQUIRED_FILES:
        if not (root / rel).is_file():
            yield Finding("E-LAYOUT-MISSING", rel, "required file missing")
    dirs = L.REQUIRED_DIRS + (L.GUI_DIRS if profile in L.GUI_PROFILES else [])
    for rel in dirs:
        if not (root / rel).is_dir():
            yield Finding("E-LAYOUT-MISSING", rel, "required folder missing")
    for parent, allowed in (("docs", L.ALLOWED_IN_DOCS), ("docs/_cgspec", L.ALLOWED_IN_CGSPEC)):
        folder = root / parent
        if folder.is_dir():
            for child in sorted(folder.iterdir()):
                if child.name not in allowed:
                    yield Finding("E-LAYOUT-UNKNOWN", _rel(child, root), "not part of the CGSpec layout (spec 2)")
    state = root / STATE_DIR
    if state.is_dir():
        for child in sorted(state.iterdir()):
            if child.name not in L.ALLOWED_STATE_FILES:
                yield Finding("E-LAYOUT-UNKNOWN", _rel(child, root), "unknown state file")
    for spine in L.SPINES:
        if not (root / f"docs/spines/{spine}.md").is_file() and not (root / f"docs/spines/{spine}/INDEX.md").is_file():
            yield Finding("E-LAYOUT-MISSING", f"docs/spines/{spine}.md", "spine missing")


def symlinks(root: Path) -> Iterator[Finding]:
    for path in [root / "docs", root / "AGENTS.md", root / "CLAUDE.md"]:
        if path.is_symlink():
            yield Finding("E-SYMLINK", _rel(path, root), "symlinks are not allowed")
    docs = root / "docs"
    if docs.is_dir():
        for dirpath, dirnames, filenames in os.walk(docs):
            for name in dirnames + filenames:
                full = Path(dirpath) / name
                if full.is_symlink():
                    yield Finding("E-SYMLINK", _rel(full, root), "symlinks are not allowed")


def state_files(root: Path) -> Iterator[Finding]:
    state = root / STATE_DIR
    for name, schema in L.ALLOWED_STATE_FILES.items():
        path = state / name
        if path.is_file() and schema:
            yield from _load_json(path, root, schema)[1]
    manifest = root / "docs/_cgspec/04-checks/manifest.json"
    if manifest.is_file():
        yield from _load_json(manifest, root, "checks-manifest")[1]
    runs = root / "docs/_cgspec/05-runs"
    if runs.is_dir():
        for run in sorted(p for p in runs.iterdir() if p.is_dir()):
            if not re.match(L.RUN_NAME, run.name):
                yield Finding("E-NAME", _rel(run, root), "run folder must be named R-YYYYMMDD-xxxx")
            run_json = run / "run.json"
            if not run_json.is_file():
                yield Finding("E-LAYOUT-MISSING", _rel(run_json, root), "run folder without run.json")
            else:
                data, findings = _load_json(run_json, root, "run")
                yield from findings
                if isinstance(data, dict) and data.get("run_id") not in (None, run.name) and not findings:
                    yield Finding("E-SCHEMA", _rel(run_json, root), "run_id does not match folder name")


def spines(root: Path, stages: dict) -> Iterator[Finding]:
    reached = max((L.STAGES.index(s) for s in stages.values() if s in L.STAGES), default=0)
    for spine in L.SPINES:
        path = root / f"docs/spines/{spine}.md"
        if not path.is_file():
            path = root / f"docs/spines/{spine}/INDEX.md"
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        body = [l for l in text.splitlines() if l.strip() and not l.startswith("#") and L.EMPTY_MARKER not in l]
        empty = L.EMPTY_MARKER in text or len(body) == 0
        if not empty:
            continue
        needed = L.STAGES.index(L.SPINE_REQUIRED_FROM[spine])
        if reached >= needed:
            yield Finding("E-SPINE-EMPTY", _rel(path, root), f"empty, but a part has reached {L.STAGES[reached]}")
        else:
            yield Finding("W-SPINE-EMPTY", _rel(path, root), "still empty (fine at this stage)")


def _markdown_files(root: Path) -> list[Path]:
    docs = root / "docs"
    files = [root / "AGENTS.md", root / "CLAUDE.md"]
    if docs.is_dir():
        files += [p for p in docs.rglob("*.md") if not (root / ENGINE_DIR) in p.parents]
    return [p for p in files if p.is_file() and not p.is_symlink()]


def links(root: Path) -> Iterator[Finding]:
    archive = root / "docs/_cgspec/_archive"
    for path in _markdown_files(root):
        text = FENCE.sub("", path.read_text(encoding="utf-8"))
        text = CODE_SPAN.sub("", text)
        for match in LINK.finditer(text):
            target = match.group(1)
            if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith("#"):
                continue
            file_part = target.split("#", 1)[0]
            resolved = (path.parent / file_part).resolve()
            if not resolved.exists():
                code = "W-LINK" if archive in path.parents else "E-LINK"
                yield Finding(code, _rel(path, root), f"broken link: {target}")


def records(root: Path) -> Iterator[Finding]:
    groups = [("docs/adrs", L.ADR_NAME, L.DECISION_STATUSES), ("docs/slices", L.SLICE_NAME, L.SLICE_STATUSES)]
    for folder, pattern, statuses in groups:
        base = root / folder
        if not base.is_dir():
            continue
        numbers: dict[str, str] = {}
        for path in sorted(base.iterdir()):
            if path.name == ".gitkeep" or path.is_dir():
                continue
            name_match = re.match(pattern, path.name)
            if not name_match:
                yield Finding("E-NAME", _rel(path, root), f"name must match {pattern}")
                continue
            number = name_match.group(1)
            if number != "draft":
                if number in numbers:
                    yield Finding("E-ID-DUP", _rel(path, root), f"number {number} also used by {numbers[number]}")
                numbers[number] = path.name
            status = STATUS.search(path.read_text(encoding="utf-8"))
            if not status:
                yield Finding("E-STATUS", _rel(path, root), "no Status line")
            elif status.group(1).strip("* ") not in statuses:
                yield Finding("E-STATUS", _rel(path, root), f"status '{status.group(1)}' not in {statuses}")
    research = root / "docs/_cgspec/02-research"
    if research.is_dir():
        for path in research.iterdir():
            if path.is_file() and path.name != ".gitkeep" and not re.match(L.RES_NAME, path.name):
                yield Finding("E-NAME", _rel(path, root), f"name must match {L.RES_NAME}")
    councils = root / "docs/_cgspec/03-councils"
    if councils.is_dir():
        for path in councils.iterdir():
            if path.name != ".gitkeep" and not (path.is_dir() and re.match(L.COUNCIL_NAME, path.name)):
                yield Finding("E-NAME", _rel(path, root), f"name must match {L.COUNCIL_NAME}")


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
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    targets = {m.group(1).split("#")[0] for m in LINK.finditer(CODE_SPAN.sub("", text))}
    for rel in indexed_records(root):
        if rel not in targets and rel.rstrip("/") not in targets:
            yield Finding("E-INDEX-MISSING", f"docs/{rel}", "not listed in docs/00-INDEX.md (doctor --fix adds it)")
    for target in sorted(targets):
        if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or not target:
            continue
        if not (root / "docs" / target).exists():
            yield Finding("E-INDEX-ORPHAN", "docs/00-INDEX.md", f"lists {target}, which does not exist")


def frozen(root: Path) -> Iterator[Finding]:
    path = root / STATE_DIR / "frozen.json"
    if not path.is_file():
        return
    data, findings = _load_json(path, root, "frozen")
    if findings or not isinstance(data, dict):
        return
    for entry in data["entries"]:
        target = root / entry["path"]
        if not target.is_file():
            yield Finding("E-FROZEN-MISSING", entry["path"], "frozen file is gone")
        elif sha256_file(target) != entry["sha256"]:
            yield Finding("E-FROZEN-HASH", entry["path"], "frozen file was changed")
        elif target.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
            yield Finding("W-FROZEN-WRITABLE", entry["path"], "frozen file is writable; doctor --fix makes it read-only")


def scripts(root: Path) -> Iterator[Finding]:
    manifest_path = root / "docs/_cgspec/04-checks/manifest.json"
    registered: dict[str, str] = {}
    if manifest_path.is_file():
        data, findings = _load_json(manifest_path, root, "checks-manifest")
        if not findings and isinstance(data, dict):
            registered = {c["path"]: c["sha256"] for c in data["checks"]}
    for rel, digest in registered.items():
        target = root / rel
        if not target.is_file():
            yield Finding("E-CHECK-MISSING", rel, "registered check is missing")
        elif sha256_file(target) != digest:
            yield Finding("E-CHECK-HASH", rel, "registered check changed since approval")
    docs = root / "docs"
    engine = root / ENGINE_DIR
    if not docs.is_dir():
        return
    for path in sorted(docs.rglob("*")):
        if not path.is_file() or path.suffix not in L.SCRIPT_SUFFIXES or engine in path.parents:
            continue
        rel = _rel(path, root)
        if rel not in registered:
            yield Finding("E-SCRIPT-UNREGISTERED", rel, "scripts in docs/ must be registered checks (spec 8)")


def engine_integrity(root: Path, verify) -> Iterator[Finding]:
    if not (root / ENGINE_DIR / "manifest.json").is_file():
        return
    for problem in verify(root):
        yield Finding("E-ENGINE-HASH", ENGINE_DIR.as_posix(), problem)


def memlog(root: Path, parse) -> Iterator[Finding]:
    path = root / MEMLOG_FILE
    if not path.is_file():
        return
    seen: set[str] = set()
    for entry in parse(path.read_text(encoding="utf-8")):
        if not entry.header_ok:
            yield Finding("E-MEMLOG", MEMLOG_FILE.as_posix(), f"line {entry.line}: malformed header [{entry.id}]")
        if entry.id in seen:
            yield Finding("E-MEMLOG", MEMLOG_FILE.as_posix(), f"line {entry.line}: duplicate id {entry.id}")
        seen.add(entry.id)


def blocked(root: Path) -> Iterator[Finding]:
    evidence = root / "docs/_cgspec/06-evidence"
    count = 0
    if evidence.is_dir():
        for path in evidence.rglob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                yield Finding("E-SCHEMA", _rel(path, root), "unreadable evidence JSON")
                continue
            schema = "test-pair" if path.parent.name == "tests" else "evidence"
            for error in validate_named(data, schema):
                yield Finding("E-SCHEMA", _rel(path, root), error)
            if isinstance(data, dict) and data.get("verdict") in ("BLOCKED", "PARTIAL") and data.get("state") != "Stale":
                count += 1
    if count:
        yield Finding("W-BLOCKED", "docs/_cgspec/06-evidence", f"{count} unresolved BLOCKED or PARTIAL results")
