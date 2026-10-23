"""Tests for dark mode rendering and visual quality checks (spec 7 layer 2)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest import mock

from tests.helpers import TempDir, git_project
from tests.unit.test_browser_tools import CLEAN


class DarkModeTests(unittest.TestCase):
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

    def test_dark_mode_pixel_identical_reports_no_dark_theme_and_no_duplicate_findings(self):
        import visual_audit
        vp = {
            "errors": [], "overflow": False, "scrollWidth": 1, "width": 1, "small": [], "smallCount": 0,
            "quality": {
                "contrastFailCount": 1,
                "contrastFails": [{"text": "Bad text", "ratio": 2.0, "need": 4.5, "id": "t1"}],
            },
            "darkTheme": False,
        }
        shots = self.root / ".cgspec-scratch/visual"
        shots.mkdir(parents=True, exist_ok=True)
        for name in ("invoice-desktop.png", "invoice-desktop-dark.png", "invoice-mobile.png", "invoice-mobile-dark.png"):
            (shots / name).write_bytes(b"\x89PNG\r\n\x1a\nimage")

        driver_result = {"results": [{"label": "invoice", "viewports": [
            dict(vp, viewport="desktop"), dict(vp, viewport="mobile")]}]}

        with mock.patch.object(visual_audit.browser, "run", return_value=driver_result):
            code, lines = visual_audit.audit(self.root, ["invoice"], write=False)

        text = "\n".join(lines)
        self.assertIn("page has no dark theme", text)
        self.assertEqual(text.count("Bad text"), 2)  # once per viewport (desktop & mobile), NOT duplicated for dark
        self.assertNotIn("(dark)", text)

    def test_dark_mode_with_separate_theme_runs_contrast_and_focus_labeled_dark(self):
        import visual_audit
        vp_desktop = {
            "errors": [], "overflow": False, "scrollWidth": 1, "width": 1, "small": [], "smallCount": 0,
            "quality": {"contrastFailCount": 0, "contrastFails": []},
            "darkTheme": True,
            "darkQuality": {
                "contrastFailCount": 1,
                "contrastFails": [{"text": "Dark bad text", "ratio": 2.1, "need": 4.5, "id": "t2"}],
                "focus": {"missing": ["btn-dark"]},
            },
        }
        vp_mobile = {
            "errors": [], "overflow": False, "scrollWidth": 1, "width": 1, "small": [], "smallCount": 0,
            "quality": {"contrastFailCount": 0, "contrastFails": []},
            "darkTheme": True,
            "darkQuality": {
                "contrastFailCount": 0, "contrastFails": [],
                "focus": {"missing": []},
            },
        }
        shots = self.root / ".cgspec-scratch/visual"
        shots.mkdir(parents=True, exist_ok=True)
        for name in ("invoice-desktop.png", "invoice-desktop-dark.png", "invoice-mobile.png", "invoice-mobile-dark.png"):
            (shots / name).write_bytes(b"\x89PNG\r\n\x1a\nimage")

        driver_result = {"results": [{"label": "invoice", "viewports": [
            dict(vp_desktop, viewport="desktop"), dict(vp_mobile, viewport="mobile")]}]}

        with mock.patch.object(visual_audit.browser, "run", return_value=driver_result):
            code, lines = visual_audit.audit(self.root, ["invoice"], write=False)

        text = "\n".join(lines)
        self.assertIn("E-CONTRAST (desktop) (dark)", text)
        self.assertIn("Dark bad text", text)
        self.assertIn("E-FOCUS (desktop) (dark)", text)
        self.assertIn("btn-dark", text)
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
