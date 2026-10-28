"""Candidate runner configuration must be approved before it can supply proof."""

from __future__ import annotations

from . import commit_trust as trust
from . import runner_contracts
from .common import PROJECT_FILE
from .gitview import View


def check(view: View) -> list[str]:
    old = trust.load(view.read_old(PROJECT_FILE.as_posix()))
    new = trust.load(view.read_new(PROJECT_FILE.as_posix()))
    reasons = runner_contracts.errors(new)
    if (old.get("test_runners"), old.get("test_environments")) == \
            (new.get("test_runners"), new.get("test_environments")):
        return reasons
    if not new.get("test_runners"):
        return reasons + ["project.json removing approved test runners requires a migration, not silent fallback"]
    ref = str(new.get("test_runners_approval", ""))
    problem = trust.approval_ok(view, ref, "test_runners")
    return reasons + ([f"project.json test_runners changed; its approval {problem}"] if problem else [])


def staged_trailer_ref(view: View) -> bool:
    old = trust.load(view.read_old(PROJECT_FILE.as_posix()))
    new = trust.load(view.read_new(PROJECT_FILE.as_posix()))
    return (new.get("test_runners_approval") == trust.TRAILER_REF and
            (old.get("test_runners"), old.get("test_environments")) !=
            (new.get("test_runners"), new.get("test_environments")))
