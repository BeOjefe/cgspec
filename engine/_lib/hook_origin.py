"""Authenticate command-hook stdin using OS peer identity, not caller-supplied JSON.

Claude's native and Node launchers connect hook stdin directly to the host. Shell
pipelines, redirects and Python imports cannot manufacture that host-owned channel.
The installed host executable/launcher and the hook code must remain trusted.
"""

from __future__ import annotations

import os
import json
from pathlib import Path
import re
import shlex
import socket
import struct
import subprocess
import sys

from .common import CgspecError

HOST_RECORD = Path(__file__).resolve().parents[1] / "owned-files.json"


def _windows_peer_and_image(fd: int) -> tuple[int, Path]:
    import ctypes
    from ctypes import wintypes
    import msvcrt
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetNamedPipeServerProcessId.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.ULONG)]
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                                ctypes.POINTER(wintypes.DWORD)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    pid = wintypes.ULONG()
    if not kernel.GetNamedPipeServerProcessId(msvcrt.get_osfhandle(fd), ctypes.byref(pid)):
        raise OSError("stdin has no host pipe peer")
    handle = kernel.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        raise OSError("cannot inspect stdin peer")
    try:
        size = wintypes.DWORD(32768)
        name = ctypes.create_unicode_buffer(size.value)
        if not kernel.QueryFullProcessImageNameW(handle, 0, name, ctypes.byref(size)):
            raise OSError("cannot identify stdin peer")
        return pid.value, Path(name.value).resolve()
    finally:
        kernel.CloseHandle(handle)


def _peer_and_image(fd: int) -> tuple[int, Path]:
    if sys.platform == "win32":
        return _windows_peer_and_image(fd)
    # fromfd duplicates the descriptor; closing it must not close the hook's stdin.
    with socket.fromfd(fd, socket.AF_UNIX, socket.SOCK_STREAM) as channel:
        if sys.platform.startswith("linux"):
            pid, uid, _ = struct.unpack("3i", channel.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
            if uid != os.getuid():
                raise OSError("stdin peer belongs to another user")
            image = Path(os.readlink(f"/proc/{pid}/exe")).resolve()
        elif sys.platform == "darwin":
            # Darwin sys/un.h: SOL_LOCAL=0, LOCAL_PEERPID=2.
            pid = channel.getsockopt(0, 2)
            image = Path(subprocess.check_output(["/bin/ps", "-p", str(pid), "-o", "comm="],
                                                text=True, timeout=5).strip()).resolve()
        else:
            raise OSError("host stdin peer identity is unavailable on this platform")
    if pid <= 0:
        raise OSError("stdin peer is no longer running")
    return pid, image


def _claude_launcher() -> Path:
    # Installation/upgrade is the trust bootstrap, not a capture caller's PATH.
    # The engine-owned record is protected with the installed engine itself.
    try:
        owned = json.loads(HOST_RECORD.read_text(encoding="utf-8"))
        command = owned["adapters"]["claude"]["launcher"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise OSError("Claude launcher is not pinned; upgrade the installed CGSpec hooks") from exc
    if not isinstance(command, str) or not Path(command).is_absolute():
        raise OSError("Claude launcher is not pinned; install CGSpec with Claude available")
    launcher = Path(command).resolve(strict=True)
    if launcher.suffix.lower() == ".cmd":  # npm's Windows shim
        script = launcher.parent / "node_modules/@anthropic-ai/claude-code/cli.js"
        if script.is_file():
            return script.resolve(strict=True)
    # Also support thin shell launchers without evaluating shell code. Native
    # versioned installs are already resolved through their claude symlink.
    with launcher.open("rb") as handle:
        header = handle.read(4096)
    if header.startswith(b"#!/bin/sh") or header.startswith(b"#!/bin/bash"):
        for line in header.decode("utf-8").splitlines():
            words = shlex.split(line)
            if len(words) == 3 and words[0] == "exec" and words[2] == "$@" and Path(words[1]).is_absolute():
                return Path(words[1]).resolve(strict=True)
    return launcher


def _process_args(pid: int) -> list[str]:
    if sys.platform.startswith("linux"):
        return Path(f"/proc/{pid}/cmdline").read_bytes().decode().split("\0")
    if sys.platform == "darwin":
        return shlex.split(subprocess.check_output(["/bin/ps", "-p", str(pid), "-o", "args="],
                                                  text=True, timeout=5))
    raw = subprocess.check_output(["powershell.exe", "-NoProfile", "-Command",
                                   f"(Get-CimInstance Win32_Process -Filter 'ProcessId = {int(pid)}').CommandLine"],
                                  text=True, timeout=5)
    return [arg.strip('"') for arg in shlex.split(raw, posix=False)]


def require_claude_stdin() -> None:
    """Fail closed unless stdin comes from the installed Claude host process.

    UUIDs, environment flags and hook_event_name alone are forgeable. This check
    is deliberately at the reader, so a direct inbox.record import cannot supply
    a fabricated prompt even while inheriting a host's unrelated stdin channel.
    """
    try:
        pid, image = _peer_and_image(sys.stdin.fileno())
        launcher = _claude_launcher()
        if image == launcher:
            return
        # Auto-update can move the launcher symlink while an older host is still
        # running. Both images must belong to the same trusted native versions dir.
        if (image.parent == launcher.parent and launcher.parent.parts[-2:] == ("claude", "versions") and
                all(re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][\w.-]+)?", p.name) for p in (image, launcher))):
            return
        # npm's claude is a JS script executed by Node, rather than a native image.
        if image.name.lower() in {"node", "nodejs", "node.exe"} and launcher.name == "cli.js":
            args = _process_args(pid)
            script = args[2] if args[1:2] == ["--"] and len(args) > 2 else (args[1] if len(args) > 1 else "")
            if script and Path(script).is_absolute() and Path(script).resolve() == launcher:
                return
        raise OSError("stdin peer is not the installed Claude host")
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise CgspecError(f"approval capture requires Claude's actual UserPromptSubmit stdin ({exc}); "
                          "do not replay user-message from a shell") from exc
