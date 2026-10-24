"""Regression tests for CGSpec visual-verify repair round (defects 1-21)."""

from __future__ import annotations

import base64
import json
import math
import os
import stat
import struct
import unittest
from pathlib import Path
from unittest import mock

from tests.helpers import TempDir, approve, git_project, run_script, write_json
from tests.unit.test_browser_tools import CLEAN

# Valid 1x1 PNG bytes with valid IHDR, IDAT, IEND chunks
VALID_PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)

# Valid 10x10 PNG bytes
def make_valid_png(width: int = 10, height: int = 10) -> bytes:
    # Minimal valid PNG generator
    import zlib
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr_crc = struct.pack(">I", zlib.crc32(b"IHDR" + ihdr_data))
    ihdr = struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data + ihdr_crc
    raw_scanlines = b"".join(b"\x00" + b"\xff\x00\x00" * width for _ in range(height))
    idat_payload = zlib.compress(raw_scanlines)
    idat_crc = struct.pack(">I", zlib.crc32(b"IDAT" + idat_payload))
    idat = struct.pack(">I", len(idat_payload)) + b"IDAT" + idat_payload + idat_crc
    iend_crc = struct.pack(">I", zlib.crc32(b"IEND"))
    iend = struct.pack(">I", 0) + b"IEND" + iend_crc
    return signature + ihdr + idat + iend


class VisualVerifyRegressionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git_project(self.root)
        self.screen = self.root / "docs/prototypes/invoice"
        self.screen.mkdir(parents=True)
        (self.screen / "index.html").write_text(CLEAN)
        (self.screen / "logo.png").write_bytes(VALID_PNG_1X1)

    def tearDown(self):
        for p in self.root.rglob("*"):
            if ".git" in p.parts:
                continue
            if p.is_file() and not p.is_symlink():
                os.chmod(p, 0o644)
        self._tmp.__exit__(None, None, None)

    # 1. ./screen overwrite & canonical screen identity
    def test_regression_screen_overwrite_and_aliases_rejected(self):
        from _lib.common import CgspecError
        from _lib import visual_baseline
        import visual_audit
        # Approving with ./ alias must be rejected
        with self.assertRaises(CgspecError):
            visual_baseline.approve_baseline(self.root, "./invoice")
        with self.assertRaises(CgspecError):
            visual_baseline.approve_baseline(self.root, "../invoice")
        with self.assertRaises(CgspecError):
            visual_baseline.approve_baseline(self.root, "/invoice")

    # 2. External destination symlink & scratch->baseline symlink
    def test_regression_external_destination_symlink_rejected(self):
        from _lib.common import CgspecError
        from _lib import visual_baseline
        base_dir = self.root / "docs/prototypes/_baselines"
        base_dir.mkdir(parents=True, exist_ok=True)
        # External destination attack: symlink inside baselines pointing outside
        external_target = self.root / "external.png"
        external_target.write_bytes(b"forbidden")
        (base_dir / "invoice-v1-desktop.png").symlink_to(external_target)
        approve(self.root, "approve baseline")
        with self.assertRaises(CgspecError):
            visual_baseline.approve_baseline(self.root, "invoice")

    def test_regression_scratch_to_baseline_symlink_rejected(self):
        from _lib.common import CgspecError
        from _lib import visual_baseline
        shots = self.root / ".cgspec-scratch/visual"
        shots.mkdir(parents=True, exist_ok=True)
        # Scratch pointing to frozen file or baseline storage
        target = self.root / "docs/_cgspec/07-state/frozen.json"
        (shots / "invoice-desktop.png").symlink_to(target)
        approve(self.root, "approve baseline")
        with self.assertRaises(CgspecError):
            visual_baseline.approve_baseline(self.root, "invoice")

    # 3. Absent approvals
    def test_regression_absent_approvals_rejected(self):
        from _lib.common import CgspecError
        from _lib import visual_baseline
        # Remove approvals.json
        approvals = self.root / "docs/_cgspec/07-state/approvals.json"
        if approvals.is_file():
            approvals.unlink()
        with self.assertRaises(CgspecError):
            visual_baseline.approve_baseline(self.root, "invoice")

    # 4. Fake PNG rejected
    def test_regression_fake_png_rejected(self):
        from _lib.common import CgspecError
        from _lib import visual_baseline
        approve(self.root, "approve baseline")
        # Fake png bytes in scratch
        shots = self.root / ".cgspec-scratch/visual"
        shots.mkdir(parents=True, exist_ok=True)
        (shots / "invoice-desktop.png").write_bytes(b"\x89PNG\r\n\x1a\nnot-a-real-png")
        (shots / "invoice-mobile.png").write_bytes(b"\x89PNG\r\n\x1a\nnot-a-real-png")
        with self.assertRaises(CgspecError):
            visual_baseline.approve_baseline(self.root, "invoice")

    # 4. Stale screenshot not reused / browser unavailable fails
    def test_regression_stale_screenshot_not_reused(self):
        from _lib.common import CgspecError
        from _lib import visual_baseline
        approve(self.root, "approve baseline")
        # Pre-existing screenshot in scratch
        shots = self.root / ".cgspec-scratch/visual"
        shots.mkdir(parents=True, exist_ok=True)
        (shots / "invoice-desktop.png").write_bytes(make_valid_png())
        (shots / "invoice-mobile.png").write_bytes(make_valid_png())
        # Browser fails or is unavailable
        with mock.patch("_lib.visual_baseline.browser.run", return_value={"blocked": "browser not installed"}):
            with self.assertRaises(CgspecError):
                visual_baseline.approve_baseline(self.root, "invoice")

    # 5. Corrupt frozen fails without modification
    def test_regression_corrupt_frozen_fails_without_modification(self):
        from _lib.common import CgspecError
        from _lib import visual_baseline
        approve(self.root, "approve baseline")
        frozen_path = self.root / "docs/_cgspec/07-state/frozen.json"
        corrupt_content = "{corrupted json content"
        frozen_path.write_text(corrupt_content)
        with self.assertRaises(CgspecError):
            visual_baseline.approve_baseline(self.root, "invoice")
        # File must not be modified or overwritten!
        self.assertEqual(frozen_path.read_text(), corrupt_content)

    # 6. Versioned reapproval
    def test_regression_versioned_reapproval(self):
        from _lib import visual_baseline
        shots = self.root / ".cgspec-scratch/visual"
        shots.mkdir(parents=True, exist_ok=True)
        (shots / "invoice-desktop.png").write_bytes(make_valid_png(10, 10))
        (shots / "invoice-mobile.png").write_bytes(make_valid_png(10, 10))
        # Mock browser run to return success and leave valid PNGs
        def fake_run(root, runs, shots_dir, video=False):
            shots_dir.mkdir(parents=True, exist_ok=True)
            for r in runs:
                lbl = r["label"]
                (shots_dir / f"{lbl}-desktop.png").write_bytes(make_valid_png(10, 10))
                (shots_dir / f"{lbl}-mobile.png").write_bytes(make_valid_png(10, 10))
                (shots_dir / f"{lbl}-desktop-dark.png").write_bytes(make_valid_png(10, 10))
                (shots_dir / f"{lbl}-mobile-dark.png").write_bytes(make_valid_png(10, 10))
            return {"results": [{"label": "invoice", "viewports": [
                {"viewport": "desktop", "ok": True, "errors": [], "quality": {}},
                {"viewport": "mobile", "ok": True, "errors": [], "quality": {}},
            ]}]}

        with mock.patch("_lib.visual_baseline.browser.run", side_effect=fake_run):
            # v1 approval
            approve(self.root, "approve baseline v1")
            saved1 = visual_baseline.approve_baseline(self.root, "invoice")
            v1_paths = [p.name for p in saved1]
            self.assertTrue(any("v1" in p for p in v1_paths))

            # v2 approval
            approve(self.root, "approve baseline v2")
            saved2 = visual_baseline.approve_baseline(self.root, "invoice")
            v2_paths = [p.name for p in saved2]
            self.assertTrue(any("v2" in p for p in v2_paths))

            # Check that v1 files still exist and are untouched
            base_dir = self.root / "docs/prototypes/_baselines"
            for p in saved1:
                self.assertTrue(p.is_file())
            # Active selection should now be v2
            driver_map, has_map = visual_baseline.find_baselines(self.root, "invoice")
            self.assertIn("v2", driver_map["desktop"])

    # 9. Dark-only crash makes verify non-zero
    def test_regression_dark_only_crash_makes_verify_nonzero(self):
        import visual_audit
        import verify
        vp_desktop = {
            "errors": [], "overflow": False, "scrollWidth": 1, "width": 1, "small": [], "smallCount": 0,
            "quality": {}, "darkTheme": False,
            "darkErrors": ["Uncaught TypeError: window.darkInit is not a function"],
        }
        vp_mobile = {
            "errors": [], "overflow": False, "scrollWidth": 1, "width": 1, "small": [], "smallCount": 0,
            "quality": {}, "darkTheme": False,
            "darkErrors": [],
        }
        shots = self.root / ".cgspec-scratch/visual"
        shots.mkdir(parents=True, exist_ok=True)
        for name in ("invoice-desktop.png", "invoice-desktop-dark.png", "invoice-mobile.png", "invoice-mobile-dark.png"):
            (shots / name).write_bytes(make_valid_png())

        driver_result = {"results": [{"label": "invoice", "viewports": [
            dict(vp_desktop, viewport="desktop"), dict(vp_mobile, viewport="mobile")]}]}

        with mock.patch.object(visual_audit.browser, "run", return_value=driver_result):
            code, lines = visual_audit.audit(self.root, ["invoice"], write=False)
        self.assertEqual(code, 1)
        self.assertTrue(any("darkInit" in line for line in lines))

    # 10. Sub-tolerance AA failure
    def test_regression_sub_tolerance_aa_failure(self):
        import visual_audit
        # darkTheme is reported False (pixel-identical or sub-tolerance), but darkQuality has contrast failure
        vp = {
            "errors": [], "overflow": False, "scrollWidth": 1, "width": 1, "small": [], "smallCount": 0,
            "quality": {"contrastFailCount": 0, "contrastFails": []},
            "darkTheme": False,
            "darkQuality": {
                "contrastFailCount": 1,
                "contrastFails": [{"text": "Dark failure", "ratio": 2.0, "need": 4.5, "id": "t1"}],
            },
        }
        shots = self.root / ".cgspec-scratch/visual"
        shots.mkdir(parents=True, exist_ok=True)
        for name in ("invoice-desktop.png", "invoice-desktop-dark.png", "invoice-mobile.png", "invoice-mobile-dark.png"):
            (shots / name).write_bytes(make_valid_png())

        driver_result = {"results": [{"label": "invoice", "viewports": [
            dict(vp, viewport="desktop"), dict(vp, viewport="mobile")]}]}

        with mock.patch.object(visual_audit.browser, "run", return_value=driver_result):
            code, lines = visual_audit.audit(self.root, ["invoice"], write=False)
        self.assertEqual(code, 1)
        self.assertIn("Dark failure", "\n".join(lines))

    # 10. Focus-only identical theme (focus state does not imply dark theme)
    def test_regression_focus_only_identical_theme(self):
        import visual_audit
        # Driver should report darkTheme False when only focus ring differed
        # Here we test visual_audit handles darkTheme=False properly when focus is evaluated
        vp = {
            "errors": [], "overflow": False, "scrollWidth": 1, "width": 1, "small": [], "smallCount": 0,
            "quality": {"focus": {"missing": []}},
            "darkTheme": False,
        }
        shots = self.root / ".cgspec-scratch/visual"
        shots.mkdir(parents=True, exist_ok=True)
        for name in ("invoice-desktop.png", "invoice-desktop-dark.png", "invoice-mobile.png", "invoice-mobile-dark.png"):
            (shots / name).write_bytes(make_valid_png())
        driver_result = {"results": [{"label": "invoice", "viewports": [
            dict(vp, viewport="desktop"), dict(vp, viewport="mobile")]}]}

        with mock.patch.object(visual_audit.browser, "run", return_value=driver_result):
            code, lines = visual_audit.audit(self.root, ["invoice"], write=False)
        self.assertIn("page has no dark theme", "\n".join(lines))

    # 12. One-pixel zero threshold
    def test_regression_one_pixel_zero_threshold(self):
        import visual_audit
        pj = self.root / "docs/_cgspec/project.json"
        data = json.loads(pj.read_text())
        data["visual_drift_threshold"] = 0
        pj.write_text(json.dumps(data))

        base_dir = self.root / "docs/prototypes/_baselines"
        base_dir.mkdir(parents=True, exist_ok=True)
        (base_dir / "invoice-desktop.png").write_bytes(make_valid_png())
        (base_dir / "invoice-mobile.png").write_bytes(make_valid_png())

        vp = {"errors": [], "overflow": False, "scrollWidth": 1, "width": 1, "small": [], "smallCount": 0,
              "quality": {},
              "drift": {"changedPercent": 0.001, "changedPixels": 1, "totalPixels": 100000,
                        "regions": [[0, 0, 1, 1]]}}
        shots = self.root / ".cgspec-scratch/visual"
        shots.mkdir(parents=True, exist_ok=True)
        for name in ("invoice-desktop.png", "invoice-desktop-dark.png", "invoice-mobile.png", "invoice-mobile-dark.png"):
            (shots / name).write_bytes(make_valid_png())

        driver_result = {"results": [{"label": "invoice", "viewports": [
            dict(vp, viewport="desktop"), dict(vp, viewport="mobile")]}]}

        with mock.patch.object(visual_audit.browser, "run", return_value=driver_result):
            code, lines = visual_audit.audit(self.root, ["invoice"], write=False)
        self.assertEqual(code, 1)
        self.assertIn("E-DRIFT", "\n".join(lines))

    # 12. 5001-pixel 0.5 exceeds threshold
    def test_regression_5001_pixel_exceeds_half_percent(self):
        import visual_audit
        pj = self.root / "docs/_cgspec/project.json"
        data = json.loads(pj.read_text())
        data["visual_drift_threshold"] = 0.5
        pj.write_text(json.dumps(data))

        base_dir = self.root / "docs/prototypes/_baselines"
        base_dir.mkdir(parents=True, exist_ok=True)
        (base_dir / "invoice-desktop.png").write_bytes(make_valid_png())
        (base_dir / "invoice-mobile.png").write_bytes(make_valid_png())

        # 5001 / 1,000,000 = 0.5001%
        vp = {"errors": [], "overflow": False, "scrollWidth": 1, "width": 1, "small": [], "smallCount": 0,
              "quality": {},
              "drift": {"changedPercent": 0.500, "changedPixels": 5001, "totalPixels": 1000000,
                        "regions": [[0, 0, 10, 10]]}}
        shots = self.root / ".cgspec-scratch/visual"
        shots.mkdir(parents=True, exist_ok=True)
        for name in ("invoice-desktop.png", "invoice-desktop-dark.png", "invoice-mobile.png", "invoice-mobile-dark.png"):
            (shots / name).write_bytes(make_valid_png())

        driver_result = {"results": [{"label": "invoice", "viewports": [
            dict(vp, viewport="desktop"), dict(vp, viewport="mobile")]}]}

        with mock.patch.object(visual_audit.browser, "run", return_value=driver_result):
            code, lines = visual_audit.audit(self.root, ["invoice"], write=False)
        self.assertEqual(code, 1)
        self.assertIn("E-DRIFT", "\n".join(lines))

    # 13. NaN threshold rejected in doctor and verify
    def test_regression_nan_threshold_rejected(self):
        import doctor
        import visual_audit
        from _lib.common import CgspecError
        pj = self.root / "docs/_cgspec/project.json"
        data = json.loads(pj.read_text())
        for invalid in ("NaN", float("nan"), float("inf"), True, -1, 101):
            with self.subTest(invalid=invalid):
                data["visual_drift_threshold"] = invalid
                pj.write_text(json.dumps(data))
                findings = list(doctor.run_checks(self.root))
                drift_errors = [f for f in findings if "DRIFT-THRESHOLD" in f.code or "E-PROJECT" in f.code]
                self.assertTrue(len(drift_errors) > 0, f"doctor did not reject {invalid}")
                with self.assertRaises(CgspecError):
                    visual_audit.audit(self.root, ["invoice"], write=False)

    # 11. drift:null fails closed
    def test_regression_drift_null_fails_closed(self):
        import visual_audit
        base_dir = self.root / "docs/prototypes/_baselines"
        base_dir.mkdir(parents=True, exist_ok=True)
        (base_dir / "invoice-desktop.png").write_bytes(make_valid_png())
        (base_dir / "invoice-mobile.png").write_bytes(make_valid_png())

        vp = {"errors": [], "overflow": False, "scrollWidth": 1, "width": 1, "small": [], "smallCount": 0,
              "quality": {}, "drift": None}
        shots = self.root / ".cgspec-scratch/visual"
        shots.mkdir(parents=True, exist_ok=True)
        for name in ("invoice-desktop.png", "invoice-desktop-dark.png", "invoice-mobile.png", "invoice-mobile-dark.png"):
            (shots / name).write_bytes(make_valid_png())

        driver_result = {"results": [{"label": "invoice", "viewports": [
            dict(vp, viewport="desktop"), dict(vp, viewport="mobile")]}]}

        with mock.patch.object(visual_audit.browser, "run", return_value=driver_result):
            code, lines = visual_audit.audit(self.root, ["invoice"], write=False)
        self.assertEqual(code, 1)
        self.assertIn("E-DRIFT", "\n".join(lines))

    # 1. page.html label canonicalization
    def test_regression_page_html_label_canonical(self):
        from _lib import visual_baseline
        (self.root / "page.html").write_text(CLEAN)
        label = visual_baseline.resolve_canonical_label(self.root, "page.html")
        self.assertEqual(label, "page-html")

    # 17. Undeclared src/tokens.json
    def test_regression_undeclared_src_tokens_json(self):
        import _lib.visual_quality as vq
        tokens_file = self.root / "src/tokens.json"
        tokens_file.parent.mkdir(parents=True, exist_ok=True)
        tokens_file.write_text(json.dumps({"color": {"primary": {"$value": "#123456"}}}))

        pj = self.root / "docs/_cgspec/project.json"
        project_data = json.loads(pj.read_text())
        project_data.pop("design_tokens", None)
        project_data.pop("design_system", None)

        res = vq.find_tokens(self.root, project_data)
        self.assertIn("W-TOKENS-UNDECLARED", res.get("issue", ""))

    # 16. GUI with no journeys is PARTIAL
    def test_regression_gui_with_no_journeys_is_partial(self):
        import verify
        # invoice screen exists in docs/prototypes/invoice, but no journeys exist
        code, out = verify.verify(self.root, allow_partial=False)
        self.assertEqual(code, 2)
        self.assertIn("PARTIAL", out)

        code_allow, out_allow = verify.verify(self.root, allow_partial=True)
        self.assertEqual(code_allow, 0)
        self.assertIn("PARTIAL", out_allow)

    # 15. Per-screen failure isolation
    def test_regression_per_screen_failure_isolation(self):
        import visual_audit
        screen2 = self.root / "docs/prototypes/dashboard"
        screen2.mkdir(parents=True)
        (screen2 / "index.html").write_text(CLEAN)
        (screen2 / "logo.png").write_bytes(VALID_PNG_1X1)

        shots = self.root / ".cgspec-scratch/visual"
        shots.mkdir(parents=True, exist_ok=True)
        for s in ("invoice", "dashboard"):
            for name in (f"{s}-desktop.png", f"{s}-desktop-dark.png", f"{s}-mobile.png", f"{s}-mobile-dark.png"):
                (shots / name).write_bytes(make_valid_png())

        records = []
        driver_result = {"results": [
            {"label": "invoice", "error": "Crash on screen invoice"},
            {"label": "dashboard", "viewports": [
                {"viewport": "desktop", "errors": [], "overflow": False, "quality": {}},
                {"viewport": "mobile", "errors": [], "overflow": False, "quality": {}},
            ]}
        ]}

        with mock.patch.object(visual_audit.browser, "run", return_value=driver_result):
            code, lines = visual_audit.audit(self.root, ["invoice", "dashboard"], write=True, records=records)

        rec_map = {r["item"]: r for r in records}
        self.assertEqual(rec_map["docs/prototypes/invoice/index.html"]["verdict"], "FAIL")
        self.assertEqual(rec_map["docs/prototypes/dashboard/index.html"]["verdict"], "PASS")

    # 14. Resource bound limit breach is PARTIAL/BLOCKED
    def test_regression_resource_bound_is_partial(self):
        import visual_audit
        base_dir = self.root / "docs/prototypes/_baselines"
        base_dir.mkdir(parents=True, exist_ok=True)
        (base_dir / "invoice-desktop.png").write_bytes(make_valid_png())
        (base_dir / "invoice-mobile.png").write_bytes(make_valid_png())

        vp = {"errors": [], "overflow": False, "scrollWidth": 1, "width": 1, "small": [], "smallCount": 0,
              "quality": {},
              "drift": {"error": "resource limit exceeded: image dimensions exceed max allowed", "limitExceeded": True}}
        shots = self.root / ".cgspec-scratch/visual"
        shots.mkdir(parents=True, exist_ok=True)
        for name in ("invoice-desktop.png", "invoice-desktop-dark.png", "invoice-mobile.png", "invoice-mobile-dark.png"):
            (shots / name).write_bytes(make_valid_png())

        driver_result = {"results": [{"label": "invoice", "viewports": [
            dict(vp, viewport="desktop"), dict(vp, viewport="mobile")]}]}

        with mock.patch.object(visual_audit.browser, "run", return_value=driver_result):
            code, lines = visual_audit.audit(self.root, ["invoice"], write=False)
        self.assertNotEqual(code, 0)
        self.assertTrue(any("LIMIT" in l or "PARTIAL" in l or "BLOCKED" in l for l in lines))


if __name__ == "__main__":
    unittest.main()
