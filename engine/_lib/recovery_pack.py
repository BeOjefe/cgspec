"""Bounded checkpoint context; full detail remains in the canonical state files."""
from __future__ import annotations

from pathlib import Path

from .checkpoint_cmd import load
from .common import CgspecError
from .source_state import comparison
from .stop_state import read_retries

LIMIT = 5


def _items(label: str, values) -> list[str]:
    if not values:
        return []
    if isinstance(values, dict):
        values = [f"{key}: {value}" for key, value in values.items()]
    return [label + ": " + "; ".join(str(value)[:300] for value in values[:LIMIT])
            + (f"; {len(values)-LIMIT} more in checkpoint.json" if len(values) > LIMIT else "")]


def context(root: Path) -> tuple[dict, list[str]]:
    try:
        cp = load(root)
    except CgspecError as exc:
        cp, lines = {}, [f"recovery gap: {exc}"]
    else:
        lines = []
    missing = [key for key in ("constraints", "revision", "evidence_done", "pending", "owners") if key not in cp]
    if missing:
        lines.append("recovery fields not recorded: " + ", ".join(missing))
    for key in ("constraints", "revision", "evidence_done", "pending", "owners", "wakeup"):
        value = cp.get(key)
        lines += _items(key, [value] if isinstance(value, str) else value)
    stop = cp.get("unresolved_stop") or read_retries(root).get("unresolved_stop")
    if isinstance(stop, dict):
        lines += _items("UNRESOLVED previous stop", stop.get("problems", []))
    lines += comparison(root, cp.get("source"))
    return cp, lines
