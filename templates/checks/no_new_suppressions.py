#!/usr/bin/env python3
"""Fail when a suppression JSON list grows relative to the engine's trusted base revision.

Registered with --applies-to naming the baseline file(s); the engine passes the changed baseline paths.
The base comes only from the engine: CGSPEC_BASE_REV (HEAD at commit time, the trusted range base in CI)
read from the repository at CGSPEC_REPO_ROOT. The candidate is the file in the working directory the
engine runs the check in (the staged snapshot at commit time, the checked-out HEAD in CI). A baseline
absent at the base counts as empty. Exit 0 did not grow, 1 grew, 2 cannot compare.
"""
from __future__ import annotations

import json
import os
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


def at_base(repo: str, base: str, rel: str) -> str | None:
    """File text at the base revision, or None when the file did not exist there."""
    git = ["git", "-C", repo]
    if subprocess.run(git + ["rev-parse", "--verify", "--quiet", f"{base}^{{commit}}"],
                      capture_output=True).returncode != 0:
        raise ValueError(f"base revision {base!r} is not a commit in {repo}")
    if subprocess.run(git + ["cat-file", "-e", f"{base}:{rel}"], capture_output=True).returncode != 0:
        return None
    return subprocess.run(git + ["show", f"{base}:{rel}"], check=True, capture_output=True, text=True).stdout


def main(argv: list[str]) -> int:
    base, repo = os.environ.get("CGSPEC_BASE_REV", ""), os.environ.get("CGSPEC_REPO_ROOT", "")
    if len(argv) < 2:
        print("usage: no_new_suppressions.py <baseline.json>...", file=sys.stderr)
        return 2
    if not base or not repo:
        print("CGSPEC_BASE_REV and CGSPEC_REPO_ROOT are not set; run this as a registered CGSpec check",
              file=sys.stderr)
        return 2
    grew = False
    for raw in argv[1:]:
        rel = Path(raw).as_posix()
        try:
            old = at_base(repo, base, rel)
            before = Counter(entries(json.loads(old))) if old is not None else Counter()
            after = Counter(entries(json.loads(Path(rel).read_text(encoding="utf-8"))))
        except (OSError, ValueError, subprocess.CalledProcessError) as exc:
            print(f"cannot compare suppression baseline {rel}: {exc}", file=sys.stderr)
            return 2
        added = after - before
        if added:
            count = sum(added.values())
            print(f"{rel}: {count} suppression entr{'y' if count == 1 else 'ies'} added or changed; "
                  "tolerated errors may only shrink")
            grew = True
        else:
            print(f"{rel}: suppression baseline did not grow")
    return 1 if grew else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
