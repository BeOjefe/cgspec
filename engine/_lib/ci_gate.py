"""CI governance stage (spec 7b): re-check every commit in the range and prove failing-test records."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import checks
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
    if git(root, "diff", "--quiet", failed_at, "HEAD", "--", test_file).returncode != 0:
        return f"{name}: test file {test_file} was modified after failed_at {failed_at[:10]}; a failing test cannot be weakened to make it pass"
    if any(field in record for field in ("runner_id", "runner_hash", "selector")):
        return prove_named(root, record)
    shown = git(root, "show", "HEAD:docs/_cgspec/project.json")
    try:
        project = json.loads(shown.stdout) if shown.returncode == 0 else {}
    except ValueError:
        project = {}
    if isinstance(project, dict) and project.get("test_runners"):
        return f"{name}: named runner and assertion-aware proof are required after migration"
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


def prove_named(root: Path, record: dict) -> str | None:
    from . import runner_contracts, runner_execution
    from .common import CgspecError
    name = record["_file"]
    candidate = git(root, "rev-parse", "--verify", "HEAD^{commit}")
    if candidate.returncode:
        return f"{name}: cannot resolve candidate HEAD"
    candidate_sha = candidate.stdout.strip()
    definitions = []
    for rev in (record["failed_at"], candidate_sha):
        result = git(root, "show", f"{rev}:docs/_cgspec/project.json")
        try:
            project = json.loads(result.stdout) if result.returncode == 0 else {}
        except ValueError:
            project = {}
        if not isinstance(project, dict) or not project.get("test_runners"):
            return f"{name}: approved runner was not present at {rev[:10]}"
        reader = lambda rel: (result.stdout if (result := git(root, "show", f"{rev}:{rel}", binary=True)).returncode == 0 else None)
        problems = runner_contracts.pair_errors(project, record, reader)
        if problems:
            return f"{name}: {', '.join(problems)} at {rev[:10]}"
        try:
            runner, environment, _ = runner_contracts.resolve(project, record["runner_id"], reader)
        except CgspecError as exc:
            return f"{name}: {exc}"
        definitions.append((runner, environment))
    proof_dir = Path(os.environ.get("CGSPEC_PROOF_DIR", str(root / ".cgspec-scratch/ci-proof")))
    for label, rev, definition, expected in (("red", record["failed_at"], definitions[0], "ASSERTION_FAILED"),
                                              ("green", candidate_sha, definitions[1], "PASS")):
        detail = runner_execution.run_detail(root, rev, *definition, record["test_file"])
        detail.update(proof_file=name, test_id=record.get("test_id"), phase=label, candidate_revision=candidate_sha)
        # Names are derived from trusted hashes rather than an untrusted test_id or filename.
        import hashlib
        key = hashlib.sha256(name.encode()).hexdigest()[:20]
        try:
            proof_dir.mkdir(parents=True, exist_ok=True)
            (proof_dir / f"{key}-{label}.json").write_text(json.dumps(detail, indent=2, sort_keys=True) + "\n")
        except OSError as exc:
            return f"{name}: cannot retain structured proof: {exc}"
        if detail["result"] != expected:
            return f"{name}: {label} run was {detail['result']}, not {expected} at {rev[:10]}"
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
        view = View.commit(root, commit)
        reasons = evaluate(root, view, release_dir, strict=True)
        reasons += [f"check integrity: {problem}" for problem in checks.verify_manifest_at(view)]
        problems += [f"commit {subject}: {reason}" for reason in reasons]
    changed = [line for line in git(root, "diff", "--name-only", "--diff-filter=d", f"{base}..HEAD").stdout.splitlines()
               if line]
    # The same trusted range base the commits above were judged against (the workflow's CGSPEC_BASE).
    failures, check_notes = checks.run(root, changed, write_evidence=False, base_rev=base, repo_root=root)
    problems += [f"check {failure}" for failure in failures]
    notes += [note for note in check_notes if not note.startswith("no registered")]
    if not rerun_tests:
        problems.append("incomplete verification: --no-rerun skipped failing-test proof; "
                        "this result cannot satisfy the governance check")
    else:
        for record in new_test_records(root, base):
            problem = prove_failed(root, record)
            if problem:
                problems.append(problem)
            else:
                label = "legacy exit-code-only proof" if "runner_id" not in record else "structured runner proof"
                notes.append(f"proved ({label}): {record.get('test_id')} failed at {str(record.get('failed_at'))[:10]}")
    return problems, notes
