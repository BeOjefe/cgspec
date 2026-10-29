"""Command-line parsing for run lifecycle operations."""

from __future__ import annotations

import json
from pathlib import Path

from .common import CgspecError


def _freeze(root: Path, args) -> int:
    from .runs import freeze_run
    goal = getattr(args, "goal", None) or (args.rest[1] if len(args.rest) > 1 else "Task run")
    tier = getattr(args, "tier", None) or "T1"
    crit = [p.strip() for p in (getattr(args, "criteria", "") or "").split(",") if p.strip()]
    tests = [p.strip() for p in (getattr(args, "tests", "") or "").split(",") if p.strip()]
    units_raw = getattr(args, "units", None)
    units = json.loads(units_raw) if isinstance(units_raw, str) else (units_raw or [])
    freeze_run(root, goal, tier, crit, tests, units,
               run_id=getattr(args, "run_id", None), slice_id=getattr(args, "slice", None),
               approval_ref=getattr(args, "approval", None),
               outcomes=([p.strip() for p in args.outcomes.split(",") if p.strip()]
                         if getattr(args, "outcomes", None) is not None else None),
               proof_paths=[p.strip() for p in (getattr(args, "proofs", "") or "").split(",") if p.strip()],
               supersession=json.loads(args.supersession) if getattr(args, "supersession", None) else None)
    return 0


def _show(root: Path, args) -> int:
    from .runs import load_runs_with_errors
    runs, errors = load_runs_with_errors(root)
    target = (args.rest[1:2] or [getattr(args, "run_id", None)])[0]
    if target:
        for _, data in runs:
            if data.get("run_id") == target:
                print(json.dumps(data, indent=2))
                return 0
        if any(target in error for error in errors):
            raise CgspecError(f"run {target} is malformed")
        raise CgspecError(f"run {target} not found")
    if runs:
        print(json.dumps([data for _, data in runs], indent=2))
        return 0
    if errors:
        raise CgspecError(f"runs directory contains errors: {'; '.join(errors)}")
    print("no runs found")
    return 0


def dispatch(root: Path, args) -> int:
    """Dispatch a run CLI subcommand."""
    from .runs import complete_run, supersede_run, update_unit_status
    action = (args.rest[:1] or [""])[0]
    if action == "freeze":
        return _freeze(root, args)
    if action == "show":
        return _show(root, args)
    target = (args.rest[1:2] or [getattr(args, "run_id", None)])[0]
    if action == "complete" and target:
        complete_run(root, target)
        return 0
    if action == "supersede" and target:
        by = getattr(args, "by", None) or (args.rest[2] if len(args.rest) > 2 else None)
        if not by:
            raise CgspecError("usage: cgspec_hook.py run supersede <run_id> --by <new_run_id>")
        supersede_run(root, target, by)
        return 0
    if action == "update-unit" and target:
        uid, status = getattr(args, "unit", None), getattr(args, "unit_status", None)
        if not uid or not status:
            raise CgspecError("usage: cgspec_hook.py run update-unit <run_id> --unit <id> --unit-status <status>")
        update_unit_status(root, target, uid, status, review_rounds=getattr(args, "review_rounds", None))
        return 0
    raise CgspecError("usage: cgspec_hook.py run freeze|show|complete|supersede|update-unit ...")
