#!/usr/bin/env python3
"""Fail when a suppression JSON list grows relative to a Git revision."""
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path


def entries(value, location="$", output=None):
    output = output if output is not None else []
    if isinstance(value, list):
        output.extend((location, json.dumps(item, sort_keys=True, separators=(",", ":"))) for item in value)
        return output
    if isinstance(value, dict):
        # Common linter baselines map files or rules to lists of tolerated entries.
        if any(isinstance(item, (dict, list)) for item in value.values()):
            for key, item in sorted(value.items()):
                entries(item, f"{location}/{key}", output)
        else:
            output.extend((f"{location}/{key}", json.dumps(item, sort_keys=True, separators=(",", ":")))
                          for key, item in sorted(value.items()))
        return output
    raise ValueError("baseline must be a JSON object or array")


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3):
        print("usage: no_new_suppressions.py <baseline.json> [base-revision]", file=sys.stderr)
        return 2
    path = Path(argv[1])
    base = argv[2] if len(argv) == 3 else "HEAD"
    try:
        old = subprocess.run(["git", "show", f"{base}:{path.as_posix()}"], check=True,
                             capture_output=True, text=True).stdout
        before = Counter(entries(json.loads(old)))
        after = Counter(entries(json.loads(path.read_text(encoding="utf-8"))))
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"cannot compare suppression baseline: {exc}", file=sys.stderr)
        return 2
    added = after - before
    if added:
        count = sum(added.values())
        print(f"{count} suppression entr{'y' if count == 1 else 'ies'} added or changed; tolerated errors may only shrink")
        return 1
    print("suppression baseline did not grow")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
