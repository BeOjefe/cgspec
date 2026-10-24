"""Git hook ownership survives relocation without following stored host paths."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from tests.helpers import TempDir, git, git_live, install, run_script


class GitHookRelocationTests(unittest.TestCase):
    OWNED = "docs/_cgspec/01-engine/owned-files.json"

    def project(self, root, env: dict | None = None):
        root.mkdir()
        git(root, "init", "-q", "-b", "main")
        result = install(root, env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return root

    def legacy_record(self, root):
        path = root / self.OWNED
        owned = json.loads(path.read_text())
        owned["adapters"].pop("git_hooks", None)
        owned["adapters"]["git_abs"] = [str(root / ".git/hooks" / name)
                                           for name in ("pre-commit", "commit-msg")]
        path.write_text(json.dumps(owned))

    def uninstall(self, root, env: dict | None = None):
        result = run_script("install.py", "uninstall", "--root", str(root), env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def uninstall_refused(self, root, env: dict | None = None):
        """A hook that might still invoke CGSpec after removal blocks the whole uninstall."""
        result = run_script("install.py", "uninstall", "--root", str(root), env=env)
        self.assertNotEqual(result.returncode, 0)
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
            engine_file = root / "docs/_cgspec/01-engine/cgspec_hook.py"
            result = self.uninstall_refused(root)
            self.assertEqual(target.read_bytes(), before)
            self.assertTrue(engine_file.exists())
            self.assertIn("modified", result.stdout + result.stderr)

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
                if operation == "uninstall":
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("symlink", result.stdout + result.stderr)
                else:
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
            engine_file = root / "docs/_cgspec/01-engine/cgspec_hook.py"
            result = self.uninstall_refused(root)
            self.assertTrue(target.is_symlink())
            self.assertEqual(outside.read_bytes(), before)
            self.assertTrue(engine_file.exists())
            self.assertIn("symlink", result.stdout + result.stderr)

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

    # --- Findings 1-5 & marker overwrite regressions ---

    def test_f1_inherited_git_dir_does_not_select_foreign_repo(self):
        with TempDir() as tmp:
            a = self.project(tmp / "a")
            b = self.project(tmp / "b")
            b_before = {p.name: p.read_bytes() for p in (b / ".git/hooks").iterdir()}
            env = os.environ.copy()
            env["GIT_DIR"] = str(b / ".git")
            self.uninstall(a, env=env)
            # b must be completely untouched
            self.assertEqual(b_before, {p.name: p.read_bytes() for p in (b / ".git/hooks").iterdir()})
            # a's hooks must be uninstalled
            for name in ("pre-commit", "commit-msg"):
                self.assertFalse((a / ".git/hooks" / name).exists())

    def test_f1_inherited_git_common_dir_does_not_select_foreign_repo(self):
        with TempDir() as tmp:
            a = self.project(tmp / "a")
            b = self.project(tmp / "b")
            b_before = {p.name: p.read_bytes() for p in (b / ".git/hooks").iterdir()}
            env = os.environ.copy()
            env["GIT_COMMON_DIR"] = str(b / ".git")
            self.uninstall(a, env=env)
            # b must be completely untouched
            self.assertEqual(b_before, {p.name: p.read_bytes() for p in (b / ".git/hooks").iterdir()})
            # a's hooks must be uninstalled
            for name in ("pre-commit", "commit-msg"):
                self.assertFalse((a / ".git/hooks" / name).exists())

    def test_f2_symlinked_dot_git_directory_refused(self):
        with TempDir() as tmp:
            a = self.project(tmp / "a")
            b = self.project(tmp / "b")
            b_before = {p.name: p.read_bytes() for p in (b / ".git/hooks").iterdir()}
            shutil.rmtree(a / ".git")
            (a / ".git").symlink_to(b / ".git", target_is_directory=True)
            res = run_script("install.py", "uninstall", "--root", str(a))
            self.assertEqual(b_before, {p.name: p.read_bytes() for p in (b / ".git/hooks").iterdir()})
            self.assertIn("left alone", res.stdout + res.stderr)

    def test_f2_symlinked_dot_git_file_refused(self):
        with TempDir() as tmp:
            a = self.project(tmp / "a")
            b = self.project(tmp / "b")
            b_before = {p.name: p.read_bytes() for p in (b / ".git/hooks").iterdir()}
            indirection = tmp / "indirection_file"
            indirection.write_text(f"gitdir: {b}/.git\n")
            shutil.rmtree(a / ".git")
            (a / ".git").symlink_to(indirection)
            res = run_script("install.py", "uninstall", "--root", str(a))
            self.assertEqual(b_before, {p.name: p.read_bytes() for p in (b / ".git/hooks").iterdir()})
            self.assertIn("left alone", res.stdout + res.stderr)

    def test_f2_gitdir_indirection_through_symlink_refused(self):
        with TempDir() as tmp:
            a = self.project(tmp / "a")
            b = self.project(tmp / "b")
            b_before = {p.name: p.read_bytes() for p in (b / ".git/hooks").iterdir()}
            symlink_to_b = tmp / "symlink-to-b"
            symlink_to_b.symlink_to(b, target_is_directory=True)
            shutil.rmtree(a / ".git")
            (a / ".git").write_text(f"gitdir: {symlink_to_b}/.git\n")
            res = run_script("install.py", "uninstall", "--root", str(a))
            self.assertEqual(b_before, {p.name: p.read_bytes() for p in (b / ".git/hooks").iterdir()})
            self.assertIn("left alone", res.stdout + res.stderr)

    def test_f3_migration_retains_ownership_when_hooks_path_temporarily_custom(self):
        with TempDir() as tmp:
            root = self.project(tmp / "proj")
            self.legacy_record(root)
            env = os.environ.copy()
            env["GIT_CONFIG_COUNT"] = "1"
            env["GIT_CONFIG_KEY_0"] = "core.hooksPath"
            env["GIT_CONFIG_VALUE_0"] = "/dev/null"
            res = run_script("install.py", "upgrade", "--root", str(root), env=env)
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            record = json.loads((root / self.OWNED).read_text())["adapters"]
            self.assertEqual(record.get("git_hooks"), ["pre-commit", "commit-msg"])
            # Remove custom override and run uninstall
            res_un = run_script("install.py", "uninstall", "--root", str(root))
            self.assertEqual(res_un.returncode, 0, res_un.stdout + res_un.stderr)
            for name in ("pre-commit", "commit-msg"):
                self.assertFalse((root / ".git/hooks" / name).exists())

    def test_f3_migration_retains_ownership_for_user_modified_hook(self):
        with TempDir() as tmp:
            root = self.project(tmp / "proj")
            self.legacy_record(root)
            target = root / ".git/hooks/pre-commit"
            target.write_text(target.read_text() + "\n# user comment\n")
            res = run_script("install.py", "upgrade", "--root", str(root))
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            record = json.loads((root / self.OWNED).read_text())["adapters"]
            self.assertEqual(record.get("git_hooks"), ["pre-commit", "commit-msg"])
            # A modified owned hook might still call CGSpec: the whole uninstall is refused,
            # both hooks and the engine stay in place (finding 3).
            engine_file = root / "docs/_cgspec/01-engine/cgspec_hook.py"
            res_un = run_script("install.py", "uninstall", "--root", str(root))
            self.assertNotEqual(res_un.returncode, 0)
            self.assertTrue(target.exists())
            self.assertTrue((root / ".git/hooks/commit-msg").exists())
            self.assertTrue(engine_file.exists())
            self.assertIn("modified", res_un.stdout + res_un.stderr)

    def test_f4_migration_does_not_crash_on_non_utf8_comment(self):
        with TempDir() as tmp:
            root = self.project(tmp / "proj")
            self.legacy_record(root)
            target = root / ".git/hooks/pre-commit"
            target.write_bytes(target.read_bytes() + b"\n# user comment: \xff\n")
            res = run_script("install.py", "upgrade", "--root", str(root))
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            record = json.loads((root / self.OWNED).read_text())["adapters"]
            self.assertEqual(record.get("git_hooks"), ["pre-commit", "commit-msg"])

    def test_f4_crlf_modified_hook_preserved_on_uninstall(self):
        with TempDir() as tmp:
            root = self.project(tmp / "proj")
            target = root / ".git/hooks/pre-commit"
            target.write_bytes(target.read_bytes().replace(b"\n", b"\r\n"))
            engine_file = root / "docs/_cgspec/01-engine/cgspec_hook.py"
            res = self.uninstall_refused(root)
            self.assertTrue(target.exists())
            self.assertTrue(engine_file.exists())
            self.assertIn("modified", res.stdout + res.stderr)

    def test_f5_configured_empty_hooks_path_treated_as_custom(self):
        with TempDir() as tmp:
            root = self.project(tmp / "proj")
            env = os.environ.copy()
            env["GIT_CONFIG_COUNT"] = "1"
            env["GIT_CONFIG_KEY_0"] = "core.hooksPath"
            env["GIT_CONFIG_VALUE_0"] = ""
            res_un = run_script("install.py", "uninstall", "--root", str(root), env=env)
            self.assertNotEqual(res_un.returncode, 0)
            self.assertIn("core.hooksPath is set to : git hooks left alone", res_un.stdout + res_un.stderr)
            self.assertTrue((root / ".git/hooks/pre-commit").exists())

    def test_f5_configured_whitespace_hooks_path_treated_as_custom(self):
        with TempDir() as tmp:
            root = self.project(tmp / "proj")
            env = os.environ.copy()
            env["GIT_CONFIG_COUNT"] = "1"
            env["GIT_CONFIG_KEY_0"] = "core.hooksPath"
            env["GIT_CONFIG_VALUE_0"] = " "
            res_un = run_script("install.py", "uninstall", "--root", str(root), env=env)
            self.assertNotEqual(res_un.returncode, 0)
            self.assertIn("core.hooksPath is set to  : git hooks left alone", res_un.stdout + res_un.stderr)
            self.assertTrue((root / ".git/hooks/pre-commit").exists())

    def test_adjacent_reinstall_preserves_user_modified_hook_with_marker(self):
        # A hook modified after a prior wiring (comment appended) must never be clobbered by
        # a later install attempt landing on the same directory (finding 3: a modified owned
        # hook now also blocks uninstall, tested separately above).
        with TempDir() as tmp:
            root = tmp / "proj"
            root.mkdir()
            git(root, "init", "-q", "-b", "main")
            from _lib.adapters import GIT_HOOK, HOOK
            hooks_dir = root / ".git/hooks"
            hooks_dir.mkdir(parents=True, exist_ok=True)
            target = hooks_dir / "pre-commit"
            target.write_text(GIT_HOOK.format(hook=HOOK, event="pre-commit") + "\n# custom user addition\n")
            target.chmod(0o755)
            modified_bytes = target.read_bytes()
            res = run_script("install.py", "install", "--root", str(root), "--profile", "web-workspace",
                             "--topology", "single", "--tools", "git")
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            self.assertEqual(target.read_bytes(), modified_bytes)
            self.assertIn("left existing git pre-commit hook alone; add the CGSpec call to it yourself", res.stdout)

    # --- Round 2 Review 51 Regressions ---

    def test_r2_f1_copied_linked_worktree_cannot_delete_original_hooks(self):
        with TempDir() as tmp:
            main = tmp / "main"
            main.mkdir()
            git(main, "init", "-q", "-b", "main")
            git(main, "commit", "--allow-empty", "-m", "init")
            wt = tmp / "wt"
            git(main, "worktree", "add", "-b", "wt-branch", str(wt))
            install(main)
            install(wt)
            # Stage and commit the installed scaffold itself, plus a tracked file to modify
            # later (T0 allows modifying a tracked file, not creating a new one), with hooks
            # disabled for this setup step only, so a later real commit has a layout doctor
            # actually recognizes.
            (main / "file.txt").write_text("original" + chr(10))
            git(main, "add", "-A")
            git(main, "commit", "-q", "-m", "scaffold")
            hooks_before = {p.name: p.read_bytes() for p in (main / ".git/hooks").iterdir()}
            copied_wt = tmp / "copied_wt"
            shutil.copytree(wt, copied_wt)
            res = run_script("install.py", "uninstall", "--root", str(copied_wt))
            self.assertNotEqual(res.returncode, 0)
            self.assertEqual(hooks_before, {p.name: p.read_bytes() for p in (main / ".git/hooks").iterdir()})
            # Original commit succeeds with CGSpec hooks active (finding 5: a real commit, not
            # one run under the test helper's core.hooksPath=/dev/null override).
            (main / "file.txt").write_text("content" + chr(10))  # modifies the tracked file
            tier = run_script("cgspec_hook.py", "tier", "set", "--tier", "T0", "--reason", "verify hooks",
                              "--files", "file.txt", "--root", str(main))
            self.assertEqual(tier.returncode, 0, tier.stdout + tier.stderr)
            git_live(main, "add", "file.txt", "docs/_cgspec/07-state/tier.json")
            git_live(main, "commit", "-m", "verify hooks intact")

    def test_r2_f1_moved_worktree_reused_location_cannot_delete_new_repo_hooks(self):
        with TempDir() as tmp:
            main1 = tmp / "main1"
            main1.mkdir()
            git(main1, "init", "-q", "-b", "main")
            git(main1, "commit", "--allow-empty", "-m", "init")
            wt = tmp / "wt"
            git(main1, "worktree", "add", "-b", "trial", str(wt))
            install(wt)
            wt_moved = tmp / "wt_moved"
            wt.rename(wt_moved)
            # Old location wt reused for another project with a worktree
            main2 = tmp / "main2"
            main2.mkdir()
            git(main2, "init", "-q", "-b", "main")
            git(main2, "commit", "--allow-empty", "-m", "init")
            git(main2, "worktree", "add", "-b", "trial", str(wt))
            install(wt)
            hooks_before = {p.name: p.read_bytes() for p in (main2 / ".git/hooks").iterdir()}
            res = run_script("install.py", "uninstall", "--root", str(wt_moved))
            self.assertNotEqual(res.returncode, 0)
            self.assertEqual(hooks_before, {p.name: p.read_bytes() for p in (main2 / ".git/hooks").iterdir()})

    def test_r2_f1_crafted_commondir_in_primary_git_dir_refused(self):
        with TempDir() as tmp:
            a = self.project(tmp / "a")
            b = self.project(tmp / "b")
            b_before = {p.name: p.read_bytes() for p in (b / ".git/hooks").iterdir()}
            (a / ".git/commondir").write_text(f"{b}/.git" + chr(10))
            res = run_script("install.py", "uninstall", "--root", str(a))
            self.assertNotEqual(res.returncode, 0)
            self.assertEqual(b_before, {p.name: p.read_bytes() for p in (b / ".git/hooks").iterdir()})

    def test_r2_f1_repaired_moved_worktree_uninstalls_normally(self):
        with TempDir() as tmp:
            main = tmp / "main"
            main.mkdir()
            git(main, "init", "-q", "-b", "main")
            git(main, "commit", "--allow-empty", "-m", "init")
            wt = tmp / "wt"
            git(main, "worktree", "add", "-b", "trial", str(wt))
            install(wt)
            wt_moved = tmp / "wt_moved"
            wt.rename(wt_moved)
            git(main, "worktree", "repair", str(wt_moved))
            res = run_script("install.py", "uninstall", "--root", str(wt_moved))
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            for name in ("pre-commit", "commit-msg"):
                self.assertFalse((main / ".git/hooks" / name).exists())

    def test_r2_f2_uninstall_under_temporary_override_fails_closed_and_commits_continue(self):
        with TempDir() as tmp:
            root = self.project(tmp / "proj")
            # Stage and commit the installed scaffold itself, plus a tracked file to modify
            # later (T0 allows modifying a tracked file, not creating a new one), with hooks
            # disabled for this setup step only, so a later real commit has a layout doctor
            # actually recognizes.
            (root / "change.txt").write_text("original" + chr(10))
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "scaffold")
            pre_commit = root / ".git/hooks/pre-commit"
            engine_file = root / "docs/_cgspec/01-engine/cgspec_hook.py"
            owned_file = root / "docs/_cgspec/01-engine/owned-files.json"
            env = os.environ.copy()
            env["GIT_CONFIG_COUNT"] = "1"
            env["GIT_CONFIG_KEY_0"] = "core.hooksPath"
            env["GIT_CONFIG_VALUE_0"] = "/dev/null"
            res = run_script("install.py", "uninstall", "--root", str(root), env=env)
            self.assertNotEqual(res.returncode, 0)
            # Fail closed: engine, ownership, and hooks must remain intact
            self.assertTrue(pre_commit.exists())
            self.assertTrue(engine_file.exists())
            self.assertTrue(owned_file.exists())
            # Commit without override succeeds, with hooks active (finding 5)
            (root / "change.txt").write_text("valid" + chr(10))  # modifies the tracked file
            tier = run_script("cgspec_hook.py", "tier", "set", "--tier", "T0", "--reason", "verify commit",
                              "--files", "change.txt", "--root", str(root))
            self.assertEqual(tier.returncode, 0, tier.stdout + tier.stderr)
            git_live(root, "add", "change.txt", "docs/_cgspec/07-state/tier.json")
            git_live(root, "commit", "-m", "commit succeeds because engine is preserved")
            # Clean uninstall without override succeeds
            res_clean = run_script("install.py", "uninstall", "--root", str(root))
            self.assertEqual(res_clean.returncode, 0, res_clean.stdout + res_clean.stderr)
            self.assertFalse(pre_commit.exists())
            self.assertFalse(engine_file.exists())

    def test_r2_f3_hostile_git_config_cannot_hide_custom_hooks_path(self):
        with TempDir() as tmp:
            root = tmp / "proj"
            root.mkdir()
            git(root, "init", "-q", "-b", "main")
            git(root, "config", "core.hooksPath", "my-hooks")
            env = os.environ.copy()
            env["GIT_CONFIG"] = "/dev/null"
            res = run_script("install.py", "install", "--root", str(root), "--profile", "web-workspace",
                             "--topology", "single", "--tools", "git", env=env)
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            self.assertFalse((root / ".git/hooks/pre-commit").exists())
            self.assertIn("core.hooksPath is set to my-hooks: git hooks left alone", res.stdout)

    # --- Round 3 Review 51 Regressions (findings 1, 2, 4) ---

    def test_f1r3_bare_separate_gitdir_copy_cannot_delete_original_hooks(self):
        """A `.git` file with no `commondir` (not a worktree) gives Git no back-pointer to
        check. A `cp -a` of such a checkout shares the exact same external gitdir, so
        uninstalling the copy must refuse rather than delete the original's hooks."""
        with TempDir() as tmp:
            meta = tmp / "meta"
            original = tmp / "original"
            git(tmp, "init", "-q", "-b", "main", f"--separate-git-dir={meta}", str(original))
            result = install(original)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            hooks_before = {p.name: p.read_bytes() for p in (meta / "hooks").iterdir()
                            if p.name in ("pre-commit", "commit-msg")}
            copied = tmp / "copied"
            shutil.copytree(original, copied, symlinks=True)
            res = run_script("install.py", "uninstall", "--root", str(copied))
            self.assertNotEqual(res.returncode, 0)
            hooks_after = {p.name: p.read_bytes() for p in (meta / "hooks").iterdir()
                           if p.name in ("pre-commit", "commit-msg")}
            self.assertEqual(hooks_before, hooks_after)

    def test_f1r3_fresh_install_into_shared_gitdir_does_not_claim_foreign_hooks(self):
        """A copy that was never itself installed (no ownership record yet) must not claim
        hooks that already sit in the external gitdir it happens to share, even when their
        bytes are byte-identical to the CGSpec template."""
        with TempDir() as tmp:
            meta = tmp / "meta"
            original = tmp / "original"
            git(tmp, "init", "-q", "-b", "main", f"--separate-git-dir={meta}", str(original))
            install(original)
            copied = tmp / "copied"
            shutil.copytree(original, copied, symlinks=True)
            shutil.rmtree(copied / "docs/_cgspec")
            hooks_before = {p.name: p.read_bytes() for p in (meta / "hooks").iterdir()}
            res = run_script("install.py", "install", "--root", str(copied), "--profile", "web-workspace",
                             "--topology", "single", "--tools", "git")
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            hooks_after = {p.name: p.read_bytes() for p in (meta / "hooks").iterdir()}
            self.assertEqual(hooks_before, hooks_after)
            record = json.loads((copied / self.OWNED).read_text())["adapters"]
            self.assertNotIn("git_hooks", record)

    def test_f1r3_submodule_parent_copy_fails_closed_on_uninstall(self):
        """A submodule's gitfile is relative, so copying the whole superproject (with its
        .git/modules) gives the copy its own, physically distinct gitdir -- not a real
        sharing risk. Our ownership record still travels with the copy (it was captured at
        install time for the original path), so the copy's uninstall fails closed rather
        than silently deleting its own (unrelated) hooks. This is the safe, conservative
        outcome: no foreign hooks are ever touched, and nothing is lost (rerunning install
        in the copy rebinds ownership)."""
        with TempDir() as tmp:
            git(tmp, "init", "-q", "-b", "main", str(tmp / "lib-src"))
            git(tmp / "lib-src", "commit", "--allow-empty", "-m", "init")
            super_dir = tmp / "super"
            git(tmp, "init", "-q", "-b", "main", str(super_dir))
            git(super_dir, "commit", "--allow-empty", "-m", "init")
            sub_result = subprocess.run(
                ["git", "-c", "protocol.file.allow=always", "-c", "user.name=Test",
                 "-c", "user.email=t@example.com", "submodule", "add", "-q",
                 str(tmp / "lib-src"), "lib"],
                cwd=super_dir, capture_output=True, text=True)
            self.assertEqual(sub_result.returncode, 0, sub_result.stdout + sub_result.stderr)
            lib = super_dir / "lib"
            result = install(lib)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            copied_super = tmp / "super-copy"
            shutil.copytree(super_dir, copied_super, symlinks=True)
            res = run_script("install.py", "uninstall", "--root", str(copied_super / "lib"))
            self.assertNotEqual(res.returncode, 0)
            for name in ("pre-commit", "commit-msg"):
                self.assertTrue((copied_super / "lib" / ".git").exists())

    def test_f2r3_trailing_space_in_gitdir_path_is_not_collapsed(self):
        """A `.strip()` on gitfile content silently turns the real target `meta ` (trailing
        space) into `meta` -- a different, unrelated directory. Here `meta` is a symlink
        (flagged as unsafe); `meta ` is the real, plain target directory for this checkout.
        Stripping the space makes the code check the wrong path and misreport a symlink."""
        with TempDir() as tmp:
            real_target = tmp / "meta "
            real_target.mkdir()
            wrong_target = tmp / "meta"
            (tmp / "elsewhere").mkdir()
            wrong_target.symlink_to(tmp / "elsewhere", target_is_directory=True)
            root = tmp / "proj"
            root.mkdir()
            dot_git = root / ".git"
            dot_git.write_text(f"gitdir: {real_target}\n")
            from _lib import git_hooks
            problem, needs_record = git_hooks._gitfile_problem(root, dot_git)
            self.assertIsNone(problem)
            self.assertTrue(needs_record)

    def test_f4r3_toctou_hooks_dir_symlink_swap_before_delete_is_refused(self):
        """Simulate a race: the hooks directory passes validation, then (before anything is
        opened or deleted) an attacker swaps it for a symlink to a victim repo's hooks. The
        fix opens the validated directory once with O_NOFOLLOW, so the swapped-in symlink is
        refused rather than followed into the victim's hooks."""
        with TempDir() as tmp:
            root = self.project(tmp / "proj")
            victim = self.project(tmp / "victim")
            victim_hooks = victim / ".git/hooks"
            victim_before = {p.name: p.read_bytes() for p in victim_hooks.iterdir()}
            real_hooks = root / ".git/hooks"
            owned = json.loads((root / self.OWNED).read_text())
            record = owned["adapters"]

            from _lib import git_hooks
            from _lib.adapters import GIT_HOOK, HOOK
            orig_directory = git_hooks.directory

            def swap_then_return(r):
                result = orig_directory(r)
                shutil.rmtree(real_hooks)
                real_hooks.symlink_to(victim_hooks, target_is_directory=True)
                return result

            with mock.patch.object(git_hooks, "directory", side_effect=swap_then_return):
                with self.assertRaises(git_hooks.CgspecError):
                    git_hooks.remove(root, record, GIT_HOOK, HOOK)

            self.assertEqual(victim_before, {p.name: p.read_bytes() for p in victim_hooks.iterdir()})

    def test_f4r3_toctou_hook_name_symlink_before_write_does_not_truncate_victim(self):
        """Simulate a race on the write path: right after the hooks directory is prepared
        (but before a brand-new hook file is ever opened for writing), an attacker plants a
        symlink at the hook's name pointing at a pre-existing victim file. The fix never
        opens the real hook name for writing (it writes a temp name and renames over the
        target through a directory fd), so the victim is never truncated."""
        with TempDir() as tmp:
            root = tmp / "proj"
            root.mkdir()
            git(root, "init", "-q", "-b", "main")
            hooks_dir = root / ".git/hooks"
            victim = tmp / "victim-secret.txt"
            victim.write_bytes(b"do not touch")

            from _lib import adapters
            orig_mkdir = Path.mkdir
            swapped = {"done": False}

            def mkdir_then_swap(self_path, *args, **kwargs):
                result = orig_mkdir(self_path, *args, **kwargs)
                if not swapped["done"] and self_path == hooks_dir:
                    swapped["done"] = True
                    (hooks_dir / "pre-commit").symlink_to(victim)
                return result

            with mock.patch.object(Path, "mkdir", mkdir_then_swap):
                adapters._wire_git(root, {})

            self.assertEqual(victim.read_bytes(), b"do not touch")
