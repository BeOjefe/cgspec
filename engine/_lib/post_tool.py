"""post-tool hook (spec 8): mark evidence covering changed files stale, count helper agents."""

from __future__ import annotations

import json
from pathlib import Path

from .common import EVIDENCE_DIR, STATE_DIR, write_json
from .globs import match_any

HELPER_TOOLS = {"Task", "Agent"}


def mark_stale(root: Path, changed: list[str]) -> list[str]:
    stale = []
    folder = root / EVIDENCE_DIR
    for path in sorted(folder.rglob("*.json")) if folder.is_dir() else []:
        if path.parent.name == "tests":
            continue  # failing-test proofs are history, not freshness claims
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        covers = data.get("covers") if isinstance(data, dict) else None
        if not covers or data.get("state") == "Stale":
            continue
        if any(match_any(rel, covers) for rel in changed):
            data["state"] = "Stale"
            write_json(path, data)
            stale.append(path.relative_to(root).as_posix())
    return stale


def count_helper(root: Path) -> str | None:
    """Increment budget.used.helpers; return a warning when the limit is passed."""
    path = root / STATE_DIR / "budget.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    used, limits = data.get("used", {}), data.get("limits", {})
    used["helpers"] = int(used.get("helpers", 0)) + 1
    write_json(path, data)
    if used["helpers"] > int(limits.get("helpers", 0)):
        return (f"CGSpec budget: {used['helpers']} helper agents used, limit {limits.get('helpers')} for "
                f"{data.get('task')}; stop starting helpers and report, or ask to raise the limit")
    return None
