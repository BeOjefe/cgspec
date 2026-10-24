"""Integration tests demonstrating subagent run scope and frozen-test enforcement
in a disposable installed project with real pre-tool, pre-commit, and CI hooks."""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

from tests.helpers import TempDir, approve, claude_payload, git, git_project, hook, install, make_slice, run_script, write_json
from _lib import runs


def call_hook(root: Path, event: str, payload: dict | None = None, *extra: str, env: dict | None = None):
    return run_script("cgspec_hook.py", event, "--root", str(root), *extra,
                      stdin=json.dumps(payload) if payload is not None else "", env=env)


class RunIntegrationTests(unittest.TestCase):
    """Disposable installed project integration tests for run enforcement."""

    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git_project(self.root)

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def test_end_to_end_disposable_project_run_lifecycle(self):
        """End-to-end test on installed disposable project: freeze, pre-tool gate, pre-commit, and complete."""
        # Setup initial criteria and test file
        crit = self.root / "tests/criteria.txt"
        crit.parent.mkdir(parents=True, exist_ok=True)
        crit.write_text("# Requirements\nMust be fast.\n")

        test_file = self.root / "tests/test_feature.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("def test_core(): pass\n")

        # Set up an approved slice covering src/** and tests/**
        make_slice(self.root, number="001", scope="src/**, tests/**")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "initial baseline with slice")
        base_commit = git(self.root, "rev-parse", "HEAD").stdout.strip()

        # Declare active T1 tier for SLICE-001
        call_hook(self.root, "tier", None, "set", "--tier", "T1", "--slice", "SLICE-001", "--reason", "feature work")

        # Step 1: Freeze run via CLI with unit restricted to src/login/**
        units_spec = json.dumps([
            {"id": "unit-login", "owner": "builder-auth", "allowed_paths": ["src/login/**"]}
        ])
        freeze_res = call_hook(
            self.root,
            "run",
            None,
            "freeze",
            "--goal", "Implement login module",
            "--tier", "T1",
            "--slice", "SLICE-001",
            "--criteria", "tests/criteria.txt",
            "--tests", "tests/test_feature.py",
            "--units", units_spec,
            "--run-id", "R-20261024-0001",
        )
        self.assertEqual(freeze_res.returncode, 0, f"Freeze failed: {freeze_res.stderr}")
        self.assertIn("frozen run R-20261024-0001", freeze_res.stdout)

        # Commit frozen run record
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "freeze R-20261024-0001")
        frozen_commit = git(self.root, "rev-parse", "HEAD").stdout.strip()

        # Step 2: Pre-tool enforcement with CGSPEC_UNIT="unit-login"
        env_auth = os.environ.copy()
        env_auth["CGSPEC_RUN"] = "R-20261024-0001"
        env_auth["CGSPEC_UNIT"] = "unit-login"

        # Case 2A: Out-of-scope write (src/billing/pay.py is in slice src/** but outside unit-login)
        payload_blocked = claude_payload(
            self.root, "Write", file_path="src/billing/pay.py", content="def pay(): pass\n"
        )
        res_blocked = call_hook(self.root, "pre-tool", payload_blocked, "--tool", "claude", env=env_auth)
        self.assertEqual(res_blocked.returncode, 2, "Out-of-scope write was not blocked!")
        self.assertIn("outside unit unit-login allowed_paths", res_blocked.stderr)

        # Case 2B: Tampering with frozen test file must be BLOCKED
        payload_tamper_test = claude_payload(
            self.root, "Write", file_path="tests/test_feature.py", content="def test_core(): return True\n"
        )
        res_tamper = call_hook(self.root, "pre-tool", payload_tamper_test, "--tool", "claude", env=env_auth)
        self.assertEqual(res_tamper.returncode, 2, "Writing to frozen test was not blocked!")
        self.assertIn("is frozen in active run R-20261024-0001", res_tamper.stderr)

        # Case 2C: In-scope write (src/login/auth.py) must be ALLOWED
        (self.root / "src/login").mkdir(parents=True, exist_ok=True)
        (self.root / "src/login/auth.py").write_text("def login(): pass\n")
        payload_allowed = claude_payload(
            self.root, "Write", file_path="src/login/auth.py", content="def login(): pass\n"
        )
        res_allowed = call_hook(self.root, "pre-tool", payload_allowed, "--tool", "claude", env=env_auth)
        self.assertEqual(res_allowed.returncode, 0, f"In-scope write blocked: {res_allowed.stderr}")

        # Step 3: Staged / Pre-commit gate enforcement
        # Modify frozen test and stage it: pre-commit must FAIL
        test_file.write_text("def test_core(): pass # modified\n")
        git(self.root, "add", "tests/test_feature.py")
        pre_commit_res = call_hook(self.root, "pre-commit", None)
        self.assertEqual(pre_commit_res.returncode, 1, "Pre-commit did not catch modified frozen test!")
        self.assertIn("frozen tests file tests/test_feature.py was modified", pre_commit_res.stdout)

        # Revert the test file
        git(self.root, "checkout", "--", "tests/test_feature.py")

        # Step 4: Complete the run via CLI
        complete_res = call_hook(self.root, "run", None, "complete", "R-20261024-0001")
        self.assertEqual(complete_res.returncode, 0, f"Complete run failed: {complete_res.stderr}")
        self.assertIn("completed run R-20261024-0001", complete_res.stdout)

        # Commit completed run record
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "complete R-20261024-0001")

        # Step 5: After run is completed, subsequent authorized task can modify test
        env_new = os.environ.copy()
        env_new.pop("CGSPEC_RUN", None)
        env_new.pop("CGSPEC_UNIT", None)
        test_file.write_text("def test_core(): pass # new task update\n")
        payload_new_task = claude_payload(
            self.root, "Write", file_path="tests/test_feature.py", content="def test_core(): pass # new task update\n"
        )
        res_new_task = call_hook(self.root, "pre-tool", payload_new_task, "--tool", "claude", env=env_new)
        self.assertEqual(res_new_task.returncode, 0, f"New task was blocked on completed test: {res_new_task.stderr}")

    def test_pre_tool_rejects_symlink_escape_and_unknown_identities(self):
        """pre-tool gate blocks symlink escapes and unknown run/unit identities fail-closed."""
        # 1. Unknown CGSPEC_RUN
        env_unknown_run = os.environ.copy()
        env_unknown_run["CGSPEC_RUN"] = "R-20261024-9999"
        payload = claude_payload(self.root, "Write", file_path="src/login/form.ts", content="export const x = 1;\n")
        res_run = call_hook(self.root, "pre-tool", payload, "--tool", "claude", env=env_unknown_run)
        self.assertEqual(res_run.returncode, 2)
        self.assertIn("requested run R-20261024-9999 does not exist", res_run.stderr)

        # 2. Unknown CGSPEC_UNIT
        env_unknown_unit = os.environ.copy()
        env_unknown_unit["CGSPEC_UNIT"] = "unit_missing"
        res_unit = call_hook(self.root, "pre-tool", payload, "--tool", "claude", env=env_unknown_unit)
        self.assertEqual(res_unit.returncode, 2)
        self.assertIn("unknown CGSPEC_UNIT 'unit_missing'", res_unit.stderr)

        # 3. Symlink escape write attempt
        link_dir = self.root / "src/escaped_dir"
        link_dir.parent.mkdir(parents=True, exist_ok=True)
        try:
            link_dir.symlink_to("/tmp", target_is_directory=True)
            payload_escape = claude_payload(self.root, "Write", file_path="src/escaped_dir/pw.txt", content="secret\n")
            res_escape = call_hook(self.root, "pre-tool", payload_escape, "--tool", "claude", env=env_unknown_unit)
            self.assertEqual(res_escape.returncode, 2)
        except OSError:
            pass

    def test_commit_gate_rejects_tampered_run_and_ci_passes_clean_run(self):
        """Pre-commit and CI gates catch run tampering and pass clean runs."""
        crit = self.root / "tests/criteria.txt"
        crit.parent.mkdir(parents=True, exist_ok=True)
        crit.write_text("# Criteria\n")
        test_file = self.root / "tests/test_feature.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("def test_ok(): pass\n")

        make_slice(self.root, number="001", scope="src/**, tests/**")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "baseline")
        base_commit = git(self.root, "rev-parse", "HEAD").stdout.strip()

        # Freeze run via CLI
        call_hook(
            self.root, "run", None, "freeze",
            "--goal", "Clean task",
            "--tier", "T1",
            "--slice", "SLICE-001",
            "--criteria", "tests/criteria.txt",
            "--tests", "tests/test_feature.py",
            "--units", json.dumps([{"id": "u1", "owner": "b", "allowed_paths": ["src/**"]}]),
            "--run-id", "R-20261024-0001",
        )
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "freeze R-20261024-0001")

        # Case A: Commit that tampers with unit scope in run.json
        run_json = self.root / "docs/_cgspec/05-runs/R-20261024-0001/run.json"
        data = json.loads(run_json.read_text(encoding="utf-8"))
        data["units"][0]["allowed_paths"] = ["**"]
        run_json.write_text(json.dumps(data, indent=2), encoding="utf-8")
        git(self.root, "add", "docs/_cgspec/05-runs/R-20261024-0001/run.json")

        pre_commit_res = call_hook(self.root, "pre-commit", None)
        self.assertEqual(pre_commit_res.returncode, 1)
        self.assertIn("allowed_paths cannot change after frozen_at", pre_commit_res.stdout)

        # Revert tampering
        git(self.root, "checkout", "--", "docs/_cgspec/05-runs/R-20261024-0001/run.json")

        # Case B: Clean CI evaluation
        ci_res = call_hook(self.root, "ci", None, "--base", base_commit)
        self.assertEqual(ci_res.returncode, 0, f"CI failed: {ci_res.stdout}{ci_res.stderr}")
        self.assertIn("CGSpec governance passed", ci_res.stdout)


if __name__ == "__main__":
    unittest.main()
