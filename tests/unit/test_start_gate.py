"""Success agreements and executable readiness (issue #30)."""

from __future__ import annotations

import copy
import json
import os
import unittest
from pathlib import Path

from tests.helpers import (
    TempDir,
    approve,
    claude_payload,
    doctor,
    hook,
    install,
    make_slice,
    run_script,
)


def draft() -> dict:
    return {
        "goal": "A member can sign in through the real service",
        "outcomes": [
            {
                "id": "OUT-login",
                "statement": "A member reaches their workspace after valid sign-in",
                "covers": ["src/login/**"],
                "accept": ["Valid credentials reach the member workspace"],
                "reject": ["Invalid credentials never create a session"],
                "evaluation": {
                    "method": "Exercise sign-in through the real API and database",
                    "requires_real": True,
                    "data_source": "real_backend",
                    "proof": ["logs", "recording"],
                },
                "development": {"uses_mocks": False, "data_source": "real_backend"},
            }
        ],
        "exclusions": ["Social sign-in is not included"],
        "constraints": ["Existing sessions remain valid"],
        "design": {"required": False, "target": None, "states": []},
        "prerequisites": [
            {
                "id": "REQ-database",
                "need": "The real test database is reachable",
                "owner": "agent",
                "when": "before_start",
                "outcomes": ["OUT-login"],
                "assistance": "Start the approved test database and rerun readiness",
                "check": {
                    "argv": ["python3", "-c", "from pathlib import Path; Path('probe-ran').write_text('yes')"],
                    "cwd": ".",
                    "timeout_seconds": 5,
                    "inputs": [],
                },
            }
        ],
    }


class StartFixture:
    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        install(self.root)
        (self.root / "src/login").mkdir(parents=True)
        (self.root / "src/login/form.ts").write_text("export const f = 1;\n")
        self.slice_path = make_slice(self.root, scope="src/**,tests/**,docs/prototypes/**")
        self.draft = draft()

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def cli(self, *args: str, env: dict | None = None):
        return run_script("cgspec_hook.py", "start", *args, "--root", str(self.root), env=env)

    def set_draft(self, value: dict | None = None):
        path = self.root / ".cgspec-scratch/start-draft.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(value if value is not None else self.draft))
        return self.cli("set", "--slice", "SLICE-001", "--file", str(path))

    def agree(self):
        ref = approve(self.root, "approve SLICE-001")
        return ref, self.cli("agree", "--slice", "SLICE-001", "--approval", ref)

    def start_path(self) -> Path:
        return self.slice_path.with_suffix(".start.json")

class StartTests(StartFixture, unittest.TestCase):
    def test_definition_requires_clear_outcomes_and_evaluation(self):
        value = copy.deepcopy(self.draft)
        value["outcomes"][0]["accept"] = []
        result = self.set_draft(value)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("accept", result.stderr)

    def test_real_readiness_executes_and_allows_eligible_outcome(self):
        self.assertEqual(self.set_draft().returncode, 0)
        _, agreed = self.agree()
        self.assertEqual(agreed.returncode, 0, agreed.stderr)
        ready = self.cli("ready", "--slice", "SLICE-001")
        self.assertEqual(ready.returncode, 0, ready.stderr)
        self.assertTrue((self.root / "probe-ran").is_file())
        begun = self.cli("begin", "--slice", "SLICE-001", "--outcome", "OUT-login")
        self.assertEqual(begun.returncode, 0, begun.stderr)
        record = json.loads(self.start_path().read_text())
        self.assertEqual(record["status"], "In progress")
        self.assertEqual(record["active_outcomes"], ["OUT-login"])
        self.assertFalse(record["readiness"]["mocks_allowed"])

    def test_failed_probe_blocks_only_its_outcome(self):
        other = copy.deepcopy(self.draft["outcomes"][0])
        other.update(id="OUT-other", statement="An independent settings flow works", covers=["src/other/**"])
        self.draft["outcomes"].append(other)
        failed = copy.deepcopy(self.draft["prerequisites"][0])
        failed.update(
            id="REQ-service",
            need="The required other service is unavailable",
            outcomes=["OUT-other"],
            assistance="Ask the service owner for a test endpoint",
            check={"argv": ["python3", "-c", "raise SystemExit(1)"], "cwd": ".", "timeout_seconds": 5, "inputs": []},
        )
        self.draft["prerequisites"].append(failed)
        self.set_draft()
        self.agree()
        self.assertEqual(self.cli("ready", "--slice", "SLICE-001").returncode, 0)
        self.assertEqual(self.cli("begin", "--slice", "SLICE-001", "--outcome", "OUT-login").returncode, 0)
        blocked = self.cli("begin", "--slice", "SLICE-001", "--outcome", "OUT-other")
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("required other service", blocked.stderr)
        self.assertIn("service owner", blocked.stderr)

    def test_missing_user_validation_names_owner_and_assistance(self):
        requirement = self.draft["prerequisites"][0]
        requirement.update(owner="user", check=None, assistance="Complete sign-in, then the AI will rerun its probe")
        self.set_draft()
        self.agree()
        result = self.cli("ready", "--slice", "SLICE-001")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("user", result.stderr)
        self.assertIn("Complete sign-in", result.stderr)

    def test_future_human_checkpoint_is_disclosed_without_blocking_start(self):
        self.draft["prerequisites"][0]["when"] = "before_proof"
        self.draft["prerequisites"][0]["owner"] = "user"
        self.set_draft()
        self.agree()
        self.assertEqual(self.cli("ready", "--slice", "SLICE-001").returncode, 0)
        shown = self.cli("show", "--slice", "SLICE-001")
        self.assertIn("before_proof", shown.stdout)
        self.assertIn("REQ-database", shown.stdout)

    def test_mock_kill_switch_blocks_mock_substitution(self):
        self.draft["outcomes"][0]["development"] = {"uses_mocks": True, "data_source": "fixture"}
        self.draft["prerequisites"] = []
        self.set_draft()
        self.agree()
        off = os.environ.copy()
        off["CGSPEC_ALLOW_MOCKS"] = "0"
        self.assertNotEqual(self.cli("ready", "--slice", "SLICE-001", env=off).returncode, 0)
        on = off.copy()
        on["CGSPEC_ALLOW_MOCKS"] = "1"
        self.assertEqual(self.cli("ready", "--slice", "SLICE-001", env=on).returncode, 0)
        self.assertEqual(self.cli("begin", "--slice", "SLICE-001", "--outcome", "OUT-login", env=on).returncode, 0)
        self.assertTrue(json.loads(self.start_path().read_text())["readiness"]["mocks_allowed"])

    def test_secret_shaped_probe_content_is_rejected(self):
        self.draft["prerequisites"][0]["check"]["argv"].append("sk-cgspec-fixture-123456789012345")  # cgspec:test-fixture
        result = self.set_draft()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("environment variable", result.stderr)

    def test_real_integration_cannot_be_defined_as_mock_proof(self):
        evaluation = self.draft["outcomes"][0]["evaluation"]
        evaluation.update(data_source="fixture")
        result = self.set_draft()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("real", result.stderr.lower())

    def test_gui_design_target_and_states_are_required(self):
        self.draft["design"] = {"required": True, "target": None, "states": []}
        result = self.set_draft()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("design", result.stderr)

    def test_revision_requires_new_approval_and_readiness(self):
        self.set_draft()
        old_ref, _ = self.agree()
        self.cli("ready", "--slice", "SLICE-001")
        changed = copy.deepcopy(self.draft)
        changed["goal"] = "A revised and materially different goal"
        self.assertEqual(self.set_draft(changed).returncode, 0)
        record = json.loads(self.start_path().read_text())
        self.assertEqual(record["status"], "Draft")
        self.assertEqual(record["version"], 2)
        self.assertNotEqual(self.cli("begin", "--slice", "SLICE-001", "--outcome", "OUT-login").returncode, 0)
        reused = self.cli("agree", "--slice", "SLICE-001", "--approval", old_ref)
        self.assertNotEqual(reused.returncode, 0)

    def test_approval_captured_before_draft_is_rejected(self):
        old = approve(self.root, "approve SLICE-001")
        self.assertEqual(self.set_draft().returncode, 0)
        result = self.cli("agree", "--slice", "SLICE-001", "--approval", old)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("predates", result.stderr)

    def test_probe_input_change_invalidates_readiness(self):
        probe = self.root / "probe.py"
        probe.write_text("pass\n")
        check = self.draft["prerequisites"][0]["check"]
        check.update(argv=["python3", "probe.py"], inputs=["probe.py"])
        self.set_draft()
        self.agree()
        self.cli("ready", "--slice", "SLICE-001")
        probe.write_text("raise SystemExit(1)\n")
        result = self.cli("begin", "--slice", "SLICE-001", "--outcome", "OUT-login")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("readiness input", result.stderr)

    def test_probe_output_is_not_persisted(self):
        self.draft["prerequisites"][0]["check"]["argv"] = [
            "python3", "-c", "print('sensitive' + ' probe output'); raise SystemExit(1)"
        ]
        self.set_draft()
        self.agree()
        self.cli("ready", "--slice", "SLICE-001")
        self.assertNotIn("sensitive probe output", self.start_path().read_text())

    def test_doctor_validates_start_sidecar(self):
        self.assertEqual(self.set_draft().returncode, 0)
        self.assertEqual(doctor(self.root).returncode, 0, doctor(self.root).stdout)
        record = json.loads(self.start_path().read_text())
        record["unexpected"] = True
        self.start_path().write_text(json.dumps(record))
        result = doctor(self.root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unexpected", result.stdout)


class StartHookTests(StartFixture, unittest.TestCase):
    def edit(self, rel: str):
        payload = claude_payload(self.root, "Edit", file_path=rel, old_string="1", new_string="2")
        return hook(self.root, "pre-tool", payload, "--tool", "claude")

    def test_pretool_allows_design_and_tests_but_not_unready_implementation(self):
        run_script(
            "cgspec_hook.py", "tier", "set", "--tier", "T1", "--reason", "Build sign-in",
            "--slice", "SLICE-001", "--root", str(self.root),
        )
        self.assertEqual(self.edit("tests/login.test.ts").returncode, 0)
        self.assertEqual(self.edit("docs/prototypes/login/ui.ts").returncode, 0)
        self.assertNotEqual(self.edit("src/login/form.ts").returncode, 0)
        self.set_draft()
        self.agree()
        self.cli("ready", "--slice", "SLICE-001")
        self.cli("begin", "--slice", "SLICE-001", "--outcome", "OUT-login")
        self.assertEqual(self.edit("src/login/form.ts").returncode, 0)
        self.assertEqual(self.edit("src/login/form.test.ts").returncode, 0)
        self.assertNotEqual(self.edit("src/other/form.ts").returncode, 0)

    def test_t0_requires_explicit_lightweight_verification(self):
        base = (
            "cgspec_hook.py", "tier", "set", "--tier", "T0", "--reason", "Fix the login label",
            "--files", "src/login/form.ts", "--root", str(self.root),
        )
        self.assertNotEqual(run_script(*base).returncode, 0)
        self.assertEqual(run_script(*base, "--verify", "Run the login unit check").returncode, 0)
        self.assertEqual(self.edit("src/login/form.ts").returncode, 0)


if __name__ == "__main__":
    unittest.main()
