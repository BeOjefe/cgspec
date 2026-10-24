"""Tests for verify.py: one project verify command (spec 7 layer 1-2)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest import mock

from tests.helpers import TempDir, git_project
from tests.unit.test_browser_tools import CLEAN


class VerifyTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git_project(self.root)
        self.screen = self.root / "docs/prototypes/invoice"
        self.screen.mkdir(parents=True)
        (self.screen / "index.html").write_text(CLEAN)
        (self.screen / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def test_verify_summary_table_and_exit_code_on_success(self):
        import verify
        with mock.patch("verify.run_doctor", return_value=("PASS", 0, 0)), \
             mock.patch("verify.run_journeys", return_value=("PASS", 0, 0, [])), \
             mock.patch("verify.run_visual_audit", return_value=("PASS", 0, 0, [".cgspec-scratch/visual/invoice-desktop.png"])):
            code, out = verify.verify(self.root)
            self.assertEqual(code, 0)
            self.assertIn("doctor", out)
            self.assertIn("journeys", out)
            self.assertIn("visual_audit", out)
            self.assertIn("PASS", out)
            self.assertIn(".cgspec-scratch/visual/invoice-desktop.png", out)

    def test_verify_fails_if_any_check_fails(self):
        import verify
        with mock.patch("verify.run_doctor", return_value=("FAIL", 2, 0)), \
             mock.patch("verify.run_journeys", return_value=("PASS", 0, 0, [])), \
             mock.patch("verify.run_visual_audit", return_value=("PASS", 0, 0, [])):
            code, out = verify.verify(self.root)
            self.assertEqual(code, 1)
            self.assertIn("FAIL", out)

    def test_verify_partial_exits_nonzero_unless_allow_partial(self):
        import verify
        with mock.patch("verify.run_doctor", return_value=("PASS", 0, 0)), \
             mock.patch("verify.run_journeys", return_value=("PASS", 0, 0, [])), \
             mock.patch("verify.run_visual_audit", return_value=("PARTIAL", 0, 0, [])):
            code_no_allow, out1 = verify.verify(self.root, allow_partial=False)
            self.assertNotEqual(code_no_allow, 0)
            self.assertIn("PARTIAL", out1)

            code_allow, out2 = verify.verify(self.root, allow_partial=True)
            self.assertEqual(code_allow, 0)
            self.assertIn("PARTIAL", out2)

    def test_verify_json_output(self):
        import verify
        with mock.patch("verify.run_doctor", return_value=("PASS", 0, 0)), \
             mock.patch("verify.run_journeys", return_value=("PASS", 0, 0, [])), \
             mock.patch("verify.run_visual_audit", return_value=("PASS", 0, 0, [".cgspec-scratch/visual/invoice-desktop.png"])):
            data = verify.verify_json(self.root, allow_partial=False)
            self.assertEqual(data["verdict"], "PASS")
            self.assertEqual(len(data["checks"]), 3)
            checks = {c["check"]: c for c in data["checks"]}
            self.assertEqual(checks["doctor"]["result"], "PASS")
            self.assertEqual(checks["journeys"]["result"], "PASS")
            self.assertEqual(checks["visual_audit"]["result"], "PASS")
            self.assertIn(".cgspec-scratch/visual/invoice-desktop.png", checks["visual_audit"]["artifacts"])


if __name__ == "__main__":
    unittest.main()
