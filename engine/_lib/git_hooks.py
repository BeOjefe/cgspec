"""Git-discovered hook locations; persisted ownership never selects a host path."""

from __future__ import annotations

import subprocess
from pathlib import Path

EVENTS = ("pre-commit", "commit-msg")


def git_out(root: Path, *args: str) -> str | None:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def directory(root: Path) -> tuple[Path | None, str]:
    """Use this checkout's default hooks, including a linked worktree's common dir."""
    top = git_out(root, "rev-parse", "--show-toplevel")
    if top is None or Path(top).resolve() != root.resolve():
        return None, "not a git repository root: git hooks left alone"
    custom = git_out(root, "config", "--get", "core.hooksPath")
    if custom:
        return None, f"core.hooksPath is set to {custom}: git hooks left alone; add the CGSpec call yourself"
    common = git_out(root, "rev-parse", "--git-common-dir")
    if not common:
        return None, "cannot locate git common directory: git hooks left alone"
    base = (root / common).resolve()
    hooks = base / "hooks"
    if hooks.is_symlink():
        return None, "git hooks directory is a symlink: git hooks left alone"
    return hooks, ""


def owned_names(record: dict) -> list[str]:
    """Legacy paths provide event names only; never open or resolve their targets."""
    names = set()
    for key in ("git_hooks", "git_abs", "git"):
        entries = record.get(key, [])
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, str):
                continue
            name = entry if key == "git_hooks" else Path(entry).name
            if name in EVENTS and (key != "git" or entry == f".git/hooks/{name}"):
                names.add(name)
    return [name for name in EVENTS if name in names]


def migrate(root: Path, record: dict, template: str, hook: str) -> list[str]:
    """Retain ownership only for exact installed scripts in the current Git directory."""
    if not any(key in record for key in ("git_abs", "git")):
        return []
    hooks, reason = directory(root)
    names = []
    if hooks is not None:
        for name in owned_names(record):
            path = hooks / name
            if path.is_file() and not path.is_symlink() and path.read_text() == template.format(hook=hook, event=name):
                names.append(name)
    record["git_hooks"] = names
    record.pop("git_abs", None)
    record.pop("git", None)
    return [reason or "migrated Git hook ownership to current repository event names; stored paths were not followed"]


def remove(root: Path, record: dict, template: str, hook: str) -> list[str]:
    names = owned_names(record)
    if not names:
        return []
    hooks, reason = directory(root)
    if hooks is None:
        return [reason]
    notes = []
    for name in names:
        path = hooks / name
        if path.is_symlink():
            notes.append(f"kept symlinked git {name} hook")
        elif path.is_file():
            if path.read_text(errors="replace") == template.format(hook=hook, event=name):
                path.unlink()
            else:
                notes.append(f"kept modified git {name} hook; remove the CGSpec call manually")
    return notes
