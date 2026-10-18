"""CI governance stage (spec 7b): re-check every commit in the range and prove failing-test records."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from .commit_gate import evaluate
from .gitview import View, git

TEST_TIMEOUT = 600


def commits_in_range(root: Path, base: str) -> list[str]:
    out = git(root, "rev-list", "--reverse", f"{base}..HEAD")
    if out.returncode != 0:
        raise RuntimeError(f"cannot list commits {base}..HEAD: {out.stderr.strip()}")
    return [c for c in out.stdout.split() if c]


def new_test_records(root: Path, base: str) -> list[dict]:
    out = git(root, "diff", "--name-only", "--diff-filter=AM", "-z", base, "HEAD", "--",
              "docs/_cgspec/06-evidence/tests").stdout
    records = []
    for rel in filter(None, out.split("\0")):
        shown = git(root, "show", f"HEAD:{rel}")
        try:
            data = json.loads(shown.stdout) if shown.returncode == 0 else None
        except ValueError:
            data = None
        if isinstance(data, dict):
            data["_file"] = rel
            records.append(data)
    return records


def prove_failed(root: Path, record: dict) -> str | None:
    """Run the recorded command at failed_at in a throwaway worktree; it must exit non-zero."""
    rev, command = record.get("failed_at", ""), record.get("command")
    if not isinstance(command, list) or not command:
        return f"{record['_file']}: no command to re-run"
    tmp = Path(tempfile.mkdtemp(prefix="cgspec-proof-"))
    tree = tmp / "tree"
    try:
        added = git(root, "worktree", "add", "--detach", "-q", str(tree), rev)
        if added.returncode != 0:
            return f"{record['_file']}: failed_at {rev} cannot be checked out"
        try:
            run = subprocess.run(command, cwd=tree, capture_output=True, timeout=TEST_TIMEOUT)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return f"{record['_file']}: could not run the test at {rev}: {exc}"
        if run.returncode == 0:
            return f"{record['_file']}: test {record.get('test_id')} did not fail at {rev[:10]}; the record is not proof"
        return None
    finally:
        git(root, "worktree", "remove", "--force", str(tree))
        shutil.rmtree(tmp, ignore_errors=True)


def run(root: Path, base: str, rerun_tests: bool = True) -> tuple[list[str], list[str]]:
    """(problems, notes) for the range base..HEAD."""
    problems, notes = [], []
    for commit in commits_in_range(root, base):
        subject = git(root, "log", "-1", "--format=%h %s", commit).stdout.strip()
        problems += [f"commit {subject}: {reason}" for reason in evaluate(root, View.commit(root, commit))]
    if rerun_tests:
        for record in new_test_records(root, base):
            problem = prove_failed(root, record)
            if problem:
                problems.append(problem)
            else:
                notes.append(f"proved: {record.get('test_id')} failed at {str(record.get('failed_at'))[:10]}")
    return problems, notes
