"""Unit tests for subagent run enforcement, test immutability, and helper detection."""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

from tests.helpers import TempDir, git, git_project, hook, run_script, set_test_command, write_json
from _lib import ci_gate, post_tool, runs
from _lib.common import CgspecError, sha256_file
from _lib.gitview import View
from _lib.schema import validate_named


class SubagentRunsTests(unittest.TestCase):
    """Test suite for runs, ci_gate weakening checks, and helper tools."""

    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git_project(self.root)

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def test_freeze_run_creates_valid_schema_and_hashes(self):
        """freeze_run creates run.json validating against schema with exact hashes."""
        crit = self.root / "docs/criteria.md"
        crit.parent.mkdir(parents=True, exist_ok=True)
        crit.write_text("# Criteria\nMust pass all tests\n")
        test_file = self.root / "tests/test_feature.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("def test_one(): pass\n")

        units = [
            {
                "id": "u1",
                "owner": "builder-1",
                "allowed_paths": ["src/login/**"],
                "status": "todo",
            }
        ]
        data = runs.freeze_run(
            self.root,
            goal="Add feature",
            tier="T1",
            criteria_paths=["docs/criteria.md"],
            test_paths=["tests/test_feature.py"],
            units=units,
            run_id="R-20261024-0001",
            slice_id="SLICE-001",
            approval_ref="trailer",
        )

        self.assertEqual(data["run_id"], "R-20261024-0001")
        self.assertEqual(data["status"], "active")
        self.assertEqual(data["criteria"][0]["sha256"], sha256_file(crit))
        self.assertEqual(data["tests"][0]["sha256"], sha256_file(test_file))
        self.assertIsNotNone(data["frozen_at"])
        self.assertEqual(validate_named(data, "run"), [])

        loaded = runs.load_runs(self.root)
        self.assertEqual(len(loaded), 1)
        rel_path, run_obj = loaded[0]
        self.assertEqual(rel_path, "docs/_cgspec/05-runs/R-20261024-0001/run.json")
        self.assertEqual(run_obj["run_id"], "R-20261024-0001")
        self.assertEqual(run_obj["status"], "active")

        frozen = runs.frozen_run_files(self.root)
        self.assertEqual(frozen["docs/criteria.md"], "R-20261024-0001")
        self.assertEqual(frozen["tests/test_feature.py"], "R-20261024-0001")
        self.assertEqual(frozen["docs/_cgspec/05-runs/R-20261024-0001/run.json"], "R-20261024-0001")

    def test_contained_path_and_symlink_escape_rejection(self):
        """validate_contained_path rejects path traversal, absolute paths, and symlink escapes."""
        # Valid relative paths
        self.assertEqual(runs.validate_contained_path(self.root, "src/index.ts"), "src/index.ts")
        self.assertEqual(runs.validate_contained_path(self.root, "tests/unit/test_a.py"), "tests/unit/test_a.py")

        # Absolute paths
        with self.assertRaises(ValueError):
            runs.validate_contained_path(self.root, "/etc/passwd")

        # Directory traversal
        with self.assertRaises(ValueError):
            runs.validate_contained_path(self.root, "../escape.txt")
        with self.assertRaises(ValueError):
            runs.validate_contained_path(self.root, "src/../../outside.txt")

        # Symlink escape outside project root
        link = self.root / "src/escapelink"
        link.parent.mkdir(parents=True, exist_ok=True)
        try:
            link.symlink_to("/tmp", target_is_directory=True)
            with self.assertRaises(ValueError):
                runs.validate_contained_path(self.root, "src/escapelink/evil.txt")
        except OSError:
            pass  # if OS disallows symlink creation in test environment

    def test_freeze_run_run_id_validation_and_cannot_overwrite(self):
        """freeze_run enforces run_id format and refuses to overwrite existing runs."""
        crit = self.root / "docs/criteria.md"
        crit.parent.mkdir(parents=True, exist_ok=True)
        crit.write_text("# Criteria\n")
        test_file = self.root / "tests/test_a.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("def test_a(): pass\n")

        # Invalid run_id format
        with self.assertRaises(CgspecError):
            runs.freeze_run(self.root, "Goal", "T1", ["docs/criteria.md"], ["tests/test_a.py"],
                            [{"id": "u1", "owner": "b", "allowed_paths": ["src/**"]}],
                            run_id="bad-run-id")

        with self.assertRaises(CgspecError):
            runs.freeze_run(self.root, "Goal", "T1", ["docs/criteria.md"], ["tests/test_a.py"],
                            [{"id": "u1", "owner": "b", "allowed_paths": ["src/**"]}],
                            run_id="R-20261024-../../escape")

        # First freeze succeeds
        runs.freeze_run(self.root, "Goal", "T1", ["docs/criteria.md"], ["tests/test_a.py"],
                        [{"id": "u1", "owner": "b", "allowed_paths": ["src/**"]}],
                        run_id="R-20261024-0001")

        # Second freeze with same run_id must fail closed (cannot overwrite existing run)
        with self.assertRaises(CgspecError) as ctx:
            runs.freeze_run(self.root, "Goal 2", "T1", ["docs/criteria.md"], ["tests/test_a.py"],
                            [{"id": "u1", "owner": "b", "allowed_paths": ["src/**"]}],
                            run_id="R-20261024-0001")
        self.assertIn("already exists", str(ctx.exception))

    def test_freeze_run_approval_validation(self):
        """freeze_run validates approval reference against approvals.json or trailer."""
        crit = self.root / "docs/criteria.md"
        crit.parent.mkdir(parents=True, exist_ok=True)
        crit.write_text("# Criteria\n")
        test_file = self.root / "tests/test_a.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("def test_a(): pass\n")

        # Fabricated approval ref when approvals.json exists must be rejected
        approvals_file = self.root / "docs/_cgspec/07-state/approvals.json"
        write_json(approvals_file, {
            "schema": 1,
            "approvals": [
                {"id": "A-20261024-0001", "at": "2026-10-24T12:00:00Z", "excerpt": "approved R-20261024-0001"}
            ]
        })

        with self.assertRaises(CgspecError) as ctx:
            runs.freeze_run(self.root, "Goal", "T1", ["docs/criteria.md"], ["tests/test_a.py"],
                            [{"id": "u1", "owner": "b", "allowed_paths": ["src/**"]}],
                            run_id="R-20261024-0001", approval_ref="A-99999999-9999")
        self.assertIn("not registered in approvals.json", str(ctx.exception))

        # Real approval from approvals.json succeeds
        data = runs.freeze_run(self.root, "Goal", "T1", ["docs/criteria.md"], ["tests/test_a.py"],
                               [{"id": "u1", "owner": "b", "allowed_paths": ["src/**"]}],
                               run_id="R-20261024-0001", approval_ref="A-20261024-0001")
        self.assertEqual(data["approval"]["ref"], "A-20261024-0001")
        self.assertEqual(data["approval"]["source"], "message-hook")

    def test_malformed_run_records_fail_closed(self):
        """Malformed run records are not silently ignored and cause fail-closed behavior."""
        run_dir = self.root / "docs/_cgspec/05-runs/R-20261024-0001"
        run_dir.mkdir(parents=True, exist_ok=True)
        bad_json = run_dir / "run.json"
        bad_json.write_text("{malformed json", encoding="utf-8")

        # load_runs_with_errors reports error
        valid_runs, errors = runs.load_runs_with_errors(self.root)
        self.assertEqual(len(valid_runs), 0)
        self.assertTrue(len(errors) > 0)
        self.assertIn("malformed", errors[0].lower())

        # If CGSPEC_RUN or CGSPEC_UNIT points to malformed run, check_unit_scope blocks
        try:
            os.environ["CGSPEC_RUN"] = "R-20261024-0001"
            err = runs.check_unit_scope(self.root, "src/anything.py")
            self.assertIsNotNone(err)
            self.assertIn("malformed", err.lower())
        finally:
            os.environ.pop("CGSPEC_RUN", None)

    def test_check_unit_scope_explicit_identities_and_ambiguity(self):
        """check_unit_scope requires explicit identities, rejects unknown units, and detects ambiguity."""
        crit = self.root / "docs/criteria.md"
        crit.parent.mkdir(parents=True, exist_ok=True)
        crit.write_text("# Criteria\n")
        test_file = self.root / "tests/test_feature.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("def test_ok(): pass\n")

        runs.freeze_run(
            self.root,
            goal="Add feature",
            tier="T1",
            criteria_paths=["docs/criteria.md"],
            test_paths=["tests/test_feature.py"],
            units=[
                {"id": "u1", "owner": "builder1", "allowed_paths": ["src/login/**"], "status": "todo"},
                {"id": "u2", "owner": "builder2", "allowed_paths": ["src/signup/**"], "status": "todo"},
            ],
            run_id="R-20261024-0001",
        )

        # 1. Unknown CGSPEC_RUN must fail closed
        try:
            os.environ["CGSPEC_RUN"] = "R-20261024-9999"
            err = runs.check_unit_scope(self.root, "src/login/form.ts")
            self.assertIsNotNone(err)
            self.assertIn("does not exist", err)
        finally:
            os.environ.pop("CGSPEC_RUN", None)

        # 2. Unknown CGSPEC_UNIT must fail closed (NEVER silently permit writes)
        try:
            os.environ["CGSPEC_RUN"] = "R-20261024-0001"
            os.environ["CGSPEC_UNIT"] = "u_nonexistent"
            err = runs.check_unit_scope(self.root, "src/login/form.ts")
            self.assertIsNotNone(err)
            self.assertIn("unknown CGSPEC_UNIT 'u_nonexistent'", err)
        finally:
            os.environ.pop("CGSPEC_RUN", None)
            os.environ.pop("CGSPEC_UNIT", None)

        # 3. Multiple in-progress units without CGSPEC_UNIT must fail closed due to ambiguity
        runs.update_unit_status(self.root, "R-20261024-0001", "u1", "in-progress")
        runs.update_unit_status(self.root, "R-20261024-0001", "u2", "in-progress")

        try:
            os.environ["CGSPEC_RUN"] = "R-20261024-0001"
            # No CGSPEC_UNIT provided while both u1 and u2 are in-progress
            err = runs.check_unit_scope(self.root, "src/login/form.ts")
            self.assertIsNotNone(err)
            self.assertIn("ambiguous active unit", err)
            self.assertIn("specify CGSPEC_UNIT explicitly", err)
        finally:
            os.environ.pop("CGSPEC_RUN", None)

        # 4. Explicit CGSPEC_UNIT resolves ambiguity and enforces scoped path
        try:
            os.environ["CGSPEC_RUN"] = "R-20261024-0001"
            os.environ["CGSPEC_UNIT"] = "u1"
            # in-scope for u1
            self.assertIsNone(runs.check_unit_scope(self.root, "src/login/form.ts"))
            # out-of-scope for u1 (even though in u2)
            err = runs.check_unit_scope(self.root, "src/signup/form.ts")
            self.assertIsNotNone(err)
            self.assertIn("outside unit u1 allowed_paths", err)
            # editing frozen criteria or test blocked
            err_crit = runs.check_unit_scope(self.root, "docs/criteria.md")
            self.assertIn("is frozen in active run R-20261024-0001", err_crit)
        finally:
            os.environ.pop("CGSPEC_RUN", None)
            os.environ.pop("CGSPEC_UNIT", None)

    def test_ordinary_project_without_runs_is_compatible(self):
        """Ordinary project without active runs allows writes and is not blocked by run checks."""
        # Clean root, no runs dir
        self.assertIsNone(runs.check_unit_scope(self.root, "src/foo.py"))
        # But if an explicit CGSPEC_RUN is requested in an empty project, it must block
        try:
            os.environ["CGSPEC_RUN"] = "R-20261024-0001"
            err = runs.check_unit_scope(self.root, "src/foo.py")
            self.assertIsNotNone(err)
            self.assertIn("does not exist", err)
        finally:
            os.environ.pop("CGSPEC_RUN", None)

    def test_run_lifecycle_complete_and_supersede_unfreezes_for_new_work(self):
        """Completing or superseding a run unfreezes tests for future work while preserving history."""
        crit = self.root / "docs/criteria.md"
        crit.parent.mkdir(parents=True, exist_ok=True)
        crit.write_text("# Criteria\n")
        test_file = self.root / "tests/test_feature.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("def test_ok(): pass\n")

        runs.freeze_run(
            self.root,
            goal="Add feature",
            tier="T1",
            criteria_paths=["docs/criteria.md"],
            test_paths=["tests/test_feature.py"],
            units=[{"id": "u1", "owner": "builder", "allowed_paths": ["src/**"], "status": "in-progress"}],
            run_id="R-20261024-0001",
        )

        # While active, test is in frozen_run_files
        self.assertIn("tests/test_feature.py", runs.frozen_run_files(self.root))

        # Complete the run
        runs.complete_run(self.root, "R-20261024-0001")
        run_data, _ = runs.load_run_file(self.root / "docs/_cgspec/05-runs/R-20261024-0001/run.json")
        self.assertEqual(run_data["status"], "completed")
        self.assertIsNotNone(run_data["completed_at"])

        # Once completed, tests are no longer frozen for future tasks
        self.assertNotIn("tests/test_feature.py", runs.frozen_run_files(self.root))
        # Now a new task can freeze new criteria or tests or modify the test file without run block
        self.assertIsNone(runs.check_unit_scope(self.root, "tests/test_feature.py"))

        # Test supersede lifecycle
        runs.freeze_run(
            self.root,
            goal="Feature v2",
            tier="T1",
            criteria_paths=["docs/criteria.md"],
            test_paths=["tests/test_feature.py"],
            units=[{"id": "u1", "owner": "builder", "allowed_paths": ["src/**"], "status": "in-progress"}],
            run_id="R-20261024-0002",
        )
        self.assertIn("tests/test_feature.py", runs.frozen_run_files(self.root))

        # Supersede R-20261024-0002 with R-20261024-0003
        runs.supersede_run(self.root, "R-20261024-0002", superseded_by="R-20261024-0003")
        r2_data, _ = runs.load_run_file(self.root / "docs/_cgspec/05-runs/R-20261024-0002/run.json")
        self.assertEqual(r2_data["status"], "superseded")
        self.assertEqual(r2_data["superseded_by"], "R-20261024-0003")
        self.assertIsNotNone(r2_data["superseded_at"])

    def _setup_frozen_run_commit(self) -> tuple[str, Path, Path]:
        """Helper to create and commit a frozen run."""
        crit = self.root / "docs/criteria.md"
        crit.parent.mkdir(parents=True, exist_ok=True)
        crit.write_text("# Criteria\n")
        test_file = self.root / "tests/test_feature.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("def test_ok(): pass\n")

        runs.freeze_run(
            self.root,
            goal="Add feature",
            tier="T1",
            criteria_paths=["docs/criteria.md"],
            test_paths=["tests/test_feature.py"],
            units=[{"id": "u1", "owner": "builder", "allowed_paths": ["src/**"], "status": "todo"}],
            run_id="R-20261024-0001",
        )
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "freeze run")
        freeze_commit = git(self.root, "rev-parse", "HEAD").stdout.strip()
        run_json = self.root / "docs/_cgspec/05-runs/R-20261024-0001/run.json"
        return freeze_commit, test_file, run_json

    def test_check_run_commit_allows_clean_and_catches_modified_test(self):
        """check_run_commit passes on untouched runs and flags modified frozen tests."""
        freeze_commit, test_file, _ = self._setup_frozen_run_commit()

        (self.root / "src/a.ts").write_text("export const a = 2;\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "update code")
        view_clean = View.commit(self.root, git(self.root, "rev-parse", "HEAD").stdout.strip())
        self.assertEqual(runs.check_run_commit(view_clean), [])

        test_file.write_text("def test_tampered(): pass\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "modify test")
        view_tampered = View.commit(self.root, git(self.root, "rev-parse", "HEAD").stdout.strip())
        reasons = runs.check_run_commit(view_tampered)
        self.assertTrue(any("frozen tests file tests/test_feature.py was modified or is missing" in r for r in reasons))

    def test_check_run_commit_catches_tampered_or_deleted_run_json(self):
        """check_run_commit catches modifications to run metadata, unit definitions, and record deletion."""
        freeze_commit, _, run_json = self._setup_frozen_run_commit()

        # Tampering with tier
        data = json.loads(run_json.read_text(encoding="utf-8"))
        data["tier"] = "T2"
        run_json.write_text(json.dumps(data), encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "tamper run metadata")
        view_tampered = View.commit(self.root, git(self.root, "rev-parse", "HEAD").stdout.strip())
        reasons = runs.check_run_commit(view_tampered)
        self.assertTrue(any("frozen run criteria, tests, and metadata cannot change after frozen_at" in r for r in reasons))

        # Tampering with unit allowed_paths
        git(self.root, "reset", "--hard", freeze_commit)
        data = json.loads(run_json.read_text(encoding="utf-8"))
        data["units"][0]["allowed_paths"] = ["**"]
        run_json.write_text(json.dumps(data), encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "widen unit scope")
        view_widen = View.commit(self.root, git(self.root, "rev-parse", "HEAD").stdout.strip())
        reasons = runs.check_run_commit(view_widen)
        self.assertTrue(any("allowed_paths cannot change after frozen_at" in r for r in reasons))

        # Deleting run.json
        git(self.root, "reset", "--hard", freeze_commit)
        run_json.unlink()
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "delete run.json")
        view_deleted = View.commit(self.root, git(self.root, "rev-parse", "HEAD").stdout.strip())
        reasons = runs.check_run_commit(view_deleted)
        self.assertTrue(any("frozen run record may not be deleted" in r for r in reasons))

    def test_check_run_commit_allows_valid_status_transition(self):
        """check_run_commit permits unit status and run completion transitions."""
        freeze_commit, _, run_json = self._setup_frozen_run_commit()

        # Update unit status and complete run
        data = json.loads(run_json.read_text(encoding="utf-8"))
        data["units"][0]["status"] = "PASS"
        data["units"][0]["review_rounds"] = 1
        data["status"] = "completed"
        data["completed_at"] = "2026-10-24T12:00:00Z"
        run_json.write_text(json.dumps(data), encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "complete run")
        view_completed = View.commit(self.root, git(self.root, "rev-parse", "HEAD").stdout.strip())
        self.assertEqual(runs.check_run_commit(view_completed), [])

    def test_cli_run_freeze_show_complete_supersede(self):
        """cgspec_hook.py run CLI subcommands create, display, and transition runs."""
        crit = self.root / "docs/criteria.md"
        crit.parent.mkdir(parents=True, exist_ok=True)
        crit.write_text("# Criteria\n")
        test_file = self.root / "tests/test_feature.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("def test_ok(): pass\n")

        units_json = json.dumps([{"id": "u1", "owner": "builder", "allowed_paths": ["src/**"]}])
        # CLI freeze
        res = hook(
            self.root,
            "run",
            None,
            "freeze",
            "--goal", "CLI Test Run",
            "--tier", "T1",
            "--criteria", "docs/criteria.md",
            "--tests", "tests/test_feature.py",
            "--units", units_json,
            "--run-id", "R-20261024-0001",
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("frozen run R-20261024-0001", res.stdout)

        # CLI show
        res_show = hook(self.root, "run", None, "show", "R-20261024-0001")
        self.assertEqual(res_show.returncode, 0)
        show_data = json.loads(res_show.stdout)
        self.assertEqual(show_data["run_id"], "R-20261024-0001")
        self.assertEqual(show_data["status"], "active")

        # CLI complete
        res_comp = hook(self.root, "run", None, "complete", "R-20261024-0001")
        self.assertEqual(res_comp.returncode, 0)
        self.assertIn("completed run R-20261024-0001", res_comp.stdout)

        res_show_comp = hook(self.root, "run", None, "show", "R-20261024-0001")
        show_comp_data = json.loads(res_show_comp.stdout)
        self.assertEqual(show_comp_data["status"], "completed")

    def test_prove_failed_rejects_weakened_test_file(self):
        """prove_failed rejects tests modified between failed_at and HEAD."""
        set_test_command(self.root, ["python3", "{test_file}"])
        test_file = self.root / "tests/failing_check.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text(
            "import pathlib, sys\nsys.exit(0 if pathlib.Path('src/fixed.txt').exists() else 1)\n"
        )
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "add failing test")
        failed_at = git(self.root, "rev-parse", "HEAD").stdout.strip()

        # Case A: test_file is weakened/modified to pass
        test_file.write_text("import sys\nsys.exit(0)\n")
        record = {
            "_file": "docs/_cgspec/06-evidence/tests/failing.json",
            "test_id": "test-failing",
            "test_file": "tests/failing_check.py",
            "command": ["python3", "tests/failing_check.py"],
            "failed_at": failed_at,
        }
        write_json(self.root / record["_file"], record)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "weakened test")

        err = ci_gate.prove_failed(self.root, record)
        self.assertIsNotNone(err)
        self.assertIn("was modified after failed_at", err)
        self.assertIn("a failing test cannot be weakened to make it pass", err)

        # Case B: test_file is untouched, src/ fixed.txt fixes it honestly
        git(self.root, "reset", "--hard", failed_at)
        (self.root / "src/fixed.txt").write_text("fixed\n")
        write_json(self.root / record["_file"], record)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "honest fix")

        self.assertIsNone(ci_gate.prove_failed(self.root, record))

    def test_is_helper_call_detection(self):
        """is_helper_call detects Claude, Antigravity, and T3 helper/subagent invocations."""
        # Claude tools
        self.assertTrue(post_tool.is_helper_call({"tool_name": "Task"}))
        self.assertTrue(post_tool.is_helper_call({"tool_name": "Agent"}))
        self.assertFalse(post_tool.is_helper_call({"tool_name": "Edit"}))
        self.assertFalse(post_tool.is_helper_call({"tool_name": "Write"}))

        # Antigravity tools
        self.assertTrue(post_tool.is_helper_call({"toolCall": {"name": "invoke_subagent", "args": {}}}))
        self.assertTrue(post_tool.is_helper_call({"toolCall": {"name": "delegate_task", "args": {}}}))
        self.assertTrue(post_tool.is_helper_call({"toolCall": {"name": "mcp__t3_code__delegate_task", "args": {}}}))
        self.assertFalse(post_tool.is_helper_call({"toolCall": {"name": "write_to_file", "args": {}}}))

        # T3 call_mcp_tool delegate_task
        t3_payload = {
            "toolCall": {
                "name": "call_mcp_tool",
                "args": {"ToolName": "delegate_task", "ServerName": "t3-code"},
            }
        }
        self.assertTrue(post_tool.is_helper_call(t3_payload))

        # T3 other mcp tool
        t3_other = {
            "toolCall": {
                "name": "call_mcp_tool",
                "args": {"ToolName": "preview_status", "ServerName": "t3-code"},
            }
        }
        self.assertFalse(post_tool.is_helper_call(t3_other))


if __name__ == "__main__":
    unittest.main()
