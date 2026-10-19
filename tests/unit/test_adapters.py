"""Adapters: Antigravity payloads, and install wiring for Claude Code, Antigravity, git, CI and Cursor."""

from __future__ import annotations

import json
import os
import subprocess
import unittest

from tests.helpers import TempDir, git, hook, install, run_script


def ag_payload(root, name, **args):
    return {"conversationId": "c1", "workspacePaths": [str(root)], "toolCall": {"name": name, "args": args}, "stepIdx": 3}


class AntigravityPayloadTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        install(self.root)

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def run_hook(self, payload, event="pre-tool"):
        return hook(self.root, event, payload, "--tool", "antigravity")

    def test_denied_write_answers_with_json_decision(self):
        result = self.run_hook(ag_payload(self.root, "write_to_file",
                                          TargetFile=str(self.root / "docs/_cgspec/01-engine/doctor.py"), CodeContent="x"))
        self.assertEqual(result.returncode, 0)
        answer = json.loads(result.stdout)
        self.assertEqual(answer["decision"], "deny")
        self.assertIn("protected", answer["reason"])

    def test_allowed_write_prints_nothing_blocking(self):
        result = self.run_hook(ag_payload(self.root, "replace_file_content",
                                          TargetFile=str(self.root / "docs/spines/01-INTENT.md"), ReplacementContent="text"))
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("deny", result.stdout)

    def test_run_command_uses_cwd(self):
        snap = self.root / "docs/prototypes/_snapshots"
        payload = ag_payload(self.root, "run_command", CommandLine="sed -i s/a/b/ ../../_memlog.md", Cwd=str(snap))
        self.assertEqual(json.loads(self.run_hook(payload).stdout)["decision"], "deny")

    def test_emoji_found_in_any_content_field(self):
        payload = ag_payload(self.root, "multi_replace_file_content", TargetFile=str(self.root / "docs/spines/01-INTENT.md"),
                             ReplacementChunks=[{"TargetContent": "a", "ReplacementContent": "b \U0001F680"}])
        self.assertEqual(json.loads(self.run_hook(payload).stdout)["decision"], "deny")

    def test_stop_keeps_agent_running_with_continue(self):
        (self.root / "docs/random.md").write_text("x\n")
        result = self.run_hook({"conversationId": "c1", "workspacePaths": [str(self.root)], "fullyIdle": True}, "stop")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["decision"], "continue")


class WiringTests(unittest.TestCase):
    TOOLS = "claude,antigravity,git,ci,cursor"

    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git(self.root, "init", "-q", "-b", "main")

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def do_install(self):
        return run_script("install.py", "install", "--root", str(self.root), "--profile", "web-workspace",
                          "--topology", "single", "--tools", self.TOOLS)

    def test_all_adapters_are_wired(self):
        result = self.do_install()
        self.assertEqual(result.returncode, 0)
        self.assertIn("require the 'governance' status check", result.stdout)
        claude = json.loads((self.root / ".claude/settings.json").read_text())
        self.assertIn("PreToolUse", claude["hooks"])
        self.assertIn("cgspec_hook.py pre-tool --tool claude", json.dumps(claude))
        ag = json.loads((self.root / ".agents/hooks.json").read_text())
        self.assertIn("cgspec", ag)
        self.assertIn("PreToolUse", ag["cgspec"])
        self.assertTrue(os.access(self.root / ".git/hooks/pre-commit", os.X_OK))
        self.assertTrue((self.root / ".git/hooks/commit-msg").exists())
        workflow = (self.root / ".github/workflows/cgspec.yml").read_text()
        self.assertIn("engine/cgspec_hook.py\" ci", workflow)
        frozen = json.loads((self.root / "docs/_cgspec/07-state/frozen.json").read_text())
        self.assertIn(".github/workflows/cgspec.yml", [e["path"] for e in frozen["entries"]])
        self.assertIn("CONTRACT.md", (self.root / ".cursor/rules/cgspec.mdc").read_text())
        self.assertEqual(run_script("doctor.py", "--root", str(self.root)).returncode, 0)

    def test_antigravity_hook_resolves_engine_from_agents_working_directory(self):
        self.assertEqual(self.do_install().returncode, 0)
        data = json.loads((self.root / ".agents/hooks.json").read_text())
        command = data["cgspec"]["PreToolUse"][0]["hooks"][0]["command"]
        payload = ag_payload(self.root, "replace_file_content",
                             TargetFile=str(self.root / "docs/spines/01-INTENT.md"),
                             ReplacementContent="text")
        result = subprocess.run(command, shell=True, cwd=self.root / ".agents", input=json.dumps(payload),
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("can't open file", result.stderr)

    def test_antigravity_hook_resolves_engine_before_git_init(self):
        with TempDir() as root:
            result = run_script("install.py", "install", "--root", str(root), "--profile", "web-workspace",
                                "--topology", "single", "--tools", "antigravity")
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads((root / ".agents/hooks.json").read_text())
            command = data["cgspec"]["PreToolUse"][0]["hooks"][0]["command"]
            payload = ag_payload(root, "replace_file_content", TargetFile=str(root / "docs/spines/01-INTENT.md"),
                                 ReplacementContent="text")
            called = subprocess.run(command, shell=True, cwd=root / ".agents", input=json.dumps(payload),
                                    capture_output=True, text=True)
            self.assertEqual(called.returncode, 0, called.stderr)

    def test_upgrade_refreshes_claude_hook_without_removing_user_hook(self):
        self.assertEqual(self.do_install().returncode, 0)
        path = self.root / ".claude/settings.json"
        data = json.loads(path.read_text())
        data["hooks"]["PreToolUse"].append({"matcher": "Read", "hooks": [
            {"type": "command", "command": "echo my-hook"}]})
        data["hooks"]["Stop"][0]["hooks"][0]["command"] = "python3 stale/cgspec_hook.py stop --tool claude"
        path.write_text(json.dumps(data))
        result = run_script("install.py", "upgrade", "--root", str(self.root))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        after = json.loads(path.read_text())
        self.assertIn("echo my-hook", json.dumps(after))
        self.assertIn('"$CLAUDE_PROJECT_DIR"/docs/_cgspec/01-engine/cgspec_hook.py stop',
                      after["hooks"]["Stop"][0]["hooks"][0]["command"])
        self.assertNotIn("stale/cgspec_hook.py", json.dumps(after))

    def test_existing_settings_are_merged_and_restored(self):
        (self.root / ".claude").mkdir()
        mine = {"model": "opus", "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "my-check"}]}]}}
        (self.root / ".claude/settings.json").write_text(json.dumps(mine))
        self.do_install()
        merged = json.loads((self.root / ".claude/settings.json").read_text())
        self.assertEqual(merged["model"], "opus")
        self.assertIn("my-check", json.dumps(merged))
        self.assertIn("cgspec_hook.py", json.dumps(merged))
        run_script("install.py", "uninstall", "--root", str(self.root))
        after = json.loads((self.root / ".claude/settings.json").read_text())
        self.assertNotIn("cgspec_hook.py", json.dumps(after))
        self.assertIn("my-check", json.dumps(after))

    def test_foreign_git_hook_is_not_overwritten(self):
        hooks = self.root / ".git/hooks"
        hooks.mkdir(parents=True, exist_ok=True)
        (hooks / "pre-commit").write_text("#!/bin/sh\necho mine\n")
        result = self.do_install()
        self.assertEqual(result.returncode, 0)
        self.assertEqual((hooks / "pre-commit").read_text(), "#!/bin/sh\necho mine\n")
        self.assertIn("pre-commit", result.stdout + result.stderr)

    def test_real_git_hook_rejects_a_bad_commit(self):
        self.do_install()
        git(self.root, "add", "-A")
        env = dict(os.environ, GIT_AUTHOR_NAME="T", GIT_AUTHOR_EMAIL="t@e", GIT_COMMITTER_NAME="T", GIT_COMMITTER_EMAIL="t@e")
        first = subprocess.run(["git", "commit", "-q", "-m", "install cgspec"], cwd=self.root, capture_output=True, text=True, env=env)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        (self.root / "src").mkdir()
        (self.root / "src/a.ts").write_text("export const a = 1;\n")
        git(self.root, "add", "-A")
        bad = subprocess.run(["git", "commit", "-q", "-m", "no tier"], cwd=self.root, capture_output=True, text=True, env=env)
        self.assertNotEqual(bad.returncode, 0)
        self.assertIn("no change tier", bad.stdout + bad.stderr)

    def test_uninstall_unwires_everything_it_added(self):
        self.do_install()
        run_script("install.py", "uninstall", "--root", str(self.root))
        for rel in (".agents/hooks.json", ".git/hooks/pre-commit", ".github/workflows/cgspec.yml", ".cursor/rules/cgspec.mdc"):
            self.assertFalse((self.root / rel).exists(), rel)


if __name__ == "__main__":
    unittest.main()
