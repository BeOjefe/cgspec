"""Semantic Versioning release governance (issue #42)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from tests.helpers import TempDir, install, make_slice, run_script

from _lib import release


def release_block(**overrides) -> dict:
    data = {"enabled": True, "pre_1_0": "0.minor.0", "current_version": "0.2.0"}
    data.update(overrides)
    return data


class ReleaseFixture:
    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        install(self.root)
        self.pj = self.root / "docs/_cgspec/project.json"
        self.proj = json.loads(self.pj.read_text())

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def set_release(self, **overrides):
        self.proj["release"] = release_block(**overrides)
        self.pj.write_text(json.dumps(self.proj, indent=2) + "\n")

    def add_slice(self, release_field: str | None, number: str = "001", status: str = "Approved"):
        path = make_slice(self.root, status=status, number=number)
        if release_field is not None:
            text = path.read_text()
            path.write_text(text + f"- **Release:** {release_field}\n")
        return path

    def cli(self, *args: str):
        return run_script("cgspec_hook.py", "release", *args, "--root", str(self.root))


class ReleaseUnitTests(unittest.TestCase):
    def test_parse_version_strict(self):
        self.assertEqual(release.parse_version("1.2.3"), (1, 2, 3))
        self.assertEqual(release.parse_version("0.0.0"), (0, 0, 0))
        self.assertIsNone(release.parse_version("1.2"))
        self.assertIsNone(release.parse_version("v1.2.3"))
        self.assertIsNone(release.parse_version("1.2.3.4"))

    def test_bump_stable_project(self):
        self.assertEqual(release.bump("1.2.3", "patch"), "1.2.4")
        self.assertEqual(release.bump("1.2.3", "minor"), "1.3.0")
        self.assertEqual(release.bump("1.2.3", "major"), "2.0.0")
        self.assertEqual(release.bump("1.2.3", "none"), "1.2.4")

    def test_bump_pre_1_0_policies(self):
        self.assertEqual(release.bump("0.2.3", "major", "0.minor.0"), "0.3.0")
        self.assertEqual(release.bump("0.2.3", "major", "0.patch.0"), "0.2.4")
        self.assertEqual(release.bump("0.2.3", "major", "0.major.0"), "1.0.0")
        self.assertEqual(release.bump("0.2.3", "minor", "0.minor.0"), "0.3.0")
        self.assertEqual(release.bump("0.2.3", "patch", "0.patch.0"), "0.2.4")

    def test_deprecation_hint_raises_requirement_to_minor(self):
        self.assertEqual(release.effective_impact("patch", "deprecate the old export"), "minor")
        self.assertEqual(release.effective_impact("patch", "fix the retry loop"), "patch")
        self.assertEqual(release.effective_impact("minor", "backward-compatible feature"), "minor")

    def test_invalid_impact_value_rejected(self):
        with self.assertRaises(release.CgspecError):
            release.bump("1.0.0", "huge")


class ReleaseCheckTests(ReleaseFixture, unittest.TestCase):
    def test_no_policy_is_blocked_never_guessed(self):
        result = self.cli("check", "--target", "0.3.0")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("declares no release policy", result.stderr)

    def test_explicit_opt_out_passes(self):
        self.set_release(enabled=False)
        result = self.cli("check", "--target", "0.2.0")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("opt-out", result.stdout)

    def test_enabled_without_current_version_is_blocked(self):
        self.set_release(enabled=True, current_version=None)
        result = self.cli("check", "--target", "0.2.1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("current_version", result.stderr)

    def test_patch_impact_is_released_under_patch(self):
        self.set_release(current_version="0.2.0")
        self.add_slice("patch (internal retry logic)")
        ok = self.cli("check", "--target", "0.2.1")
        self.assertEqual(ok.returncode, 0, ok.stderr)
        low = self.cli("check", "--target", "0.2.0")
        self.assertNotEqual(low.returncode, 0)
        self.assertIn("below the required 0.2.1", low.stderr)
        self.assertIn("SLICE-001", low.stderr)

    def test_mixed_slices_require_highest_bump(self):
        self.set_release(current_version="0.2.0")
        self.add_slice("minor (new public capability)", number="001")
        self.add_slice("major (breaking public export format)", number="002")
        low = self.cli("check", "--target", "0.2.5")
        self.assertNotEqual(low.returncode, 0)
        self.assertIn("required 0.3.0", low.stderr)  # pre-1.0 major -> minor under 0.minor.0
        self.assertIn("SLICE-002", low.stderr)
        ok = self.cli("check", "--target", "0.3.0")
        self.assertEqual(ok.returncode, 0, ok.stderr)

    def test_deprecation_declared_patch_still_requires_minor(self):
        self.set_release(current_version="1.4.0")
        self.add_slice("patch (deprecate the old export, behavior preserved)")
        patch_only = self.cli("check", "--target", "1.4.1")
        self.assertNotEqual(patch_only.returncode, 0)
        self.assertIn("required 1.5.0", patch_only.stderr)
        ok = self.cli("check", "--target", "1.5.0")
        self.assertEqual(ok.returncode, 0, ok.stderr)

    def test_internal_only_migration_is_not_major(self):
        self.set_release(current_version="1.4.0")
        self.add_slice("minor (rewrite persistence layer; public contracts unchanged)")
        ok = self.cli("check", "--target", "1.5.0")
        self.assertEqual(ok.returncode, 0, ok.stderr)
        ok_low = self.cli("check", "--target", "1.4.1")
        self.assertNotEqual(ok_low.returncode, 0)

    def test_breaking_public_format_forces_major_on_stable(self):
        self.set_release(current_version="1.4.0")
        self.add_slice("major (public export file format no longer reads old files; migration script included)")
        low = self.cli("check", "--target", "1.5.0")
        self.assertNotEqual(low.returncode, 0)
        self.assertIn("required 2.0.0", low.stderr)
        self.assertEqual(self.cli("check", "--target", "2.0.0").returncode, 0)

    def test_missing_release_field_on_included_slice_is_blocked(self):
        self.set_release(current_version="0.2.0")
        self.add_slice(None)
        result = self.cli("check", "--target", "0.3.0")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no Release field", result.stderr)

    def test_invalid_impact_value_is_classified_as_error(self):
        self.set_release(current_version="0.2.0")
        self.add_slice("enormous (everything changes)")
        result = self.cli("check", "--target", "0.3.0")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not one of", result.stderr)

    def test_draft_slices_are_not_included(self):
        self.set_release(current_version="0.2.0")
        self.add_slice("major (breaking change in a draft)", status="Draft")
        result = self.cli("check", "--target", "0.2.1")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_slices_scope_limits_included_slices(self):
        self.set_release(current_version="0.2.0")
        self.add_slice("major (breaking)", number="001")
        self.add_slice("minor (new capability)", number="002")
        result = self.cli("check", "--target", "0.2.1", "--slices", "SLICE-002")
        self.assertNotEqual(result.returncode, 0)  # minor still needs 0.3.0
        self.assertNotIn("SLICE-001", result.stderr)
        ok = self.cli("check", "--target", "0.3.0", "--slices", "SLICE-002")
        self.assertEqual(ok.returncode, 0, ok.stderr)
        plan = json.loads(self.cli("plan", "--slices", "SLICE-002").stdout)
        self.assertEqual(plan["required_bump"], "minor")
        self.assertEqual(plan["causes"], ["SLICE-002"])

    def test_plan_reports_policy_and_classified_slices(self):
        self.set_release(enabled=True, current_version="1.0.0")
        self.add_slice("patch (fix timeout retry)")
        plan = json.loads(self.cli("plan").stdout)
        self.assertEqual(plan["policy"]["current_version"], "1.0.0")
        self.assertEqual(plan["required_bump"], "patch")
        self.assertEqual(plan["slices"][0]["effective_impact"], "patch")
        self.assertFalse(plan["policy_problems"])


class ReleaseSchemaTests(ReleaseFixture, unittest.TestCase):
    def test_doctor_rejects_unknown_release_keys(self):
        self.proj["release"] = {"enabled": True, "mystery": 1}
        self.pj.write_text(json.dumps(self.proj) + "\n")
        result = run_script("doctor.py", "--root", str(self.root))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("mystery", result.stdout)

    def test_doctor_accepts_declared_policy(self):
        self.set_release()
        result = run_script("doctor.py", "--root", str(self.root))
        self.assertEqual(result.returncode, 0, result.stdout)


if __name__ == "__main__":
    unittest.main()
