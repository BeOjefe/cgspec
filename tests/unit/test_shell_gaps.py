"""Shell-command detection gaps and false positives from the enforcement review."""

from __future__ import annotations

import os
import unittest

from tests.helpers import TempDir, claude_payload, git, git_project, hook, run_script

FROZEN = "docs/_cgspec/07-state/frozen.json"


class ShellGapTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git_project(self.root)

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def bash(self, command):
        return hook(self.root, "pre-tool", claude_payload(self.root, "Bash", command=command), "--tool", "claude")

    def test_hidden_writes_are_blocked(self):
        for command in (
            f"echo hi\nrm {FROZEN}",
            f"bash -c 'rm {FROZEN}'",
            f"sh -c \"echo x > {FROZEN}\"",
            f"python3 -c \"open('{FROZEN}','w').write('x')\"",
            f"python3 - <<'EOF'\nopen('{FROZEN}','w').write('x')\nEOF",
            f"(rm {FROZEN})",
            f"echo $(rm {FROZEN})",
            f"echo x >| {FROZEN}",
            f"perl -pi -e 's/a/b/' {FROZEN}",
            f"awk -i inplace '{{print}}' {FROZEN}",
            f"find docs -name frozen.json -exec rm {{}} \\;",
            f"find docs -name frozen.json -delete",
            f"echo {FROZEN} | xargs rm",
            "tar -xf evil.tar -C docs/_cgspec/07-state",
            "git apply evil.patch",
            f"node -e \"require('fs').writeFileSync('{FROZEN}','x')\"",
        ):
            with self.subTest(command=command):
                self.assertEqual(self.bash(command).returncode, 2, command)

    def test_everyday_commands_are_allowed(self):
        for command in ("git checkout -b feature/login", "git checkout main", "git switch -c x",
                        "npm test 2>&1 | tee /tmp/out.txt", "git status && git diff", "ls -la docs",
                        f"cat {FROZEN} | python3 -m json.tool", "python3 -m pytest -q",
                        "rm -rf node_modules", "rm -rf .cgspec-scratch/tmp"):
            with self.subTest(command=command):
                result = self.bash(command)
                self.assertEqual(result.returncode, 0, command + "\n" + result.stderr)

    def test_gitignored_build_output_needs_no_tier(self):
        (self.root / ".gitignore").write_text((self.root / ".gitignore").read_text() + "build/\n")
        self.assertEqual(self.bash("rm -rf build/out").returncode, 0)


class EmojiRangeTests(unittest.TestCase):
    def test_symbols_pass_emoji_fail(self):
        from tests import helpers  # noqa: F401
        from _lib.gates import EMOJI
        for text in ("♔ king", "☀ sun", "♀", "⚠ warning", "→ arrow", "✓ done"):
            with self.subTest(text=text):
                self.assertIsNone(EMOJI.search(text))
        for text in ("\U0001F680", "✅", "⚠️", "✨", "⭐", "⚡"):
            with self.subTest(text=text):
                self.assertIsNotNone(EMOJI.search(text))


class GitHookPlacementTests(unittest.TestCase):
    def test_worktree_gets_hooks(self):
        with TempDir() as root:
            main = root / "main"
            main.mkdir()
            git(main, "init", "-q", "-b", "main")
            (main / "README.md").write_text("x\n")
            git(main, "add", "-A")
            git(main, "commit", "-q", "-m", "init")
            wt = root / "wt"
            git(main, "worktree", "add", "-q", str(wt), "-b", "feature")
            result = run_script("install.py", "install", "--root", str(wt), "--profile", "headless",
                                "--topology", "single", "--tools", "git")
            self.assertEqual(result.returncode, 0, result.stderr)
            import subprocess
            hooks_dir = subprocess.run(["git", "rev-parse", "--git-path", "hooks"], cwd=wt,
                                       capture_output=True, text=True).stdout.strip()
            hook_file = os.path.join(hooks_dir if os.path.isabs(hooks_dir) else str(wt / hooks_dir), "pre-commit")
            self.assertTrue(os.path.exists(hook_file), hook_file)

    def test_custom_hooks_path_is_reported(self):
        with TempDir() as root:
            git(root, "init", "-q", "-b", "main")
            git(root, "config", "core.hooksPath", ".husky")
            result = run_script("install.py", "install", "--root", str(root), "--profile", "headless",
                                "--topology", "single", "--tools", "git")
            self.assertIn("core.hooksPath", result.stdout + result.stderr)


class StagedDoctorTests(unittest.TestCase):
    def test_doctor_judges_the_staged_tree(self):
        with TempDir() as root:
            git_project(root)
            (root / "docs/random.md").write_text("unstaged junk\n")  # not staged: must not block
            (root / "docs/00-INBOX.md").write_text((root / "docs/00-INBOX.md").read_text() + "\n- idea\n")
            git(root, "add", "docs/00-INBOX.md")
            result = hook(root, "pre-commit", None, "--tool", "git")
            self.assertEqual(result.returncode, 0, result.stdout)
            (root / "docs/random.md").unlink()
            (root / "docs/junk.md").write_text("staged junk\n")
            git(root, "add", "docs/junk.md")
            (root / "docs/junk.md").unlink()  # removed from the working tree, still staged: must block
            result = hook(root, "pre-commit", None, "--tool", "git")
            self.assertEqual(result.returncode, 1, result.stdout)


if __name__ == "__main__":
    unittest.main()
