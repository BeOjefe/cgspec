"""Process-bound hook receipts, with an authenticated witness outside the checkout.

This detects missing hooks and casual file fabrication, not a hostile same-UID process:
the OS account can ultimately read the witness key or impersonate its own host.
No diagnostic command is allowed to create or refresh a receipt.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import stat
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from .common import CgspecError, STATE_DIR, atomic_write_text, write_json

EVENTS = {"session-start": "SessionStart", "pre-tool": "PreToolUse", "post-tool": "PostToolUse",
          "user-message": "UserPromptSubmit", "stop": "Stop", "pre-compact": "PreCompact"}
RECEIPTS = STATE_DIR / "hook-heartbeats"
STALE_SECONDS = 120


@dataclass(frozen=True)
class Host:
    tool: str
    pid: int
    identity: str
    started: float
    direct: bool
    cwd: Path | None = None
    argv: tuple[str, ...] = ()


def _governs(host: Host, root: Path) -> bool:
    if host.cwd is None and not host.argv:
        return True
    root_resolved = root.resolve()
    if host.cwd is not None:
        try:
            if root_resolved == host.cwd or root_resolved.is_relative_to(host.cwd) or host.cwd.is_relative_to(root_resolved):
                return True
        except (ValueError, OSError):
            pass
    root_str = str(root_resolved)
    if any(root_str in arg for arg in host.argv):
        return True
    try:
        exe = Path(host.argv[0])
        if not exe.is_absolute() and host.cwd:
            exe = host.cwd / exe
        if exe.resolve().is_relative_to(root_resolved):
            return True
    except (ValueError, IndexError, OSError):
        pass
    return False


def host_process() -> Host | None:
    """Use kernel ancestry/start ticks, never a caller-supplied PID or timestamp.

    Linux currently supplies verifiable process identity. An explicitly requested
    host check on another platform fails visibly rather than trusting environment IDs.
    """
    try:
        boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        boot_at = next(int(line.split()[1]) for line in Path("/proc/stat").read_text().splitlines()
                       if line.startswith("btime "))
        ticks = os.sysconf("SC_CLK_TCK")
        pid, between = os.getppid(), []
        for _ in range(64):
            proc = Path(f"/proc/{pid}")
            fields = (proc / "stat").read_text().rsplit(")", 1)[1].split()
            argv = (proc / "cmdline").read_bytes().decode(errors="replace").split("\0")
            name = Path(argv[0]).name.lower()
            tool = "antigravity" if name in ("antigravity", "agy") else (name if name == "claude" else None)
            if not tool and name == "node" and len(argv) > 1 and "/claude-code/" in argv[1]:
                tool = "claude"
            if tool:
                identity = hashlib.sha256(f"{boot}:{pid}:{fields[19]}".encode()).hexdigest()
                direct = not between or (len(between) == 1 and between[0] in ("sh", "bash", "dash", "zsh"))
                try:
                    host_cwd = Path(os.readlink(f"/proc/{pid}/cwd")).resolve()
                except OSError:
                    host_cwd = None
                return Host(tool, pid, identity, boot_at + int(fields[19]) / ticks, direct, host_cwd, tuple(argv))
            between.append(name)
            pid = int(fields[1])
            if not pid:
                break
    except (OSError, ValueError, IndexError, StopIteration):
        pass
    return None


def witness_directory(root: Path) -> Path:
    # Ephemeral across reboot is intentional: every reboot changes the host identity.
    project = hashlib.sha256(str(root.resolve()).encode()).hexdigest()
    return Path(tempfile.gettempdir()) / f"cgspec-hook-witness-{os.getuid()}" / project


def _private_dir(path: Path) -> None:
    path.parent.mkdir(mode=0o700, exist_ok=True)
    path.mkdir(mode=0o700, exist_ok=True)
    for folder in (path.parent, path):
        info = folder.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise CgspecError("unsafe hook witness directory")


@contextmanager
def _locked(directory: Path, create: bool = True):
    import fcntl
    _private_dir(directory)
    fd = os.open(directory / "lock", os.O_RDWR | (os.O_CREAT if create else 0) | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "r+") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def _canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _key(directory: Path, create: bool = False) -> bytes:
    path = directory / "key"
    if create and not path.exists():
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(secrets.token_bytes(32))
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as handle:
        info = os.fstat(handle.fileno())
        key = handle.read(33)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or len(key) != 32:
        raise CgspecError("unsafe hook witness key")
    return key


def _read(path: Path) -> dict:
    if path.is_symlink():
        raise CgspecError("symlinked hook receipt or witness")
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError("hook receipt is not an object")
    return value


def _verified(root: Path, host: Host, directory: Path) -> dict:
    anchor = _read(directory / f"{host.identity}.json")
    receipt = _read(root / RECEIPTS / f"{host.identity}.json")
    body = {k: v for k, v in receipt.items() if k != "mac"}
    mac = hmac.new(_key(directory), _canonical(body), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(mac, str(receipt.get("mac", ""))) or receipt != anchor:
        raise CgspecError("hook receipt authentication/witness mismatch")
    if receipt["host"] != host.identity or receipt["event"] not in EVENTS or \
            receipt["pid"] != host.pid or receipt["at"] < host.started or receipt["at"] > time.time() + 5:
        raise CgspecError("hook receipt does not belong to this live process")
    return receipt


def record(root: Path, event: str, tool: str, payload: dict) -> bool:
    """Only called by the six callback dispatch paths, before executing their work.

    Ordinary CLI invocations, mismatched events and nested tool subprocesses cannot
    seed a witness. Payload IDs alone are never evidence that hooks loaded.
    """
    host = host_process()
    if event not in EVENTS or not host or not host.direct or host.tool != tool or \
            payload.get("hook_event_name") != EVENTS[event]:
        return False
    directory = witness_directory(root)
    with _locked(directory):
        anchor = directory / f"{host.identity}.json"
        previous = _verified(root, host, directory) if anchor.exists() else None
        body = {"schema": 1, "host": host.identity, "pid": host.pid, "event": event, "at": time.time(),
                "session_id": payload.get("session_id"), "sequence": previous["sequence"] + 1 if previous else 1,
                "previous": previous["mac"] if previous else None}
        receipt = dict(body, mac=hmac.new(_key(directory, create=True), _canonical(body), hashlib.sha256).hexdigest())
        # Anchor first: interruption is a visible mismatch, never a false healthy check.
        write_json(anchor, receipt)
        target = root / RECEIPTS / f"{host.identity}.json"
        if any(p.is_symlink() for p in (target, *target.parents) if p != root and root in p.parents):
            raise CgspecError("symlinked hook heartbeat path")
        target.parent.mkdir(parents=True, exist_ok=True)
        # Receipts are machine-local, not portable governance evidence for Git/CI.
        ignore = target.parent / ".gitignore"
        if ignore.is_symlink():
            raise CgspecError("symlinked hook heartbeat ignore file")
        if not ignore.exists():
            atomic_write_text(ignore, "*\n")
        write_json(target, receipt)
    return True


def _recent_edits(root: Path, since: float) -> int:
    from .source_state import _git, _paths
    raw = _git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    count = 0
    for rel, status in _paths(raw):
        if rel.startswith(STATE_DIR.as_posix() + "/"):
            continue
        path = root / rel
        # Deletions have no mtime. Count them conservatively in a stale session.
        if "D" in status:
            count += 1
        else:
            try:
                if path.lstat().st_mtime > since:
                    count += 1
            except OSError:
                count += 1
    return count


def problems(root: Path, tool: str = "generic") -> list[str]:
    host = host_process()
    if not host or not _governs(host, root):
        return (["cannot verify hook coverage: no supported live host process (Linux /proc required)"]
                if tool in ("claude", "antigravity") else [])
    elapsed = max(0, int(time.time() - host.started))
    directory = witness_directory(root)
    try:
        # Never create keys, locks, receipts or a witness as a side effect of checking.
        if not directory.is_dir():
            raise FileNotFoundError
        with _locked(directory, create=False):
            receipt = _verified(root, host, directory)
        age = time.time() - receipt["at"]
        if age > STALE_SECONDS:
            edits = _recent_edits(root, receipt["at"])
            if edits:
                return [f"hook heartbeat is {int(age)}s old with {edits} edited/deleted paths since it; "
                        f"host PID {host.pid} has run for {elapsed}s"]
    except FileNotFoundError:
        return [f"no authenticated hook activity for this session (host PID {host.pid}, running {elapsed}s); "
                "a heartbeat file alone is not proof that hooks loaded"]
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired, CgspecError) as exc:
        return [f"hook coverage cannot be verified: {exc}"]
    return []


def report(problems: list[str]) -> str:
    return ("CGSpec HOOK COVERAGE FAILURE: lifecycle gates may be inactive.\n- " + "\n- ".join(problems) +
            "\nStop editing. Relaunch the host from the installed project root, confirm its hook settings load, "
            "then run session-check again. Do not manufacture a heartbeat or use session-check to seed one.")


def session_check(root: Path, tool: str, errors: int, summary: str) -> int:
    from install import verify_engine
    coverage = problems(root, tool)
    if coverage:
        print(report(coverage), file=sys.stderr)
    engine_problems = verify_engine(root)
    print(f"doctor: {summary}" + (f"; engine: {len(engine_problems)} problems" if engine_problems else "; engine OK"))
    host = host_process()
    print("hooks: verified for this live host process" if not coverage and host and _governs(host, root)
          else "hooks: FAILED" if coverage else "hooks: UNVERIFIED (no supported live host ancestor)")
    return 1 if errors or engine_problems or coverage else 0


def read_payload(raw: str) -> dict:
    try:
        data = json.loads(raw) if raw.strip() else {}
        return data if isinstance(data, dict) else {}
    except ValueError:
        return {}


def dispatch(root: Path, args, adapter) -> int:
    """Capture callback stdin once, then forward it unchanged to the entry point's handlers."""
    raw = "" if not sys.stdin or sys.stdin.isatty() else sys.stdin.read()
    try:
        record(root, args.event, args.tool, read_payload(raw))
    except Exception as exc:  # never block a user message or a finished tool
        print(report([f"cannot record hook invocation: {exc}"]), file=sys.stderr)
        if args.event == "pre-tool":
            return adapter.block(args.tool, "CGSpec cannot authenticate hook activity; repair hook coverage before continuing")
    if args.event == "pre-tool":
        return adapter.pre_tool(root, args.tool, raw)
    if args.event == "post-tool":
        return adapter.post_tool(root, args.tool, raw)
    return adapter.lifecycle(root, args.event, args, raw)
