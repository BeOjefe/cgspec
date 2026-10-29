"""Copy CGSpec's skills into a project for hosts that read workspace skills instead of plugins
(Antigravity: <project>/.agents/skills/). Links are rewritten to the installed engine and to a copy of the
method docs, so the skills work without the plugin. Lab finding 2026-10-19: Antigravity agents had
the contract but none of the method's skills."""

from __future__ import annotations

import os
import re
import shutil
import hashlib
from pathlib import Path

from .common import CgspecError

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


def _sources(plugin: Path, dest_base: Path) -> list[tuple[Path, Path]]:
    skills, docs = plugin / "skills", plugin / "docs"
    if not skills.is_dir():
        return []
    sources = [(p, dest_base / p.relative_to(skills)) for p in skills.rglob("*") if p.is_file()]
    sources += [(docs / "METHOD.md", dest_base / DOCS / "METHOD.md")] if (docs / "METHOD.md").is_file() else []
    research = docs / "_cgspec/02-research"
    sources += [(p, dest_base / DOCS / p.relative_to(docs)) for p in research.glob("*.md")] if research.is_dir() else []
    return [(src, dest) for src, dest in sources if "__pycache__" not in src.parts and src.suffix != ".pyc"]


def _content(src: Path, dest: Path, plugin: Path, root: Path, dest_base: Path) -> bytes:
    if src.suffix == ".md":
        return _rewrite(src.read_text(encoding="utf-8"), src.resolve(), dest, plugin.resolve(), root,
                        dest_base).encode("utf-8")
    return src.read_bytes()


def install(root: Path, plugin: Path, rel_base: str = ".agents/skills") -> list[str]:
    """Write the skills and method docs; return the project-relative files written."""
    dest_base = root / rel_base
    written = []
    sources = _sources(plugin, dest_base)
    for src, dest in sources:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(_content(src, dest, plugin, root, dest_base))
        written.append(dest.relative_to(root).as_posix())
    return written


def refresh(root: Path, plugin: Path, owned: list[str], rel_base: str = ".agents/skills") -> tuple[list[str], int]:
    """Refresh owned copies, archiving old bytes first; never replace an unrelated workspace skill."""
    dest_base = root / rel_base
    sources = _sources(plugin, dest_base)
    if not sources:
        raise CgspecError("CGSpec plugin has no skills to refresh")
    expected = {dest.relative_to(root).as_posix() for _, dest in sources}
    for rel in owned:
        path = root / rel
        if (Path(rel).is_absolute() or ".." in Path(rel).parts or not Path(rel).is_relative_to(Path(rel_base))
                or path.is_symlink() or not path.resolve().is_relative_to(root.resolve())):
            raise CgspecError(f"unsafe owned Antigravity skill path: {rel}")
    for _, dest in sources:
        if dest.exists() and dest.relative_to(root).as_posix() not in owned:
            raise CgspecError(f"unowned Antigravity skill blocks update: {dest.relative_to(root)}")
        if dest.is_symlink() or not dest.resolve().is_relative_to(root.resolve()):
            raise CgspecError(f"unsafe Antigravity skill path: {dest.relative_to(root)}")
    backup_count = 0

    def archive(path: Path) -> None:
        nonlocal backup_count
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        rel = path.relative_to(root)
        backup = root / "docs/_cgspec/_archive/agent-skills" / digest / rel
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            shutil.copyfile(path, backup)
            backup_count += 1

    for rel in owned:
        path = root / rel
        if rel not in expected and path.is_file():
            archive(path)
            path.unlink()
    for src, dest in sources:
        data = _content(src, dest, plugin, root, dest_base)
        if dest.is_file() and dest.read_bytes() == data:
            continue
        if dest.is_file():
            archive(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    return sorted(expected), backup_count


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
