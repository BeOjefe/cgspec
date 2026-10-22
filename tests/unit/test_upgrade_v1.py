"""Old-layout adoption must preserve source bytes and fail closed on ambiguity."""

from __future__ import annotations

import json
import os
import shutil
import unittest
from unittest.mock import patch

from tests.helpers import TempDir, doctor, git, install, run_script, snapshot_tree


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
                        "--tools", "", *flags)
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
            self.assertEqual(json.loads((root / "docs/_cgspec/project.json").read_text())["cgspec_version"], "0.2.0")
            imported = (root / "docs/adrs/ADR-001-choice.md").read_text()
            self.assertIn("Created: unknown · Last edited:", imported)
            self.assertEqual((imported.splitlines(keepends=True)[0] +
                              "".join(imported.splitlines(keepends=True)[2:])).encode(), original)
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
            opts = {"profile": "web-workspace", "topology": "single", "tools": "",
                    "repo_prefix": "", "plugin_source": "https://github.com/BeOjefe/cgspec.git"}
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

    def test_existing_code_gets_unapproved_legacy_baseline(self):
        import hashlib
        with TempDir() as root:
            old_project(root)
            source = root / "src/main.py"
            source.parent.mkdir()
            source.write_text("print('original')\n")
            result, report = upgrade(root, "--apply")
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            baseline = json.loads((root / "docs/_cgspec/07-state/legacy-baseline.json").read_text())
            self.assertEqual(baseline["files"]["src/main.py"]["sha256"], hashlib.sha256(source.read_bytes()).hexdigest())
            slice_text = (root / "docs/slices/SLICE-000-baseline.md").read_text()
            self.assertIn("**Status:** Draft", slice_text)
            self.assertIn("legacy-baseline.json", slice_text)
            self.assertEqual(doctor(root).returncode, 0, doctor(root).stdout)

    def test_existing_agent_rules_need_semantic_mapping(self):
        with TempDir() as root:
            old_project(root)
            (root / "AGENTS.md").write_text("# Project rules\nNever deploy without review.\n")
            before = snapshot_tree(root)
            result, report = upgrade(root, "--apply")
            self.assertEqual(result.returncode, 2)
            self.assertIn("AGENTS.md", str(report["unresolved"]))
            self.assertEqual(snapshot_tree(root), before)

    def test_rollback_refuses_symlinked_restore_temp_without_touching_target(self):
        with TempDir() as root:
            old_project(root)
            self.assertEqual(upgrade(root, "--apply")[0].returncode, 0)
            target = root / "outside.txt"
            target.write_text("do not touch\n")
            temp = root / "docs/00-INDEX.md.upgrade-restore"
            temp.symlink_to(target)
            result, report = upgrade(root, "--rollback")
            self.assertEqual(result.returncode, 2)
            self.assertIn("upgrade-restore", str(report["unresolved"]))
            self.assertEqual(target.read_text(), "do not touch\n")
            self.assertTrue(temp.is_symlink())

    def test_concurrent_edit_after_journal_is_not_overwritten(self):
        from engine._lib import upgrade_v1 as migration
        with TempDir() as root:
            old_project(root)
            save = migration._save_journal

            def edit_after_journal(*args):
                save(*args)
                path = root / "docs/00-INDEX.md"
                path.write_text(path.read_text() + "\nconcurrent human edit\n")

            opts = {"profile": "web-workspace", "topology": "single", "tools": "",
                    "repo_prefix": "", "plugin_source": "https://github.com/BeOjefe/cgspec.git"}
            with patch.object(migration, "_save_journal", side_effect=edit_after_journal):
                code, report = migration.run(root, opts, apply=True)
            self.assertEqual(code, 2, report)
            self.assertIn("concurrent human edit", (root / "docs/00-INDEX.md").read_text())
            self.assertFalse((root / "docs/_cgspec/project.json").exists())

    def test_git_requested_wires_live_hooks_or_reports_partial(self):
        with TempDir() as root:
            old_project(root)
            before = snapshot_tree(root)
            result, report = upgrade(root, "--tools", "git", "--apply")
            self.assertEqual(result.returncode, 2)
            self.assertIn("git", str(report["unresolved"]).lower())
            self.assertEqual(snapshot_tree(root), before)
        with TempDir() as root:
            old_project(root)
            git(root, "init", "-q")
            result, report = upgrade(root, "--tools", "git", "--apply")
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            for event in ("pre-commit", "commit-msg"):
                path = root / ".git/hooks" / event
                self.assertTrue(path.is_file(), event)
                self.assertIn("cgspec_hook.py", path.read_text())
            owned = json.loads((root / "docs/_cgspec/01-engine/owned-files.json").read_text())
            self.assertEqual(owned["adapters"]["git_hooks"], ["pre-commit", "commit-msg"])

    def test_modes_and_empty_legacy_dirs_survive_upgrade_rollback(self):
        with TempDir() as root:
            old_project(root)
            adr = root / "docs/adr/ADR-001-choice.md"
            empty = root / "docs/_cgspec/01-script"
            os.chmod(adr, 0o640)
            os.chmod(empty, 0o750)
            self.assertEqual(upgrade(root, "--apply")[0].returncode, 0)
            self.assertEqual((root / "docs/adrs/ADR-001-choice.md").stat().st_mode & 0o777, 0o640)
            result, report = upgrade(root, "--rollback")
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertEqual(adr.stat().st_mode & 0o777, 0o640)
            self.assertTrue(empty.is_dir())
            self.assertEqual(empty.stat().st_mode & 0o777, 0o750)

    def test_created_git_hooks_are_removed_by_rollback(self):
        with TempDir() as root:
            old_project(root)
            git(root, "init", "-q")
            self.assertEqual(upgrade(root, "--tools", "git", "--apply")[0].returncode, 0)
            result, report = upgrade(root, "--rollback")
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertFalse((root / ".git/hooks/pre-commit").exists())
            self.assertFalse((root / ".git/hooks/commit-msg").exists())

    def test_existing_unrelated_git_hook_blocks_adoption(self):
        with TempDir() as root:
            old_project(root)
            git(root, "init", "-q")
            path = root / ".git/hooks/pre-commit"
            path.write_text("#!/bin/sh\nexit 0\n")
            before = snapshot_tree(root)
            result, report = upgrade(root, "--tools", "git", "--apply")
            self.assertEqual(result.returncode, 2)
            self.assertIn("reviewed integration", str(report["unresolved"]))
            self.assertEqual(snapshot_tree(root), before)

    def test_edit_after_publication_blocks_version_marker(self):
        from engine._lib import upgrade_v1 as migration, upgrade_v1_txn as transaction
        with TempDir() as root:
            old_project(root)
            original = transaction.publish_hooks

            def edit_after_files(project, hooks):
                original(project, hooks)
                path = root / "docs/00-INDEX.md"
                path.write_text(path.read_text() + "\nnew human note\n")

            with patch.object(transaction, "publish_hooks", side_effect=edit_after_files):
                code, report = migration.run(root, {"profile": "web-workspace", "topology": "single",
                                                     "tools": "", "repo_prefix": "",
                                                     "plugin_source": "https://github.com/BeOjefe/cgspec.git"}, apply=True)
            self.assertEqual(code, 2, report)
            self.assertFalse((root / "docs/_cgspec/project.json").exists())
            self.assertIn("new human note", (root / "docs/00-INDEX.md").read_text())

    def test_rollback_edit_during_backup_read_is_preserved(self):
        from engine._lib import upgrade_v1 as migration, upgrade_v1_txn as transaction
        with TempDir() as root:
            old_project(root)
            self.assertEqual(upgrade(root, "--apply")[0].returncode, 0)
            index = root / "docs/00-INDEX.md"
            read_backup = transaction._backup_content

            def edit_while_reading(*args):
                result = read_backup(*args)
                index.write_text(index.read_text() + "\nHUMAN CHANGE DURING ROLLBACK\n")
                return result

            opts = {"profile": "web-workspace", "topology": "single", "tools": "",
                    "repo_prefix": "", "plugin_source": "https://github.com/BeOjefe/cgspec.git"}
            with patch.object(transaction, "_backup_content", side_effect=edit_while_reading):
                code, report = migration.run(root, opts, apply=False, rollback=True)
            self.assertEqual(code, 2, report)
            self.assertEqual(report["verdict"], "PARTIAL")
            self.assertIn("HUMAN CHANGE DURING ROLLBACK", index.read_text())
            self.assertTrue((root / "docs/_cgspec/project.json").exists())

    def test_chmod_during_staging_blocks_publish_with_partial_verdict(self):
        from engine._lib import upgrade_v1 as migration
        with TempDir() as root:
            old_project(root)
            target = root / "docs/00-INDEX.md"
            os.chmod(target, 0o644)
            prepare = migration._prepare

            def chmod_while_staging(*args):
                result = prepare(*args)
                os.chmod(target, 0o600)
                return result

            opts = {"profile": "web-workspace", "topology": "single", "tools": "",
                    "repo_prefix": "", "plugin_source": "https://github.com/BeOjefe/cgspec.git"}
            with patch.object(migration, "_prepare", side_effect=chmod_while_staging):
                code, report = migration.run(root, opts, apply=True)
            self.assertEqual(code, 2, report)
            self.assertEqual(report["verdict"], "PARTIAL")
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            self.assertFalse((root / "docs/_cgspec/project.json").exists())
            self.assertFalse((root / ".cgspec-upgrade-v1").exists())


if __name__ == "__main__":
    unittest.main()
