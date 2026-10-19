"""Plan and verify Git hook wiring for an old-layout adoption."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

from .adapters import GIT_HOOK, HOOK


def _git(root: Path, *args: str) -> str | None:
    done = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else None


def hook_dir(root: Path) -> Path | None:
    top = _git(root, "rev-parse", "--show-toplevel")
    if not top or Path(top).resolve() != root.resolve():
        return None
    if _git(root, "config", "--get", "core.hooksPath"):
        return None
    raw = _git(root, "rev-parse", "--git-path", "hooks")
    if not raw:
        return None
    path = Path(raw)
    path = path if path.is_absolute() else root / path
    if any(p.is_symlink() for p in (path, *path.parents) if p != Path("/")):
        return None
    return path.resolve()


def plan(root: Path, tools: str) -> tuple[list[dict], list[str]]:
    if "git" not in set(tools.split(",")):
        return [], []
    hooks = hook_dir(root)
    if hooks is None:
        return [], ["git hooks unavailable: require a Git repository rooted here without custom hooksPath"]
    out, issues = [], []
    for event in ("pre-commit", "commit-msg"):
        target = hooks / event
        desired = GIT_HOOK.format(hook=HOOK, event=event).encode()
        if target.is_symlink() or (target.exists() and not target.is_file()):
            issues.append(f"git hook target unsafe: {target}")
        elif target.exists() and target.read_bytes() != desired:
            issues.append(f"existing git hook needs reviewed integration: {target}")
        elif target.exists() and not target.stat().st_mode & 0o111:
            issues.append(f"existing git hook is not executable: {target}")
        else:
            out.append({"path": str(target), "event": event,
                        "created": not target.exists(), "sha256": hashlib.sha256(desired).hexdigest(),
                        "mode": (target.stat().st_mode & 0o777) if target.exists() else 0o755})
    return out, issues


def check(root: Path, hooks: list[dict], published: bool) -> list[str]:
    expected_dir = hook_dir(root)
    issues = []
    for item in hooks:
        target = Path(item["path"])
        if expected_dir is None or target.parent != expected_dir or target.is_symlink():
            issues.append(f"git hook path changed: {target}")
            continue
        exists = target.is_file()
        if item["created"] and not published and exists:
            issues.append(f"git hook appeared during upgrade: {target}")
        elif published and (not exists or hashlib.sha256(target.read_bytes()).hexdigest() != item["sha256"]
                            or (target.stat().st_mode & 0o777) != item["mode"]):
            issues.append(f"git hook changed since upgrade: {target}")
        elif not item["created"] and (not exists or hashlib.sha256(target.read_bytes()).hexdigest() != item["sha256"]
                                      or (target.stat().st_mode & 0o777) != item["mode"]):
            issues.append(f"existing git hook changed: {target}")
    return issues


def publish(root: Path, hooks: list[dict]) -> None:
    issues = check(root, hooks, published=False)
    if issues:
        raise ValueError("; ".join(issues))
    for item in hooks:
        if not item["created"]:
            continue
        target = Path(item["path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        desired = GIT_HOOK.format(hook=HOOK, event=item["event"]).encode()
        with target.open("xb") as handle:
            handle.write(desired)
        os.chmod(target, item["mode"])


def rollback(root: Path, hooks: list[dict]) -> list[str]:
    issues = check(root, hooks, published=True)
    if issues:
        return issues
    for item in hooks:
        if item["created"]:
            Path(item["path"]).unlink()
    return []


def check_rollback(root: Path, hooks: list[dict]) -> list[str]:
    expected_dir = hook_dir(root)
    issues = []
    for item in hooks:
        target = Path(item["path"])
        if expected_dir is None or target.parent != expected_dir or target.is_symlink():
            issues.append(f"unsafe git hook path: {target}")
        elif target.exists() and (not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != item["sha256"]
                                  or (target.stat().st_mode & 0o777) != item["mode"]):
            issues.append(f"git hook changed since upgrade: {target}")
        elif not item["created"] and not target.is_file():
            issues.append(f"pre-existing git hook missing: {target}")
    return issues


def remove_created(hooks: list[dict]) -> None:
    for item in hooks:
        if item["created"]:
            Path(item["path"]).unlink(missing_ok=True)
