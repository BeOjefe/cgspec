"""Git hook ownership survives relocation without following stored host paths."""

from __future__ import annotations

import json
import shutil
import unittest

from tests.helpers import TempDir, git, install, run_script


class GitHookRelocationTests(unittest.TestCase):
    OWNED = "docs/_cgspec/01-engine/owned-files.json"

    def project(self, root):
        root.mkdir()
        git(root, "init", "-q", "-b", "main")
        result = install(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return root

    def legacy_record(self, root):
        path = root / self.OWNED
        owned = json.loads(path.read_text())
        owned["adapters"].pop("git_hooks", None)
        owned["adapters"]["git_abs"] = [str(root / ".git/hooks" / name)
                                           for name in ("pre-commit", "commit-msg")]
        path.write_text(json.dumps(owned))

    def uninstall(self, root):
        result = run_script("install.py", "uninstall", "--root", str(root))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_new_ownership_has_no_workstation_path(self):
        with TempDir() as tmp:
            root = self.project(tmp / "original")
            record = json.loads((root / self.OWNED).read_text())["adapters"]
            self.assertNotIn("git_abs", record)
            self.assertEqual(record["git_hooks"], ["pre-commit", "commit-msg"])

    def test_uninstall_after_move_does_not_touch_reused_old_location(self):
        for legacy in (False, True):
            with self.subTest(legacy=legacy), TempDir() as tmp:
                old = self.project(tmp / "original")
                if legacy:
                    self.legacy_record(old)
                moved = tmp / "moved ü project"
                old.rename(moved)
                self.project(old)
                before = {p.name: p.read_bytes() for p in (old / ".git/hooks").iterdir()}
                self.uninstall(moved)
                self.assertEqual(before, {p.name: p.read_bytes() for p in (old / ".git/hooks").iterdir()})
                for name in ("pre-commit", "commit-msg"):
                    self.assertFalse((moved / ".git/hooks" / name).exists())

    def test_upgrade_migrates_legacy_ownership_after_move(self):
        with TempDir() as tmp:
            old = self.project(tmp / "original")
            self.legacy_record(old)
            moved = tmp / "moved"
            old.rename(moved)
            result = run_script("install.py", "upgrade", "--root", str(moved))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            record = json.loads((moved / self.OWNED).read_text())["adapters"]
            self.assertNotIn("git_abs", record)
            self.assertEqual(record["git_hooks"], ["pre-commit", "commit-msg"])

    def test_uninstall_keeps_user_modified_hook(self):
        with TempDir() as tmp:
            root = self.project(tmp / "original")
            target = root / ".git/hooks/pre-commit"
            target.write_text(target.read_text() + "\n# My additional check\n")
            before = target.read_bytes()
            result = self.uninstall(root)
            self.assertEqual(target.read_bytes(), before)
            self.assertIn("kept", result.stdout)

    def test_symlinked_hook_directory_is_never_written_or_removed(self):
        for operation in ("install", "upgrade", "uninstall"):
            with self.subTest(operation=operation), TempDir() as tmp:
                root = self.project(tmp / "project")
                outside = tmp / "outside"
                (root / ".git/hooks").rename(outside)
                (root / ".git/hooks").symlink_to(outside, target_is_directory=True)
                before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in outside.iterdir()}
                if operation == "install":
                    # A new project must also refuse the redirected directory.
                    shutil.rmtree(root / "docs")
                    result = install(root)
                else:
                    result = run_script("install.py", operation, "--root", str(root))
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in outside.iterdir()})

    def test_tampered_legacy_ownership_cannot_delete_external_hook(self):
        with TempDir() as tmp:
            root = self.project(tmp / "project")
            victim = self.project(tmp / "victim") / ".git/hooks/pre-commit"
            before = victim.read_bytes()
            path = root / self.OWNED
            owned = json.loads(path.read_text())
            owned["adapters"]["git_abs"] = [str(victim)]
            owned["adapters"]["git"] = ["../victim/.git/hooks/pre-commit"]
            owned["adapters"]["git_hooks"] = ["../victim/.git/hooks/pre-commit"]
            path.write_text(json.dumps(owned))
            self.uninstall(root)
            self.assertEqual(victim.read_bytes(), before)

    def test_individual_hook_symlink_is_preserved(self):
        with TempDir() as tmp:
            root = self.project(tmp / "project")
            target = root / ".git/hooks/pre-commit"
            outside = tmp / "outside-hook"
            target.rename(outside)
            target.symlink_to(outside)
            before = outside.read_bytes()
            self.uninstall(root)
            self.assertTrue(target.is_symlink())
            self.assertEqual(outside.read_bytes(), before)

    def test_git_worktree_uses_git_discovered_common_hooks(self):
        with TempDir() as tmp:
            main = tmp / "main"
            main.mkdir()
            git(main, "init", "-q", "-b", "main")
            git(main, "commit", "--allow-empty", "-m", "initial")
            worktree = tmp / "linked checkout"
            git(main, "worktree", "add", "-b", "trial", str(worktree))
            result = install(worktree)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            hooks = main / ".git/hooks"
            self.assertTrue((hooks / "pre-commit").exists())
            self.uninstall(worktree)
            self.assertFalse((hooks / "pre-commit").exists())
