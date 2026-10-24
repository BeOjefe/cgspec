"""Tests for visual drift against approved baselines (spec 7 layer 2)."""

from __future__ import annotations

import json
import os
import stat
import unittest
from pathlib import Path
from unittest import mock

from tests.helpers import TempDir, git_project
from tests.unit.test_browser_tools import CLEAN


class BaselineApprovalTests(unittest.TestCase):
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

    def test_approve_baseline_freezes_pngs_and_prevents_silent_overwrite(self):
        import base64
        import visual_audit
        from tests.helpers import approve
        valid_png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")

        def fake_run(root, runs, shots_dir, video=False):
            shots_dir.mkdir(parents=True, exist_ok=True)
            for r in runs:
                (shots_dir / f"{r['label']}-desktop.png").write_bytes(valid_png)
                (shots_dir / f"{r['label']}-mobile.png").write_bytes(valid_png)
                (shots_dir / f"{r['label']}-desktop-dark.png").write_bytes(valid_png)
                (shots_dir / f"{r['label']}-mobile-dark.png").write_bytes(valid_png)
            return {"results": [{"label": "invoice", "viewports": [
                {"viewport": "desktop", "ok": True, "errors": [], "quality": {}},
                {"viewport": "mobile", "ok": True, "errors": [], "quality": {}},
            ]}]}

        with mock.patch("_lib.visual_baseline.browser.run", side_effect=fake_run):
            # Baseline approval requires user approval
            approve(self.root, "approve baseline for invoice")
            code = visual_audit.main(["--approve-baseline", "invoice", "--root", str(self.root)])
            self.assertEqual(code, 0)

            base_dir = self.root / "docs/prototypes/_baselines"
            desktop_base = base_dir / "invoice-v1-desktop.png"
            mobile_base = base_dir / "invoice-v1-mobile.png"
            self.assertTrue(desktop_base.is_file())
            self.assertTrue(mobile_base.is_file())
            self.assertFalse(desktop_base.stat().st_mode & stat.S_IWUSR)

            frozen_path = self.root / "docs/_cgspec/07-state/frozen.json"
            self.assertTrue(frozen_path.is_file())
            frozen_data = json.loads(frozen_path.read_text(encoding="utf-8"))
            paths = [e["path"] for e in frozen_data.get("entries", [])]
            self.assertIn("docs/prototypes/_baselines/invoice-v1-desktop.png", paths)
            self.assertIn("docs/prototypes/_baselines/invoice-v1-mobile.png", paths)

            # Re-approval creates v2 without modifying v1
            approve(self.root, "approve baseline v2 for invoice")
            code2 = visual_audit.main(["--approve-baseline", "invoice", "--root", str(self.root)])
            self.assertEqual(code2, 0)
            self.assertTrue((base_dir / "invoice-v2-desktop.png").is_file())
            self.assertTrue((base_dir / "invoice-v1-desktop.png").is_file())


class VisualDriftAuditTests(unittest.TestCase):
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

    def test_no_baseline_reports_info_not_pass_by_default(self):
        import visual_audit
        vp = {"errors": [], "overflow": False, "scrollWidth": 1, "width": 1, "small": [], "smallCount": 0,
              "quality": {}}
        shots = self.root / ".cgspec-scratch/visual"
        shots.mkdir(parents=True, exist_ok=True)
        for name in ("invoice-desktop.png", "invoice-desktop-dark.png", "invoice-mobile.png", "invoice-mobile-dark.png"):
            (shots / name).write_bytes(b"\x89PNG\r\n\x1a\nimage")

        driver_result = {"results": [{"label": "invoice", "viewports": [
            dict(vp, viewport="desktop"), dict(vp, viewport="mobile")]}]}

        with mock.patch.object(visual_audit.browser, "run", return_value=driver_result):
            code, lines = visual_audit.audit(self.root, ["invoice"], write=False)

        text = "\n".join(lines)
        self.assertIn("no approved baseline", text)

    def test_drift_within_threshold_is_warning(self):
        import visual_audit
        base_dir = self.root / "docs/prototypes/_baselines"
        base_dir.mkdir(parents=True, exist_ok=True)
        (base_dir / "invoice-desktop.png").write_bytes(b"\x89PNG\r\n\x1a\nbase-desktop")
        (base_dir / "invoice-mobile.png").write_bytes(b"\x89PNG\r\n\x1a\nbase-mobile")

        vp = {"errors": [], "overflow": False, "scrollWidth": 1, "width": 1, "small": [], "smallCount": 0,
              "quality": {},
              "drift": {"changedPercent": 0.2, "changedPixels": 200, "totalPixels": 100000,
                        "regions": [[0, 10, 100, 50]], "diffFile": "invoice-desktop-diff.png"}}
        shots = self.root / ".cgspec-scratch/visual"
        shots.mkdir(parents=True, exist_ok=True)
        for name in ("invoice-desktop.png", "invoice-desktop-dark.png", "invoice-mobile.png", "invoice-mobile-dark.png"):
            (shots / name).write_bytes(b"\x89PNG\r\n\x1a\nimage")

        driver_result = {"results": [{"label": "invoice", "viewports": [
            dict(vp, viewport="desktop"), dict(vp, viewport="mobile", drift=None)]}]}

        with mock.patch.object(visual_audit.browser, "run", return_value=driver_result):
            code, lines = visual_audit.audit(self.root, ["invoice"], write=False)

        text = "\n".join(lines)
        self.assertIn("W-DRIFT", text)
        self.assertIn("0.2", text)

    def test_drift_exceeding_threshold_is_error(self):
        import visual_audit
        base_dir = self.root / "docs/prototypes/_baselines"
        base_dir.mkdir(parents=True, exist_ok=True)
        (base_dir / "invoice-desktop.png").write_bytes(b"\x89PNG\r\n\x1a\nbase-desktop")
        (base_dir / "invoice-mobile.png").write_bytes(b"\x89PNG\r\n\x1a\nbase-mobile")

        vp = {"errors": [], "overflow": False, "scrollWidth": 1, "width": 1, "small": [], "smallCount": 0,
              "quality": {},
              "drift": {"changedPercent": 1.5, "changedPixels": 1500, "totalPixels": 100000,
                        "regions": [[0, 10, 100, 50]], "diffFile": "invoice-desktop-diff.png"}}
        shots = self.root / ".cgspec-scratch/visual"
        shots.mkdir(parents=True, exist_ok=True)
        for name in ("invoice-desktop.png", "invoice-desktop-dark.png", "invoice-mobile.png", "invoice-mobile-dark.png"):
            (shots / name).write_bytes(b"\x89PNG\r\n\x1a\nimage")

        driver_result = {"results": [{"label": "invoice", "viewports": [
            dict(vp, viewport="desktop"), dict(vp, viewport="mobile", drift=None)]}]}

        with mock.patch.object(visual_audit.browser, "run", return_value=driver_result):
            code, lines = visual_audit.audit(self.root, ["invoice"], write=False)

        text = "\n".join(lines)
        self.assertIn("E-DRIFT", text)
        self.assertIn("1.5", text)
        self.assertEqual(code, 1)

    def test_dimension_mismatch_is_100_percent_drift_layout_height_changed(self):
        import visual_audit
        base_dir = self.root / "docs/prototypes/_baselines"
        base_dir.mkdir(parents=True, exist_ok=True)
        (base_dir / "invoice-desktop.png").write_bytes(b"\x89PNG\r\n\x1a\nbase-desktop")
        (base_dir / "invoice-mobile.png").write_bytes(b"\x89PNG\r\n\x1a\nbase-mobile")

        vp = {"errors": [], "overflow": False, "scrollWidth": 1, "width": 1, "small": [], "smallCount": 0,
              "quality": {},
              "drift": {"differentDimensions": True, "changedPercent": 100.0, "w1": 1440, "h1": 900, "w2": 1440, "h2": 1200}}
        shots = self.root / ".cgspec-scratch/visual"
        shots.mkdir(parents=True, exist_ok=True)
        for name in ("invoice-desktop.png", "invoice-desktop-dark.png", "invoice-mobile.png", "invoice-mobile-dark.png"):
            (shots / name).write_bytes(b"\x89PNG\r\n\x1a\nimage")

        driver_result = {"results": [{"label": "invoice", "viewports": [
            dict(vp, viewport="desktop"), dict(vp, viewport="mobile", drift=None)]}]}

        with mock.patch.object(visual_audit.browser, "run", return_value=driver_result):
            code, lines = visual_audit.audit(self.root, ["invoice"], write=False)

        text = "\n".join(lines)
        self.assertIn("E-DRIFT", text)
        self.assertIn("100% changed", text)
        self.assertIn("layout height changed", text)
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
