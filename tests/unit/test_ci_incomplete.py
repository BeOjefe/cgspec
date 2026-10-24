"""An audit that skips failure proof cannot satisfy strict CI."""

from __future__ import annotations

import unittest

from tests.helpers import TempDir, git_project


class IncompleteCiTests(unittest.TestCase):
    def test_no_rerun_is_explicitly_incomplete(self):
        from _lib.ci_gate import run

        with TempDir() as root:
            git_project(root)
            problems, _ = run(root, None, rerun_tests=False)
            self.assertTrue(any("incomplete verification" in p for p in problems), problems)


if __name__ == "__main__":
    unittest.main()
