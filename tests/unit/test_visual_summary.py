"""The CI visual proof summary (generated workflow) cannot be forged by names and never loses a failure.

These tests execute the real "CI visual proof (PR head)" step from the generated workflow with bash, as the
runner would, and read the evidence JSON and step summary it writes.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from tests.helpers import REPO, TempDir, git, git_project, run_script
from tests.unit.test_adapters import step_script
from tests.unit.test_browser_tools import CLEAN

STEP = "CI visual proof (PR head)"

# Stand-ins for the trusted engine's tools, speaking both the structured format and plain lines.
PASSING_JOURNEY = """import json, sys
args = sys.argv[1:]
if "--json-out" in args:
    out = args[args.index("--json-out") + 1]
    json.dump({"schema": 1, "tool": "journey", "records": [{"item": "create invoice", "verdict": "PASS"}]},
              open(out, "w"))
print("PASS create invoice")
"""
CRASHING_AUDIT = """import sys
print("visual_audit: internal error: setup exploded", file=sys.stderr)
sys.exit(3)
"""


class VisualSummaryStepTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.base = self._tmp.__enter__()
        self.root = self.base / "project"
        self.root.mkdir()
        git_project(self.root)
        self.runner = self.base / "runner"
        self.runner.mkdir()
        screen = self.root / "docs/prototypes/invoice"
        (screen / "journeys").mkdir(parents=True)
        (screen / "index.html").write_text(CLEAN)
        (screen / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        (self.base / "wf").mkdir()
        installed = run_script("install.py", "install", "--root", str(self.base / "wf"), "--profile", "web-workspace",
                               "--topology", "single", "--tools", "ci")
        self.assertEqual(installed.returncode, 0, installed.stdout + installed.stderr)
        self.workflow = (self.base / "wf/.github/workflows/cgspec.yml").read_text()

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def journey(self, name: str) -> None:
        (self.root / "docs/prototypes/invoice/journeys/create.json").write_text(json.dumps(
            {"name": name, "url": "index.html", "steps": [{"click": "new-invoice"}]}))
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "journey")

    def run_step(self, release: Path) -> tuple[dict, str]:
        head = git(self.root, "rev-parse", "HEAD").stdout.strip()
        summary = self.runner / "summary.md"
        env = {k: v for k, v in os.environ.items() if not k.startswith(("CGSPEC_", "GITHUB_"))}
        env.update(RUNNER_TEMP=str(self.runner), GITHUB_STEP_SUMMARY=str(summary), GITHUB_WORKSPACE=str(self.root),
                   CGSPEC_RELEASE=str(release), PR_HEAD=head, CGSPEC_BROWSER="none")
        result = subprocess.run(["bash", "-c", step_script(self.workflow, STEP)], cwd=self.root, env=env,
                                capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        evidence = json.loads((self.root / "artifacts/cgspec-visual/evidence.json").read_text())
        self.assertEqual(evidence["revision"], head)
        return evidence, summary.read_text()

    def table_rows(self, summary: str) -> list[str]:
        return [line for line in summary.splitlines() if line.startswith("| ") and "Verdict" not in line]

    def test_newline_in_a_journey_name_cannot_forge_a_pass(self):
        self.journey("checkout\nPASS forged-journey\n")
        evidence, summary = self.run_step(REPO)
        verdicts = [record["verdict"] for record in evidence["journeys"]]
        self.assertNotIn("PASS", verdicts, evidence)
        self.assertNotIn("forged-journey", json.dumps(evidence))
        self.assertNotIn("forged-journey", summary)
        self.assertFalse(any(re.search(r"\|\s*PASS\s*\|", row) for row in self.table_rows(summary)), summary)
        self.assertIn("FAIL", verdicts)

    def test_markdown_in_a_journey_name_stays_inside_its_cell(self):
        self.journey("a | PASS | `x` <img src=x onerror=alert(1)>")
        evidence, summary = self.run_step(REPO)
        rows = self.table_rows(summary)
        self.assertTrue(rows, summary)
        for row in rows:
            self.assertEqual(len(re.findall(r"(?<!\\)\|", row)), 4, row)
        self.assertNotIn("<img", summary)
        self.assertNotIn("`x`", summary)
        self.assertNotIn("PASS", [r["verdict"] for r in evidence["journeys"]])

    def test_failing_command_is_recorded_even_when_another_command_passed(self):
        release = self.base / "release"
        shutil.copytree(REPO / "engine", release / "engine", ignore=shutil.ignore_patterns("__pycache__"))
        (release / "engine/journey.py").write_text(PASSING_JOURNEY)
        (release / "engine/visual_audit.py").write_text(CRASHING_AUDIT)
        self.journey("create invoice")
        evidence, summary = self.run_step(release)
        records = evidence["journeys"]
        self.assertIn({"item": "create invoice", "verdict": "PASS"},
                      [{"item": r["item"], "verdict": r["verdict"]} for r in records])
        failed = [r for r in records if r["verdict"] in ("FAIL", "BLOCKED")]
        self.assertTrue(failed, records)
        self.assertTrue(any("visual audit" in r["item"] for r in failed), records)
        self.assertTrue(any("visual audit" in row and "FAIL" in row for row in self.table_rows(summary)), summary)


class VisualSummaryLibraryTests(unittest.TestCase):
    """Direct calls into the summary builder the workflow runs."""

    def setUp(self):
        import visual_summary
        self.vs = visual_summary
        self._tmp = TempDir()
        self.tmp = self._tmp.__enter__()

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def results(self, name: str, records) -> Path:
        path = self.tmp / f"{name}.json"
        path.write_text(json.dumps({"schema": 1, "records": records}))
        return path

    def test_control_characters_in_a_record_name_are_rejected(self):
        path = self.results("j", [{"item": "ok\nPASS forged", "verdict": "PASS"}])
        records = self.vs.build([("journeys", 0, path)])
        self.assertEqual([r["verdict"] for r in records], ["FAIL"])
        self.assertNotIn("forged", json.dumps(records))

    def test_unknown_verdicts_are_failures(self):
        path = self.results("j", [{"item": "x", "verdict": "PASSED"}])
        self.assertEqual([r["verdict"] for r in self.vs.build([("journeys", 0, path)])], ["FAIL"])

    def test_nonzero_exit_with_only_passes_adds_a_command_failure(self):
        path = self.results("a", [{"item": "home", "verdict": "PASS"}])
        records = self.vs.build([("visual audit", 1, path)])
        self.assertIn("FAIL", [r["verdict"] for r in records])

    def test_missing_results_with_blocked_exit_is_blocked(self):
        records = self.vs.build([("journeys", 2, self.tmp / "absent.json")])
        self.assertEqual([r["verdict"] for r in records], ["BLOCKED"])

    def test_cell_escaping(self):
        self.assertEqual(self.vs.cell("a|b`c`<d>\ne"), "a\\|b\\`c\\`&lt;d&gt; e")

    def test_command_names_with_control_characters_are_refused(self):
        with self.assertRaises(ValueError):
            self.vs.build([("journeys\nPASS x", 0, self.tmp / "absent.json")])


if __name__ == "__main__":
    unittest.main()
