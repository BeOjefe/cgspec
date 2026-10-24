"""Paths that can change how CGSpec is invoked or trusted.

This fixed floor comes from the checker, not the candidate's project settings.
It is an accidental-change guard; an independent verifier is still required.
"""

from __future__ import annotations


GOVERNANCE_FILES = frozenset({
    ".claude/settings.json",
    ".agents/hooks.json",
    ".github/cgspec-select.sh",
    ".git/config",
    ".gitmodules",
    ".github/CODEOWNERS",
    "CODEOWNERS",
    "docs/CODEOWNERS",
})

GOVERNANCE_DIRS = (
    ".github/workflows/",
    ".github/actions/",
    ".github/scripts/",
    ".githooks/",
    ".husky/",
    ".git/hooks/",
)


def governance_path(rel: str) -> bool:
    """Recognize fixed governance surfaces, including newly named workflows."""
    rel = rel.removeprefix("./")
    return rel in GOVERNANCE_FILES or any(
        rel == prefix[:-1] or rel.startswith(prefix) for prefix in GOVERNANCE_DIRS
    )
