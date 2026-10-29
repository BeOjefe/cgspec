"""Staged-candidate enforcement for issue #30, independent of the working tree."""

from __future__ import annotations

import json
import unittest

from tests.helpers import (
    TempDir,
    approve,
    git,
    git_project,
    make_git_plan,
    make_slice,
    run_script,
    set_test_command,
    write_json,
)
from tests.unit.test_start_gate import draft
from _lib.commit_gate import evaluate
from _lib.gitview import View


class StartCommitTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git_project(self.root)
        self.failed_at = git(self.root, "rev-parse", "HEAD").stdout.strip()
        set_test_command(self.root, ["python3", "{test_file}"])
        self.slice_path = make_slice(self.root, scope="src/login/**,tests/**,docs/prototypes/**")
        source = self.root / ".cgspec-scratch/start.json"
        source.parent.mkdir(exist_ok=True)
        source.write_text(json.dumps(draft()))
        self.start("set", "--file", str(source))
        ref = approve(self.root, "approve SLICE-001")
        self.start("agree", "--approval", ref)
        self.start("ready")
        self.start("begin", "--outcome", "OUT-login")
        run_script(
            "cgspec_hook.py", "tier", "set", "--tier", "T1", "--reason", "Implement sign-in",
            "--slice", "SLICE-001", "--root", str(self.root),
        )
        make_git_plan(self.root, outcome_id="OUT-login")
        (self.root / "src/login/form.ts").write_text("export const f = 2;\n")
        (self.root / "tests").mkdir(exist_ok=True)
        (self.root / "tests/login.test.ts").write_text("test('sign-in', () => {});\n")
        write_json(self.root / "docs/_cgspec/06-evidence/tests/login.json", {
            "schema": 1,
            "test_id": "login",
            "test_file": "tests/login.test.ts",
            "command": ["python3", "tests/login.test.ts"],
            "failed_at": self.failed_at,
            "passed_at": None,
            "covers": ["src/login/form.ts"],
            "slice": "SLICE-001",
            "recorded": "2026-10-28T00:00:00Z",
        })
        sha = "a" * 64
        rev = git(self.root, "rev-parse", "HEAD").stdout.strip()
        write_json(self.root / "docs/prototypes/parity.json", {
            "schema": 1,
            "covers": ["src/login/form.ts"],
            "build_mode": "development",
            "data_source": "unknown",
            "authentication_method": "none",
            "mock_switch_state": "absent",
            "app": {"build": ["true"], "serve": ["true"], "ready_url": "http://localhost:0"},
            "states": [{"name": "default", "route": "/", "data_set": "empty", "screen": "login",
                        "journey": "login", "baselines": {
                            "desktop-light": {"file": "login-desktop.png", "sha256": sha,
                                "approval": "approved", "approval_sha256": sha,
                                "reviewer": "test", "approved_at": "2026-01-01T00:00:00Z", "revision": rev},
                            "desktop-dark": {"file": "login-desktop-dark.png", "sha256": sha,
                                "approval": "approved", "approval_sha256": sha,
                                "reviewer": "test", "approved_at": "2026-01-01T00:00:00Z", "revision": rev},
                            "mobile-light": {"file": "login-mobile.png", "sha256": sha,
                                "approval": "approved", "approval_sha256": sha,
                                "reviewer": "test", "approved_at": "2026-01-01T00:00:00Z", "revision": rev},
                            "mobile-dark": {"file": "login-mobile-dark.png", "sha256": sha,
                                "approval": "approved", "approval_sha256": sha,
                                "reviewer": "test", "approved_at": "2026-01-01T00:00:00Z", "revision": rev}}}],
            "review": {"approval": "approved", "approval_sha256": sha, "reviewer": "test", "approved_at": "2026-01-01T00:00:00Z",
                       "revision": rev, "base_revision": rev, "functional_revision": rev, "visual_revision": rev,
                       "content_sha256": sha, "diff_sha256": sha},
        })
        git(self.root, "add", "docs", "src", "tests")

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def start(self, action: str, *args: str):
        result = run_script(
            "cgspec_hook.py", "start", action, "--slice", "SLICE-001", "--root", str(self.root), *args,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def reasons(self):
        return evaluate(self.root, View.staged(self.root))

    def test_ready_active_agreement_passes_staged_candidate(self):
        self.assertEqual(self.reasons(), [])

    def test_unstaged_ready_file_cannot_authorize_staged_code(self):
        git(self.root, "reset", "-q", "HEAD", str(self.slice_path.with_suffix(".start.json")))
        reasons = self.reasons()
        self.assertTrue(any("no success agreement" in reason for reason in reasons), reasons)

    def test_staged_probe_input_cannot_be_replaced_by_passing_working_tree(self):
        path = self.slice_path.with_suffix(".start.json")
        record = json.loads(path.read_text())
        from hashlib import sha256
        probe = self.root / "probe.py"
        probe.write_text("raise SystemExit(1)\n")
        git(self.root, "add", "probe.py")
        record["prerequisites"][0]["check"].update(argv=["python3", "probe.py"], inputs=["probe.py"])
        record["readiness"]["checks"][0]["input_hashes"] = {"probe.py": sha256(b"pass\n").hexdigest()}
        from _lib.start import definition_hash
        record["readiness"]["definition_hash"] = definition_hash(record)
        record["approval"]["definition_hash"] = definition_hash(record)
        path.write_text(json.dumps(record))
        git(self.root, "add", str(path))
        probe.write_text("pass\n")
        reasons = self.reasons()
        self.assertTrue(any("staged readiness input probe.py" in reason for reason in reasons), reasons)

    def test_unclassified_root_source_requires_agreement(self):
        from _lib.start_gate import is_implementation
        self.assertTrue(is_implementation("server.py", {"code": ["src/**"], "tests": ["tests/**"]}))
        self.assertTrue(is_implementation("server.cpp", {"code": ["src/**"], "tests": ["tests/**"]}))
        self.assertTrue(is_implementation("App.swift", {"code": ["src/**"], "tests": ["tests/**"]}))
        self.assertFalse(is_implementation("tests/server.test.ts", {"code": ["**/*.ts"], "tests": ["tests/**"]}))

    def test_preparatory_test_commit_does_not_require_start(self):
        git(self.root, "reset", "-q", "HEAD", str(self.slice_path.with_suffix(".start.json")))
        git(self.root, "reset", "-q", "HEAD", "src/login/form.ts")
        git(self.root, "reset", "-q", "HEAD", "docs/_cgspec/06-evidence/tests/login.json")
        self.assertEqual(self.reasons(), [])

    def test_staged_blocked_outcome_cannot_use_working_tree_override(self):
        path = self.slice_path.with_suffix(".start.json")
        staged = json.loads(path.read_text())
        staged["readiness"]["checks"][0]["status"] = "BLOCKED"
        staged["readiness"]["checks"][0]["detail"] = "The real test database is unavailable"
        path.write_text(json.dumps(staged))
        git(self.root, "add", str(path))
        staged["readiness"]["checks"][0]["status"] = "PASS"
        staged["readiness"]["checks"][0]["detail"] = "Probe passed: the real test database is reachable"
        path.write_text(json.dumps(staged))
        reasons = self.reasons()
        self.assertTrue(any("Probe passed" not in reason and "database" in reason for reason in reasons), reasons)

    def test_mock_switch_is_rechecked_at_commit(self):
        from unittest.mock import patch
        from _lib.start import definition_hash
        path = self.slice_path.with_suffix(".start.json")
        record = json.loads(path.read_text())
        evaluation = record["outcomes"][0]["evaluation"]
        record["outcomes"][0]["development"] = {"uses_mocks": True, "data_source": "fixture"}
        record["readiness"]["mocks_allowed"] = True
        record["readiness"]["definition_hash"] = definition_hash(record)
        record["prior_approvals"].append(record["approval"]["ref"])
        record["approval"]["ref"] = approve(self.root, "approve SLICE-001")
        record["approval"]["definition_hash"] = definition_hash(record)
        path.write_text(json.dumps(record))
        git(self.root, "add", "docs")
        with patch.dict("os.environ", {"CGSPEC_ALLOW_MOCKS": "0"}):
            reasons = self.reasons()
        self.assertTrue(any("CGSPEC_ALLOW_MOCKS=0" in reason for reason in reasons), reasons)

    def test_malformed_approval_shape_is_a_finding_not_a_crash(self):
        path = self.slice_path.with_suffix(".start.json")
        record = json.loads(path.read_text())
        record["approval"] = "not-an-object"
        path.write_text(json.dumps(record))
        git(self.root, "add", "docs")
        reasons = self.reasons()
        self.assertTrue(any("approval" in reason for reason in reasons), reasons)

    def test_missing_execution_timestamp_cannot_authorize_code(self):
        path = self.slice_path.with_suffix(".start.json")
        record = json.loads(path.read_text())
        record["readiness"]["ran_at"] = None
        path.write_text(json.dumps(record))
        git(self.root, "add", "docs")
        self.assertTrue(any("execution timestamp" in reason for reason in self.reasons()))

    def test_missing_declared_probe_hash_cannot_authorize_code(self):
        path = self.slice_path.with_suffix(".start.json")
        record = json.loads(path.read_text())
        record["prerequisites"][0]["check"]["inputs"] = ["probe.py"]
        from _lib.start import definition_hash
        record["readiness"]["definition_hash"] = definition_hash(record)
        record["approval"]["definition_hash"] = definition_hash(record)
        path.write_text(json.dumps(record))
        git(self.root, "add", "docs")
        self.assertTrue(any("missing declared probe input hashes" in reason for reason in self.reasons()))

    def test_uncommitted_trailer_claim_does_not_approve_start(self):
        other = self.root / ".cgspec-scratch/other.json"
        other.write_text(json.dumps(draft()))
        run_script(
            "cgspec_hook.py", "start", "set", "--slice", "SLICE-001", "--file", str(other),
            "--root", str(self.root),
        )
        result = run_script(
            "cgspec_hook.py", "start", "agree", "--slice", "SLICE-001", "--approval", "trailer",
            "--root", str(self.root),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("committed and signed", result.stderr)


if __name__ == "__main__":
    unittest.main()
