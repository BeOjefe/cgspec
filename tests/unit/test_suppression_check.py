"""The shipped suppression ratchet permits only a same-or-smaller baseline."""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.helpers import REPO, git


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
        return subprocess.run(["python3", str(REPO / "templates/checks/no_new_suppressions.py"),
                               "eslint-suppressions.json"], cwd=self.root, capture_output=True, text=True)

    def test_shrinking_passes(self):
        self.path.write_text(json.dumps({"a": [1]}))
        self.assertEqual(self.run_check().returncode, 0)

    def test_growing_fails(self):
        self.path.write_text(json.dumps({"a": [1, 2, 4], "b": [3]}))
        self.assertEqual(self.run_check().returncode, 1)

    def test_replacing_an_entry_fails_even_when_count_is_unchanged(self):
        self.path.write_text(json.dumps({"a": [1, 9], "b": [3]}))
        self.assertEqual(self.run_check().returncode, 1)


if __name__ == "__main__":
    unittest.main()
