"""Verifiable hook provenance for inbox approvals.

Approvals in approvals.json authorize changes only when backed by genuine hook
activity, not handwritten JSON entries or direct agent tool invocations.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .common import STATE_DIR


def session_activity_problem(root: Path, session_id: str, captured_ns: int) -> str | None:
    heartbeats_dir = root / STATE_DIR / "hook-heartbeats"
    if heartbeats_dir.is_dir():
        receipts = []
        for path in heartbeats_dir.glob("*.json"):
            if not path.is_symlink():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    if isinstance(data, dict):
                        receipts.append(data)
                except (OSError, ValueError):
                    pass
        if receipts:
            matching = [r for r in receipts if r.get("session_id") == session_id]
            if not matching:
                return f"has no verified hook activity for session '{session_id}'"
            captured_s = captured_ns / 1e9
            times = [r["at"] for r in matching if isinstance(r.get("at"), (int, float))]
            if times and (captured_s < min(times) - 60 or captured_s > max(times) + 60):
                return "has capture time outside recorded hook activity"
    return None


def replay_problem(view, entry: dict) -> str | None:
    from .commit_trust import APPROVALS, load
    session_id = entry.get("session_id")
    captured_ns = entry.get("captured_ns")
    if not session_id or not captured_ns:
        return None
    key = (session_id, captured_ns)
    # Check within the candidate approvals.json
    new_entries = load(view.read_new(APPROVALS)).get("approvals", [])
    count = sum(isinstance(other, dict) and (other.get("session_id"), other.get("captured_ns")) == key
                for other in new_entries)
    if count > 1:
        return "replays a hook event already recorded as another approval"
    # Check within committed parent history
    if view.old:
        old_entries = load(view.read_old(APPROVALS)).get("approvals", [])
        if any(isinstance(old, dict) and old.get("id") != entry.get("id") and
               (old.get("session_id"), old.get("captured_ns")) == key for old in old_entries):
            return "replays a hook event already recorded in parent history"
    return None


def approval_provenance_problem(view, entry: dict) -> str | None:
    if not isinstance(entry, dict):
        return "is not a valid approval record"
    session_id = entry.get("session_id")
    if not isinstance(session_id, str) or not session_id.strip():
        return "has no verified hook session provenance; use the human signed-trailer path"
    captured_ns = entry.get("captured_ns")
    if not isinstance(captured_ns, int) or captured_ns <= 0:
        return "has invalid hook capture timestamp"
    excerpt = entry.get("excerpt")
    sha256 = entry.get("sha256")
    if not isinstance(excerpt, str) or not isinstance(sha256, str) or sha256 != hashlib.sha256(excerpt.encode()).hexdigest():
        return "has mismatched hook message digest"
    replay = replay_problem(view, entry)
    if replay:
        return replay
    activity = session_activity_problem(view.root, session_id, captured_ns)
    if activity:
        return activity
    return None


def commit_msg_problem(root: Path, text: str) -> str | None:
    """Check staged provenance now; local post-commit, pre-push, and CI check the signature."""
    from . import commit_trust as trust
    from .gitview import View
    view = View.staged(root)
    problems = trust.approvals_have_inbox_lines(view)
    if problems:
        return "CGSpec: " + "; ".join(problems)
    if trust.TRAILER.search(text):
        return None
    if trust.staged_trailer_refs(view):
        return "CGSpec: this commit cites the 'trailer' approval; add 'Approved-by: <you>' to the message yourself"
    if trust.governance_change(view):
        return ("CGSpec: this commit changes governance files (hooks, workflows, ownership, plugin source); "
                "add 'Approved-by: <you>' yourself and sign the commit with a trusted approver key")
    return None
