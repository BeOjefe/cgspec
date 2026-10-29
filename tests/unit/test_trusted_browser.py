"""Browser proof cannot be forged by Node modules the checked project controls (spec 7, CI visual proof).

In trusted mode (CGSPEC_PLAYWRIGHT_DIR set, as the generated CI workflow does) the driver loads Playwright
only from that directory, never from the project's node_modules. In every mode a journey or audit passes
only when the driver reported every expected viewport and every expected screenshot (and video) exists.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.helpers import ENGINE, PY, TempDir, git_project
from tests.unit.test_browser_tools import CLEAN

# A stand-in "playwright" that never starts a browser: every call succeeds and nothing is rendered.
FAKE_PLAYWRIGHT = """
const fs = require("fs"), path = require("path");
fs.writeFileSync(path.join(__dirname, "LOADED"), "fake playwright was loaded\\n");
const handler = { get(target, prop) { if (prop === "then") return undefined; return () => fake; } };
const fake = new Proxy(function () {}, handler);
module.exports = { chromium: { launch: async () => fake } };
"""

JOURNEY = {"name": "create invoice", "url": "index.html", "viewports": ["desktop", "mobile"],
           "steps": [{"click": "new-invoice"}, {"screenshot": "after"}]}


def fake_module(base: Path) -> Path:
    package = base / "node_modules/playwright"
    package.mkdir(parents=True)
    (package / "package.json").write_text(json.dumps({"name": "playwright", "main": "index.js"}))
    (package / "index.js").write_text(FAKE_PLAYWRIGHT)
    return package


@unittest.skipUnless(shutil.which("node"), "Node.js is not installed")
class TrustedPlaywrightTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git_project(self.root)
        screen = self.root / "docs/prototypes/invoice"
        (screen / "journeys").mkdir(parents=True)
        (screen / "index.html").write_text(CLEAN)
        (screen / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        (screen / "journeys/create.json").write_text(json.dumps(JOURNEY))
        self.trusted = Path(tempfile.mkdtemp(prefix="cgspec-trusted-pw-"))

    def tearDown(self):
        shutil.rmtree(self.trusted, ignore_errors=True)
        self._tmp.__exit__(None, None, None)

    def run_tool(self, script: str, *args: str, trusted: bool):
        env = {k: v for k, v in os.environ.items() if k not in {"CGSPEC_BROWSER", "CGSPEC_PLAYWRIGHT_DIR", "NODE_PATH"}}
        if trusted:
            env["CGSPEC_PLAYWRIGHT_DIR"] = str(self.trusted)
        return subprocess.run([PY, str(ENGINE / script), *args, "--no-evidence", "--root", str(self.root)],
                              capture_output=True, text=True, env=env, timeout=120)

    def test_project_node_modules_are_not_loaded_in_trusted_mode(self):
        planted = fake_module(self.root)
        result = self.run_tool("journey.py", trusted=True)
        self.assertFalse((planted / "LOADED").exists(), "the project's playwright module was executed")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertNotIn("PASS", result.stdout)
        self.assertIn("BLOCKED", result.stdout)

    def test_project_node_modules_are_not_loaded_by_the_audit_in_trusted_mode(self):
        planted = fake_module(self.root)
        result = self.run_tool("visual_audit.py", trusted=True)
        self.assertFalse((planted / "LOADED").exists(), "the project's playwright module was executed")
        self.assertNotIn("PASS", result.stdout)

    def test_trusted_directory_inside_the_project_is_refused(self):
        self.trusted = self.root / "vendor-pw"
        planted = fake_module(self.trusted)
        result = self.run_tool("journey.py", trusted=True)
        self.assertFalse((planted / "LOADED").exists())
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

    def test_forged_success_without_screenshots_is_not_a_pass(self):
        fake_module(self.root)  # untrusted local mode: the project's module is used, but proved by artifacts
        journey = self.root / "docs/prototypes/invoice/journeys/create.json"
        journey.write_text(json.dumps({**JOURNEY, "steps": [{"state": "ready"}, {"screenshot": "after"}]}))
        result = self.run_tool("journey.py", trusted=False)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("PASS", result.stdout)
        self.assertIn("screenshot", result.stdout)

    def test_forged_audit_without_screenshots_is_not_a_pass(self):
        fake_module(self.root)
        result = self.run_tool("visual_audit.py", trusted=False)
        self.assertNotIn("PASS", result.stdout)


class ForgedResultTests(unittest.TestCase):
    """Driver output that omits viewports or artifacts cannot produce PASS."""

    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git_project(self.root)
        screen = self.root / "docs/prototypes/invoice"
        (screen / "journeys").mkdir(parents=True)
        (screen / "index.html").write_text(CLEAN)
        (screen / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        journey_file = screen / "journeys/create.json"
        journey_file.write_text(json.dumps(JOURNEY))
        import journey as _journey
        self.label = _journey.label_for(journey_file, self.root, screen, JOURNEY["name"])

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def journey(self, result, video=False):
        import journey
        with mock.patch.object(journey.browser, "run", return_value=result):
            return journey.run(self.root, [], write=False, video=video)

    def audit(self, result, video=False):
        import visual_audit
        with mock.patch.object(visual_audit.browser, "run", return_value=result):
            return visual_audit.audit(self.root, [], write=False, video=video)

    def test_empty_viewport_list_fails_the_journey(self):
        code, lines = self.journey({"results": [{"label": self.label, "viewports": []}]})
        self.assertNotEqual(code, 0)
        self.assertFalse(any(line.startswith("PASS") for line in lines), lines)

    def test_missing_result_fails_the_journey(self):
        code, lines = self.journey({"results": []})
        self.assertNotEqual(code, 0)
        self.assertFalse(any(line.startswith("PASS") for line in lines), lines)

    def test_forged_label_cannot_stand_in_for_the_journey(self):
        code, lines = self.journey({"results": [{"label": "other", "viewports": [
            {"viewport": "desktop", "ok": True, "state": "s", "errors": []}]}]})
        self.assertNotEqual(code, 0)
        self.assertFalse(any(line.startswith("PASS") for line in lines), lines)

    def test_ok_viewports_without_screenshot_files_fail(self):
        ok = [{"viewport": v, "ok": True, "state": "start", "errors": []} for v in ("desktop", "mobile")]
        code, lines = self.journey({"results": [{"label": self.label, "viewports": ok}]})
        self.assertNotEqual(code, 0)
        self.assertIn("screenshot", "\n".join(lines))

    def test_ok_viewports_with_real_screenshots_pass_and_video_is_required_when_asked(self):
        shots = self.root / ".cgspec-scratch/journeys"
        ok = [{"viewport": v, "ok": True, "state": "start", "errors": []} for v in ("desktop", "mobile")]
        result = {"results": [{"label": self.label, "viewports": ok}]}

        def driver(root, runs, folder, video=False):
            for vp in ("desktop", "mobile"):
                for name in (f"{self.label}-{vp}-after.png", f"{self.label}-{vp}.png"):
                    (folder / name).write_bytes(b"\x89PNG\r\n\x1a\nimage")
            return result
        import journey
        shots.mkdir(parents=True, exist_ok=True)
        with mock.patch.object(journey.browser, "run", side_effect=driver):
            code, lines = journey.run(self.root, [], write=False)
        self.assertNotEqual(code, 0, lines)
        self.assertIn(".webm", "\n".join(lines))

    def test_empty_viewport_list_fails_the_audit(self):
        code, lines = self.audit({"results": [{"label": "invoice", "viewports": []}]})
        self.assertFalse(any(line.startswith("PASS") for line in lines), lines)
        self.assertNotEqual(code, 0)

    def test_audit_without_screenshot_files_fails(self):
        vp = {"errors": [], "overflow": False, "scrollWidth": 1, "width": 1, "small": [], "smallCount": 0,
              "quality": {}}
        code, lines = self.audit({"results": [{"label": "invoice", "viewports": [
            dict(vp, viewport="desktop"), dict(vp, viewport="mobile")]}]})
        self.assertFalse(any(line.startswith("PASS") for line in lines), lines)
        self.assertNotEqual(code, 0)


class CollidingJourneyLabelTests(unittest.TestCase):
    """'pay now' and 'pay-now' share a slug. A failed first journey and a passing second one must not
    produce exit 0 with two PASS records for the same name: run identity must come from each journey
    file's own unique path, and a duplicate label returned by the driver must fail closed, not overwrite."""

    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git_project(self.root)
        self.screen = self.root / "docs/prototypes/pay"
        (self.screen / "journeys").mkdir(parents=True)
        (self.screen / "index.html").write_text(CLEAN)
        step = [{"click": "new-invoice"}]
        (self.screen / "journeys/a.json").write_text(json.dumps({"name": "pay now", "url": "index.html", "steps": step}))
        (self.screen / "journeys/b.json").write_text(json.dumps({"name": "pay-now", "url": "index.html", "steps": step}))

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def test_colliding_names_do_not_erase_the_failure(self):
        import journey
        captured = {}

        def driver(root, runs, shots, video=False):
            captured["runs"] = runs
            results = []
            shots.mkdir(parents=True, exist_ok=True)
            for i, run in enumerate(runs):
                ok = i != 0  # the first discovered journey fails, the second passes
                vp = {"viewport": "desktop", "ok": ok, "state": "s", "errors": [] if ok else ["boom"]}
                (shots / f"{run['label']}-desktop.png").write_bytes(b"\x89PNG\r\n\x1a\nimage")
                if ok:
                    (shots / f"{run['label']}-desktop.webm").write_bytes(b"\x1a\x45\xdf\xa3video")
                results.append({"label": run["label"], "viewports": [vp]})
            return {"results": results}

        with mock.patch.object(journey.browser, "run", side_effect=driver):
            code, lines = journey.run(self.root, [], write=False)
        self.assertNotEqual(code, 0, lines)
        labels = [r["label"] for r in captured["runs"]]
        self.assertEqual(len(labels), 2)
        self.assertEqual(len(set(labels)), 2, f"journey run labels must be unique, got {labels}")
        joined = "\n".join(lines)
        self.assertEqual(joined.count("PASS"), 1, joined)
        self.assertIn("FAIL", joined)

    def test_driver_returning_a_duplicate_label_fails_closed(self):
        """Even if two runs' labels happened to collide, a driver answer that returns the same label
        twice must not let the later (or earlier) entry silently stand in for the other."""
        from _lib import browser
        shots = self.root / ".cgspec-scratch/journeys"
        shots.mkdir(parents=True, exist_ok=True)
        duplicate_result = {"results": [
            {"label": "dup", "viewports": [{"viewport": "desktop", "ok": False, "state": "s", "errors": ["boom"]}]},
            {"label": "dup", "viewports": [{"viewport": "desktop", "ok": True, "state": "s", "errors": []}]},
        ]}
        reported = browser.results_by_label(duplicate_result)
        self.assertIs(reported["dup"], browser.DUPLICATE)
        item = {"kind": "journey", "label": "dup", "steps": [], "viewports": ["desktop"]}
        problems = browser.proof_problems(item, reported["dup"], shots)
        self.assertTrue(problems)
        self.assertIn("duplicate", problems[0])


if __name__ == "__main__":
    unittest.main()
