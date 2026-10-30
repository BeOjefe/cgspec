"""Per-slice Git execution protocol: plan declaration, commit sequencing,
review binding, worker isolation, multi-repo links, and monolithic/unbound rejection.

Tests cover: normal delivery, multiple atomic commits, stale review after a new
commit, conflicting workers, a multi-repo outcome, and unbound/monolithic rejection.
Uses disposable Git fixtures; no network or external tools.
"""

from __future__ import annotations

import json
import os
import subprocess
import unittest
from pathlib import Path

from tests.helpers import (
    REPO, TempDir, approve, git, git_project, hook, make_ready_start,
    make_slice, run_script, write_json,
)

ENGINE = REPO / "engine"


def _git_plan_hook(root, *args):
    return run_script("cgspec_hook.py", "git-plan", "--root", str(root), *args)


def _plan_draft(root, base=None, branch=None, outcomes=None,
                file_ownership=None, worker_worktrees=None, stacked=None, multi_repo=None):
    base = base or git(root, "rev-parse", "HEAD").stdout.strip()
    branch = branch or git(root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    repos = [{
        "id": "main", "base": base, "branch": branch, "worktree": None,
        "outcomes": outcomes or ["OUT-work"], "file_ownership": file_ownership or {},
        "worker_worktrees": worker_worktrees or {},
    }]
    if multi_repo:
        repos = [{"id": item["id"], "base": base, "branch": item["branch"], "worktree": None,
                  "outcomes": [multi_repo["outcome_id"]], "file_ownership": {}}
                 for item in multi_repo["repos"]]
        branch = repos[0]["branch"]
    draft = {
        "repositories": repos,
        "default_branch": branch,
    }
    if stacked:
        draft["stacked_branches"] = stacked
    if multi_repo:
        draft["multi_repo"] = multi_repo
    path = root / ".cgspec-scratch" / "plan-draft.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, draft)
    return path


def _declare_plan(root, slice_id="SLICE-001", **kwargs):
    draft_path = _plan_draft(root, **kwargs)
    result = _git_plan_hook(root, "declare", "--slice", slice_id, "--file", str(draft_path))
    if result.returncode:
        raise AssertionError(f"declare failed: {result.stderr}")
    return result


def _record_commit(root, slice_id, sha, summary="fix", kind="implementation"):
    return _git_plan_hook(root, "record-commit", sha, "--slice", slice_id,
                           "--description", summary, "--commit-kind", kind)


def _commit(root, name, content):
    path = root / "src" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", name)
    return git(root, "rev-parse", "HEAD").stdout.strip()


def _green_candidate(root):
    red = _commit(root, "login.test.ts", "test('red', () => {});\n")
    assert _record_commit(root, "SLICE-001", red, "failing behavior", "red-test").returncode == 0
    implementation = _commit(root, "login.ts", "export const login = true;\n")
    assert _record_commit(root, "SLICE-001", implementation, "implement behavior").returncode == 0
    green = _commit(root, "login.test.ts", "test('green', () => {});\n")
    assert _record_commit(root, "SLICE-001", green, "passing behavior", "green-test").returncode == 0
    return green


class TestPlanDeclaration(unittest.TestCase):
    """AC-1: Before implementation, record repository IDs, approved base revisions,
    branch/worktree, affected outcomes, and shared-file ownership."""

    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git_project(self.root)
        make_slice(self.root)

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def test_declare_creates_plan(self):
        _declare_plan(self.root)
        plan_files = list((self.root / "docs/slices").glob("SLICE-001-*.git-plan.json"))
        self.assertEqual(len(plan_files), 1)
        data = json.loads(plan_files[0].read_text())
        self.assertEqual(data["schema"], 1)
        self.assertEqual(data["slice"], "SLICE-001")
        self.assertEqual(len(data["repositories"]), 1)
        repo = data["repositories"][0]
        self.assertEqual(repo["id"], "main")
        self.assertEqual(repo["base"], git(self.root, "rev-parse", "HEAD").stdout.strip())
        branch = git(self.root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        self.assertEqual(repo["branch"], branch)
        self.assertEqual(repo["outcomes"], ["OUT-work"])
        self.assertEqual(data["branch_policy"]["default_branch"], branch)

    def test_declare_with_file_ownership(self):
        ownership = {"worker-1": ["src/login/**"], "worker-2": ["src/auth/**"]}
        worktrees = {"worker-1": str(self.root), "worker-2": str(self.root.parent / "worker-2")}
        _declare_plan(self.root, file_ownership=ownership, worker_worktrees=worktrees)
        plan_files = list((self.root / "docs/slices").glob("SLICE-001-*.git-plan.json"))
        data = json.loads(plan_files[0].read_text())
        self.assertEqual(data["repositories"][0]["file_ownership"], ownership)

    def test_double_declare_rejected(self):
        _declare_plan(self.root)
        result = _git_plan_hook(self.root, "declare", "--slice", "SLICE-001",
                                "--file", str(_plan_draft(self.root)))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already has a git plan", result.stderr)

    def test_show(self):
        _declare_plan(self.root)
        result = _git_plan_hook(self.root, "show", "--slice", "SLICE-001")
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertEqual(data["slice"], "SLICE-001")

    def test_declare_missing_slice(self):
        result = _git_plan_hook(self.root, "declare", "--slice", "SLICE-999",
                                "--file", str(_plan_draft(self.root)))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not found", result.stderr)


class TestBranchPolicy(unittest.TestCase):
    """AC-2: Default one branch; stacked branches require an explicit dependency reason."""

    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git_project(self.root)
        make_slice(self.root)

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def test_single_branch_default(self):
        _declare_plan(self.root)
        plan_files = list((self.root / "docs/slices").glob("SLICE-001-*.git-plan.json"))
        data = json.loads(plan_files[0].read_text())
        self.assertEqual(data["branch_policy"]["stacked_branches"], [])

    def test_stacked_branches_require_reason(self):
        current = git(self.root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        stacked = [{"branch": "feat/step-2", "depends_on": current,
                     "reason": "API must land before UI consumers"}]
        _declare_plan(self.root, stacked=stacked)
        plan_files = list((self.root / "docs/slices").glob("SLICE-001-*.git-plan.json"))
        data = json.loads(plan_files[0].read_text())
        self.assertEqual(len(data["branch_policy"]["stacked_branches"]), 1)
        self.assertIn("API must land", data["branch_policy"]["stacked_branches"][0]["reason"])

    def test_declared_stacked_branch_allows_implementation_context(self):
        current = git(self.root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        stacked = [{"branch": "feat/step-2", "depends_on": current,
                    "reason": "API must land before UI consumers", "worktree": None}]
        _declare_plan(self.root, stacked=stacked)
        git(self.root, "checkout", "-q", "-b", "feat/step-2")
        from _lib.git_protocol import check_plan_declared
        self.assertIsNone(check_plan_declared(self.root, "SLICE-001"))

    def test_stacked_without_reason_rejected(self):
        draft = {
            "repositories": [{"id": "main", "base": "a" * 40, "branch": "feat/test",
                               "worktree": None, "outcomes": ["OUT-work"], "file_ownership": {}}],
            "default_branch": "feat/test",
            "stacked_branches": [{"branch": "feat/step-2", "depends_on": "feat/test", "reason": "ab"}],
        }
        path = self.root / ".cgspec-scratch" / "plan-draft.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, draft)
        result = _git_plan_hook(self.root, "declare", "--slice", "SLICE-001", "--file", str(path))
        self.assertNotEqual(result.returncode, 0)


class TestCommitSequencing(unittest.TestCase):
    """AC-3/AC-4: Logical commit units, red-green-review sequencing,
    intentional intermediate red commits."""

    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git_project(self.root)
        make_slice(self.root)
        _declare_plan(self.root)

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def test_record_red_then_green_then_review(self):
        sha1 = _commit(self.root, "red.test.ts", "fails\n")
        r1 = _git_plan_hook(self.root, "record-commit", sha1, "--slice", "SLICE-001",
                            "--description", "add failing test", "--commit-kind", "red-test")
        self.assertEqual(r1.returncode, 0)
        sha2 = _commit(self.root, "feature.ts", "implemented\n")
        r2 = _git_plan_hook(self.root, "record-commit", sha2, "--slice", "SLICE-001",
                            "--description", "implement login", "--commit-kind", "implementation")
        self.assertEqual(r2.returncode, 0)
        sha3 = _commit(self.root, "red.test.ts", "passes\n")
        r3 = _git_plan_hook(self.root, "record-commit", sha3, "--slice", "SLICE-001",
                            "--description", "tests pass", "--commit-kind", "green-test")
        self.assertEqual(r3.returncode, 0)
        plan_files = list((self.root / "docs/slices").glob("SLICE-001-*.git-plan.json"))
        data = json.loads(plan_files[0].read_text())
        self.assertEqual(len(data["commits"]), 3)
        self.assertEqual([c["kind"] for c in data["commits"]],
                         ["red-test", "implementation", "green-test"])

    def test_multiple_atomic_commits(self):
        kinds = ["red-test", "implementation", "implementation", "green-test"]
        for i, kind in enumerate(kinds):
            sha = _commit(self.root, f"step-{i}.ts", f"step {i}\n")
            result = _git_plan_hook(self.root, "record-commit", sha, "--slice", "SLICE-001",
                                    "--description", f"step {i}", "--commit-kind", kind)
            self.assertEqual(result.returncode, 0)
        plan_files = list((self.root / "docs/slices").glob("SLICE-001-*.git-plan.json"))
        data = json.loads(plan_files[0].read_text())
        self.assertEqual(len(data["commits"]), 4)

    def test_duplicate_commit_rejected(self):
        sha = _commit(self.root, "duplicate.test.ts", "fails\n")
        _git_plan_hook(self.root, "record-commit", sha, "--slice", "SLICE-001",
                       "--description", "first", "--commit-kind", "red-test")
        result = _git_plan_hook(self.root, "record-commit", sha, "--slice", "SLICE-001",
                                "--description", "dupe", "--commit-kind", "red-test")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already recorded", result.stderr)

    def test_invalid_kind_rejected(self):
        result = _git_plan_hook(self.root, "record-commit", "e" * 40, "--slice", "SLICE-001",
                                "--description", "bad", "--commit-kind", "yolo")
        self.assertNotEqual(result.returncode, 0)

    def test_short_sha_rejected(self):
        result = _git_plan_hook(self.root, "record-commit", "abcdef", "--slice", "SLICE-001",
                                "--description", "short", "--commit-kind", "implementation")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("40-character", result.stderr)

    def test_fabricated_commit_rejected(self):
        result = _record_commit(self.root, "SLICE-001", "e" * 40, "not real", "red-test")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not exist", result.stderr)

    def test_implementation_before_red_rejected(self):
        sha = _commit(self.root, "too-early.ts", "implementation\n")
        result = _record_commit(self.root, "SLICE-001", sha, "too early", "implementation")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("red-test", result.stderr)


class TestReviewBinding(unittest.TestCase):
    """AC-5: PR review and required checks bind to the exact candidate HEAD;
    later changes invalidate affected review/evidence."""

    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git_project(self.root)
        make_slice(self.root)
        _declare_plan(self.root)

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def test_bind_review_to_head(self):
        head = _green_candidate(self.root)
        result = _git_plan_hook(self.root, "bind-review", head, "--slice", "SLICE-001", "--checks-passed")
        self.assertEqual(result.returncode, 0)
        plan_files = list((self.root / "docs/slices").glob("SLICE-001-*.git-plan.json"))
        data = json.loads(plan_files[0].read_text())
        self.assertIsNotNone(data["review"])
        self.assertEqual(data["review"]["bound_head"], head)
        self.assertTrue(data["review"]["valid"])
        self.assertIsNone(data["review"]["invalidated_by"])

    def test_new_commit_invalidates_review(self):
        head = _green_candidate(self.root)
        _git_plan_hook(self.root, "bind-review", head, "--slice", "SLICE-001", "--checks-passed")
        new_sha = _commit(self.root, "review-fix.ts", "fixed\n")
        _git_plan_hook(self.root, "record-commit", new_sha, "--slice", "SLICE-001",
                       "--description", "late fix", "--commit-kind", "review-fix")
        plan_files = list((self.root / "docs/slices").glob("SLICE-001-*.git-plan.json"))
        data = json.loads(plan_files[0].read_text())
        self.assertFalse(data["review"]["valid"])
        self.assertEqual(data["review"]["invalidated_by"], new_sha)

    def test_review_rejects_non_head_and_missing_checks(self):
        head = _green_candidate(self.root)
        base = git(self.root, "rev-parse", "HEAD~1").stdout.strip()
        wrong = _git_plan_hook(self.root, "bind-review", base, "--slice", "SLICE-001", "--checks-passed")
        self.assertNotEqual(wrong.returncode, 0)
        unchecked = _git_plan_hook(self.root, "bind-review", head, "--slice", "SLICE-001")
        self.assertNotEqual(unchecked.returncode, 0)
        self.assertIn("checks", unchecked.stderr)

    def test_review_sidecar_commit_wraps_reviewed_parent(self):
        from _lib.git_protocol import commit_plan_reasons
        from _lib.gitview import View
        head = _green_candidate(self.root)
        result = _git_plan_hook(self.root, "bind-review", head, "--slice", "SLICE-001", "--checks-passed")
        self.assertEqual(result.returncode, 0, result.stderr)
        git(self.root, "add", "docs/slices")
        git(self.root, "commit", "-q", "-m", "bind review")
        envelope = git(self.root, "rev-parse", "HEAD").stdout.strip()
        self.assertEqual(commit_plan_reasons(View.commit(self.root, envelope),
                                             {"tier": "T1", "slice": "SLICE-001"}), [])

    def test_stale_review_detected_by_check(self):
        import sys
        sys.path.insert(0, str(ENGINE))
        from _lib.git_protocol import check_review_valid
        plan = {
            "review": {
                "bound_head": "f" * 40,
                "bound_at": "2026-01-01T00:00:00Z",
                "checks_passed": True,
                "valid": False,
                "invalidated_by": "1" * 40,
            }
        }
        problem = check_review_valid(plan)
        self.assertIsNotNone(problem)
        self.assertIn("invalidated", problem)

    def test_valid_review_passes(self):
        import sys
        sys.path.insert(0, str(ENGINE))
        from _lib.git_protocol import check_review_valid
        plan = {
            "review": {
                "bound_head": "f" * 40,
                "bound_at": "2026-01-01T00:00:00Z",
                "checks_passed": True,
                "valid": True,
                "invalidated_by": None,
            }
        }
        self.assertIsNone(check_review_valid(plan))


class TestWorkerIsolation(unittest.TestCase):
    """AC-6: Parallel workers use isolated worktrees/checkouts, have explicit file
    ownership, and cannot silently overwrite each other's proof or outputs."""

    def setUp(self):
        import sys
        sys.path.insert(0, str(ENGINE))
        from _lib.git_protocol import check_worker_ownership

    def test_worker_allowed_in_own_paths(self):
        from _lib.git_protocol import check_worker_ownership
        data = {"repositories": [{
            "id": "main", "base": "a" * 40, "branch": "feat/test",
            "outcomes": ["OUT-work"],
            "file_ownership": {
                "worker-1": ["src/login/**"],
                "worker-2": ["src/auth/**"],
            },
        }]}
        self.assertIsNone(check_worker_ownership(data, "worker-1", "src/login/form.ts"))

    def test_worker_blocked_from_other_paths(self):
        from _lib.git_protocol import check_worker_ownership
        data = {"repositories": [{
            "id": "main", "base": "a" * 40, "branch": "feat/test",
            "outcomes": ["OUT-work"],
            "file_ownership": {
                "worker-1": ["src/login/**"],
                "worker-2": ["src/auth/**"],
            },
        }]}
        problem = check_worker_ownership(data, "worker-1", "src/auth/handler.ts")
        self.assertIsNotNone(problem)
        self.assertIn("worker-2", problem)

    def test_undeclared_worker_blocked(self):
        from _lib.git_protocol import check_worker_ownership
        data = {"repositories": [{
            "id": "main", "base": "a" * 40, "branch": "feat/test",
            "outcomes": ["OUT-work"],
            "file_ownership": {
                "worker-1": ["src/login/**"],
            },
        }]}
        problem = check_worker_ownership(data, "rogue-agent", "src/login/form.ts")
        self.assertIsNotNone(problem)
        self.assertIn("not declared", problem)

    def test_no_ownership_means_no_restriction(self):
        from _lib.git_protocol import check_worker_ownership
        data = {"repositories": [{
            "id": "main", "base": "a" * 40, "branch": "feat/test",
            "outcomes": ["OUT-work"],
            "file_ownership": {},
        }]}
        self.assertIsNone(check_worker_ownership(data, "anyone", "src/login/form.ts"))


class TestMultiRepoOutcome(unittest.TestCase):
    """AC-7: Multi-repo outcomes link per-repo branches/commits/PRs to one outcome ID
    and declare compatible contract versions, integration order, and cross-repo verification."""

    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git_project(self.root)
        make_slice(self.root)

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def test_multi_repo_plan(self):
        multi = {
            "outcome_id": "OUT-work",
            "repos": [
                {"id": "api", "branch": "feat/api-login", "commit": None, "pr": None, "status": "planned"},
                {"id": "web", "branch": "feat/web-login", "commit": None, "pr": None, "status": "planned"},
            ],
            "integration_order": ["api", "web"],
            "contract_version": "v1.2.0",
            "verification": "Run cross-repo contract tests after both PRs merge",
        }
        _declare_plan(self.root, multi_repo=multi)
        plan_files = list((self.root / "docs/slices").glob("SLICE-001-*.git-plan.json"))
        data = json.loads(plan_files[0].read_text())
        self.assertIsNotNone(data["multi_repo"])
        self.assertEqual(data["multi_repo"]["outcome_id"], "OUT-work")
        self.assertEqual(len(data["multi_repo"]["repos"]), 2)
        self.assertEqual(data["multi_repo"]["integration_order"], ["api", "web"])
        self.assertEqual(data["multi_repo"]["contract_version"], "v1.2.0")

    def test_multi_repo_needs_at_least_two(self):
        multi = {
            "outcome_id": "OUT-work",
            "repos": [
                {"id": "api", "branch": "feat/api", "commit": None, "pr": None, "status": "planned"},
            ],
            "integration_order": ["api"],
            "contract_version": "v1.0",
            "verification": "Check it",
        }
        draft = _plan_draft(self.root, multi_repo=multi)
        result = _git_plan_hook(self.root, "declare", "--slice", "SLICE-001", "--file", str(draft))
        self.assertNotEqual(result.returncode, 0)

    def test_multi_repo_integration_order_must_match(self):
        multi = {
            "outcome_id": "OUT-work",
            "repos": [
                {"id": "api", "branch": "feat/api", "commit": None, "pr": None, "status": "planned"},
                {"id": "web", "branch": "feat/web", "commit": None, "pr": None, "status": "planned"},
            ],
            "integration_order": ["api", "web", "ghost"],
            "contract_version": "v1.0",
            "verification": "Check both",
        }
        draft = _plan_draft(self.root, multi_repo=multi)
        result = _git_plan_hook(self.root, "declare", "--slice", "SLICE-001", "--file", str(draft))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("integration_order", result.stderr)


class TestUnboundRejection(unittest.TestCase):
    """AC-9 (partial): Rejection of unbound delivery - implementation without a
    declared git plan is rejected at editor and commit gates."""

    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git_project(self.root)
        make_slice(self.root, status="Approved", scope="src/login/**")
        make_ready_start(self.root, with_git_plan=False)

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def test_editor_blocks_without_plan(self):
        import sys
        sys.path.insert(0, str(ENGINE))
        from _lib import start_gate
        tier = {"tier": "T1", "slice": "SLICE-001"}
        classes = {"code": ["src/**"], "tests": ["tests/**"]}
        reason = start_gate.editor_reason(self.root, tier, "src/login/form.ts", classes)
        self.assertIsNotNone(reason)
        self.assertIn("git execution plan", reason)

    def test_editor_allows_with_plan(self):
        import sys
        sys.path.insert(0, str(ENGINE))
        _declare_plan(self.root)
        from _lib import start_gate
        tier = {"tier": "T1", "slice": "SLICE-001"}
        classes = {"code": ["src/**"], "tests": ["tests/**"]}
        reason = start_gate.editor_reason(self.root, tier, "src/login/form.ts", classes)
        self.assertIsNone(reason)

    def test_editor_rejects_outcome_missing_from_plan(self):
        import sys
        sys.path.insert(0, str(ENGINE))
        _declare_plan(self.root, outcomes=["OUT-other"])
        from _lib import start_gate
        reason = start_gate.editor_reason(self.root, {"tier": "T1", "slice": "SLICE-001"},
                                          "src/login/form.ts", {"code": ["src/**"], "tests": ["tests/**"]})
        self.assertIn("absent from the git execution plan", reason)

    def test_editor_enforces_worker_identity_and_worktree(self):
        import sys
        from unittest.mock import patch
        sys.path.insert(0, str(ENGINE))
        ownership = {"worker-1": ["src/login/**"]}
        _declare_plan(self.root, file_ownership=ownership,
                      worker_worktrees={"worker-1": str(self.root)})
        from _lib import start_gate
        tier = {"tier": "T1", "slice": "SLICE-001"}
        classes = {"code": ["src/**"], "tests": ["tests/**"]}
        with patch.dict(os.environ, {}, clear=True):
            missing = start_gate.editor_reason(self.root, tier, "src/login/form.ts", classes)
        self.assertIn("CGSPEC_WORKER_ID", missing)
        with patch.dict(os.environ, {"CGSPEC_WORKER_ID": "worker-1"}):
            self.assertIsNone(start_gate.editor_reason(self.root, tier, "src/login/form.ts", classes))


class TestCommitGateIntegration(unittest.TestCase):
    """AC-9 (partial): Commit-level enforcement of git plan existence for
    implementation commits."""

    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git_project(self.root)
        make_slice(self.root, status="Approved", scope="src/login/**")
        make_ready_start(self.root, with_git_plan=False)

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def test_commit_blocks_implementation_without_plan(self):
        import sys
        sys.path.insert(0, str(ENGINE))
        from _lib.start_gate import commit_implementation
        from _lib.gitview import View
        (self.root / "src/login/form.ts").write_text("export const f = 2;\n")
        git(self.root, "add", "src/login/form.ts")
        view = View.staged(self.root)
        tier = {"tier": "T1", "slice": "SLICE-001"}
        reasons = commit_implementation(view, tier, {"src/login/form.ts"})
        has_plan_reason = any("git execution plan" in r for r in reasons)
        self.assertTrue(has_plan_reason, f"expected plan rejection, got: {reasons}")

    def test_commit_allows_implementation_with_plan(self):
        import sys
        sys.path.insert(0, str(ENGINE))
        _declare_plan(self.root)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "add plan")
        from _lib.start_gate import commit_implementation
        from _lib.gitview import View
        (self.root / "src/login/form.ts").write_text("export const f = 2;\n")
        plan_files = list((self.root / "docs/slices").glob("SLICE-001-*.git-plan.json"))
        git(self.root, "add", "src/login/form.ts", str(plan_files[0]))
        view = View.staged(self.root)
        tier = {"tier": "T1", "slice": "SLICE-001"}
        reasons = commit_implementation(view, tier, {"src/login/form.ts"})
        plan_reasons = [r for r in reasons if "git execution plan" in r]
        self.assertEqual(plan_reasons, [], f"unexpected plan rejection: {plan_reasons}")

    def test_commit_rejects_multiple_unrelated_outcomes(self):
        import copy
        from _lib.start import definition_hash
        from _lib.start_gate import commit_implementation
        from _lib.gitview import View
        start_path = next((self.root / "docs/slices").glob("*.start.json"))
        record = json.loads(start_path.read_text())
        other = copy.deepcopy(record["outcomes"][0])
        other.update(id="OUT-other", covers=["src/auth/**"])
        record["outcomes"].append(other)
        record["active_outcomes"].append("OUT-other")
        record["readiness"]["definition_hash"] = definition_hash(record)
        record["approval"]["definition_hash"] = definition_hash(record)
        write_json(start_path, record)
        _declare_plan(self.root, outcomes=["OUT-work", "OUT-other"])
        (self.root / "src/auth").mkdir(parents=True)
        (self.root / "src/auth/form.ts").write_text("export const auth = 2;\n")
        git(self.root, "add", "-A")
        reasons = commit_implementation(View.staged(self.root), {"tier": "T1", "slice": "SLICE-001"},
                                        {"src/login/form.ts", "src/auth/form.ts"})
        self.assertTrue(any("unrelated outcomes" in reason for reason in reasons), reasons)


class TestDestructiveProtections(unittest.TestCase):
    """AC-8: Destructive history operations and merges remain subject to existing
    user-approval protections; opening a PR never grants merge permission."""

    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git_project(self.root)

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def _bash(self, command):
        from tests.helpers import claude_payload
        return hook(self.root, "pre-tool",
                    claude_payload(self.root, "Bash", command=command), "--tool", "claude")

    def test_force_push_blocked(self):
        result = self._bash("git push --force origin main")
        self.assertEqual(result.returncode, 2)

    def test_merge_pr_blocked(self):
        result = self._bash("gh pr merge 42")
        self.assertEqual(result.returncode, 2)

    def test_reset_hard_blocked(self):
        result = self._bash("git reset --hard HEAD~1")
        self.assertEqual(result.returncode, 2)

    def test_filter_branch_blocked(self):
        result = self._bash("git filter-branch --force HEAD")
        self.assertEqual(result.returncode, 2)


class TestSchemaValidation(unittest.TestCase):
    """Schema validation for git-plan.json catches structural errors."""

    def test_valid_plan(self):
        import sys
        sys.path.insert(0, str(ENGINE))
        from _lib.git_protocol import validate_plan
        plan = {
            "schema": 1, "slice": "SLICE-001",
            "repositories": [{"id": "main", "base": "a" * 40, "branch": "feat/x",
                               "worktree": None, "outcomes": ["OUT-a"], "file_ownership": {}}],
            "branch_policy": {"default_branch": "feat/x", "stacked_branches": []},
            "commits": [], "review": None, "multi_repo": None,
            "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z",
        }
        self.assertEqual(validate_plan(plan), [])

    def test_missing_required_field(self):
        import sys
        sys.path.insert(0, str(ENGINE))
        from _lib.git_protocol import validate_plan
        plan = {"schema": 1, "slice": "SLICE-001"}
        errors = validate_plan(plan)
        self.assertTrue(len(errors) > 0)

    def test_duplicate_repo_ids(self):
        import sys
        sys.path.insert(0, str(ENGINE))
        from _lib.git_protocol import validate_plan
        plan = {
            "schema": 1, "slice": "SLICE-001",
            "repositories": [
                {"id": "main", "base": "a" * 40, "branch": "feat/x",
                 "worktree": None, "outcomes": ["OUT-a"], "file_ownership": {}},
                {"id": "main", "base": "b" * 40, "branch": "feat/y",
                 "worktree": None, "outcomes": ["OUT-b"], "file_ownership": {}},
            ],
            "branch_policy": {"default_branch": "feat/x", "stacked_branches": []},
            "commits": [], "review": None, "multi_repo": None,
            "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z",
        }
        errors = validate_plan(plan)
        self.assertTrue(any("unique" in e for e in errors))


class TestReviewInvalidationAtCommitGate(unittest.TestCase):
    """Stale review is surfaced through the commit gate when a plan has an
    invalidated review binding."""

    def test_commit_plan_reasons_flags_stale_review(self):
        import sys
        sys.path.insert(0, str(ENGINE))
        from _lib.git_protocol import commit_plan_reasons

        class FakeView:
            new = "1" * 40
            def files_new(self, prefix):
                return ["docs/slices/SLICE-001-login.git-plan.json"]
            def read_new(self, path):
                plan = {
                    "schema": 1, "slice": "SLICE-001",
                    "repositories": [{"id": "main", "base": "a" * 40, "branch": "feat/x",
                                       "worktree": None, "outcomes": ["OUT-a"], "file_ownership": {}}],
                    "branch_policy": {"default_branch": "feat/x", "stacked_branches": []},
                    "commits": [],
                    "review": {"bound_head": "f" * 40, "bound_at": "2026-01-01T00:00:00Z",
                               "checks_passed": True, "valid": False, "invalidated_by": "1" * 40},
                    "multi_repo": None,
                    "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z",
                }
                return json.dumps(plan).encode()
            def changes(self):
                return []

        tier = {"tier": "T1", "slice": "SLICE-001"}
        reasons = commit_plan_reasons(FakeView(), tier)
        self.assertTrue(any("invalidated" in r for r in reasons))

    def test_commit_plan_reasons_clean_for_valid_review(self):
        import sys
        sys.path.insert(0, str(ENGINE))
        from _lib.git_protocol import commit_plan_reasons

        class FakeView:
            new = "f" * 40
            def files_new(self, prefix):
                return ["docs/slices/SLICE-001-login.git-plan.json"]
            def read_new(self, path):
                plan = {
                    "schema": 1, "slice": "SLICE-001",
                    "repositories": [{"id": "main", "base": "a" * 40, "branch": "feat/x",
                                       "worktree": None, "outcomes": ["OUT-a"], "file_ownership": {}}],
                    "branch_policy": {"default_branch": "feat/x", "stacked_branches": []},
                    "commits": [],
                    "review": {"bound_head": "f" * 40, "bound_at": "2026-01-01T00:00:00Z",
                               "checks_passed": True, "valid": True, "invalidated_by": None},
                    "multi_repo": None,
                    "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z",
                }
                return json.dumps(plan).encode()
            def changes(self):
                return []

        tier = {"tier": "T1", "slice": "SLICE-001"}
        reasons = commit_plan_reasons(FakeView(), tier)
        self.assertEqual(reasons, [])


if __name__ == "__main__":
    unittest.main()
