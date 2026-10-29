"""Unit tests for subagent run enforcement, test immutability, and helper detection."""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

from tests.helpers import TempDir, approve, git, git_project, hook, run_script, set_test_command, write_json
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
            outcomes=[],
        )
        self.assertIn("tests/test_feature.py", runs.frozen_run_files(self.root))

        # A normal run cannot silently replace it.
        with self.assertRaisesRegex(CgspecError, "replacement run not found"):
            runs.supersede_run(self.root, "R-20261024-0002", superseded_by="R-20261024-0003")

        approval = approve(self.root, "approve supersession R-20261024-0002 to R-20261024-0003")
        runs.freeze_run(
            self.root,
            goal="Feature v3",
            tier="T1",
            criteria_paths=["docs/criteria.md"],
            test_paths=["tests/test_feature.py"],
            units=[{"id": "u1", "owner": "builder", "allowed_paths": ["src/**"], "status": "todo"}],
            run_id="R-20261024-0003",
            outcomes=[],
            supersession={
                "replaces": "R-20261024-0002", "reason": "replace the implementation direction",
                "approval_ref": approval,
                "links": {"agreements": [{"old": "docs/criteria.md", "new": "docs/criteria.md"}],
                          "outcomes": [],
                          "tests": [{"old": "tests/test_feature.py", "new": "tests/test_feature.py"}],
                          "proofs": []},
            },
        )
        runs.supersede_run(self.root, "R-20261024-0002", superseded_by="R-20261024-0003")
        r2_data, _ = runs.load_run_file(self.root / "docs/_cgspec/05-runs/R-20261024-0002/run.json")
        self.assertEqual(r2_data["status"], "superseded")
        self.assertEqual(r2_data["superseded_by"], "R-20261024-0003")
        self.assertIsNotNone(r2_data["superseded_at"])
        r3_data, _ = runs.load_run_file(self.root / "docs/_cgspec/05-runs/R-20261024-0003/run.json")
        self.assertEqual(r3_data["supersession"]["approval"]["ref"], approval)
        self.assertEqual(r3_data["supersession"]["links"]["tests"][0]["old"], "tests/test_feature.py")

    def test_supersession_requires_approval_and_preserves_every_required_outcome_and_proof(self):
        criteria = self.root / "docs/criteria-old.md"
        criteria.parent.mkdir(parents=True, exist_ok=True)
        criteria.write_text("# Old criteria\n", encoding="utf-8")
        test_file = self.root / "tests/test_old.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("def test_old(): pass\n", encoding="utf-8")
        proof = self.root / "docs/_cgspec/06-evidence/tests/old.json"
        write_json(proof, {"schema": 1, "test_id": "tests/test_old.py::test_old", "test_file": "tests/test_old.py",
                           "command": ["python3", "tests/test_old.py"], "failed_at": "aaaaaaa",
                           "covers": ["src/old.py"], "slice": "SLICE-001", "recorded": "2026-10-28T00:00:00Z"})
        write_json(self.root / "docs/slices/SLICE-001-replacement.start.json", {
            "outcomes": [{"id": "OUT-required"}],
        })
        runs.freeze_run(
            self.root, "Old direction", "T2", ["docs/criteria-old.md"], ["tests/test_old.py"],
            [{"id": "u1", "owner": "builder", "allowed_paths": ["src/**"]}],
            run_id="R-20261024-0010", slice_id="SLICE-001", outcomes=["OUT-required"],
            proof_paths=["docs/_cgspec/06-evidence/tests/old.json"],
        )
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "freeze active old direction")
        replacement_criteria = self.root / "docs/criteria-new.md"
        replacement_criteria.write_text("# New criteria\n", encoding="utf-8")
        replacement_test = self.root / "tests/test_new.py"
        replacement_test.write_text("def test_new(): pass\n", encoding="utf-8")
        replacement_proof = self.root / "docs/_cgspec/06-evidence/tests/new.json"
        write_json(replacement_proof, {
            "schema": 1,
            "test_id": "tests/test_new.py::test_new",
            "test_file": "tests/test_new.py",
            "command": ["python3", "tests/test_new.py"],
            "runner_id": "unit",
            "runner_hash": "a" * 64,
            "selector": "tests/test_new.py",
            "test_semantics": {
                "adapter": "command-json-v1",
                "fingerprint": "b" * 64,
                "dependencies": [],
            },
            "failed_at": "aaaaaaa",
            "runner_id": "unit", "runner_hash": "a" * 64, "selector": "tests/test_new.py",
            "test_semantics": {"adapter": "command-json-v1", "fingerprint": "b" * 64, "dependencies": []},
            "covers": ["src/new.py"],
            "slice": "SLICE-001",
            "recorded": "2026-10-28T00:00:00Z",
        })
        links = {
            "agreements": [{"old": "docs/criteria-old.md", "new": "docs/criteria-new.md"}],
            "outcomes": [],
            "tests": [{"old": "tests/test_old.py", "new": "tests/test_new.py"}],
            "proofs": [{"old": "docs/_cgspec/06-evidence/tests/old.json",
                        "new": "docs/_cgspec/06-evidence/tests/new.json"}],
        }
        with self.assertRaisesRegex(CgspecError, "explicit approval"):
            runs.freeze_run(
                self.root, "New direction", "T2", ["docs/criteria-new.md"], ["tests/test_new.py"],
                [{"id": "u1", "owner": "builder", "allowed_paths": ["src/**"]}],
                run_id="R-20261024-0011", slice_id="SLICE-001", outcomes=["OUT-required"],
                proof_paths=["docs/_cgspec/06-evidence/tests/new.json"],
                supersession={"replaces": "R-20261024-0010", "reason": "approved architecture replacement",
                              "links": links},
            )
        generic = approve(self.root, "approved, go ahead")
        with self.assertRaisesRegex(CgspecError, "must explicitly name"):
            runs.freeze_run(
                self.root, "New direction", "T2", ["docs/criteria-new.md"], ["tests/test_new.py"],
                [{"id": "u1", "owner": "builder", "allowed_paths": ["src/**"]}],
                run_id="R-20261024-0011", slice_id="SLICE-001", outcomes=["OUT-required"],
                proof_paths=["docs/_cgspec/06-evidence/tests/new.json"],
                supersession={"replaces": "R-20261024-0010", "reason": "approved architecture replacement",
                              "approval_ref": generic, "links": links},
            )
        approval = approve(self.root, "approve supersession R-20261024-0010 to R-20261024-0011")
        with self.assertRaisesRegex(CgspecError, "still-required references: OUT-required"):
            runs.freeze_run(
                self.root, "New direction", "T2", ["docs/criteria-new.md"], ["tests/test_new.py"],
                [{"id": "u1", "owner": "builder", "allowed_paths": ["src/**"]}],
                run_id="R-20261024-0011", slice_id="SLICE-001", outcomes=["OUT-required"],
                proof_paths=["docs/_cgspec/06-evidence/tests/new.json"],
                supersession={"replaces": "R-20261024-0010", "reason": "approved architecture replacement",
                              "approval_ref": approval, "links": links},
            )
        links["outcomes"] = [{"old": "OUT-required", "new": "OUT-required"}]
        runs.freeze_run(
            self.root, "New direction", "T2", ["docs/criteria-new.md"], ["tests/test_new.py"],
            [{"id": "u1", "owner": "builder", "allowed_paths": ["src/**"]}],
            run_id="R-20261024-0011", slice_id="SLICE-001", outcomes=["OUT-required"],
            proof_paths=["docs/_cgspec/06-evidence/tests/new.json"],
            supersession={"replaces": "R-20261024-0010", "reason": "approved architecture replacement",
                          "approval_ref": approval, "links": links},
        )
        old_before = json.loads((self.root / "docs/_cgspec/05-runs/R-20261024-0010/run.json").read_text())
        runs.supersede_run(self.root, "R-20261024-0010", "R-20261024-0011")
        old_after = json.loads((self.root / "docs/_cgspec/05-runs/R-20261024-0010/run.json").read_text())
        for field in runs.FROZEN_FIELDS:
            self.assertEqual(old_before.get(field), old_after.get(field))
        self.assertEqual(old_after["status"], "superseded")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "approved architectural supersession")
        committed = git(self.root, "rev-parse", "HEAD").stdout.strip()
        self.assertEqual(runs.check_run_commit(View.commit(self.root, committed)), [])
        write_json(proof, {"historical": "rewritten"})
        git(self.root, "add", proof.relative_to(self.root).as_posix())
        self.assertTrue(any("frozen proofs file" in reason for reason in
                            runs.check_run_commit(View.staged(self.root))))

    def test_new_terminal_run_is_rejected_before_it_can_bypass_supersession(self):
        criteria = self.root / "docs/criteria.md"
        criteria.parent.mkdir(parents=True, exist_ok=True)
        criteria.write_text("# Criteria\n", encoding="utf-8")
        test_file = self.root / "tests/test_feature.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("def test_feature(): pass\n", encoding="utf-8")
        data = runs.freeze_run(
            self.root, "Injected history", "T1", ["docs/criteria.md"],
            ["tests/test_feature.py"],
            [{"id": "u1", "owner": "builder", "allowed_paths": ["src/**"]}],
            run_id="R-20261024-0020", outcomes=[],
        )
        data.update(status="superseded", superseded_by="R-20261024-0021",
                    superseded_at="2026-10-28T00:00:00Z")
        write_json(self.root / "docs/_cgspec/05-runs/R-20261024-0020/run.json", data)
        git(self.root, "add", "-A")
        reasons = runs.check_run_commit(View.staged(self.root))
        self.assertTrue(any("newly added runs must start active" in reason for reason in reasons))

    def test_supersession_rejects_self_linked_and_non_pair_proofs(self):
        from _lib import run_supersession

        proof_path = "docs/_cgspec/06-evidence/tests/old.json"
        write_json(self.root / proof_path, {
            "schema": 1, "test_id": "tests/test_old.py::test_old",
            "test_file": "tests/test_old.py", "command": ["python3", "tests/test_old.py"],
            "failed_at": "aaaaaaa",
            "runner_id": "unit", "runner_hash": "a" * 64, "selector": "tests/test_new.py",
            "test_semantics": {"adapter": "command-json-v1", "fingerprint": "b" * 64, "dependencies": []}, "covers": ["src/old.py"], "slice": "SLICE-001",
            "recorded": "2026-10-28T00:00:00Z",
        })
        old = {"run_id": "R-20261024-0030", "proofs": [{"path": proof_path}],
               "tests": [{"path": "tests/test_old.py"}], "outcomes": [], "criteria": []}
        new = {"run_id": "R-20261024-0031", "slice": "SLICE-001",
               "proofs": [{"path": proof_path}], "tests": [{"path": "tests/test_old.py"}],
               "outcomes": [], "criteria": [],
               "supersession": {"links": {"proofs": [{"old": proof_path, "new": proof_path}]}}}
        reader = lambda path: (self.root / path).read_bytes() if (self.root / path).is_file() else None
        reasons = run_supersession.proof_link_errors(old, new, reader)
        self.assertIn("replacement proof must be distinct from every retired proof", reasons)

        new["proofs"] = [{"path": "docs/criteria.md"}]
        new["supersession"]["links"]["proofs"][0]["new"] = "docs/criteria.md"
        reasons = run_supersession.proof_link_errors(old, new, reader)
        self.assertIn("replacement proof must name a test-pair record", reasons)

    def test_omitted_outcomes_do_not_become_an_empty_inventory(self):
        criteria = self.root / "docs/criteria.md"
        criteria.parent.mkdir(parents=True, exist_ok=True)
        criteria.write_text("# Criteria\n", encoding="utf-8")
        test_file = self.root / "tests/test_feature.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("def test_feature(): pass\n", encoding="utf-8")
        old = runs.freeze_run(
            self.root, "Legacy run", "T1", ["docs/criteria.md"], ["tests/test_feature.py"],
            [{"id": "u1", "owner": "builder", "allowed_paths": ["src/**"]}],
            run_id="R-20261024-0040",
        )
        self.assertNotIn("outcomes", old)
        approval = approve(self.root, "approve supersession R-20261024-0040 to R-20261024-0041")
        with self.assertRaisesRegex(CgspecError, "outcomes inventory is unknown"):
            runs.freeze_run(
                self.root, "Replacement", "T1", ["docs/criteria.md"], ["tests/test_feature.py"],
                [{"id": "u1", "owner": "builder", "allowed_paths": ["src/**"]}],
                run_id="R-20261024-0041", outcomes=[],
                supersession={
                    "replaces": "R-20261024-0040", "reason": "replace legacy direction",
                    "approval_ref": approval,
                    "links": {"agreements": [{"old": "docs/criteria.md", "new": "docs/criteria.md"}],
                              "outcomes": [],
                              "tests": [{"old": "tests/test_feature.py", "new": "tests/test_feature.py"}],
                              "proofs": []},
                },
            )

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

    def test_legacy_run_without_status_field_is_treated_as_completed(self):
        """Legacy 0.2.0 run.json files without top-level status are treated as completed."""
        _, test_file, run_json = self._setup_frozen_run_commit()
        data = json.loads(run_json.read_text(encoding="utf-8"))
        del data["status"]
        run_json.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "legacy run without status")
        test_file.write_text("def test_later_slice(): pass\n", encoding="utf-8")
        git(self.root, "add", "-A")
        self.assertEqual(runs.check_run_commit(View.staged(self.root)), [])
        self.assertIsNone(runs.check_unit_scope(self.root, "src/unrelated.ts"))

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
