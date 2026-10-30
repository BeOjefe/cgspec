"""Project-wide implementation preflight and protected-branch policy."""

from __future__ import annotations

import json
import unittest

from tests.helpers import TempDir, approve, doctor, git, git_project, make_slice, run_script, write_json
from tests.unit.test_capabilities import CapabilityFixture, capability


class GlobalCapabilityPolicyTests(CapabilityFixture, unittest.TestCase):
    def configure(self, *ids: str) -> None:
        path = self.root / "docs/_cgspec/project.json"
        data = json.loads(path.read_text())
        data["implementation_capabilities"] = list(ids)
        write_json(path, data)

    def approve_empty_prerequisite_slice(self) -> None:
        self.draft["prerequisites"] = []
        self.set_draft()
        self.agree()

    def test_empty_slice_prerequisites_cannot_bypass_global_preflight(self):
        self.configure("CAP-github-browser")
        self.set_registry(capability(code="raise SystemExit(4)"))
        self.agree_registry()
        self.approve_empty_prerequisite_slice()
        result = self.cli("ready", "--slice", "SLICE-001")
        self.assertEqual(result.returncode, 2)
        self.assertIn("CAP-github-browser", result.stderr)

    def test_complete_global_preflight_unlocks_every_outcome_and_binds_policy(self):
        self.configure("CAP-github-browser")
        self.set_registry()
        self.agree_registry()
        self.approve_empty_prerequisite_slice()
        self.assertEqual(self.cli("ready", "--slice", "SLICE-001").returncode, 0)
        record = json.loads(self.start_path().read_text())
        check = record["readiness"]["checks"][0]
        self.assertEqual(check["id"], "REQ-PREFLIGHT-CAP-github-browser")
        self.assertIn("docs/_cgspec/project.json", check["input_hashes"])
        self.assertEqual(self.cli("begin", "--slice", "SLICE-001", "--outcome", "OUT-login").returncode, 0)

    def test_project_policy_change_invalidates_readiness(self):
        self.configure("CAP-github-browser")
        self.set_registry(capability(), capability("CAP-whatsapp", kind="human_contact"))
        self.agree_registry()
        self.approve_empty_prerequisite_slice()
        self.assertEqual(self.cli("ready", "--slice", "SLICE-001").returncode, 0)
        self.configure("CAP-github-browser", "CAP-whatsapp")
        result = self.cli("begin", "--slice", "SLICE-001", "--outcome", "OUT-login")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("rerun start ready", result.stderr)

    def test_doctor_rejects_ready_record_that_bypasses_global_policy(self):
        self.configure("CAP-github-browser")
        self.approve_empty_prerequisite_slice()
        path = self.start_path()
        record = json.loads(path.read_text())
        from _lib.start import definition_hash
        record["status"] = "Ready"
        record["readiness"] = {"definition_hash": definition_hash(record), "mocks_allowed": False,
                               "ran_at": "2026-10-30T00:00:00Z", "checks": []}
        write_json(path, record)
        result = doctor(self.root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("global implementation preflight", result.stdout)


class ProtectedBranchPolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TempDir()
        self.root = self.tmp.__enter__()
        git_project(self.root)
        make_slice(self.root)

    def tearDown(self):
        self.tmp.__exit__(None, None, None)

    def declare(self, branch: str):
        base = git(self.root, "rev-parse", "HEAD").stdout.strip()
        draft = {"repositories": [{"id": "main", "base": base, "branch": branch, "worktree": None,
                                    "outcomes": ["OUT-work"], "file_ownership": {}}],
                 "default_branch": branch}
        path = self.root / ".cgspec-scratch/policy-plan.json"
        write_json(path, draft)
        return run_script("cgspec_hook.py", "git-plan", "declare", "--root", str(self.root),
                          "--slice", "SLICE-001", "--file", str(path))

    def test_declaration_rejects_protected_default_branch(self):
        git(self.root, "checkout", "-q", "main")
        result = self.declare("main")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("protected branch", result.stderr)

    def test_renamed_protected_branch_is_enforced_and_feature_branch_is_allowed(self):
        project = self.root / "docs/_cgspec/project.json"
        data = json.loads(project.read_text())
        data["protected_branches"] = ["trunk"]
        write_json(project, data)
        blocked = self.declare("trunk")
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("protected branch", blocked.stderr)
        allowed = self.declare("codex/slice-001")
        self.assertEqual(allowed.returncode, 0, allowed.stderr)


if __name__ == "__main__":
    unittest.main()
