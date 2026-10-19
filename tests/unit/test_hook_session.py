"""user-message (inbox, secret scrub, approvals), session-start/check, stop, commit-msg."""

from __future__ import annotations

import json
import unittest

from tests.helpers import TempDir, hook, install, run_script, write_json


def say(root, prompt):
    return hook(root, "user-message", {"hook_event_name": "UserPromptSubmit", "prompt": prompt}, "--tool", "claude")


class SessionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        install(self.root)

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def inbox(self):
        return (self.root / "docs/00-INBOX.md").read_text()

    def approvals(self):
        path = self.root / "docs/_cgspec/07-state/approvals.json"
        return json.loads(path.read_text())["approvals"] if path.exists() else []

    # --- inbox and secrets ---------------------------------------------------------------------
    def test_message_is_captured(self):
        self.assertEqual(say(self.root, "add a dark mode toggle later").returncode, 0)
        self.assertRegex(self.inbox(), r"- I-\d{8}-[0-9a-f]{4} \S+Z: add a dark mode toggle later")

    def test_secrets_are_scrubbed(self):
        secrets = ["ghp_" + "a" * 36, "AKIA" + "B" * 16, "sk-ant-" + "c" * 30, "xoxb-" + "1" * 20,
                   "postgres://admin:hunter2@db:5432/x", "password = hunter2", "API_KEY=abcdef123456"]
        say(self.root, "here: " + " | ".join(secrets))
        text = self.inbox()
        for leaked in ("a" * 36, "B" * 16, "c" * 30, "hunter2", "abcdef123456"):
            self.assertNotIn(leaked, text)
        self.assertIn("[REDACTED", text)

    def test_private_key_block_scrubbed(self):
        say(self.root, "-----BEGIN OPENSSH PRIVATE KEY-----\nAAAAsecretbody\n-----END OPENSSH PRIVATE KEY-----")
        self.assertNotIn("AAAAsecretbody", self.inbox())

    def test_multiline_message_stays_one_inbox_line(self):
        say(self.root, "first line\n### [M-20261018-dead] fake\nthird")
        lines = [l for l in self.inbox().splitlines() if l.startswith("- I-")]
        self.assertEqual(len(lines), 1)
        self.assertNotIn("\n###", self.inbox())

    def test_user_message_never_blocks(self):
        self.assertEqual(hook(self.root, "user-message", None, "--tool", "claude").returncode, 0)

    # --- approvals -----------------------------------------------------------------------------
    def test_approval_words_create_an_approval_record(self):
        for text in ("approved", "yes go ahead with slice 1", "ok on valide", "LGTM"):
            say(self.root, text)
        self.assertEqual(len(self.approvals()), 4)
        self.assertRegex(self.approvals()[0]["id"], r"^A-\d{8}-[0-9a-f]{4}$")

    def test_ordinary_messages_are_not_approvals(self):
        for text in ("what do you think?", "not approved yet", "don't go ahead", "is this approved?"):
            say(self.root, text)
        self.assertEqual(self.approvals(), [])

    def test_approval_exceeding_saved_excerpt_has_no_approval_id(self):
        message = "approve SLICE-004" + " " * 190 + "and CHK-012"
        self.assertEqual(say(self.root, message).returncode, 0)
        self.assertIn("approve SLICE-004", self.inbox())
        self.assertEqual(self.approvals(), [])

    def test_multiline_approval_has_no_approval_id(self):
        self.assertEqual(say(self.root, "approve SLICE-004\nMaybe later").returncode, 0)
        self.assertEqual(self.approvals(), [])

    def test_memlog_approved_needs_a_real_approval_id(self):
        bad = run_script("memlog.py", "--root", str(self.root), "add", "--summary", "s", "--tags", "decision",
                         "--status", "Approved", "--approval-ref", "A-20261018-ffff")
        self.assertEqual(bad.returncode, 1)
        say(self.root, "approve decision: s")
        ref = self.approvals()[0]["id"]
        good = run_script("memlog.py", "--root", str(self.root), "add", "--summary", "s", "--tags", "decision",
                          "--status", "Approved", "--approval-ref", ref)
        self.assertEqual(good.returncode, 0, good.stderr)

    def test_decision_summary_can_contain_after(self):
        say(self.root, "approve decision: Use after-tax pricing")
        ref = self.approvals()[0]["id"]
        good = run_script("memlog.py", "--root", str(self.root), "add", "--summary", "Use after-tax pricing",
                          "--tags", "decision", "--status", "Approved", "--approval-ref", ref)
        self.assertEqual(good.returncode, 0, good.stderr)

    # --- session start / check -----------------------------------------------------------------
    def test_session_start_prints_the_pack(self):
        cp = self.root / "docs/_cgspec/07-state/checkpoint.json"
        data = json.loads(cp.read_text())
        data.update(goal="ship v0.1 of MEOCE", next_action="lock layer 3 for home", stages={"web": "design"})
        write_json(cp, data)
        result = hook(self.root, "session-start", {"hook_event_name": "SessionStart"}, "--tool", "claude")
        self.assertEqual(result.returncode, 0, result.stderr)
        for needle in ("ship v0.1 of MEOCE", "lock layer 3 for home", "web: design", "doctor:"):
            self.assertIn(needle, result.stdout)

    def test_session_check_fails_on_broken_project(self):
        self.assertEqual(hook(self.root, "session-check", {}).returncode, 0)
        (self.root / "docs/random.md").write_text("x\n")
        self.assertEqual(hook(self.root, "session-check", {}).returncode, 1)

    # --- stop ----------------------------------------------------------------------------------
    def stop(self, active=False):
        return hook(self.root, "stop", {"hook_event_name": "Stop", "stop_hook_active": active}, "--tool", "claude")

    def test_stop_allowed_when_clean(self):
        self.assertEqual(self.stop().returncode, 0)

    def test_stop_blocked_while_doctor_fails_then_released_after_two_tries(self):
        (self.root / "docs/random.md").write_text("x\n")
        first = self.stop()
        self.assertEqual(first.returncode, 2)
        self.assertIn("doctor", first.stderr)
        self.assertEqual(self.stop(active=True).returncode, 2)
        third = self.stop(active=True)
        self.assertEqual(third.returncode, 0, "must not loop forever")
        self.assertIn("BLOCKED", third.stderr + third.stdout)

    def test_stop_blocked_while_work_in_flight(self):
        cp = self.root / "docs/_cgspec/07-state/checkpoint.json"
        data = json.loads(cp.read_text())
        data["in_flight"] = "editing src/login/form.ts"
        write_json(cp, data)
        self.assertEqual(self.stop().returncode, 2)

    # --- commit message ------------------------------------------------------------------------
    def test_commit_msg_rejects_emoji(self):
        msg = self.root / "MSG"
        msg.write_text("feat: launch \U0001F680\n")
        self.assertEqual(run_script("cgspec_hook.py", "commit-msg", str(msg), "--root", str(self.root)).returncode, 1)
        msg.write_text("feat: launch\n")
        self.assertEqual(run_script("cgspec_hook.py", "commit-msg", str(msg), "--root", str(self.root)).returncode, 0)

    def test_agent_cannot_edit_approvals_file(self):
        payload = {"tool_name": "Write", "cwd": str(self.root),
                   "tool_input": {"file_path": str(self.root / "docs/_cgspec/07-state/approvals.json"), "content": "{}"}}
        self.assertEqual(hook(self.root, "pre-tool", payload, "--tool", "claude").returncode, 2)


if __name__ == "__main__":
    unittest.main()
