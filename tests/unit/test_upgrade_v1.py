"""Old-layout adoption must preserve source bytes and fail closed on ambiguity."""

from __future__ import annotations

import json
import shutil
import unittest
from unittest.mock import patch

from tests.helpers import TempDir, doctor, install, run_script, snapshot_tree


def old_project(root):
    """Small CortexGate-shaped v1 tree with a real old script and relative links."""
    assert install(root).returncode == 0
    (root / "docs/_cgspec/project.json").unlink()
    shutil.rmtree(root / "docs/_cgspec/01-engine")
    (root / "docs/adrs/.gitkeep").unlink()
    (root / "docs/adrs").rmdir()
    (root / "docs/adr").mkdir()
    (root / "docs/adr/ADR-001-choice.md").write_text("# Choice\n\n- **Status:** Imported\n")
    (root / "docs/_cgspec/03-councils/.gitkeep").unlink()
    (root / "docs/_cgspec/03-councils").rmdir()
    council = root / "docs/_cgspec/03-council/COUNCIL-001-choice"
    council.mkdir(parents=True)
    (council / "00-brief.md").write_text("# Brief\n")
    (root / "docs/_cgspec/01-script").mkdir()
    old_spine = root / "docs/02-OOUX.md"
    source = root / "docs/spines/02-OOUX.md"
    source.rename(old_spine)
    index = root / "docs/00-INDEX.md"
    index.write_text("# Index\n\n- [Choice](adr/ADR-001-choice.md)\n"
                     "- [Council](_cgspec/03-council/COUNCIL-001-choice/)\n")


def upgrade(root, *flags):
    result = run_script("install.py", "upgrade", "--root", str(root), "--from-v1",
                        "--profile", "web-workspace", "--topology", "single",
                        "--tools", "git", *flags)
    return result, json.loads(result.stdout)


class UpgradeV1Tests(unittest.TestCase):
    def test_dry_run_is_read_only_and_reports_exact_moves(self):
        with TempDir() as root:
            old_project(root)
            before = snapshot_tree(root)
            result, report = upgrade(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(report["verdict"], "READY")
            self.assertEqual(snapshot_tree(root), before)
            self.assertIn("docs/adr/ADR-001-choice.md", report["path_map"])
            self.assertEqual(report["path_map"]["docs/02-OOUX.md"], "docs/spines/02-OOUX.md")
            self.assertIn("docs/_cgspec/01-script", report["remove_empty"])

    def test_complete_upgrade_preserves_archived_bytes_and_passes_doctor(self):
        with TempDir() as root:
            old_project(root)
            original = (root / "docs/adr/ADR-001-choice.md").read_bytes()
            result, report = upgrade(root, "--apply")
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertEqual(report["verdict"], "PASS")
            self.assertTrue((root / "docs/adrs/ADR-001-choice.md").is_file())
            self.assertTrue((root / "docs/spines/02-OOUX.md").is_file())
            self.assertFalse((root / "docs/adr").exists())
            self.assertFalse((root / "docs/_cgspec/01-script").exists())
            self.assertEqual(doctor(root).returncode, 0, doctor(root).stdout)
            self.assertIn("adrs/ADR-001-choice.md", (root / "docs/00-INDEX.md").read_text())
            self.assertEqual(json.loads((root / "docs/_cgspec/project.json").read_text())["cgspec_version"], "2.0.0")
            self.assertEqual((root / "docs/adrs/ADR-001-choice.md").read_bytes(), original)
            second, again = upgrade(root, "--apply")
            self.assertEqual(second.returncode, 0)
            self.assertEqual(again["verdict"], "ALREADY_CURRENT")

    def test_destination_conflict_stops_without_change(self):
        with TempDir() as root:
            old_project(root)
            (root / "docs/adrs").mkdir()
            (root / "docs/adrs/ADR-001-choice.md").write_text("different decision\n")
            before = snapshot_tree(root)
            result, report = upgrade(root, "--apply")
            self.assertEqual(result.returncode, 2)
            self.assertEqual(report["verdict"], "PARTIAL")
            self.assertIn("docs/adrs/ADR-001-choice.md", str(report["unresolved"]))
            self.assertEqual(snapshot_tree(root), before)

    def test_stale_link_stops_before_marker_and_restores_all_content(self):
        with TempDir() as root:
            old_project(root)
            index = root / "docs/00-INDEX.md"
            index.write_text(index.read_text() + "- [missing](.cgspec/04-adr/ADR-999-missing.md)\n")
            before = snapshot_tree(root)
            result, report = upgrade(root, "--apply")
            self.assertEqual(result.returncode, 2)
            self.assertEqual(report["verdict"], "PARTIAL")
            self.assertFalse((root / "docs/_cgspec/project.json").exists())
            self.assertEqual(snapshot_tree(root), before)

    def test_legacy_custom_script_requires_review(self):
        with TempDir() as root:
            old_project(root)
            (root / "docs/_cgspec/01-script/doctor.py").write_text("print('old checker')\n")
            before = snapshot_tree(root)
            result, report = upgrade(root, "--apply")
            self.assertEqual(result.returncode, 2)
            self.assertEqual(report["verdict"], "PARTIAL")
            self.assertIn("docs/_cgspec/01-script/doctor.py", str(report["unresolved"]))
            self.assertEqual(snapshot_tree(root), before)

    def test_successful_upgrade_can_roll_back_untouched_result(self):
        with TempDir() as root:
            old_project(root)
            before = snapshot_tree(root)
            self.assertEqual(upgrade(root, "--apply")[0].returncode, 0)
            result, report = upgrade(root, "--rollback")
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertEqual(report["verdict"], "ROLLED_BACK")
            self.assertEqual(snapshot_tree(root), before)

    def test_interrupted_publish_requires_rollback_before_retry(self):
        from engine._lib import upgrade_v1 as migration
        with TempDir() as root:
            old_project(root)
            before = snapshot_tree(root)
            opts = {"profile": "web-workspace", "topology": "single", "tools": "git",
                    "repo_prefix": "", "plugin_source": "https://github.com/mrojefe/cgspec.git"}
            replace = migration.os.replace
            calls = 0

            def fail_after_first(src, dst):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("simulated interruption")
                return replace(src, dst)

            publish = migration._publish

            def interrupted_publish(*args):
                with patch.object(migration.os, "replace", side_effect=fail_after_first):
                    return publish(*args)

            with patch.object(migration, "_publish", side_effect=interrupted_publish):
                code, report = migration.run(root, opts, apply=True)
            self.assertEqual(code, 2, report)
            self.assertTrue((root / ".cgspec-upgrade-v1/plan.json").is_file())
            self.assertFalse((root / "docs/_cgspec/project.json").exists())
            self.assertEqual(upgrade(root, "--apply")[1]["verdict"], "PARTIAL")
            self.assertEqual(upgrade(root, "--rollback")[1]["verdict"], "ROLLED_BACK")
            self.assertEqual(snapshot_tree(root), before)

    def test_old_version_marker_requires_from_v1_path(self):
        with TempDir() as root:
            old_project(root)
            marker = root / "docs/_cgspec/project.json"
            marker.write_text('{"schema":1,"cgspec_version":"1.2.0"}\n')
            direct = run_script("install.py", "upgrade", "--root", str(root))
            self.assertEqual(direct.returncode, 1)
            self.assertIn("--from-v1", direct.stderr)
            result, report = upgrade(root)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertEqual(report["verdict"], "READY")

    def test_rollback_refuses_later_edits(self):
        with TempDir() as root:
            old_project(root)
            self.assertEqual(upgrade(root, "--apply")[0].returncode, 0)
            index = root / "docs/00-INDEX.md"
            index.write_text(index.read_text() + "\nHuman note after upgrade.\n")
            before = snapshot_tree(root)
            result, report = upgrade(root, "--rollback")
            self.assertEqual(result.returncode, 2)
            self.assertIn("docs/00-INDEX.md", str(report["unresolved"]))
            self.assertEqual(snapshot_tree(root), before)

    def test_publish_rejects_project_changed_during_staging(self):
        from engine._lib import upgrade_v1 as migration
        with TempDir() as root:
            old_project(root)
            before = migration.files(root)
            index = root / "docs/00-INDEX.md"
            index.write_text(index.read_text() + "\nconcurrent edit\n")
            changed = snapshot_tree(root)
            with self.assertRaisesRegex(ValueError, "changed during stage"):
                migration._publish(root, root, before, before, {})
            self.assertEqual(snapshot_tree(root), changed)
            self.assertFalse((root / ".cgspec-upgrade-v1").exists())

    def test_rollback_rejects_corrupt_backup(self):
        from engine._lib import upgrade_v1 as migration
        with TempDir() as root:
            old_project(root)
            self.assertEqual(upgrade(root, "--apply")[0].returncode, 0)
            archive = root / migration.ARCHIVE / "before.tar.gz"
            archive.write_bytes(b"not a tar archive")
            before = snapshot_tree(root)
            result, report = upgrade(root, "--rollback")
            self.assertEqual(result.returncode, 2)
            self.assertEqual(report["verdict"], "PARTIAL")
            self.assertEqual(snapshot_tree(root), before)


if __name__ == "__main__":
    unittest.main()
