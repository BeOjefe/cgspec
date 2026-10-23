"""Git-discovered hook locations; persisted ownership never selects a host path."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .common import CgspecError

EVENTS = ("pre-commit", "commit-msg")

_REPO_SELECTORS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_COMMON_DIR",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_GRAFT_FILE",
    "GIT_NAMESPACE",
    "GIT_PREFIX",
    "GIT_CONFIG",
)


def git_env() -> dict[str, str]:
    """Pass process config (e.g. GIT_CONFIG_*) but drop repo selection overrides."""
    env = os.environ.copy()
    for var in _REPO_SELECTORS:
        env.pop(var, None)
    return env


def git_out(root: Path, *args: str) -> str | None:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, env=git_env())
    return result.stdout.strip() if result.returncode == 0 else None


def git_config_get(root: Path, key: str) -> str | None:
    """Return configured value preserving whitespace, or None if unset."""
    result = subprocess.run(["git", "config", "--get", key], cwd=root, capture_output=True, text=True, env=git_env())
    if result.returncode != 0:
        return None
    val = result.stdout
    return val[:-1] if val.endswith(chr(10)) else val


def has_symlink(path: Path) -> bool:
    """Check if any component in the uncanonicalized path is a symlink."""
    parts = path.parts
    if not parts:
        return False
    cur = Path(parts[0]) if path.is_absolute() else Path(".")
    for part in parts[1 if path.is_absolute() else 0:]:
        cur = cur / part
        try:
            if cur.is_symlink() and cur not in (Path("/var"), Path("/tmp"), Path("/etc")):
                return True
        except OSError:
            return True
    return False


def _gitfile_problem(root: Path, dot_git: Path) -> str | None:
    """Why a `.git` file's worktree pointers cannot be trusted, or None when they belong here."""
    try:
        content = dot_git.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return "cannot read git metadata file: git hooks left alone"
    if not content.startswith("gitdir:"):
        return "invalid gitdir pointer in .git file: git hooks left alone"
    raw_gitdir = content[len("gitdir:"):].strip()
    gitdir_path = Path(raw_gitdir)
    if not gitdir_path.is_absolute():
        gitdir_path = root / gitdir_path
    if has_symlink(gitdir_path):
        return "git metadata path contains a symlink: git hooks left alone"
    commondir_file = gitdir_path / "commondir"
    if commondir_file.is_symlink():
        return "git metadata path contains a symlink: git hooks left alone"
    if commondir_file.is_file():
        try:
            raw_common = commondir_file.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            return "cannot read git commondir file: git hooks left alone"
        common_path = Path(raw_common)
        if not common_path.is_absolute():
            common_path = gitdir_path / common_path
        if has_symlink(common_path):
            return "git metadata path contains a symlink: git hooks left alone"
        gitdir_back = gitdir_path / "gitdir"
        if gitdir_back.is_symlink():
            return "git metadata path contains a symlink: git hooks left alone"
        if not gitdir_back.is_file():
            return "git worktree back-pointer is missing; run 'git worktree repair': git hooks left alone"
        try:
            raw_back = gitdir_back.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            return "cannot read git worktree back-pointer: git hooks left alone"
        back_path = Path(raw_back)
        if not back_path.is_absolute():
            back_path = gitdir_path / back_path
        if has_symlink(back_path):
            return "git metadata path contains a symlink: git hooks left alone"
        try:
            if back_path.resolve() != dot_git.resolve():
                return "git worktree back-pointer does not belong to this checkout; run 'git worktree repair': git hooks left alone"
        except OSError:
            return "git worktree back-pointer does not belong to this checkout; run 'git worktree repair': git hooks left alone"
    return None


def directory(root: Path) -> tuple[Path | None, str]:
    """Use this checkout's default hooks, including a linked worktree's common dir."""
    dot_git = root / ".git"
    if dot_git.is_symlink():
        return None, "git metadata entry is a symlink: git hooks left alone"
    if not dot_git.exists():
        return None, "not a git repository root: git hooks left alone"

    if dot_git.is_dir():
        commondir_file = dot_git / "commondir"
        if commondir_file.is_symlink() or commondir_file.exists():
            return None, "commondir file inside normal git directory: git hooks left alone"

    if dot_git.is_file():
        problem = _gitfile_problem(root, dot_git)
        if problem:
            return None, problem

    top = git_out(root, "rev-parse", "--show-toplevel")
    if top is None or Path(top).resolve() != root.resolve():
        return None, "not a git repository root: git hooks left alone"
    custom = git_config_get(root, "core.hooksPath")
    if custom is not None:
        return None, f"core.hooksPath is set to {custom}: git hooks left alone"
    common = git_out(root, "rev-parse", "--git-common-dir")
    if not common:
        return None, "cannot locate git common directory: git hooks left alone"
    base = Path(common)
    if not base.is_absolute():
        base = root / base
    if has_symlink(base):
        return None, "git metadata path contains a symlink: git hooks left alone"
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


def migrate(root: Path, record: dict, template: str = "", hook: str = "") -> list[str]:
    """Migrate legacy Git hook ownership to event names without inspecting current files."""
    if not any(key in record for key in ("git_abs", "git")):
        return []
    names = owned_names(record)
    record["git_hooks"] = names
    record.pop("git_abs", None)
    record.pop("git", None)
    return ["migrated Git hook ownership to current repository event names; stored paths were not followed"]


def expected_hook_bytes(template: str, hook: str, event: str) -> bytes:
    """Explicit LF byte encoding for exact hook identity comparison and writing."""
    text = template.format(hook=hook, event=event)
    text = text.replace(chr(13) + chr(10), chr(10)).replace(chr(13), chr(10))
    return text.encode("utf-8")


def remove(root: Path, record: dict, template: str, hook: str) -> list[str]:
    names = owned_names(record)
    if not names:
        return []
    hooks, reason = directory(root)
    if hooks is None:
        raise CgspecError(
            f"owned Git hooks ({', '.join(names)}) cannot be located ({reason}); "
            "uninstall aborted to prevent dangling hooks"
        )
    notes = []
    for name in names:
        path = hooks / name
        if path.is_symlink():
            notes.append(f"kept symlinked git {name} hook")
        elif path.is_file():
            expected = expected_hook_bytes(template, hook, name)
            try:
                actual = path.read_bytes()
            except OSError:
                notes.append(f"kept unreadable git {name} hook; remove the CGSpec call manually")
                continue
            if actual == expected:
                path.unlink()
            else:
                notes.append(f"kept modified git {name} hook; remove the CGSpec call manually")
    return notes
