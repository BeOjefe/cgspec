"""Copy CGSpec's skills into a project for hosts that read workspace skills instead of plugins
(Antigravity: <project>/.agents/skills/). Links are rewritten to the installed engine and to a copy of the
method docs, so the skills work without the plugin. Lab finding 2026-10-19: Antigravity agents had
the contract but none of the method's skills."""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

LINK = re.compile(r"(\]\()([^)\s#]+)(#[^)]*)?\)")
DOCS = "_cgspec-docs"


def _target(plugin: Path, root: Path, dest_base: Path, resolved: Path) -> Path | None:
    for src, dst in ((plugin / "engine", root / "docs/_cgspec/01-engine"), (plugin / "docs", dest_base / DOCS),
                     (plugin / "skills", dest_base)):
        try:
            return dst / resolved.relative_to(src)
        except ValueError:
            continue
    return None


def _rewrite(text: str, src_file: Path, dest_file: Path, plugin: Path, root: Path, dest_base: Path) -> str:
    def fix(m):
        ref = m.group(2)
        if re.match(r"^[a-z][a-z0-9+.-]*:", ref, re.I):
            return m.group(0)
        new = _target(plugin, root, dest_base, (src_file.parent / ref).resolve())
        if new is None:
            return m.group(0)
        return f"{m.group(1)}{os.path.relpath(new, dest_file.parent).replace(os.sep, '/')}{m.group(3) or ''})"
    return LINK.sub(fix, text)


def install(root: Path, plugin: Path, rel_base: str = ".agents/skills") -> list[str]:
    """Write the skills and method docs; return the project-relative files written."""
    skills, docs = plugin / "skills", plugin / "docs"
    if not skills.is_dir():
        return []
    dest_base = root / rel_base
    written = []
    sources = [(p, dest_base / p.relative_to(skills)) for p in skills.rglob("*") if p.is_file()]
    sources += [(docs / "METHOD-v2.md", dest_base / DOCS / "METHOD-v2.md")] if (docs / "METHOD-v2.md").is_file() else []
    research = docs / "_cgspec/02-research"
    sources += [(p, dest_base / DOCS / p.relative_to(docs)) for p in research.glob("*.md")] if research.is_dir() else []
    for src, dest in sources:
        if "__pycache__" in src.parts or src.suffix == ".pyc":
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix == ".md":
            dest.write_text(_rewrite(src.read_text(encoding="utf-8"), src.resolve(), dest, plugin.resolve(), root,
                                     dest_base), encoding="utf-8")
        else:
            shutil.copyfile(src, dest)
        written.append(dest.relative_to(root).as_posix())
    return written


def uninstall(root: Path, files: list[str]) -> None:
    for rel in files:
        path = root / rel
        if path.is_file() and not path.is_symlink():
            path.unlink()
    for rel in sorted({str(Path(f).parent) for f in files}, key=len, reverse=True):
        for parent in [root / rel, *(root / rel).parents]:
            if parent == root:
                break
            try:
                parent.rmdir()
            except OSError:
                break
