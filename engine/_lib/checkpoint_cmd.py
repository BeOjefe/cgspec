"""`cgspec_hook.py checkpoint`: update 07-state/checkpoint.json without hand-writing JSON (lab finding:
weak agents broke the schema editing it by hand to satisfy the stop check)."""

from __future__ import annotations

import json
from pathlib import Path

from .common import STATE_DIR, CgspecError, utc_now, write_json

CMD = "python3 docs/_cgspec/01-engine/cgspec_hook.py checkpoint"


def update(root: Path, args) -> dict:
    path = root / STATE_DIR / "checkpoint.json"
    try:
        cp = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cp = {}
    cp.setdefault("schema", 1)
    cp.setdefault("goal", "")
    cp.setdefault("stages", {})
    cp.setdefault("next_action", "")
    cp.setdefault("in_flight", None)
    if not any([args.next, args.in_flight, args.done, args.blocked, args.goal]):
        raise CgspecError(f"usage: {CMD} [--next '...'] [--in-flight '...' | --done | --blocked 'why'] [--goal '...']")
    if args.goal:
        cp["goal"] = args.goal.strip()
    if args.next:
        cp["next_action"] = args.next.strip()
    if args.in_flight:
        cp["in_flight"] = args.in_flight.strip()
    if args.done:
        cp["in_flight"] = None
    if args.blocked:
        issues = [i for i in cp.get("open_issues", []) if isinstance(i, str)]
        issues.append(f"BLOCKED {utc_now()[:10]}: {args.blocked.strip()}")
        cp["open_issues"] = issues[-20:]
        cp["in_flight"] = None
    cp["updated"] = utc_now()
    write_json(path, cp)
    return cp
