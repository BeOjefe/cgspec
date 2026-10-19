"""Layout checks against spec section 2 (folders, allowed entries, one level of nesting)."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from . import layout as L
from .common import STATE_DIR
from .findings import Finding, rel as _rel


def layout(root: Path, profile: str) -> Iterator[Finding]:
    for rel in L.REQUIRED_FILES:
        if not (root / rel).is_file():
            yield Finding("E-LAYOUT-MISSING", rel, "required file missing")
    for rel in L.REQUIRED_DIRS + (L.GUI_DIRS if profile in L.GUI_PROFILES else []):
        if not (root / rel).is_dir():
            yield Finding("E-LAYOUT-MISSING", rel, "required folder missing")
    for parent, allowed in (("docs", L.ALLOWED_IN_DOCS), ("docs/_cgspec", L.ALLOWED_IN_CGSPEC),
                            (STATE_DIR.as_posix(), set(L.ALLOWED_STATE_FILES))):
        folder = root / parent
        if folder.is_dir():
            for child in sorted(folder.iterdir()):
                if child.name not in allowed:
                    yield Finding("E-LAYOUT-UNKNOWN", _rel(child, root), "not part of the CGSpec layout (spec 2)")
    yield from _nested(root)
    for spine in L.SPINES:
        if not (root / f"docs/spines/{spine}.md").is_file() and not (root / f"docs/spines/{spine}/INDEX.md").is_file():
            yield Finding("E-LAYOUT-MISSING", f"docs/spines/{spine}.md", "spine missing")


def _nested(root: Path) -> Iterator[Finding]:
    """One level deeper: flat record folders, known spines, snapshots as plain HTML files."""
    for folder in ("docs/adrs", "docs/slices", "docs/_cgspec/02-research", "docs/_cgspec/04-checks"):
        base = root / folder
        if base.is_dir():
            for child in base.iterdir():
                if child.is_dir():
                    yield Finding("E-LAYOUT-UNKNOWN", _rel(child, root), "this folder must stay flat")
    spines = root / "docs/spines"
    if spines.is_dir():
        known = set(L.SPINES) | {f"{s}.md" for s in L.SPINES}
        for child in spines.iterdir():
            if child.name not in known:
                yield Finding("E-LAYOUT-UNKNOWN", _rel(child, root), f"spines are {', '.join(L.SPINES)}")
    snaps = root / "docs/prototypes/_snapshots"
    if snaps.is_dir():
        for child in snaps.iterdir():
            if child.is_dir() or (child.name != ".gitkeep" and child.suffix.lower() != ".html"):
                yield Finding("E-LAYOUT-UNKNOWN", _rel(child, root), "snapshots are single .html files")
    protos = root / "docs/prototypes"
    for child in protos.iterdir() if protos.is_dir() else []:
        if child.is_file() and child.name != ".gitkeep":
            yield Finding("E-LAYOUT-UNKNOWN", _rel(child, root), "prototype files live in a screen folder")
    evidence = root / "docs/_cgspec/06-evidence"
    for child in evidence.rglob("*") if evidence.is_dir() else []:
        if child.is_file() and child.name != ".gitkeep" and child.suffix.lower() != ".json":
            yield Finding("E-LAYOUT-UNKNOWN", _rel(child, root), "evidence records are .json files")
