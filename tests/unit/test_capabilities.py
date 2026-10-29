"""Declare-once agent-side capabilities checked before work starts (issue #53)."""

from __future__ import annotations

import copy
import json
import unittest

from tests.helpers import TempDir, approve, claude_payload, doctor, git, hook, run_script
from tests.unit.test_start_commit import StartCommitTests
from tests.unit.test_start_gate import StartFixture
from _lib.capabilities import REGISTRY_REL, commit_records, registry_hash, validate_registry
from _lib.gitview import View
from _lib.inbox import approval_target
from _lib.schema import validate_named
from _lib.start import validate_record

NOW = "2026-10-29T12:00:00Z"


def capability(cap_id: str = "CAP-github-browser", code: str = "pass", kind: str = "account_access") -> dict:
    return {
        "id": cap_id, "kind": kind,
        "summary": "The agent has an authenticated browser session for GitHub",
        "usage": "Use the existing browser session; never type or store the user's credentials",
        "owner": "user",
        "assistance": "Sign in to GitHub in the agent's browser, then the agent reruns the check",
        "check": {"argv": ["python3", "-c", code], "cwd": ".", "timeout_seconds": 5, "inputs": []},
    }


def registry(*caps: dict) -> dict:
    return {"schema": 1, "capabilities": list(caps or [capability()]), "approval": None,
            "drafted_at": NOW, "drafted_ns": 1, "updated": NOW}


class RegistrySchemaTests(unittest.TestCase):
    def test_valid_registry_and_each_kind(self):
        kinds = ["account_access", "model_delegation", "human_contact", "tool_access", "other"]
        data = registry(*(capability(f"CAP-{k}", kind=k) for k in kinds))
        self.assertEqual(validate_registry(data), [])

    def test_schema_rejects_defects(self):
        cases = [
            ("bad id", lambda d: d["capabilities"][0].update(id="github")),
            ("unknown kind", lambda d: d["capabilities"][0].update(kind="telepathy")),
            ("unchecked capability", lambda d: d["capabilities"][0].update(check=None)),
            ("extra key", lambda d: d["capabilities"][0].update(assumed=True)),
            ("long timeout", lambda d: d["capabilities"][0]["check"].update(timeout_seconds=61)),
            ("empty argv", lambda d: d["capabilities"][0]["check"].update(argv=[])),
            ("unknown owner", lambda d: d["capabilities"][0].update(owner="model")),
        ]
        for label, mutate in cases:
            with self.subTest(label):
                data = registry()
                mutate(data)
                self.assertTrue(validate_named(data, "capabilities"), label)

    def test_duplicate_ids_and_stale_approval_are_rejected(self):
        self.assertIn("capability IDs must be unique", validate_registry(registry(capability(), capability())))
        data = registry()
        data["approval"] = {"ref": "A-20261029-abcd", "at": NOW, "registry_hash": registry_hash(data), "commit": None}
        self.assertEqual(validate_registry(data), [])
        data["capabilities"][0]["check"]["argv"] = ["true"]
        self.assertIn("approval is stale for this capability registry", validate_registry(data))

    def test_approval_message_targets_the_registry(self):
        self.assertEqual(approval_target("approve capabilities"), "capabilities")
        self.assertIsNone(approval_target("approved, go ahead"))

    def test_start_prerequisite_reference_is_optional_and_exclusive(self):
        from tests.unit.test_start_gate import draft
        record = {"schema": 1, "slice": "SLICE-001", "version": 1, "status": "Draft", **draft(),
                  "approval": None, "prior_approvals": [],
                  "readiness": {"definition_hash": "", "mocks_allowed": False, "ran_at": None, "checks": []},
                  "active_outcomes": [], "drafted_at": NOW, "drafted_ns": 1, "updated": NOW}
        self.assertEqual(validate_record(copy.deepcopy(record)), [])  # infra-only prerequisites unchanged
        record["prerequisites"][0]["capability"] = "CAP-github-browser"
        self.assertTrue(any("set check to null" in e for e in validate_record(copy.deepcopy(record))))
        record["prerequisites"][0]["check"] = None
        self.assertEqual(validate_record(copy.deepcopy(record)), [])
        record["prerequisites"][0]["capability"] = "github-browser"
        self.assertTrue(validate_record(record))


class CapabilityFixture(StartFixture):
    def capability_cli(self, *args: str):
        return run_script("cgspec_hook.py", "capability", *args, "--root", str(self.root))

    def set_registry(self, *caps: dict):
        path = self.root / ".cgspec-scratch/capabilities-draft.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps({"capabilities": list(caps or [capability()])}))
        return self.capability_cli("set", "--file", str(path))

    def agree_registry(self, text: str = "approve capabilities"):
        ref = approve(self.root, text)
        return ref, self.capability_cli("agree", "--approval", ref)

    def use_capability(self, cap_id: str = "CAP-github-browser"):
        req = self.draft["prerequisites"][0]
        req.update(capability=cap_id, check=None, owner="user",
                   need="The agent can open the GitHub pull request page as the user")
        self.set_draft()
        self.agree()

    def registry_path(self):
        return self.root / REGISTRY_REL


class CapabilityRegistryTests(CapabilityFixture, unittest.TestCase):
    def test_unapproved_registry_cannot_be_relied_on(self):
        self.assertEqual(self.set_registry().returncode, 0)
        shown = json.loads(self.capability_cli("show").stdout)
        self.assertFalse(shown["approved"])
        result = self.capability_cli("check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not approved", result.stderr)

    def test_registry_approval_must_name_capabilities_and_follow_the_draft(self):
        early = approve(self.root, "approve capabilities")
        self.set_registry()
        stale = self.capability_cli("agree", "--approval", early)
        self.assertNotEqual(stale.returncode, 0)
        self.assertIn("predates", stale.stderr)
        _, wrong = self.agree_registry("approve SLICE-001")
        self.assertNotEqual(wrong.returncode, 0)
        _, right = self.agree_registry()
        self.assertEqual(right.returncode, 0, right.stderr)
        record = json.loads(self.registry_path().read_text())
        self.assertEqual(record["approval"]["registry_hash"], registry_hash(record))

    def test_check_probes_each_capability_and_fails_closed(self):
        self.set_registry(capability(), capability("CAP-whatsapp", "raise SystemExit(3)", "human_contact"))
        self.agree_registry()
        before = self.registry_path().read_bytes()
        result = self.capability_cli("check")
        self.assertEqual(result.returncode, 2, result.stderr)
        statuses = {r["id"]: r["status"] for r in json.loads(result.stdout)}
        self.assertEqual(statuses, {"CAP-github-browser": "PASS", "CAP-whatsapp": "BLOCKED"})
        self.assertIn("CAP-whatsapp: BLOCKED", result.stderr)
        self.assertEqual(self.registry_path().read_bytes(), before)  # results are reported, never cached
        only = self.capability_cli("check", "--id", "CAP-github-browser")
        self.assertEqual(only.returncode, 0, only.stderr)
        self.assertNotEqual(self.capability_cli("check", "--id", "CAP-missing").returncode, 0)

    def test_registry_is_written_only_through_commands(self):
        payload = claude_payload(self.root, "Write", file_path=REGISTRY_REL, content="{}")
        result = hook(self.root, "pre-tool", payload, "--tool", "claude")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("capability", result.stderr + result.stdout)

    def test_secret_values_are_refused(self):
        leaky = capability()
        leaky["check"]["argv"].append("sk-cgspec-fixture-123456789012345")  # cgspec:test-fixture
        result = self.set_registry(leaky)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("environment variable", result.stderr)

    def test_doctor_accepts_valid_and_rejects_invalid_registry(self):
        self.set_registry()
        ok = doctor(self.root)
        self.assertEqual(ok.returncode, 0, ok.stdout)
        data = json.loads(self.registry_path().read_text())
        data["capabilities"][0]["assumed"] = True
        self.registry_path().write_text(json.dumps(data))
        bad = doctor(self.root)
        self.assertNotEqual(bad.returncode, 0)
        self.assertIn("assumed", bad.stdout)


class CapabilityReadinessTests(CapabilityFixture, unittest.TestCase):
    def test_slice_reuses_registry_check_and_binds_registry(self):
        self.set_registry(capability(code="from pathlib import Path; Path('cap-ran').write_text('yes')"))
        self.agree_registry()
        self.use_capability()
        ready = self.cli("ready", "--slice", "SLICE-001")
        self.assertEqual(ready.returncode, 0, ready.stderr)
        self.assertTrue((self.root / "cap-ran").is_file())
        result = json.loads(self.start_path().read_text())["readiness"]["checks"][0]
        self.assertEqual(result["status"], "PASS")
        self.assertIn(REGISTRY_REL, result["input_hashes"])
        self.assertEqual(self.cli("begin", "--slice", "SLICE-001", "--outcome", "OUT-login").returncode, 0)

    def test_missing_unapproved_or_unknown_capability_blocks(self):
        self.use_capability()
        missing = self.cli("ready", "--slice", "SLICE-001")
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("no capability registry", missing.stderr)
        self.set_registry()
        unapproved = self.cli("ready", "--slice", "SLICE-001")
        self.assertNotEqual(unapproved.returncode, 0)
        self.assertIn("not approved", unapproved.stderr)
        self.set_registry(capability("CAP-other"))
        self.agree_registry()
        unknown = self.cli("ready", "--slice", "SLICE-001")
        self.assertNotEqual(unknown.returncode, 0)
        self.assertIn("CAP-github-browser is not declared", unknown.stderr)

    def test_failing_capability_blocks_only_its_outcome_with_its_assistance(self):
        other = copy.deepcopy(self.draft["outcomes"][0])
        other.update(id="OUT-other", statement="An independent settings flow works", covers=["src/other/**"])
        self.draft["outcomes"].append(other)
        self.draft["prerequisites"][0]["outcomes"] = ["OUT-other"]
        self.set_registry(capability(code="raise SystemExit(1)"))
        self.agree_registry()
        self.use_capability()
        self.assertEqual(self.cli("ready", "--slice", "SLICE-001").returncode, 0)
        self.assertEqual(self.cli("begin", "--slice", "SLICE-001", "--outcome", "OUT-login").returncode, 0)
        blocked = self.cli("begin", "--slice", "SLICE-001", "--outcome", "OUT-other")
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("CAP-github-browser", blocked.stderr)
        self.assertIn("Sign in to GitHub", blocked.stderr)

    def test_registry_change_after_readiness_requires_rerun(self):
        self.set_registry()
        self.agree_registry()
        self.use_capability()
        self.assertEqual(self.cli("ready", "--slice", "SLICE-001").returncode, 0)
        self.set_registry(capability(code="raise SystemExit(0)"))
        result = self.cli("begin", "--slice", "SLICE-001", "--outcome", "OUT-login")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"readiness input {REGISTRY_REL}", result.stderr)


class CapabilityCommitTests(CapabilityFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "fixture")

    def staged(self) -> list[str]:
        git(self.root, "add", "-A")
        view = View.staged(self.root)
        return commit_records(view, view.changes())

    def test_registry_approval_given_in_the_change_passes(self):
        self.set_registry()
        self.agree_registry()
        self.assertEqual(self.staged(), [])

    def test_unapproved_draft_may_be_committed(self):
        self.set_registry()
        self.assertEqual(self.staged(), [])

    def test_hand_edited_approval_is_rejected(self):
        self.set_registry()
        self.agree_registry()
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "approved capabilities")
        data = json.loads(self.registry_path().read_text())
        data["capabilities"][0]["check"]["argv"] = ["true"]
        data["approval"]["registry_hash"] = registry_hash(data)
        self.registry_path().write_text(json.dumps(data))
        reasons = self.staged()
        self.assertTrue(any("capability approval" in r for r in reasons), reasons)

    def test_approval_for_another_record_is_rejected(self):
        self.set_registry()
        ref = approve(self.root, "approve SLICE-001")
        data = json.loads(self.registry_path().read_text())
        data["approval"] = {"ref": ref, "at": NOW, "registry_hash": registry_hash(data), "commit": None}
        self.registry_path().write_text(json.dumps(data))
        reasons = self.staged()
        self.assertTrue(any("capabilities" in r for r in reasons), reasons)


class CapabilityStagedImplementationTests(StartCommitTests):
    """A capability-backed prerequisite binds the staged registry like any probe input."""

    def capability_cli(self, *args: str):
        result = run_script("cgspec_hook.py", "capability", *args, "--root", str(self.root))
        self.assertEqual(result.returncode, 0, result.stderr)

    def write_registry(self, code: str):
        source = self.root / ".cgspec-scratch/capabilities-draft.json"
        source.parent.mkdir(exist_ok=True)
        source.write_text(json.dumps({"capabilities": [capability(code=code)]}))
        self.capability_cli("set", "--file", str(source))
        self.capability_cli("agree", "--approval", approve(self.root, "approve capabilities"))

    def before_start(self) -> None:
        self.write_registry("pass")

    def definition(self) -> dict:
        from tests.unit.test_start_gate import draft
        value = draft()
        value["prerequisites"][0].update(capability="CAP-github-browser", check=None)
        return value

    # These inherited cases rewrite a slice-local check; a capability-backed prerequisite has none.
    test_staged_probe_input_cannot_be_replaced_by_passing_working_tree = None
    test_missing_declared_probe_hash_cannot_authorize_code = None

    def test_staged_registry_binding_cannot_be_dropped(self):
        path = self.slice_path.with_suffix(".start.json")
        record = json.loads(path.read_text())
        record["readiness"]["checks"][0]["input_hashes"].pop(REGISTRY_REL)
        path.write_text(json.dumps(record, indent=2))
        git(self.root, "add", "docs")
        reasons = self.reasons()
        self.assertTrue(any("did not bind the capability registry" in reason for reason in reasons), reasons)

    def test_staged_registry_change_after_readiness_is_rejected(self):
        self.write_registry("raise SystemExit(0)")
        git(self.root, "add", "docs")
        reasons = self.reasons()
        self.assertTrue(any(f"readiness input {REGISTRY_REL}" in reason for reason in reasons), reasons)


del StartCommitTests  # run the inherited cases only through the capability-backed subclass

if __name__ == "__main__":
    unittest.main()
