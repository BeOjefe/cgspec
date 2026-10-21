"""Bounded stop retries with durable unresolved reasons and a corrupt-checkpoint fallback."""
from __future__ import annotations

import json
from pathlib import Path

from .checkpoint_cmd import load, save
from .common import STATE_DIR, CgspecError, utc_now, write_json

RETRIES = STATE_DIR / "stop-retries.json"
MAX_STOP_BLOCKS = 2


def read_retries(root: Path) -> dict:
    try:
        data = json.loads((root / RETRIES).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write(root: Path, value: dict) -> str:
    try:
        write_json(root / RETRIES, value)
        return ""
    except OSError as exc:
        return f"SAVE FAILED: stop recovery state: {exc}"


def _checkpoint_record(root: Path, record: dict | None) -> str:
    try:
        cp = load(root)
        if record is not None:
            cp["unresolved_stop"] = record
        elif "unresolved_stop" in cp:
            del cp["unresolved_stop"]
        else:
            return ""
        save(root, cp)  # leave semantic cp.updated unchanged
        return ""
    except CgspecError as exc:
        return f"SAVE FAILED: {exc}"


def stop_decision(root: Path, problems: list[str]) -> tuple[bool, str]:
    state = read_retries(root)
    raw = state.get("count", 0)
    count = raw if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0 else 0
    if not problems:
        error = _checkpoint_record(root, None)
        if error:
            return True, error + "; BLOCKED: recovery state was not cleared"
        error = _write(root, {"count": 0, "updated": utc_now()})
        return True, error
    record = {"at": utc_now(), "problems": problems}
    if count >= MAX_STOP_BLOCKS:
        error = _checkpoint_record(root, record)
        fallback = {"count": 0, "updated": utc_now(), "unresolved_stop": record}
        save_error = _write(root, fallback)
        message = "Ending with unresolved items; report them to the user as BLOCKED:\n- " + "\n- ".join(problems)
        return True, "\n".join(p for p in (message, error, save_error) if p)
    # Retain prior escape diagnostics until clean, including during a new retry cycle.
    state.update(count=count + 1, updated=utc_now())
    error = _write(root, state)
    if error:
        return True, error + "; BLOCKED: cannot persist retry state\n- " + "\n- ".join(problems)
    return False, "Not done yet (CGSpec stop check):\n- " + "\n- ".join(problems)
