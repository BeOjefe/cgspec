#!/usr/bin/env python3
"""Fail the PR when engine/** changed without a strict SemVer bump of engine/VERSION.

Called from .github/workflows/version-bump.yml. Reads the base-ref and head-ref
copies of engine/VERSION from argv, and the list of changed files from stdin
(one path per line, as produced by `git diff --name-only $base...$head`).

Exits 0 when:
- no engine/** files changed, OR
- head VERSION is a strict SemVer bump above base VERSION.

Exits 1 with an explanatory message otherwise.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
# scripts/ -> .github/ -> repo root -> engine/_lib
sys.path.insert(0, str(HERE.parents[2] / "engine"))
from _lib.release import compare_versions, parse_version  # noqa: E402


def changed_engine_files(paths: list[str]) -> list[str]:
    return [p for p in paths if p.startswith("engine/") and p != "engine/VERSION"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-version", required=True)
    parser.add_argument("--head-version", required=True)
    args = parser.parse_args()

    paths = [line.strip() for line in sys.stdin if line.strip()]
    engine_changes = changed_engine_files(paths)

    base = args.base_version.strip()
    head = args.head_version.strip()

    if not engine_changes:
        print(f"OK: no engine/** files changed; VERSION {base} unchanged is fine.")
        return 0

    print(f"engine/** changed ({len(engine_changes)} files):")
    for p in engine_changes[:10]:
        print(f"  - {p}")
    if len(engine_changes) > 10:
        print(f"  ... and {len(engine_changes) - 10} more")

    if parse_version(head) is None:
        print(f"FAIL: engine/VERSION on head ({head!r}) is not a valid SemVer "
              "(e.g. '0.3.1', '1.0.0').")
        return 1

    if parse_version(base) is None:
        # Base is malformed; still require head to strictly dominate.
        print(f"NOTE: base engine/VERSION ({base!r}) is not valid SemVer; "
              "accepting any valid-SemVer head.")
        return 0

    try:
        order = compare_versions(head, base)
    except Exception as exc:
        print(f"FAIL: {exc}")
        return 1

    if order <= 0:
        print(f"FAIL: engine/** changed but engine/VERSION did not advance "
              f"({base} -> {head}). Bump VERSION in this PR.")
        return 1

    print(f"OK: engine/VERSION bumped {base} -> {head}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
