"""Verify finished approvals locally before Git can publish them.

commit-msg runs before Git creates the signed object, so it cannot verify that
signature. pre-push is blocking and checks every outgoing commit, including
intermediate commits, against that commit's own parent policy.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import commit_trust as trust
from .common import EXIT_FAIL, EXIT_OK
from .gitview import View, git


def commit_problems(view: View) -> list[str]:
    reasons = trust.append_only(view) + trust.approvals_have_inbox_lines(view) + trust.approver_key_change(view)
    message = trust.commit_message(view) or ""
    if trust.TRAILER.search(message) or trust.staged_trailer_refs(view) or trust.governance_change(view):
        if not trust.TRAILER.search(message):
            reasons.append("approval requires an Approved-by: trailer written by the human")
        if not trust.trusted_signature(view):
            reasons.append("approval commit is not signed by a key in the parent's project.json approver_keys")
    return reasons


def post_commit(root: Path) -> int:
    """Check the newly-created commit object immediately after commit creation."""
    import sys
    view = View.commit(root, "HEAD")
    if trust.is_bootstrap(view):
        return EXIT_OK
    reasons = commit_problems(view)
    if reasons:
        sha = git(root, "rev-parse", "--short", "HEAD").stdout.strip()
        print(f"CGSpec local approval check failed ({sha}):\n- " + "\n- ".join(reasons), file=sys.stderr)
        return EXIT_FAIL
    return EXIT_OK


def pre_push(root: Path, raw: str) -> int:
    commits, reasons = set(), []
    for line in raw.splitlines():
        fields = line.split()
        if len(fields) != 4 or any(not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", fields[i]) for i in (1, 3)):
            reasons.append("invalid pre-push ref update; cannot establish outgoing commits")
            continue
        local, remote = fields[1], fields[3]
        if set(local) == {"0"}:
            continue  # ref deletion has no outgoing approvals
        args = ["rev-list", local]
        if set(remote) != {"0"}:
            args.append("^" + remote)
        result = git(root, *args)
        if result.returncode:
            reasons.append("cannot establish outgoing commit range; fetch the remote history and retry")
            continue
        commits.update(result.stdout.splitlines())
    for sha in sorted(commits):
        view = View.commit(root, sha)
        # The initial installation baseline needs separate human review; it has
        # no earlier key policy that any local/CI signature check could trust.
        if trust.is_bootstrap(view):
            continue
        reasons += [f"{sha[:12]}: {problem}" for problem in commit_problems(view)]
    if reasons:
        print("CGSpec local approval check failed (push blocked):\n- " + "\n- ".join(reasons))
        return EXIT_FAIL
    print("CGSpec local approval check passed")
    return EXIT_OK
