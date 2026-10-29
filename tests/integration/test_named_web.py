"""Opt-in real Vitest and Chromium Playwright red/green proof in disposable Git trees."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.helpers import REPO, git, write_json
from tests.unit.test_named_runners import runner_project
from _lib.ci_gate import prove_failed
from _lib.runner_contracts import resolve, selected_command
from _lib.test_evolution import capture_at


@unittest.skipUnless(os.environ.get("CGSPEC_RUN_WEB_INTEGRATION") == "1", "opt-in real browser/npm integration")
class NamedWebIntegrationTests(unittest.TestCase):
    def setUp(self):
        scratch = Path("/tmp/opencode")
        self.temp = tempfile.TemporaryDirectory(prefix="cgspec-real-web-",
                                                dir=str(scratch) if scratch.is_dir() else None)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "project"
        shutil.copytree(REPO / "tests/fixtures/named-web", self.root)
        self.browser_cache = Path(self.temp.name) / "browsers"
        env = dict(os.environ, PLAYWRIGHT_BROWSERS_PATH=str(self.browser_cache))
        chrome = shutil.which("google-chrome")
        if chrome:
            env["CGSPEC_CHROME_PATH"] = chrome
        self.env_patch = patch.dict(os.environ, env)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        subprocess.run(["npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"],
                       cwd=self.root, stdout=subprocess.DEVNULL, check=True, timeout=180)
        if not chrome:
            subprocess.run(["npm", "exec", "--", "playwright", "install", "--only-shell", "chromium"],
                           cwd=self.root, stdout=subprocess.DEVNULL, check=True, timeout=300)
        shutil.rmtree(self.root / "node_modules")
        project = runner_project()
        project["test_environments"][0]["setup"] = ["npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"]
        project["test_environments"][0]["inputs"] = [
            "package.json", "package-lock.json", "playwright.config.js", "tools/semantic-adapter.js"]
        write_json(self.root / "docs/_cgspec/project.json", project)
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "failing unit and browser behavior")
        self.red = git(self.root, "rev-parse", "HEAD").stdout.strip()
        (self.root / "src/widget.js").write_text(
            "export function countAfterClick(count) { return count + 1; }\n")
        git(self.root, "add", "src/widget.js")
        git(self.root, "commit", "-q", "-m", "implement click")

    def test_real_vitest_and_playwright_assertion_proof(self):
        for runner_id, test_file in (("unit", "tests/unit.test.js"), ("browser", "tests/browser.spec.js")):
            with self.subTest(runner=runner_id):
                runner, environment, digest = resolve(json.loads((self.root / "docs/_cgspec/project.json").read_text()),
                                                       runner_id, lambda rel: (self.root / rel).read_bytes())
                identity, problem = capture_at(self.root, self.red, runner, environment, test_file, runner_id)
                self.assertIsNone(problem)
                record = {"_file": f"docs/_cgspec/06-evidence/tests/{runner_id}.json", "test_id": runner_id,
                          "failed_at": self.red, "test_file": test_file, "selector": test_file,
                          "runner_id": runner_id, "runner_hash": digest,
                          "command": selected_command(runner, test_file), "covers": ["src/widget.js"],
                          "test_semantics": identity}
                self.assertIsNone(prove_failed(self.root, record))
                substituted = dict(record, command=["true", test_file])
                self.assertIn("command or selection", prove_failed(self.root, substituted))


if __name__ == "__main__":
    unittest.main()
