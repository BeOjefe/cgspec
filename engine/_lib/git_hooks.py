"""Git-discovered hook locations; persisted ownership never selects a host path."""

from __future__ import annotations

import os
import stat
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

_DIR_FD_OPS = (os.open, os.unlink, os.stat, os.rename)


def git_env() -> dict[str, str]:
    """Pass process config (e.g. GIT_CONFIG_*) but drop repo selection overrides."""
    env = os.environ.copy()
    for var in _REPO_SELECTORS:
        env.pop(var, None)
    return env


def _rstrip_newline(text: str) -> str:
    """Remove exactly one trailing newline; never touch any other whitespace in the path."""
    return text[:-1] if text.endswith(chr(10)) else text


def git_out(root: Path, *args: str) -> str | None:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, env=git_env())
    return _rstrip_newline(result.stdout) if result.returncode == 0 else None


def git_config_get(root: Path, key: str) -> str | None:
    """Return configured value preserving whitespace, or None if unset."""
    result = subprocess.run(["git", "config", "--get", key], cwd=root, capture_output=True, text=True, env=git_env())
    if result.returncode != 0:
        return None
    return _rstrip_newline(result.stdout)


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


def _read_pointer(path: Path, prefix: str = "") -> str | None:
    """Read a Git metadata file preserving whitespace; strip only the trailing newline and prefix."""
    try:
        content = _rstrip_newline(path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return None
    if prefix:
        if not content.startswith(prefix):
            return None
        return content[len(prefix):]
    return content


def _resolve_pointer(base: Path, raw: str) -> Path:
    target = Path(raw)
    return target if target.is_absolute() else base / target


def _gitfile_problem(root: Path, dot_git: Path) -> tuple[str | None, bool]:
    """Why a `.git` file's worktree pointers cannot be trusted, and whether an ownership
    record is needed because Git's own worktree back-pointer cannot vouch for this checkout."""
    raw_gitdir = _read_pointer(dot_git, prefix="gitdir: ")
    if raw_gitdir is None:
        try:
            dot_git.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return "cannot read git metadata file: git hooks left alone", False
        return "invalid gitdir pointer in .git file: git hooks left alone", False
    gitdir_path = _resolve_pointer(root, raw_gitdir)
    if has_symlink(gitdir_path):
        return "git metadata path contains a symlink: git hooks left alone", False
    commondir_file = gitdir_path / "commondir"
    if commondir_file.is_symlink():
        return "git metadata path contains a symlink: git hooks left alone", False
    if not commondir_file.is_file():
        # A bare separate-git-dir or submodule gitfile: Git gives us no back-pointer to
        # verify against, so an ownership record must bind this hooks dir to this checkout.
        return None, True
    raw_common = _read_pointer(commondir_file)
    if raw_common is None:
        return "cannot read git commondir file: git hooks left alone", False
    common_path = _resolve_pointer(gitdir_path, raw_common)
    if has_symlink(common_path):
        return "git metadata path contains a symlink: git hooks left alone", False
    return _check_worktree_backpointer(gitdir_path, dot_git)


def _check_worktree_backpointer(gitdir_path: Path, dot_git: Path) -> tuple[str | None, bool]:
    gitdir_back = gitdir_path / "gitdir"
    if gitdir_back.is_symlink():
        return "git metadata path contains a symlink: git hooks left alone", False
    if not gitdir_back.is_file():
        return "git worktree back-pointer is missing; run 'git worktree repair': git hooks left alone", False
    raw_back = _read_pointer(gitdir_back)
    if raw_back is None:
        return "cannot read git worktree back-pointer: git hooks left alone", False
    back_path = _resolve_pointer(gitdir_path, raw_back)
    if has_symlink(back_path):
        return "git metadata path contains a symlink: git hooks left alone", False
    try:
        if back_path.resolve() != dot_git.resolve():
            return ("git worktree back-pointer does not belong to this checkout; "
                    "run 'git worktree repair': git hooks left alone", False)
    except OSError:
        return ("git worktree back-pointer does not belong to this checkout; "
                "run 'git worktree repair': git hooks left alone", False)
    return None, False


def directory(root: Path) -> tuple[Path | None, str, bool]:
    """Use this checkout's default hooks, including a linked worktree's common dir.

    The third element is True when the hooks directory's trust rests only on an ownership
    record (a bare separate-git-dir or submodule gitfile), never on Git's own validation.
    """
    dot_git = root / ".git"
    if dot_git.is_symlink():
        return None, "git metadata entry is a symlink: git hooks left alone", False
    if not dot_git.exists():
        return None, "not a git repository root: git hooks left alone", False

    if dot_git.is_dir():
        commondir_file = dot_git / "commondir"
        if commondir_file.is_symlink() or commondir_file.exists():
            return None, "commondir file inside normal git directory: git hooks left alone", False

    needs_owner_record = False
    if dot_git.is_file():
        problem, needs_owner_record = _gitfile_problem(root, dot_git)
        if problem:
            return None, problem, False

    top = git_out(root, "rev-parse", "--show-toplevel")
    if top is None or Path(top).resolve() != root.resolve():
        return None, "not a git repository root: git hooks left alone", False
    custom = git_config_get(root, "core.hooksPath")
    if custom is not None:
        return None, f"core.hooksPath is set to {custom}: git hooks left alone", False
    common = git_out(root, "rev-parse", "--git-common-dir")
    if not common:
        return None, "cannot locate git common directory: git hooks left alone", False
    base = Path(common)
    if not base.is_absolute():
        base = root / base
    if has_symlink(base):
        return None, "git metadata path contains a symlink: git hooks left alone", False
    hooks = base / "hooks"
    if hooks.is_symlink():
        return None, "git hooks directory is a symlink: git hooks left alone", False
    return hooks, "", needs_owner_record


def check_ownership(root: Path, hooks: Path, record: dict) -> str | None:
    """None when this checkout's own record already binds it to this external hooks dir."""
    try:
        current_root = str(root.resolve())
        current_hooks = str(hooks.resolve())
    except OSError:
        return "cannot resolve this checkout's path to verify git hook ownership"
    if record.get("git_owner_root") == current_root and record.get("git_owner_hooks") == current_hooks:
        return None
    return ("this checkout is not confirmed as the owner of a shared git hooks directory "
            "(moved, copied, or never recorded)")


def bind_ownership(root: Path, hooks: Path, record: dict) -> None:
    record["git_owner_root"] = str(root.resolve())
    record["git_owner_hooks"] = str(hooks.resolve())


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


def _dir_fd_supported() -> bool:
    return (hasattr(os, "O_DIRECTORY") and hasattr(os, "O_NOFOLLOW")
            and all(op in os.supports_dir_fd for op in _DIR_FD_OPS))


def open_hooks_dir(hooks: Path) -> int:
    """Open the validated hooks directory once, refusing to follow a symlink. Every later
    unlink/create binds to this exact directory (dir_fd), closing the TOCTOU window."""
    if not _dir_fd_supported():
        raise CgspecError("this platform cannot safely bind git hook operations to a directory: "
                           "git hooks left alone")
    try:
        return os.open(str(hooks), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError as exc:
        raise CgspecError(f"cannot open git hooks directory safely ({exc}): git hooks left alone") from exc


def entry_kind(fd: int, name: str) -> str:
    """'missing', 'symlink', 'file' or 'other', as seen through the bound directory fd."""
    try:
        info = os.stat(name, dir_fd=fd, follow_symlinks=False)
    except OSError:
        return "missing"
    if stat.S_ISLNK(info.st_mode):
        return "symlink"
    if stat.S_ISREG(info.st_mode):
        return "file"
    return "other"


def read_hook(fd: int, name: str) -> bytes | None:
    """Read a regular file's bytes through the bound fd. None when missing or unreadable."""
    try:
        hfd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
    except OSError:
        return None
    try:
        with os.fdopen(hfd, "rb") as handle:
            return handle.read()
    except OSError:
        return None


def unlink_hook(fd: int, name: str) -> None:
    os.unlink(name, dir_fd=fd)


def write_hook(fd: int, name: str, data: bytes, mode: int) -> None:
    """Write atomically via a temp name in the same directory, then rename over the target.
    Never opens the target name itself, so a symlink planted at that name is never followed
    for writing. A no-op when the target already holds these exact bytes."""
    if entry_kind(fd, name) == "file" and read_hook(fd, name) == data:
        return
    tmp = f".{name}.cgspec-tmp-{os.getpid()}"
    try:
        os.unlink(tmp, dir_fd=fd)
    except OSError:
        pass
    tfd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode, dir_fd=fd)
    try:
        with os.fdopen(tfd, "wb") as handle:
            handle.write(data)
        os.chmod(tmp, mode, dir_fd=fd)
    except OSError:
        os.unlink(tmp, dir_fd=fd)
        raise
    os.rename(tmp, name, src_dir_fd=fd, dst_dir_fd=fd)


def _hook_risk(fd: int, name: str, expected: bytes) -> str | None:
    """Why this owned hook cannot be safely deleted: it may still invoke CGSpec once the
    engine is removed."""
    kind = entry_kind(fd, name)
    if kind == "missing":
        return None
    if kind == "symlink":
        return "symlinked"
    actual = read_hook(fd, name)
    if actual is None:
        return "unreadable"
    if actual == expected:
        return None
    return "modified"


def remove(root: Path, record: dict, template: str, hook: str) -> list[str]:
    names = owned_names(record)
    if not names:
        return []
    hooks, reason, needs_owner_record = directory(root)
    if hooks is None:
        raise CgspecError(
            f"owned Git hooks ({', '.join(names)}) cannot be located ({reason}); "
            "uninstall aborted to prevent dangling hooks"
        )
    if needs_owner_record:
        problem = check_ownership(root, hooks, record)
        if problem:
            raise CgspecError(
                f"owned Git hooks ({', '.join(names)}) cannot be verified ({problem}); "
                "uninstall aborted to prevent dangling hooks"
            )
    fd = open_hooks_dir(hooks)
    try:
        return _remove_via_fd(fd, names, template, hook)
    finally:
        os.close(fd)


def _remove_via_fd(fd: int, names: list[str], template: str, hook: str) -> list[str]:
    expected = {name: expected_hook_bytes(template, hook, name) for name in names}
    risky = [f"{name} ({risk})" for name in names if (risk := _hook_risk(fd, name, expected[name]))]
    if risky:
        raise CgspecError(
            f"owned Git hooks were changed and may still call CGSpec after removal ({', '.join(risky)}); "
            "uninstall aborted; remove the CGSpec call from them yourself, then retry"
        )
    removed = [name for name in names if entry_kind(fd, name) == "file"]
    for name in removed:
        unlink_hook(fd, name)
    return [f"removed git {name} hook" for name in removed]
