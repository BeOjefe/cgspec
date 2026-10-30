"""Tests for .github/scripts/check_version_bump.py (issue #70)."""
from __future__ import annotations

import io
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / ".github" / "scripts" / "check_version_bump.py"


def run(stdin: str, *, base: str, head: str) -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--base-version", base, "--head-version", head],
        input=stdin, capture_output=True, text=True, check=False,
    )
    return result.returncode, result.stdout + result.stderr


class VersionBumpTests(unittest.TestCase):
    def test_no_engine_changes_pass(self):
        code, out = run("docs/METHOD.md\nREADME.md\n", base="0.3.0", head="0.3.0")
        self.assertEqual(code, 0, out)
        self.assertIn("no engine/** files changed", out)

    def test_version_only_change_is_not_an_engine_change(self):
        # engine/VERSION itself must not count: a VERSION-only PR doesn't need to bump above itself.
        code, out = run("engine/VERSION\n", base="0.3.0", head="0.3.0")
        self.assertEqual(code, 0, out)

    def test_engine_change_without_bump_fails(self):
        code, out = run("engine/_lib/release.py\n", base="0.3.0", head="0.3.0")
        self.assertEqual(code, 1, out)
        self.assertIn("did not advance", out)

    def test_engine_change_with_patch_bump_passes(self):
        code, out = run("engine/_lib/release.py\n", base="0.3.0", head="0.3.1")
        self.assertEqual(code, 0, out)
        self.assertIn("bumped 0.3.0 -> 0.3.1", out)

    def test_engine_change_with_minor_bump_passes(self):
        code, out = run("engine/_lib/release.py\n", base="0.3.9", head="0.4.0")
        self.assertEqual(code, 0, out)

    def test_engine_change_with_downgrade_fails(self):
        code, out = run("engine/doctor.py\n", base="0.3.1", head="0.3.0")
        self.assertEqual(code, 1, out)
        self.assertIn("did not advance", out)

    def test_invalid_head_semver_fails(self):
        code, out = run("engine/doctor.py\n", base="0.3.0", head="not-a-version")
        self.assertEqual(code, 1, out)
        self.assertIn("not a valid SemVer", out)

    def test_many_engine_files_truncate_listing(self):
        paths = "\n".join(f"engine/_lib/file{i}.py" for i in range(25))
        code, out = run(paths, base="0.3.0", head="0.3.1")
        self.assertEqual(code, 0, out)
        self.assertIn("and 15 more", out)


if __name__ == "__main__":
    unittest.main()
