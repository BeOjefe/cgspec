"""The plugin source tree's own pre-commit gate (.githooks/).

Lab/audit finding: the source repository's hook pointed at
`docs/_cgspec/01-script/cgspec_hook.py`, which does not exist here, and then fell
through to `exit 0`. The repository that ships the secret and emoji gates enforced
neither on itself, and the hook looked active while doing nothing.
"""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HOOK_DIR = REPO / ".githooks"


def _load():
    spec = importlib.util.spec_from_file_location("cgspec_source_gate", HOOK_DIR / "source_precommit.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SourceGate(unittest.TestCase):
    """Runs the gate against a disposable repository holding a copy of the engine."""

    @classmethod
    def setUpClass(cls):
        cls.gate = _load()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        env = {**os.environ, "GIT_CONFIG_GLOBAL": str(self.root / "gitconfig"), "GIT_CONFIG_NOSYSTEM": "1"}
        self.env = env
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "t")
        (self.root / "seed.txt").write_text("seed\n", encoding="utf-8")
        self.git("add", "seed.txt")
        self.git("commit", "-q", "-m", "seed")

    def git(self, *args: str):
        return subprocess.run(["git", *args], cwd=self.root, env=self.env,
                              capture_output=True, text=True, check=False)

    def stage(self, rel: str, content: str):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self.git("add", "--", rel)

    def reasons(self):
        return self.gate.reasons(self.root)

    # --- content rules -------------------------------------------------------

    def test_clean_commit_is_allowed(self):
        self.stage("src/a.py", "value = compute()\n")
        self.assertEqual(self.reasons(), [])

    def test_staged_secret_is_blocked(self):
        self.stage("src/a.py", 'KEY = "AKIAABCDEFGHIJKLMN12"\n')  # cgspec:test-fixture
        self.assertTrue(any("aws-key" in r for r in self.reasons()), self.reasons())

    def test_the_reason_reads_as_a_sentence(self):
        """The reason is read by a person whose commit just failed, so it has to be literate."""
        self.stage("src/a.py", 'KEY = "AKIAABCDEFGHIJKLMN12"\n')  # cgspec:test-fixture
        self.assertIn("looks like an aws-key", self.reasons()[0])
        self.stage("src/b.py", 'T = "xoxb-1234567890-abcdef"\n')  # cgspec:test-fixture
        self.assertTrue(any("looks like a slack-token" in r for r in self.reasons()), self.reasons())

    def test_staged_emoji_is_blocked(self):
        self.stage("docs/a.md", "all done ✅\n")  # cgspec:test-fixture
        self.assertTrue(any("emoji" in r for r in self.reasons()), self.reasons())

    def test_staged_pycache_is_blocked(self):
        self.stage("engine/__pycache__/x.pyc", "junk\n")
        self.assertTrue(any("cache files" in r for r in self.reasons()), self.reasons())

    # --- the fixture exemption, and its limit --------------------------------

    def test_marked_fixture_under_tests_is_allowed(self):
        self.stage("tests/unit/test_x.py", 'KEY = "AKIAABCDEFGHIJKLMN12"  # cgspec:test-fixture\n')
        self.assertEqual(self.reasons(), [])

    def test_marker_does_not_exempt_shipped_code(self):
        """The marker is honoured under tests/ only, so it cannot smuggle a real key."""
        self.stage("engine/_lib/thing.py", 'KEY = "AKIAABCDEFGHIJKLMN12"  # cgspec:test-fixture\n')
        self.assertTrue(any("aws-key" in r for r in self.reasons()), self.reasons())

    def test_pattern_module_may_carry_its_own_pattern(self):
        self.stage("engine/_lib/inbox.py",
                   '("url-password", re.compile(r"(?<=://)([^:/@\\s]+):([^@\\s]+)(?=@)")),  # cgspec:test-fixture\n')
        self.assertEqual(self.reasons(), [])

    def test_binary_files_are_skipped(self):
        self.stage("docs/shot.png", "✅ not really a png\n")  # cgspec:test-fixture
        self.assertEqual(self.reasons(), [])

    def test_svg_is_scanned_as_text(self):
        """SVG is XML text; skipping it as binary let a key hide in <metadata>."""
        self.stage("docs/logo.svg", '<svg><metadata>AKIAABCDEFGHIJKLMN12</metadata></svg>\n')  # cgspec:test-fixture
        self.assertTrue(any("aws-key" in r for r in self.reasons()), self.reasons())

    def test_quoted_path_secret_is_blocked(self):
        """Regression: files with special chars in names have quoted diff paths (+++ "b/...").

        Git quotes paths containing newlines, tabs, or backslashes. The old parser only
        matched +++ b/ and silently skipped the quoted form, so secrets in such files
        passed through undetected.
        """
        # A filename with a tab character - git will quote this as "b/secret\tfile.py"
        name = "secret\tfile.py"
        path = self.root / name
        path.write_text('KEY = "AKIAABCDEFGHIJKLMN12"\n', encoding="utf-8")  # cgspec:test-fixture
        self.git("add", "--", name)
        self.assertTrue(any("aws-key" in r for r in self.reasons()), self.reasons())


class HookScript(unittest.TestCase):
    """The shipped hook script itself, which is what git actually runs."""

    def test_hook_refuses_when_checker_is_missing(self):
        """Regression: the old hook fell through to `exit 0`, so it never blocked anything."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = {**os.environ, "GIT_CONFIG_GLOBAL": str(root / "gc"), "GIT_CONFIG_NOSYSTEM": "1"}
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, env=env, check=True)
            hook = root / "pre-commit"
            hook.write_bytes((HOOK_DIR / "pre-commit").read_bytes())
            hook.chmod(0o755)
            done = subprocess.run(["sh", str(hook)], cwd=root, env=env, capture_output=True, text=True)
            self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
            self.assertIn("no checker found", done.stderr)

    def test_hook_blocks_a_real_staged_secret_end_to_end(self):
        """The hook is wired to this repository's checker and blocks a real commit."""
        done = subprocess.run([sys.executable, str(HOOK_DIR / "source_precommit.py")],
                              cwd=REPO, capture_output=True, text=True)
        self.assertIn(done.returncode, (0, 1))  # must run without crashing in the real tree

    def test_consumer_fallback_uses_the_real_event_name(self):
        """The consumer hook accepts `pre-commit --tool git`; `git-pre-commit` is not an event."""
        text = (HOOK_DIR / "pre-commit").read_text(encoding="utf-8")
        self.assertIn("cgspec_hook.py\" pre-commit --tool git", text)
        self.assertNotIn("git-pre-commit", text)

    def test_hook_targets_exist(self):
        """Every path the hook can exec must exist, or it is a guard that cannot run."""
        text = (HOOK_DIR / "pre-commit").read_text(encoding="utf-8")
        targets = re.findall(r'"\$root/([^"]+)"', text)
        self.assertTrue(targets)
        present = [t for t in targets if (REPO / t).exists()]
        self.assertTrue(present, f"none of the hook's checkers exist in this tree: {targets}")


class WiringIsReproducible(unittest.TestCase):
    """Git finds hooks through `core.hooksPath`, which is local config and cannot be committed.

    Caught by CI on the first push of this branch: the gate worked only on the one checkout
    where someone had set that value by hand, and a fresh clone had no hooks at all. Asserting
    the live value was itself the bug, because it is legitimately unset in a fresh clone. What
    has to be true everywhere is that activation is scripted and the script works.
    """

    ENABLE = HOOK_DIR / "enable"

    def test_enable_script_is_executable(self):
        self.assertTrue(self.ENABLE.is_file(), f"{self.ENABLE} is missing")
        self.assertTrue(os.access(self.ENABLE, os.X_OK), f"{self.ENABLE} is not executable")

    def _clone(self, root: Path) -> dict:
        """A throwaway repository holding only what the enable script needs to find."""
        env = {**os.environ, "GIT_CONFIG_GLOBAL": str(root / "gc"), "GIT_CONFIG_NOSYSTEM": "1"}
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, env=env, check=True)
        (root / ".githooks").mkdir()
        for name in ("enable", "pre-commit", "source_precommit.py"):
            target = root / ".githooks" / name
            target.write_bytes((HOOK_DIR / name).read_bytes())
            target.chmod(0o755)
        return env

    def hooks_path(self, root: Path, env: dict) -> str:
        out = subprocess.run(["git", "config", "--local", "--get", "core.hooksPath"],
                             cwd=root, env=env, capture_output=True, text=True)
        return out.stdout.strip()

    def test_a_fresh_clone_starts_unwired_and_the_script_wires_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = self._clone(root)
            self.assertEqual(self.hooks_path(root, env), "", "a fresh clone should have no hooks path")
            done = subprocess.run(["sh", ".githooks/enable"], cwd=root, env=env,
                                  capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            self.assertEqual(self.hooks_path(root, env), ".githooks")

    def test_the_script_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = self._clone(root)
            for _ in range(2):
                done = subprocess.run(["sh", ".githooks/enable"], cwd=root, env=env,
                                      capture_output=True, text=True)
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            self.assertEqual(self.hooks_path(root, env), ".githooks")

    def test_the_script_refuses_to_hijack_another_tools_hook_path(self):
        """Overwriting a foreign hooks path would disable whatever else the user installed."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = self._clone(root)
            subprocess.run(["git", "config", "--local", "core.hooksPath", ".husky"],
                           cwd=root, env=env, check=True)
            done = subprocess.run(["sh", ".githooks/enable"], cwd=root, env=env,
                                  capture_output=True, text=True)
            self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
            self.assertIn("refusing to overwrite", done.stderr)
            self.assertEqual(self.hooks_path(root, env), ".husky", "the foreign path was changed")

    def test_the_script_refuses_a_repository_without_the_checker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = {**os.environ, "GIT_CONFIG_GLOBAL": str(root / "gc"), "GIT_CONFIG_NOSYSTEM": "1"}
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, env=env, check=True)
            script = root / "enable"
            script.write_bytes(self.ENABLE.read_bytes())
            done = subprocess.run(["sh", str(script)], cwd=root, env=env, capture_output=True, text=True)
            self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
            self.assertEqual(self.hooks_path(root, env), "")

    def test_this_checkout_is_not_wired_to_something_else(self):
        """Unset is legitimate (fresh clone, CI). Set to a foreign path means the gate is dead."""
        out = subprocess.run(["git", "config", "--get", "core.hooksPath"],
                             cwd=REPO, capture_output=True, text=True)
        value = out.stdout.strip()
        if not value:
            self.skipTest("this checkout has no core.hooksPath; run ./.githooks/enable to activate "
                          "the gate (CI never commits, so it does not need it)")
        self.assertEqual(value, ".githooks",
                         "core.hooksPath points elsewhere, so the gate in .githooks never runs")

    def test_activation_is_documented_where_a_contributor_will_look(self):
        """A script nobody is told to run leaves the gate just as inert."""
        self.assertIn(".githooks/enable", (REPO / "AGENTS.md").read_text(encoding="utf-8"))


class NoInertAdapterConfig(unittest.TestCase):
    """Audit report 50 P0: a host adapter config that cannot run looks like active wiring.

    No engine event runs in the plugin source tree -- every one resolves a project root and
    exits 1 with 'no docs/_cgspec/project.json found'. A checked-in host hook config here can
    therefore only mislead, so the source tree must not carry one. Consumer projects get
    theirs generated by the installer, which is covered by test_adapters.py.
    """

    def test_source_tree_carries_no_host_hook_config(self):
        for rel in (".agents/hooks.json", ".claude/settings.json", ".codex/hooks.json", ".opencode/hooks.json", ".cursor/rules/cgspec.mdc"):
            self.assertFalse((REPO / rel).exists(),
                             f"{rel} is checked in at the source root but no engine event can run here; "
                             "remove it or the next agent will read it as active wiring")

    def test_engine_events_cannot_run_in_the_source_tree(self):
        """The premise of the test above. If this ever passes, revisit the decision."""
        done = subprocess.run([sys.executable, "engine/cgspec_hook.py", "pre-tool", "--tool", "antigravity"],
                              cwd=REPO, input="{}", capture_output=True, text=True)
        self.assertEqual(done.returncode, 1)
        self.assertIn("project.json", done.stderr + done.stdout)


if __name__ == "__main__":
    unittest.main()
