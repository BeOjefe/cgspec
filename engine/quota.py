#!/usr/bin/env python3
"""Read current provider quota safety advice; this command never fetches or writes usage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib.common import CgspecError, resolve_root  # noqa: E402
from _lib.quota import snapshot, summary  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = snapshot(resolve_root(args.root))
    except CgspecError as exc:
        print(f"quota: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result) if args.json else summary(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
