"""The shipped suppression ratchet permits only a same-or-smaller baseline."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.helpers import REPO, TempDir, approve, git, git_project, hook, run_script


class SuppressionRatchetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cgspec-suppressions-")
        self.root = Path(self.tmp.name)
        git(self.root, "init", "-q", "-b", "main")
        self.path = self.root / "eslint-suppressions.json"
        self.path.write_text(json.dumps({"a": [1, 2], "b": [3]}) + "\n")
        git(self.root, "add", "eslint-suppressions.json")
        git(self.root, "commit", "-q", "-m", "base")

    def tearDown(self):
        self.tmp.cleanup()

    def run_check(self):
        env = dict(os.environ, CGSPEC_BASE_REV="HEAD", CGSPEC_REPO_ROOT=str(self.root))
        return subprocess.run(["python3", str(REPO / "templates/checks/no_new_suppressions.py"),
                               "eslint-suppressions.json"], cwd=self.root, capture_output=True, text=True, env=env)

    def test_without_the_engine_base_it_refuses_to_guess(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("CGSPEC_")}
        result = subprocess.run(["python3", str(REPO / "templates/checks/no_new_suppressions.py"),
                                 "eslint-suppressions.json"], cwd=self.root, capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, 2)
        self.assertIn("CGSPEC_BASE_REV", result.stderr)

    def test_shrinking_passes(self):
        self.path.write_text(json.dumps({"a": [1]}))
        self.assertEqual(self.run_check().returncode, 0)

    def test_growing_fails(self):
        self.path.write_text(json.dumps({"a": [1, 2, 4], "b": [3]}))
        self.assertEqual(self.run_check().returncode, 1)

    def test_replacing_an_entry_fails_even_when_count_is_unchanged(self):
        self.path.write_text(json.dumps({"a": [1, 9], "b": [3]}))
        self.assertEqual(self.run_check().returncode, 1)



BASELINE = "eslint-suppressions.json"


def real_commit(root, message):
    """git commit with the installed CGSpec hooks active (no --no-verify, no hooksPath override)."""
    result = subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=t@example.com",
                             "-c", "commit.gpgsign=false", "commit", "-m", message], cwd=root,
                            capture_output=True, text=True)
    result.stdout += result.stderr  # git shows hook output on stderr
    return result


class RegisteredRatchetTests(unittest.TestCase):
    """The shipped ratchet registered as a check, judged by the engine in both gate environments."""

    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git_project(self.root)
        scratch = self.root / ".cgspec-scratch/checks"
        scratch.mkdir(parents=True)
        shutil.copyfile(REPO / "templates/checks/no_new_suppressions.py", scratch / "no_new_suppressions.py")
        shutil.copyfile(REPO / "templates/checks/no_new_suppressions.md", scratch / "no_new_suppressions.md")
        self.write({"src/a.ts": ["no-explicit-any", "no-unused-vars"], "src/login/form.ts": ["eqeqeq"]})
        result = run_script("cgspec_hook.py", "check", "register", "--file",
                            ".cgspec-scratch/checks/no_new_suppressions.py", "--guide",
                            ".cgspec-scratch/checks/no_new_suppressions.md", "--applies-to", BASELINE,
                            "--description", "tolerated lint errors may only shrink",
                            "--approval", approve(self.root, "approve the suppression ratchet"),
                            "--root", str(self.root))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "baseline and ratchet")
        self.base = git(self.root, "rev-parse", "HEAD").stdout.strip()

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def write(self, data):
        (self.root / BASELINE).write_text(json.dumps(data, indent=2) + "\n")

    def tier(self):
        result = run_script("cgspec_hook.py", "tier", "set", "--tier", "T0", "--reason", "baseline change",
                            "--files", BASELINE, "--root", str(self.root))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def grow(self):
        self.write({"src/a.ts": ["no-explicit-any", "no-unused-vars", "no-console"], "src/login/form.ts": ["eqeqeq"]})

    def shrink(self):
        self.write({"src/a.ts": ["no-explicit-any"], "src/login/form.ts": ["eqeqeq"]})

    def head(self):
        return git(self.root, "rev-parse", "HEAD").stdout.strip()

    def test_pre_commit_refuses_a_growing_baseline(self):
        self.tier()
        self.grow()
        git(self.root, "add", BASELINE, "docs/_cgspec/07-state/tier.json")
        result = real_commit(self.root, "tolerate one more error")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("CHK-001 failed", result.stdout)
        self.assertIn("entry added or changed; tolerated errors may only shrink", result.stdout)
        self.assertIn("How to fix this well (CHK-001 guide):", result.stdout)
        self.assertEqual(self.head(), self.base)

    def test_pre_commit_accepts_a_shrinking_baseline(self):
        self.tier()
        self.shrink()
        git(self.root, "add", BASELINE, "docs/_cgspec/07-state/tier.json")
        result = real_commit(self.root, "fix a tolerated error")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotEqual(self.head(), self.base)

    def test_pre_commit_judges_the_staged_baseline_not_the_working_tree(self):
        self.tier()
        self.grow()
        git(self.root, "add", BASELINE, "docs/_cgspec/07-state/tier.json")
        self.shrink()  # the working tree looks fine; the commit would still record growth
        result = real_commit(self.root, "staged growth")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("1 suppression entry added or changed", result.stdout)

    def ci(self):
        return hook(self.root, "ci", None, "--tool", "git", "--base", self.base)

    def test_ci_refuses_a_growing_baseline(self):
        self.tier()
        self.grow()
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "tolerate one more error")  # pushed past the local hook
        result = self.ci()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("CHK-001 failed", result.stdout)
        self.assertIn("entry added or changed; tolerated errors may only shrink", result.stdout)

    def test_ci_accepts_a_shrinking_baseline(self):
        self.tier()
        self.shrink()
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "fix a tolerated error")
        result = self.ci()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("CHK-001 PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
