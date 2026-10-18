"""session-start pack, session-check and the stop gate (spec 8 lifecycle, spec 9 resume)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .common import MEMLOG_FILE, STATE_DIR, read_json, utc_now, write_json

RETRIES = STATE_DIR / "stop-retries.json"
MAX_STOP_BLOCKS = 2
LEDGER_TIME = re.compile(r"^### \[[^\]]+\] (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)", re.M)


def _load(root: Path, rel) -> dict:
    try:
        data = json.loads((root / rel).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def last_ledger(root: Path, count: int = 5) -> list[str]:
    path = root / MEMLOG_FILE
    if not path.is_file():
        return []
    heads = [l for l in path.read_text(encoding="utf-8", errors="replace").splitlines() if l.startswith("### [")]
    return heads[-count:]


def pack(root: Path, doctor_summary: str) -> str:
    cp = _load(root, STATE_DIR / "checkpoint.json")
    tier = _load(root, STATE_DIR / "tier.json").get("active")
    quota = _load(root, STATE_DIR / "quota.json")
    lines = ["CGSpec session pack (read docs/_cgspec/01-engine/CONTRACT.md before acting)",
             f"goal: {cp.get('goal') or '(not set)'}",
             "stages: " + (", ".join(f"{k}: {v}" for k, v in cp.get("stages", {}).items()) or "(none yet)"),
             f"next action: {cp.get('next_action') or '(none)'}",
             f"in flight: {cp.get('in_flight') or 'nothing'}",
             f"active tier: {tier['tier'] + ' ' + tier['id'] + ' - ' + tier['reason'] if tier else 'none'}"]
    if cp.get("open_issues"):
        lines.append("open issues: " + "; ".join(cp["open_issues"]))
    if quota.get("source") and quota.get("source") != "unavailable":
        five = quota.get("five_hour", {}).get("used_pct")
        week = quota.get("weekly", {}).get("used_pct")
        lines.append(f"quota used: 5h {five}%, weekly {week}% (read {quota.get('read_at')})")
    else:
        lines.append("quota: no reading available; work in bounded mode (spec 9)")
    lines.append("recent ledger:")
    lines += [f"  {l}" for l in last_ledger(root)] or ["  (empty)"]
    lines.append(f"doctor: {doctor_summary}")
    return "\n".join(lines)


def stop_problems(root: Path, doctor_errors: int) -> list[str]:
    problems = []
    if doctor_errors:
        problems.append(f"doctor reports {doctor_errors} errors; fix them or record a BLOCKED result")
    cp = _load(root, STATE_DIR / "checkpoint.json")
    if cp.get("in_flight"):
        problems.append(f"work still in flight: {cp['in_flight']}; finish it or clear in_flight in the checkpoint")
    path = root / MEMLOG_FILE
    if path.is_file():
        times = LEDGER_TIME.findall(path.read_text(encoding="utf-8", errors="replace"))
        if times and cp.get("updated", "") < max(times):
            problems.append("checkpoint is older than the latest ledger entry; update 07-state/checkpoint.json")
    return problems


def stop_decision(root: Path, problems: list[str]) -> tuple[bool, str]:
    """(allow, message). Blocks at most MAX_STOP_BLOCKS times in a row, then lets the agent end."""
    state = _load(root, RETRIES)
    if not problems:
        write_json(root / RETRIES, {"count": 0, "updated": utc_now()})
        return True, ""
    count = int(state.get("count", 0))
    if count >= MAX_STOP_BLOCKS:
        write_json(root / RETRIES, {"count": 0, "updated": utc_now()})
        return True, ("Ending with unresolved items; report them to the user as BLOCKED:\n- " + "\n- ".join(problems))
    write_json(root / RETRIES, {"count": count + 1, "updated": utc_now()})
    return False, "Not done yet (CGSpec stop check):\n- " + "\n- ".join(problems)
