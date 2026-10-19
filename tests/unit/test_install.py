"""install.py: fresh install, idempotence, no symlinks, uninstall removes only what it owns."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest

from tests.helpers import TempDir, doctor, install, run_script, snapshot_tree


class InstallTests(unittest.TestCase):
    def test_fresh_install_layout(self):
        with TempDir() as root:
            result = install(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            for path in ["AGENTS.md", "CLAUDE.md", "docs/00-INDEX.md", "docs/_memlog.md",
                         "docs/_cgspec/project.json", "docs/_cgspec/01-engine/doctor.py",
                         "docs/_cgspec/01-engine/manifest.json", "docs/_cgspec/01-engine/owned-files.json",
                         "docs/prototypes/_snapshots/.gitkeep"]:
                self.assertTrue((root / path).exists(), path)
            project = json.loads((root / "docs/_cgspec/project.json").read_text())
            self.assertEqual(project["profile"], "web-workspace")
            self.assertIn(".cgspec-scratch/", (root / ".gitignore").read_text())

    def test_headless_has_no_prototypes(self):
        with TempDir() as root:
            self.assertEqual(install(root, "headless").returncode, 0)
            self.assertFalse((root / "docs/prototypes").exists())

    def test_polyrepo_governance_has_registry(self):
        with TempDir() as root:
            self.assertEqual(install(root, "headless", "polyrepo-governance", "--repo-prefix", "gov").returncode, 0)
            self.assertTrue((root / "docs/00-REGISTRY.md").exists())

    def test_no_symlinks_anywhere(self):
        with TempDir() as root:
            install(root)
            links = [p for p in root.rglob("*") if p.is_symlink()]
            self.assertEqual(links, [])

    def test_engine_tests_and_caches_not_vendored(self):
        with TempDir() as root:
            install(root)
            engine = root / "docs/_cgspec/01-engine"
            self.assertFalse(list(engine.rglob("__pycache__")))
            self.assertTrue((engine / "schemas/tier.schema.json").exists())

    def test_install_twice_changes_nothing(self):
        with TempDir() as root:
            install(root)
            before = snapshot_tree(root)
            second = install(root)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn("already installed", second.stdout)
            self.assertEqual(snapshot_tree(root), before)

    def test_doctor_passes_right_after_install_for_every_template(self):
        for profile, topology in [("website", "single"), ("web-workspace", "monorepo"), ("cli", "single"),
                                  ("headless", "polyrepo-governance"), ("small", "single"),
                                  ("mobile", "large-monorepo"), ("headless", "polyrepo-member")]:
            with self.subTest(profile=profile, topology=topology), TempDir() as root:
                extra = ("--repo-prefix", "svc") if topology.startswith("polyrepo") else ()
                self.assertEqual(install(root, profile, topology, *extra).returncode, 0)
                result = doctor(root)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_existing_agents_md_is_archived_and_restored_on_uninstall(self):
        with TempDir() as root:
            (root / "AGENTS.md").write_text("old rules\n")
            install(root)
            archived = root / "docs/_cgspec/_archive/pre-cgspec/AGENTS.md"
            self.assertEqual(archived.read_text(), "old rules\n")
            self.assertIn("CONTRACT.md", (root / "AGENTS.md").read_text())
            run_script("install.py", "uninstall", "--root", str(root))
            self.assertEqual((root / "AGENTS.md").read_text(), "old rules\n")

    def test_uninstall_removes_only_owned_and_untouched_files(self):
        with TempDir() as root:
            (root / "README.md").write_text("mine\n")
            (root / ".gitignore").write_text("node_modules/\n")
            install(root)
            spine = root / "docs/spines/01-INTENT.md"
            spine.write_text("# Intent\n\nReal content the user wrote.\n")
            result = run_script("install.py", "uninstall", "--root", str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((root / "README.md").read_text(), "mine\n")
            self.assertEqual((root / ".gitignore").read_text(), "node_modules/\n")
            self.assertTrue(spine.exists(), "user-edited file must be kept")
            self.assertIn("kept", result.stdout)
            self.assertFalse((root / "docs/_cgspec/01-engine").exists())
            self.assertFalse((root / "CLAUDE.md").exists())

    def test_refuses_v1_layout(self):
        with TempDir() as root:
            (root / "docs/_cgspec/01-script").mkdir(parents=True)
            result = install(root)
            self.assertEqual(result.returncode, 1)
            self.assertIn("v1", result.stderr)

    def test_verify_detects_engine_tampering(self):
        with TempDir() as root:
            install(root)
            target = root / "docs/_cgspec/01-engine/memlog.py"
            target.write_text(target.read_text() + "\n# tampered\n")
            result = run_script("install.py", "verify", "--root", str(root))
            self.assertEqual(result.returncode, 1)
            self.assertIn("memlog.py", result.stdout)

    def test_upgrade_repairs_tampered_engine_and_keeps_project_files(self):
        with TempDir() as root:
            install(root)
            target = root / "docs/_cgspec/01-engine/memlog.py"
            target.write_text("broken\n")
            spine = root / "docs/spines/01-INTENT.md"
            spine.write_text("# Intent\n\nuser text\n")
            result = run_script("install.py", "upgrade", "--root", str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotEqual(target.read_text(), "broken\n")
            self.assertEqual(spine.read_text(), "# Intent\n\nuser text\n")
            self.assertEqual(run_script("install.py", "verify", "--root", str(root)).returncode, 0)

    def test_vendored_engine_runs_from_project(self):
        with TempDir() as root:
            install(root)
            result = subprocess.run([sys.executable, "docs/_cgspec/01-engine/memlog.py", "add", "--summary", "s",
                                     "--tags", "t"], cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()


class InstallHardeningTests(unittest.TestCase):
    def test_tampered_owned_list_cannot_delete_user_files(self):
        import hashlib
        with TempDir() as root:
            project = root / "proj"
            project.mkdir()
            install(project)
            (project / "src").mkdir()
            user_file = project / "src/main.py"
            user_file.write_text("print('mine')\n")
            outside = root / "victim.txt"
            outside.write_text("outside\n")
            owned_path = project / "docs/_cgspec/01-engine/owned-files.json"
            owned = json.loads(owned_path.read_text())
            for rel, f in (("src/main.py", user_file), ("../victim.txt", outside)):
                owned["created"][rel] = hashlib.sha256(f.read_bytes()).hexdigest()
            owned_path.write_text(json.dumps(owned))
            result = run_script("install.py", "uninstall", "--root", str(project))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(user_file.exists())
            self.assertTrue(outside.exists())
            self.assertIn("ignored", result.stdout)

    def test_refuses_to_write_through_symlinks(self):
        with TempDir() as root:
            project = root / "proj"
            project.mkdir()
            outside = root / "notes.md"
            outside.write_text("my notes\n")
            os.symlink(outside, project / "AGENTS.md")
            result = install(project)
            self.assertEqual(result.returncode, 1)
            self.assertIn("symlink", result.stderr)
            self.assertEqual(outside.read_text(), "my notes\n")

    def test_edited_replaced_file_is_kept_on_uninstall(self):
        with TempDir() as root:
            (root / "AGENTS.md").write_text("old rules\n")
            install(root)
            (root / "AGENTS.md").write_text((root / "AGENTS.md").read_text() + "\nnew rule added later\n")
            result = run_script("install.py", "uninstall", "--root", str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("new rule added later", (root / "AGENTS.md").read_text())
            self.assertIn("kept", result.stdout)
            self.assertTrue((root / "docs/_cgspec/_archive/pre-cgspec/AGENTS.md").exists())

    def test_missing_archive_is_reported_not_crashed(self):
        with TempDir() as root:
            (root / "AGENTS.md").write_text("old rules\n")
            install(root)
            (root / "docs/_cgspec/_archive/pre-cgspec/AGENTS.md").unlink()
            result = run_script("install.py", "uninstall", "--root", str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertIn("archive missing", result.stdout)

    def test_upgrade_refuses_downgrade_without_force(self):
        with TempDir() as root:
            install(root)
            pj = root / "docs/_cgspec/project.json"
            data = json.loads(pj.read_text())
            data["cgspec_version"] = "9.0.0"
            pj.write_text(json.dumps(data))
            result = run_script("install.py", "upgrade", "--root", str(root))
            self.assertEqual(result.returncode, 1)
            self.assertIn("downgrade", result.stderr)
            self.assertEqual(run_script("install.py", "upgrade", "--root", str(root), "--force").returncode, 0)

    def test_upgrade_adds_missing_template_files_without_overwriting(self):
        with TempDir() as root:
            install(root)
            (root / "docs/00-INBOX.md").unlink()
            spine = root / "docs/spines/01-INTENT.md"
            spine.write_text("# Intent\n\nuser text\n")
            result = run_script("install.py", "upgrade", "--root", str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / "docs/00-INBOX.md").exists())
            self.assertEqual(spine.read_text(), "# Intent\n\nuser text\n")

    def test_interrupted_install_can_be_rerun(self):
        with TempDir() as root:
            install(root)
            (root / "docs/_cgspec/project.json").unlink()
            (root / "docs/_cgspec/01-engine/owned-files.json").unlink()
            result = install(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(doctor(root).returncode, 0)
            self.assertEqual(run_script("install.py", "uninstall", "--root", str(root)).returncode, 0)

    def test_lock_file_is_git_ignored(self):
        with TempDir() as root:
            install(root)
            self.assertIn("docs/.memlog.lock", (root / ".gitignore").read_text())


class InstallRecheckTests(unittest.TestCase):
    def test_uninstall_removes_version_marker_and_reinstall_works(self):
        with TempDir() as root:
            install(root)
            run_script("install.py", "uninstall", "--root", str(root))
            self.assertFalse((root / "docs/_cgspec/project.json").exists())
            self.assertFalse((root / "docs").exists(), sorted(p.as_posix() for p in root.rglob("*")))
            self.assertEqual(install(root).returncode, 0)
            self.assertEqual(doctor(root).returncode, 0)
