"""Bounded, nonblocking JSON reads and guarded inventory output writes."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile

MAX_FILE_BYTES = 1024 * 1024


def read_regular_json(path: Path, label: str) -> tuple[object, str]:
    flags = os.O_RDONLY | os.O_NONBLOCK | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, 'rb') as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise ValueError(f'{label} must be a regular file')
        raw = handle.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError(f'{label} exceeds 1 MiB limit')
    return json.loads(raw.decode('utf-8')), hashlib.sha256(raw).hexdigest()


def write_manifest(manifest: dict, output: Path | None, expected_digest: str | None) -> None:
    text = json.dumps(manifest, indent=2, ensure_ascii=False) + '\n'
    if output is None:
        sys.stdout.write(text)
        return
    temp = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=output.parent,
                                         prefix='.cgspec-ingest-', delete=False) as handle:
            temp = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        if expected_digest is None:
            try:
                os.link(temp, output)  # atomic no-replace if another process created it
            except FileExistsError as exc:
                raise ValueError('output appeared during inventory; left it untouched') from exc
        else:
            if output.is_symlink() or not output.is_file():
                raise ValueError('output changed to a non-regular file during inventory')
            previous, current_digest = read_regular_json(output, 'output')
            if (not isinstance(previous, dict) or previous.get('schema_version') != '2.0' or
                    previous.get('approval') != 'unreviewed' or current_digest != expected_digest):
                raise ValueError('output changed during inventory; left it untouched')
            os.replace(temp, output)
    finally:
        if temp and temp.exists():
            temp.unlink()
