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
    transition.add_argument("--awaiting", help="checkpoint: stop to ask the user; the batch stays in flight")
    parser.add_argument("--goal", help="checkpoint: the primary goal")
    parser.add_argument("--update-file", help="checkpoint: shallow object replacement patch; '-' reads stdin")
    parser.add_argument("--capture", action="store_true", help="checkpoint: bounded source observation, not test evidence")


def update(root: Path, args) -> dict:
    cp = load(root)
    patch = _patch(args.update_file)
    fields = {"goal": args.goal, "next_action": args.next, "in_flight": args.in_flight}
    conflicts = set(patch) & {key for key, value in fields.items() if value is not None}
    transition = args.done or args.blocked is not None or args.awaiting is not None
    if transition and "in_flight" in patch:
        conflicts.add("in_flight")
    if conflicts:
        raise CgspecError("checkpoint patch conflicts with flags: " + ", ".join(sorted(conflicts)))
    if args.awaiting is not None and not args.awaiting.strip():
        raise CgspecError("--awaiting needs the question you are asking the user")
    if not (patch or any(value is not None for value in fields.values()) or transition or args.capture):
        raise CgspecError(f"usage: {CMD} --next '...' | --update-file <path|-> | --capture")
    flight_before = cp.get("in_flight")
    cp.update(patch)
    for key, value in fields.items():
        if value is not None:
            cp[key] = value.strip()
    if args.done or args.blocked is not None:
        cp["in_flight"] = None
    if args.blocked is not None:
        cp["open_issues"] = cp.get("open_issues", []) + [f"BLOCKED {utc_now()[:10]}: {args.blocked.strip()}"]
    previous = cp.get("awaiting_user") if isinstance(cp.get("awaiting_user"), dict) else None
    if args.awaiting is not None:
        # Asking is a pause, not an end: in_flight is kept, and the question excuses one stop. Rewording a
        # question before any stop replaces it. The count only grows when a new question follows one already
        # put to the user during in-flight work, so a question-before-every-stop pattern is visible; it
        # cannot be prevented, only shown. Nothing is parked: on hosts without a stop check no question is
        # ever marked used, so a parked "unanswered" record would be false.
        count = 1
        if previous is not None and cp.get("in_flight"):
            count = previous.get("count", 1) + (1 if previous.get("used") else 0)
        cp["awaiting_user"] = {"at": utc_now(), "question": args.awaiting.strip(), "used": False, "count": count}
    elif args.done or args.blocked is not None or _flight(cp.get("in_flight")) != _flight(flight_before):
        cp.pop("awaiting_user", None)  # the work moved on, so the question is no longer what we wait for
    if patch or any(value is not None for value in fields.values()) or transition:
        cp["updated"] = utc_now()
    if args.capture:
        from .source_state import observe
        cp["source"] = observe(root)
    save(root, cp)
    return cp


def _flight(value) -> str | None:
    """Compare in_flight the way --in-flight stores it, so a patch with stray spaces is not a new batch."""
    return value.strip() if isinstance(value, str) else value


def capture_only(root: Path) -> None:
    """Mechanical pre-compaction capture never advances the semantic checkpoint timestamp."""
    from .source_state import observe
    cp = load(root)
    cp["source"] = observe(root)
    save(root, cp)
