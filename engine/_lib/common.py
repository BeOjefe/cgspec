"""Paths, hashing, time and atomic JSON helpers shared by every engine script."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CGSPEC_DIR = Path("docs/_cgspec")
PROJECT_FILE = CGSPEC_DIR / "project.json"
ENGINE_DIR = CGSPEC_DIR / "01-engine"
CHECKS_DIR = CGSPEC_DIR / "04-checks"
RUNS_DIR = CGSPEC_DIR / "05-runs"
EVIDENCE_DIR = CGSPEC_DIR / "06-evidence"
STATE_DIR = CGSPEC_DIR / "07-state"
MEMLOG_FILE = Path("docs/_memlog.md")

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_BLOCK = 2
EXIT_INTERNAL = 3


class CgspecError(Exception):
    """A user-facing error with a clear message; scripts print it and exit non-zero."""


def find_root(start: Path | None = None) -> Path:
    """Return the nearest directory at or above `start` holding docs/_cgspec/project.json."""
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / PROJECT_FILE).is_file():
            return candidate
    raise CgspecError(f"no {PROJECT_FILE} found at or above {here}")


def resolve_root(raw: str | None) -> Path:
    if raw:
        root = Path(raw).resolve()
        if not root.is_dir():
            raise CgspecError(f"root does not exist or is not a directory: {root}")
        return root
    return find_root()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def new_id(prefix: str) -> str:
    """IDs like M-20261018-a3f9: date plus 4 random hex, safe across branches and repos."""
    return f"{prefix}-{today_compact()}-{secrets.token_hex(2)}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise CgspecError(f"missing file: {path}") from None
    except json.JSONDecodeError as exc:
        raise CgspecError(f"invalid JSON in {path}: line {exc.lineno}: {exc.msg}") from None


def atomic_write_text(path: Path, text: str) -> None:
    """Write via a temp file and rename, keeping the original file mode if it existed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o7777 if path.exists() else None
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        if mode is not None:
            os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def write_json(path: Path, data: Any) -> None:
    atomic_write_text(path, json.dumps(data, indent=2, sort_keys=False, ensure_ascii=False) + "\n")


def rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()
