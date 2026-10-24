#!/usr/bin/env python3
"""Fail when checked files introduce unlinked TODO, FIXME, HACK, or XXX placeholders.

Every deferred comment in production code must cite a tracked record (for example TODO(SLICE-004) or TODO(ADR-002)).
Exit 0 when all markers are linked (or none exist), 1 when an unlinked marker is found, 2 on usage/read error.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

MARKER_RE = re.compile(r"(?://|#|\*|--)\s*(TODO|FIXME|HACK|XXX)\b(.*)$")
LINKED_RE = re.compile(r"^\s*\((?:[a-z0-9_-]+:)?(?:SLICE|ADR|RES|CHK|ISSUE|#)-?[A-Za-z0-9_-]+\)\s*:")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: no_deferred_todos.py <file>...", file=sys.stderr)
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
            match = MARKER_RE.search(line)
            if not match:
                continue
            tag, rest = match.group(1), match.group(2)
            if not LINKED_RE.match(rest):
                failures.append(
                    f"{target.as_posix()}:{idx}: unlinked {tag} comment; "
                    f"either finish the work now or link it to a record such as {tag}(SLICE-001): reason"
                )
    for item in failures:
        print(item)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
