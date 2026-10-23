"""visual_audit.py and journey.py (spec 6, 7): static checks everywhere; rendered checks when a browser exists."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import unittest

from tests.helpers import TempDir, git_project, run_script

CLEAN = """<!doctype html><html lang="en"><head><meta name="viewport" content="width=device-width">
<style>body{margin:0;font-family:system-ui,sans-serif;color:#222}</style></head><body>
<main><h1>Invoices</h1>
<p data-testid="empty-state">No invoices yet</p>
<label for="customer">Customer</label><input id="customer" data-testid="customer">
<button data-testid="new-invoice" id="new">New invoice</button>
<ul data-testid="lines"></ul><img src="logo.png" alt="Logo"></main>
<script>
document.getElementById('new').addEventListener('click', () => {
  document.querySelector('[data-testid="empty-state"]').hidden = true;
  const li = document.createElement('li'); li.dataset.testid = 'line';
  li.setAttribute('data-testid', 'line'); li.textContent = document.getElementById('customer').value;
  document.querySelector('[data-testid="lines"]').append(li);
});
</script></body></html>"""

JOURNEY = {"name": "create invoice", "url": "index.html", "viewports": ["desktop", "mobile"], "steps": [
    {"state": "empty", "expect": [{"visible": "empty-state"}]},
    {"fill": "customer", "value": "Acme"},
    {"click": "new-invoice"},
    {"state": "one line", "expect": [{"hidden": "empty-state"}, {"count": "line", "equals": 1},
                                     {"text": "line", "equals": "Acme"}]},
    {"screenshot": "after"}]}


def has_browser() -> bool:
    if not shutil.which("node"):
        return False
    probe = subprocess.run(["node", "-e", "require('playwright')"], capture_output=True)
    return probe.returncode == 0


class Base(unittest.TestCase):
    browser = False

    def setUp(self):
        self._env = os.environ.get("CGSPEC_BROWSER")
        if not self.browser:
            os.environ["CGSPEC_BROWSER"] = "none"
        self._tmp = TempDir()
        self.root = r = self._tmp.__enter__()
        git_project(r)
        self.screen = r / "docs/prototypes/invoice"
        (self.screen / "journeys").mkdir(parents=True)
        (self.screen / "index.html").write_text(CLEAN)
        (self.screen / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        journey_file = self.screen / "journeys/create.json"
        journey_file.write_text(json.dumps(JOURNEY))
        import journey as _journey
        self.journey_label = _journey.label_for(journey_file, self.root, self.screen, JOURNEY["name"])

    def tearDown(self):
        if self._env is None:
            os.environ.pop("CGSPEC_BROWSER", None)
        else:
            os.environ["CGSPEC_BROWSER"] = self._env
        self._tmp.__exit__(None, None, None)

    def audit(self, *args):
        return run_script("visual_audit.py", *args, "--root", str(self.root))

    def journey(self, *args):
        return run_script("journey.py", *args, "--root", str(self.root))

    def evidence(self, scope, name):
        return json.loads((self.root / f"docs/_cgspec/06-evidence/{scope}/{name}.json").read_text())

    def page(self, body, head='<meta name="viewport" content="width=device-width">'):
        (self.screen / "index.html").write_text(f'<!doctype html><html lang="en"><head>{head}</head><body>{body}</body></html>')


class StaticAuditTests(Base):
    def test_clean_screen_is_partial_without_browser(self):
        result = self.audit("invoice")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("PARTIAL", result.stdout)
        record = self.evidence("visual", "invoice")
        self.assertEqual(record["verdict"], "PARTIAL")
        self.assertEqual(record["covers"], ["docs/prototypes/invoice/**"])
        self.assertIn("rendered checks not run", record["details"])

    def test_dead_controls_and_phantom_ids_fail(self):
        self.page('<button data-testid="x">Save</button><a href="#">Help</a><label for="nope">N</label>'
                  '<a href="#missing">Jump</a><script>document.getElementById("gone")</script>')
        out = self.audit("invoice").stdout
        self.assertEqual(out.count("E-HANDLER"), 2, out)
        self.assertIn("'nope'", out)
        self.assertIn("'missing'", out)
        self.assertIn("'gone'", out)

    def test_ids_created_by_script_and_delegated_actions_are_not_phantom(self):
        self.page('<button data-action="save" data-testid="s">Save</button><a href="#panel">Open</a>'
                  '<script>const d=document.createElement("div");d.id="panel";'
                  'document.addEventListener("click",e=>e.target.dataset.action)</script>')
        result = self.audit("invoice")
        self.assertEqual(result.returncode, 2, result.stdout)

    def test_duplicate_ids_alt_names_and_emoji(self):
        self.page('<div id="a"></div><div id="a"></div><img src="x.png"><button onclick="go()"></button>'
                  '<p>Done ✅</p>')
        out = self.audit("invoice").stdout
        for code in ("E-DUP-ID", "E-IMG-ALT", "E-NO-NAME", "E-EMOJI"):
            self.assertIn(code, out)

    def test_generic_look_tells_warn_and_css_comment_cannot_allow(self):
        css = ("<style>h1{background:linear-gradient(#7c3aed,#a855f7);-webkit-background-clip:text;"
               "background-clip:text;color:transparent}.c{box-shadow:0 0 30px #a855f7}</style>")
        self.page('<h1>Hi</h1>', head='<meta name="viewport" content="width=device-width">' + css)
        result = self.audit("invoice")
        self.assertEqual(result.returncode, 2, result.stdout)
        for code in ("W-LOOK-PURPLE", "W-LOOK-GRADIENT-TEXT", "W-LOOK-GLOW"):
            self.assertIn(code, result.stdout)
        self.page('<h1>Hi</h1>', head=css.replace("<style>", "<style>/* cgspec-allow: purple */"))
        self.assertIn("W-LOOK-PURPLE", self.audit("invoice").stdout)

    def test_missing_local_file_fails(self):
        (self.screen / "logo.png").unlink()
        result = self.audit("invoice")
        self.assertEqual(result.returncode, 1)
        self.assertIn("E-MISSING-FILE", result.stdout)

    def test_register_deliberate_choice_accepts_tell(self):
        css = "<style>.a{color:#7c3aed}</style>"
        self.page('<p class="a">Hi</p>', head='<meta name="viewport" content="width=device-width">' + css)
        self.assertIn("W-LOOK-PURPLE", self.audit("invoice").stdout)
        spine = self.root / "docs/spines/03-EXPERIENCE.md"
        spine.write_text(spine.read_text().replace(
            "## Register\n", "## Register\nStatus: Locked\n"
            "- Deliberate choices: purple\n"
            "- Deliberate reason purple: existing brand since 2024\n", 1))
        self.assertNotIn("W-LOOK-PURPLE", self.audit("invoice").stdout)

    def test_unknown_target_errors(self):
        self.assertEqual(self.audit("nope").returncode, 1)


class StaticJourneyTests(Base):
    def test_valid_journey_is_blocked_without_browser(self):
        result = self.journey("invoice")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(self.evidence("journeys", self.journey_label)["verdict"], "BLOCKED")

    def test_missing_test_id_fails_without_browser(self):
        bad = dict(JOURNEY, steps=JOURNEY["steps"] + [{"click": "archive"}])
        (self.screen / "journeys/create.json").write_text(json.dumps(bad))
        result = self.journey()
        self.assertEqual(result.returncode, 1)
        self.assertIn("archive", result.stdout)
        self.assertEqual(self.evidence("journeys", self.journey_label)["verdict"], "FAIL")

    def test_malformed_journey_refused(self):
        (self.screen / "journeys/create.json").write_text(json.dumps({"name": "x", "url": "index.html",
                                                                      "steps": [{"tap": "a"}]}))
        result = self.journey("invoice")
        self.assertEqual(result.returncode, 1)
        self.assertIn("exactly one action", result.stderr)


@unittest.skipUnless(has_browser(), "Playwright for Node is not installed")
class BrowserTests(Base):
    browser = True

    def test_video_flag_writes_webm_when_browser_is_available(self):
        if not has_browser():
            self.skipTest("Playwright is not installed")
        result = self.journey("invoice", "--video")
        if result.returncode == 2:
            self.skipTest("Playwright Chromium is unavailable")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(any((self.root / ".cgspec-scratch/journeys").glob("*.webm")))

    def test_journey_passes_on_desktop_and_mobile_with_screenshots(self):
        result = self.journey("invoice")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.evidence("journeys", self.journey_label)["verdict"], "PASS")
        self.assertTrue((self.root / f".cgspec-scratch/journeys/{self.journey_label}-mobile-after.png").is_file())

    def test_wrong_assertion_fails_naming_step_and_state(self):
        bad = json.loads(json.dumps(JOURNEY))
        bad["steps"][3]["expect"][2]["equals"] = "Globex"
        (self.screen / "journeys/create.json").write_text(json.dumps(bad))
        result = self.journey("invoice")
        self.assertEqual(result.returncode, 1)
        self.assertIn("step 4 (state one line)", result.stdout)

    def test_page_error_fails_journey(self):
        (self.screen / "index.html").write_text(CLEAN.replace("<script>", "<script>undefinedFn();"))
        self.assertEqual(self.journey("invoice").returncode, 1)

    def test_low_contrast_and_missing_focus_fail(self):
        (self.screen / "index.html").write_text(CLEAN.replace(
            "color:#222}", "color:#222} p{color:#bbb} button:focus,input:focus{outline:none}"))
        result = self.audit("invoice")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("E-CONTRAST", result.stdout)
        self.assertIn("E-FOCUS", result.stdout)

    def test_sizes_outside_token_scale_warn(self):
        (self.root / "src").mkdir(exist_ok=True)
        (self.root / "src/tokens.json").write_text(json.dumps(
            {"font": {"size": {"base": {"$type": "dimension", "$value": "14px"}}},
             "space": {"unit": {"$type": "dimension", "$value": "4px"}}}))
        out = self.audit("invoice").stdout
        self.assertIn("W-TYPE-SCALE", out)

    def test_audit_passes_and_catches_mobile_overflow(self):
        result = self.audit("invoice")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.root / ".cgspec-scratch/visual/invoice-mobile.png").is_file())
        (self.screen / "index.html").write_text(CLEAN.replace("<main>", '<main style="width:1200px">'))
        result = self.audit("invoice")
        self.assertEqual(result.returncode, 1)
        self.assertIn("E-OVERFLOW", result.stdout)


if __name__ == "__main__":
    unittest.main()
