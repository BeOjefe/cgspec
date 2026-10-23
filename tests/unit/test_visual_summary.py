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
# Reads a marker file at the given --root and reports it verbatim, so a test can tell whether the
# proof ran against the committed tree or a dirty working copy that was never committed.
MARKER_READING_JOURNEY = """import json, sys
from pathlib import Path
args = sys.argv[1:]
root = Path(args[args.index("--root") + 1])
content = (root / "marker.txt").read_text().strip()
out = args[args.index("--json-out") + 1]
json.dump({"schema": 1, "tool": "journey",
           "records": [{"item": "marker", "verdict": "PASS" if content == "fixed-but-uncommitted" else "FAIL",
                        "detail": content}]}, open(out, "w"))
"""
# Reports the PLAYWRIGHT_BROWSERS_PATH seen by the trusted engine's own process.
BROWSERS_PATH_JOURNEY = """import json, os, sys
args = sys.argv[1:]
out = args[args.index("--json-out") + 1]
json.dump({"schema": 1, "tool": "journey",
           "records": [{"item": "browsers-path", "verdict": "PASS",
                        "detail": os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")}]}, open(out, "w"))
"""


def make_release(base: Path, name: str, journey_py: str | None = None) -> Path:
    release = base / name
    shutil.copytree(REPO / "engine", release / "engine", ignore=shutil.ignore_patterns("__pycache__"))
    if journey_py is not None:
        (release / "engine/journey.py").write_text(journey_py)
    return release


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

    def out_dir(self, head: str) -> Path:
        return self.runner / f"cgspec-visual-proof-{head}"

    def run_step(self, release: Path) -> tuple[dict, str]:
        head = git(self.root, "rev-parse", "HEAD").stdout.strip()
        summary = self.runner / "summary.md"
        env = {k: v for k, v in os.environ.items() if not k.startswith(("CGSPEC_", "GITHUB_"))}
        env.update(RUNNER_TEMP=str(self.runner), GITHUB_STEP_SUMMARY=str(summary), GITHUB_WORKSPACE=str(self.root),
                   CGSPEC_RELEASE=str(release), PR_HEAD=head, CGSPEC_BROWSER="none")
        result = subprocess.run(["bash", "-c", step_script(self.workflow, STEP)], cwd=self.root, env=env,
                                capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        evidence = json.loads((self.out_dir(head) / "evidence.json").read_text())
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

    def test_dirty_tracked_file_in_the_checkout_is_never_tested_as_the_pr_head(self):
        """A tracked file left dirty in the existing checkout must not leak into the proof: the proof
        must run against a fresh worktree at the exact PR head, not `git checkout --detach` in place,
        which can leave compatible uncommitted changes untouched."""
        self.journey("marker journey")
        (self.root / "marker.txt").write_text("broken-and-committed\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "marker")
        head = git(self.root, "rev-parse", "HEAD").stdout.strip()
        # An uncommitted edit to a tracked file sitting in the checkout when the proof step runs.
        (self.root / "marker.txt").write_text("fixed-but-uncommitted\n")
        release = make_release(self.base, "release-marker", MARKER_READING_JOURNEY)
        evidence, summary = self.run_step(release)
        self.assertEqual(head, git(self.root, "rev-parse", "HEAD").stdout.strip())
        marker_records = [r for r in evidence["journeys"] if r.get("item") == "marker"]
        self.assertTrue(marker_records, evidence)
        self.assertNotIn("PASS", [r["verdict"] for r in marker_records], evidence)
        self.assertEqual(marker_records[0]["detail"], "broken-and-committed", evidence)

    def test_planted_in_repo_evidence_is_left_untouched_and_ignored(self):
        """A PR-committed artifacts/cgspec-visual/ (a forged PASS, say) must never become, or influence,
        the uploaded evidence: the proof step must not read or write anything under the checkout."""
        planted_dir = self.root / "artifacts/cgspec-visual"
        planted_dir.mkdir(parents=True)
        forged = json.dumps({"schema": 1, "revision": "0" * 40, "artifact": "forged",
                             "journeys": [{"item": "forged-pass", "verdict": "PASS"}]})
        (planted_dir / "evidence.json").write_text(forged)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "attacker-planted evidence")
        self.journey("create invoice")
        evidence, summary = self.run_step(REPO)
        self.assertNotIn("forged-pass", json.dumps(evidence))
        self.assertNotIn("forged", summary)
        self.assertEqual((planted_dir / "evidence.json").read_text(), forged,
                         "the proof step must never read from or write to the checkout's artifacts directory")

    def test_playwright_browsers_path_is_set_under_runner_temp_during_the_proof(self):
        release = make_release(self.base, "release-browsers-path", BROWSERS_PATH_JOURNEY)
        self.journey("create invoice")
        evidence, summary = self.run_step(release)
        records = [r for r in evidence["journeys"] if r.get("item") == "browsers-path"]
        self.assertTrue(records, evidence)
        self.assertEqual(records[0]["detail"], str(self.runner / "cgspec-playwright-browsers"))


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
