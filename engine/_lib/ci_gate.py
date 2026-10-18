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


def _run_at(root: Path, rev: str, command: list) -> int | str:
    """Exit code of command in a throwaway worktree at rev, or an error message."""
    tmp = Path(tempfile.mkdtemp(prefix="cgspec-proof-"))
    tree = tmp / "tree"
    try:
        if git(root, "worktree", "add", "--detach", "-q", str(tree), rev).returncode != 0:
            return f"{rev} cannot be checked out"
        try:
            return subprocess.run(command, cwd=tree, capture_output=True, timeout=TEST_TIMEOUT).returncode
        except (OSError, subprocess.TimeoutExpired) as exc:
            return f"could not run at {rev[:10]}: {exc}"
    finally:
        git(root, "worktree", "remove", "--force", str(tree))
        shutil.rmtree(tmp, ignore_errors=True)


def prove_failed(root: Path, record: dict) -> str | None:
    """The recorded test must fail at failed_at and pass at HEAD."""
    command, name = record.get("command"), record["_file"]
    if not isinstance(command, list) or not command:
        return f"{name}: no command to re-run"
    failed_at, test_file = str(record.get("failed_at", "")), str(record.get("test_file", ""))
    if git(root, "cat-file", "-e", f"{failed_at}:{test_file}").returncode != 0:
        return f"{name}: test file {test_file} did not exist at {failed_at[:10]}, so it cannot have failed there"
    before = _run_at(root, record.get("failed_at", ""), command)
    if isinstance(before, str):
        return f"{name}: {before}"
    if before == 0:
        return f"{name}: test {record.get('test_id')} did not fail at {str(record.get('failed_at'))[:10]}; the record is not proof"
    after = _run_at(root, "HEAD", command)
    if isinstance(after, str):
        return f"{name}: {after}"
    if after != 0:
        return f"{name}: test {record.get('test_id')} still fails at HEAD"
    return None


def install_commit(root: Path) -> str | None:
    out = git(root, "log", "--diff-filter=A", "--format=%H", "--", "docs/_cgspec/project.json").stdout.split()
    return out[-1] if out else None


def effective_base(root: Path, base: str | None) -> str:
    """Never judge history from before CGSpec was installed; fall back to the install commit."""
    installed = install_commit(root)
    valid = bool(base) and git(root, "cat-file", "-e", f"{base}^{{commit}}").returncode == 0
    if not valid:
        if not installed:
            raise RuntimeError("no valid base and no install commit found")
        return installed
    if installed and git(root, "merge-base", "--is-ancestor", installed, base).returncode != 0:
        return installed  # base predates the install
    return base


def run(root: Path, base: str | None, rerun_tests: bool = True,
        release_dir: Path | None = None) -> tuple[list[str], list[str]]:
    """(problems, notes) for the range base..HEAD."""
    problems, notes = [], []
    base = effective_base(root, base)
    notes.append(f"checking {base[:10]}..HEAD")
    for commit in commits_in_range(root, base):
        subject = git(root, "log", "-1", "--format=%h %s", commit).stdout.strip()
        reasons = evaluate(root, View.commit(root, commit), release_dir, strict=True)
        problems += [f"commit {subject}: {reason}" for reason in reasons]
    if rerun_tests:
        for record in new_test_records(root, base):
            problem = prove_failed(root, record)
            if problem:
                problems.append(problem)
            else:
                notes.append(f"proved: {record.get('test_id')} failed at {str(record.get('failed_at'))[:10]}")
    return problems, notes
