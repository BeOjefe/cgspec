"""Approval through the commit trailer `Approved-by:` (spec 8, tools without a message hook)."""

from __future__ import annotations

import os
import subprocess
import unittest

from tests.helpers import TempDir, git, git_project, hook, make_slice, run_script


def commit(root, message):
    git(root, "add", "-A")
    git(root, "commit", "-q", "--no-verify", "-m", message)


class TrailerApprovalTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git_project(self.root)
        self.base = git(self.root, "rev-parse", "HEAD").stdout.strip()

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def ci(self):
        return hook(self.root, "ci", None, "--tool", "git", "--base", self.base)

    def test_slice_approved_by_trailer_passes(self):
        make_slice(self.root, approval="trailer")
        commit(self.root, "Approve login slice\n\nApproved-by: Ojefe <me@example.com>")
        result = self.ci()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_trailer_claim_without_trailer_fails(self):
        make_slice(self.root, approval="trailer")
        commit(self.root, "Approve login slice")
        result = self.ci()
        self.assertEqual(result.returncode, 1)
        self.assertIn("Approved-by", result.stdout)

    def test_commit_msg_hook_checks_the_trailer(self):
        make_slice(self.root, approval="trailer")
        git(self.root, "add", "-A")
        msg = self.root / ".git/COMMIT_EDITMSG"
        msg.write_text("Approve login slice\n")
        self.assertEqual(run_script("cgspec_hook.py", "commit-msg", str(msg), "--root", str(self.root)).returncode, 1)
        msg.write_text("Approve login slice\n\nApproved-by: Ojefe <me@example.com>\n")
        self.assertEqual(run_script("cgspec_hook.py", "commit-msg", str(msg), "--root", str(self.root)).returncode, 0)

    def test_tier_accepts_a_trailer_approved_slice(self):
        make_slice(self.root, approval="trailer")
        commit(self.root, "Approve\n\nApproved-by: Ojefe <me@example.com>")
        result = run_script("cgspec_hook.py", "tier", "set", "--tier", "T1", "--reason", "login work",
                            "--slice", "SLICE-001", "--root", str(self.root))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_ledger_approved_entry_needs_valid_approval_in_ci(self):
        log = self.root / "docs/_memlog.md"
        log.write_text(log.read_text() + "\n### [M-20261018-beef] 2026-10-18T00:00:00Z | tags: decision | owner: @agent | perms: public\n"
                       "- **Summary:** pick postgres\n- **Status:** Approved\n- **Approval:** A-20261018-ffff\n")
        commit(self.root, "forged decision approval")
        result = self.ci()
        self.assertEqual(result.returncode, 1)
        self.assertIn("A-20261018-ffff", result.stdout)


if __name__ == "__main__":
    unittest.main()
