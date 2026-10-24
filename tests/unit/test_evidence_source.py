"""A fixture-backed screen cannot be recorded as verified integration."""

from __future__ import annotations

import unittest

from tests.helpers import TempDir, git, git_project, write_json
from _lib.commit_gate import _evidence_rules
from _lib.gitview import Change


class EvidenceSourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TempDir()
        self.root = self.tmp.__enter__()
        git_project(self.root)

    def tearDown(self):
        self.tmp.__exit__(None, None, None)

    def record(self, claim=None, data_source=None, verdict="PASS"):
        path = self.root / "docs/_cgspec/06-evidence/manual/integration.json"
        value = {"schema": 1, "check": "studio:create", "revision": "abc1234",
                 "verdict": verdict, "ran_at": "2026-10-24T00:00:00Z", "ran_by": "test"}
        if claim is not None:
            value["claim"] = claim
        if data_source is not None:
            value["data_source"] = data_source
        write_json(path, value)
        git(self.root, "add", "-A")
        from _lib.gitview import View
        return _evidence_rules(View.staged(self.root), [Change("A", path.relative_to(self.root).as_posix())])

    def test_fixture_cannot_prove_integration(self):
        self.assertIn("cannot prove integration", " ".join(self.record("integration", "fixture")))

    def test_unknown_source_cannot_prove_integration(self):
        self.assertIn("cannot prove integration", " ".join(self.record("integration", "unknown")))

    def test_real_backend_may_prove_integration(self):
        self.assertEqual(self.record("integration", "real_backend"), [])

    def test_fixture_may_prove_fixture_ui_behavior(self):
        self.assertEqual(self.record("ui_behavior", "fixture"), [])

    def test_new_pass_requires_claim_and_source(self):
        self.assertIn("claim and data_source", " ".join(self.record()))

    def test_failed_integration_does_not_claim_success(self):
        self.assertEqual(self.record("integration", "fixture", "FAIL"), [])


if __name__ == "__main__":
    unittest.main()
