"""ci event: every commit in the range is re-checked, and failing-test records are proven by re-running them."""

from __future__ import annotations

import json
import unittest

from tests.helpers import TempDir, git, git_project, hook, make_slice, run_script, write_json

CHECK = ["python3", "-c", "import pathlib,sys; sys.exit(0 if pathlib.Path('src/login/fixed.txt').exists() else 1)"]


def head(root):
    return git(root, "rev-parse", "HEAD").stdout.strip()


def ci(root, base):
    return hook(root, "ci", None, "--tool", "git", "--base", base)


class CiTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git_project(self.root)
        self.base = head(self.root)
        make_slice(self.root, scope="src/login/**, tests/**")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "slice")
        self.failing_commit = head(self.root)

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def tier_t1(self):
        run_script("cgspec_hook.py", "tier", "set", "--tier", "T1", "--reason", "login fix",
                   "--slice", "SLICE-001", "--root", str(self.root))

    def record(self, failed_at):
        write_json(self.root / "docs/_cgspec/06-evidence/tests/login.json", {
            "schema": 1, "test_id": "login-fixed", "test_file": "tests/login_check.py", "slice": "SLICE-001",
            "command": CHECK, "failed_at": failed_at,
            "passed_at": None, "covers": ["src/login/form.ts", "src/login/fixed.txt"], "recorded": "2026-10-18T00:00:00Z"})

    def fix_commit(self, failed_at):
        self.tier_t1()
        (self.root / "src/login/form.ts").write_text("export const f = 2;\n")
        (self.root / "src/login/fixed.txt").write_text("ok\n")
        (self.root / "tests").mkdir(exist_ok=True)
        (self.root / "tests/login_check.py").write_text("# checks src/login/fixed.txt exists\n")
        self.record(failed_at)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "fix login")

    def test_honest_range_passes(self):
        self.fix_commit(self.failing_commit)
        result = ci(self.root, self.base)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("proved", result.stdout)

    def test_fake_failing_record_is_caught(self):
        # Claim the test failed at a commit where it actually passes.
        self.fix_commit(self.failing_commit)
        passing = head(self.root)
        self.record(passing)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "fake record")
        result = ci(self.root, self.base)
        self.assertEqual(result.returncode, 1)
        self.assertIn("did not fail", result.stdout)

    def test_commit_that_skipped_the_local_hook_is_caught(self):
        (self.root / "src/a.ts").write_text("export const a = 99;\n")  # no tier at all
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "--no-verify", "-m", "sneaky")
        result = ci(self.root, self.base)
        self.assertEqual(result.returncode, 1)
        self.assertIn("no change tier", result.stdout)
        self.assertIn("sneaky", result.stdout)

    def test_frozen_entry_rewritten_across_commits_is_caught(self):
        frozen = self.root / "docs/_cgspec/07-state/frozen.json"
        snap = self.root / "docs/prototypes/_snapshots/home-v1.html"
        snap.write_text("<html>v1</html>")
        import hashlib
        data = json.loads(frozen.read_text())
        data["entries"].append({"path": "docs/prototypes/_snapshots/home-v1.html",
                                "sha256": hashlib.sha256(b"<html>v1</html>").hexdigest(),
                                "kind": "snapshot", "added": "2026-10-18T00:00:00Z", "reason": "locked"})
        write_json(frozen, data)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "freeze")
        data["entries"] = []
        write_json(frozen, data)
        snap.unlink()
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "--no-verify", "-m", "unfreeze")
        result = ci(self.root, self.base)
        self.assertEqual(result.returncode, 1)
        self.assertIn("append-only", result.stdout)

    def test_working_tree_is_left_untouched(self):
        self.fix_commit(self.failing_commit)
        before = git(self.root, "status", "--porcelain").stdout
        ci(self.root, self.base)
        self.assertEqual(git(self.root, "status", "--porcelain").stdout, before)
        self.assertEqual(git(self.root, "worktree", "list").stdout.count("\n"), 1)


if __name__ == "__main__":
    unittest.main()
