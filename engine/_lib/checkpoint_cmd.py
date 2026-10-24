"""Validated updates of the existing checkpoint; never replace damaged state with defaults."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from .common import STATE_DIR, CgspecError, read_json, utc_now, write_json
from .schema import validate_named

CMD = "python3 docs/_cgspec/01-engine/cgspec_hook.py checkpoint"
PATCH_KEYS = {"goal", "stages", "constraints", "revision", "evidence_done", "pending",
              "open_issues", "owners", "next_action", "in_flight", "wakeup"}
DEFLECTION_RE = re.compile(
    r"\b(pre-?existing|out of scope|not from my changes|defer(?:red)? to later|bigger refactor|unrelated to my)\b",
    re.I,
)
EVIDENCE_REF_RE = re.compile(r"([A-Za-z0-9_./-]+\.[A-Za-z0-9]+|E-[A-Z-]+|SLICE-\d+|ADR-\d+|CHK-\d+|#\d+)")


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
    fields = {"goal", "next_action", "in_flight"}
    flag_map = {"goal": args.goal, "next_action": args.next, "in_flight": args.in_flight}
    conflicts = set(patch) & {key for key in fields if flag_map[key] is not None}
    transition = args.done or args.blocked is not None or args.awaiting is not None
    if transition and "in_flight" in patch:
        conflicts.add("in_flight")
    if conflicts:
        raise CgspecError("checkpoint patch conflicts with flags: " + ", ".join(sorted(conflicts)))
    if args.awaiting is not None and not args.awaiting.strip():
        raise CgspecError("--awaiting needs the question you are asking the user")
    if args.blocked is not None:
        reason = args.blocked.strip()
        if not reason or (DEFLECTION_RE.search(reason) and not EVIDENCE_REF_RE.search(reason)):
            raise CgspecError("--blocked requires a concrete technical reason naming the file, check code or missing input")
    if not (patch or any(v is not None for v in flag_map.values()) or transition or args.capture):
        raise CgspecError(f"usage: {CMD} --next '...' | --update-file <path|-> | --capture")
    flight_before = cp.get("in_flight")
    cp.update(patch)
    for key, value in flag_map.items():
        if value is not None:
            cp[key] = value.strip()
    if args.done or args.blocked is not None:
        cp["in_flight"] = None
    if args.blocked is not None:
        cp["open_issues"] = cp.get("open_issues", []) + [f"BLOCKED {utc_now()[:10]}: {args.blocked.strip()}"]
    previous = cp.get("awaiting_user") if isinstance(cp.get("awaiting_user"), dict) else None
    if args.awaiting is not None:
        count = 1
        if previous is not None and cp.get("in_flight"):
            count = previous.get("count", 1) + (1 if previous.get("used") else 0)
        cp["awaiting_user"] = {"at": utc_now(), "question": args.awaiting.strip(), "used": False, "count": count}
    elif args.done or args.blocked is not None or _flight(cp.get("in_flight")) != _flight(flight_before):
        cp.pop("awaiting_user", None)  # the work moved on, so the question is no longer what we wait for
    if patch or any(v is not None for v in flag_map.values()) or transition:
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
