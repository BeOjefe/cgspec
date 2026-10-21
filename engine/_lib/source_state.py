"""Bounded, partial worktree context for recovery. Never proof of tested or staged bytes."""
from __future__ import annotations

import hashlib
import os
import stat
import subprocess
import tempfile
from pathlib import Path

from .common import ENGINE_DIR, PROJECT_FILE, STATE_DIR, utc_now
from .layout import SKIP_WALK

MAX_FILES = 200
MAX_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024
MAX_OUTPUT = 2 * 1024 * 1024
VOLATILE = {str(STATE_DIR / f) for f in ("checkpoint.json", "stop-retries.json", "budget.json",
                                       "quota.json", "approvals.json")}
VOLATILE |= {"docs/00-INBOX.md", "docs/.memlog.lock", "docs/_cgspec/07-state/.state.lock"}
EXCLUDED = sorted(VOLATILE | {f"**/{name}/**" for name in SKIP_WALK})


def _git(root: Path, *args: str) -> bytes:
    # File-backed output bounds memory even when status encounters a very large index.
    with tempfile.TemporaryFile() as output:
        result = subprocess.run(["git", "--no-optional-locks", *args], cwd=root,
                                stdout=output, stderr=subprocess.DEVNULL, timeout=2)
        if result.returncode:
            raise OSError("Git information unavailable")
        output.seek(0)
        raw = output.read(MAX_OUTPUT + 1)
        if len(raw) > MAX_OUTPUT:
            raise OSError("Git output exceeded capture limit")
        return raw


def _sensitive(path: str) -> bool:
    return any(part.lower().startswith(".env") or any(s in part.lower() for s in ("secret", "credential"))
               or part.lower().endswith((".pem", ".key", ".p12", ".pfx")) for part in Path(path).parts)


def _excluded(path: str) -> bool:
    return path.rstrip("/") in VOLATILE or bool(set(Path(path).parts) & SKIP_WALK)


def _digest(root: Path, rel: str, budget: list[int]) -> tuple[str | None, str | None]:
    path = root / rel
    try:
        if any(parent.is_symlink() for parent in (path, *path.parents) if parent != root):
            return None, "symlink not read"
        if not path.resolve().is_relative_to(root.resolve()):
            return None, "outside checkout not read"
        if not path.exists():
            return None, None  # deletion
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
        with os.fdopen(fd, "rb") as handle:
            before = os.fstat(handle.fileno())
            if not stat.S_ISREG(before.st_mode):
                return None, "non-regular file not read"
            if before.st_size > MAX_BYTES or before.st_size > budget[0]:
                return None, "hash byte limit"
            raw = handle.read(min(MAX_BYTES, budget[0]) + 1)
            budget[0] -= len(raw)
            after = os.fstat(handle.fileno())
        if len(raw) > MAX_BYTES or len(raw) != before.st_size or before.st_mtime_ns != after.st_mtime_ns:
            return None, "file changed during capture"
        return hashlib.sha256(raw).hexdigest(), None
    except OSError:
        return None, "unreadable file"


def _paths(raw: bytes) -> list[tuple[str, str]]:
    records, paths, i = raw.decode("utf-8").split("\0"), [], 0
    while i < len(records) and records[i]:
        status, path = records[i][:2], records[i][3:]
        paths.append((path, status))
        if "R" in status or "C" in status:
            i += 1
            if i < len(records) and records[i]:
                paths.append((records[i], "D "))
        i += 1
    return sorted(paths)


def _entries(root: Path, raw: bytes, result: dict, budget: list[int]) -> None:
    paths = [(p, s) for p, s in _paths(raw) if not _excluded(p)]
    if len(paths) > MAX_FILES:
        result["gaps"].append(f"path count limit; {len(paths) - MAX_FILES} entries omitted")
    sensitive = 0
    for path, status in paths[:MAX_FILES]:
        if _sensitive(path):
            sensitive += 1
            continue
        entry = {"path": path, "status": status, "sha256": None}
        digest, reason = (None, "untracked directory not enumerated") if path.endswith("/") else _digest(root, path, budget)
        entry["sha256"] = digest
        if reason:
            entry["reason"] = reason
            result["gaps"].append(reason)
        result["entries"].append(entry)
    if sensitive:
        result["gaps"].append(f"{sensitive} sensitive-named paths omitted without names or hashes")


def observe(root: Path) -> dict:
    result = {"observed_at": utc_now(), "head": None, "branch": None, "entries": [],
              "complete": False, "gaps": [], "excluded": EXCLUDED, "identity": {}}
    budget = [MAX_TOTAL_BYTES]
    for label, path in (("project_sha256", PROJECT_FILE), ("engine_manifest_sha256", ENGINE_DIR / "manifest.json")):
        digest, reason = _digest(root, path.as_posix(), budget)
        result["identity"][label] = digest
        if digest is None:
            result["gaps"].append(f"{label} unavailable: {reason or 'missing'}")
    try:
        # Normal untracked mode never walks every file in an untracked directory.
        raw = _git(root, "status", "--porcelain=v1", "-z", "--untracked-files=normal")
        _entries(root, raw, result, budget)
        result["head"] = _git(root, "rev-parse", "--verify", "HEAD").decode().strip()
        result["branch"] = _git(root, "rev-parse", "--abbrev-ref", "HEAD").decode().strip()
    except (OSError, subprocess.TimeoutExpired, UnicodeError):
        result["gaps"].append("Git information unavailable or capture limit reached")
    result["gaps"] = sorted(set(result["gaps"]))
    result["complete"] = not result["gaps"]
    return result


def comparison(root: Path, saved: dict | None) -> list[str]:
    if not saved:
        return ["source observation unavailable; recover and capture before substantial work"]
    current = observe(root)
    changes = [key for key in ("head", "branch", "identity") if current[key] != saved.get(key)]
    old = {e["path"]: e for e in saved.get("entries", [])}
    new = {e["path"]: e for e in current["entries"]}
    changes += [p for p in sorted(old.keys() | new.keys()) if old.get(p) != new.get(p)]
    lines = []
    if changes:
        lines.append("changed since capture: " + "; ".join(changes[:10]) + (f"; {len(changes)-10} more" if len(changes) > 10 else ""))
    if not current["complete"] or not saved.get("complete"):
        lines.append("source observation PARTIAL; inspect before resuming writes: " + "; ".join(current["gaps"] or saved.get("gaps", [])))
    if not changes and current["complete"] and saved.get("complete"):
        lines.append("source observation unchanged (worktree context only; not tested/staged-byte evidence)")
    return lines
