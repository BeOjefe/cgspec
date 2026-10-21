"""Validated updates of the existing checkpoint; never replace damaged state with defaults."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .common import STATE_DIR, CgspecError, read_json, utc_now, write_json
from .schema import validate_named

CMD = "python3 docs/_cgspec/01-engine/cgspec_hook.py checkpoint"
PATCH_KEYS = {"goal", "stages", "constraints", "revision", "evidence_done", "pending",
              "open_issues", "owners", "next_action", "in_flight", "wakeup"}


def load(root: Path) -> dict:
    path = root / STATE_DIR / "checkpoint.json"
    try:
        cp = read_json(path)
    except (OSError, CgspecError) as exc:
        raise CgspecError(f"checkpoint preserved; cannot read {path}: {exc}") from None
    errors = validate_named(cp, "checkpoint")
    if errors:
        raise CgspecError("checkpoint preserved; repair invalid saved state explicitly: " + "; ".join(errors))
    return cp


def save(root: Path, cp: dict) -> None:
    errors = validate_named(cp, "checkpoint")
    if errors:
        raise CgspecError("checkpoint preserved; invalid update: " + "; ".join(errors))
    try:
        write_json(root / STATE_DIR / "checkpoint.json", cp)
    except OSError as exc:
        raise CgspecError(f"checkpoint save failed: {exc}") from None


def _patch(raw: str | None) -> dict:
    if raw is None:
        return {}
    try:
        data = json.loads(sys.stdin.read() if raw == "-" else Path(raw).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CgspecError(f"cannot read checkpoint patch: {exc}") from None
    if not isinstance(data, dict) or set(data) - PATCH_KEYS:
        raise CgspecError("checkpoint patch must be an object with supported semantic fields only")
    return data


def add_arguments(parser) -> None:
    parser.add_argument("--next", help="checkpoint: the next action")
    transition = parser.add_mutually_exclusive_group()
    transition.add_argument("--in-flight", dest="in_flight", help="checkpoint: work started")
    transition.add_argument("--done", action="store_true", help="checkpoint: clear in-flight note only")
    transition.add_argument("--blocked", help="checkpoint: record why the current batch cannot finish")
    parser.add_argument("--goal", help="checkpoint: the primary goal")
    parser.add_argument("--update-file", help="checkpoint: shallow object replacement patch; '-' reads stdin")
    parser.add_argument("--capture", action="store_true", help="checkpoint: bounded source observation, not test evidence")


def update(root: Path, args) -> dict:
    cp = load(root)
    patch = _patch(args.update_file)
    fields = {"goal": args.goal, "next_action": args.next, "in_flight": args.in_flight}
    conflicts = set(patch) & {key for key, value in fields.items() if value is not None}
    if (args.done or args.blocked is not None) and "in_flight" in patch:
        conflicts.add("in_flight")
    if conflicts:
        raise CgspecError("checkpoint patch conflicts with flags: " + ", ".join(sorted(conflicts)))
    if not (patch or any(value is not None for value in fields.values()) or args.done
            or args.blocked is not None or args.capture):
        raise CgspecError(f"usage: {CMD} --next '...' | --update-file <path|-> | --capture")
    cp.update(patch)
    for key, value in fields.items():
        if value is not None:
            cp[key] = value.strip()
    if args.done or args.blocked is not None:
        cp["in_flight"] = None
    if args.blocked is not None:
        cp["open_issues"] = cp.get("open_issues", []) + [f"BLOCKED {utc_now()[:10]}: {args.blocked.strip()}"]
    if patch or any(value is not None for value in fields.values()) or args.done or args.blocked is not None:
        cp["updated"] = utc_now()
    if args.capture:
        from .source_state import observe
        cp["source"] = observe(root)
    save(root, cp)
    return cp


def capture_only(root: Path) -> None:
    """Mechanical pre-compaction capture never advances the semantic checkpoint timestamp."""
    from .source_state import observe
    cp = load(root)
    cp["source"] = observe(root)
    save(root, cp)
