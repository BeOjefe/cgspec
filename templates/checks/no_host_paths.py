#!/usr/bin/env python3
"""Fail when checked files contain hardcoded workstation/host paths (/home/<user>/, /Users/<user>/, C:\\Users\\<user>\\).

Registered with --applies-to naming source or config globs. Exit 0 when clean, 1 on hardcoded host paths, 2 on error.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HOST_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:"
    r"/home/[A-Za-z0-9_.-]+/"
    r"|/Users/[A-Za-z0-9_.-]+/"
    r"|[A-Za-z]:\\\\Users\\\\[A-Za-z0-9_.-]+\\\\"
    r"|[A-Za-z]:\\Users\\[A-Za-z0-9_.-]+\\"
    r")"
)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: no_host_paths.py <file>...", file=sys.stderr)
        return 2
    failures = []
    for raw in argv[1:]:
        target = Path(raw)
        if not target.is_file():
            continue
        try:
            lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as exc:
            print(f"cannot read {raw}: {exc}", file=sys.stderr)
            return 2
        for idx, line in enumerate(lines, start=1):
            if "cgspec:test-fixture" in line:
                continue
            match = HOST_PATH_RE.search(line)
            if match:
                failures.append(
                    f"{target.as_posix()}:{idx}: hardcoded host path '{match.group(0)}'; "
                    "use project-relative paths or environment variables"
                )
    for item in failures:
        print(item)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
