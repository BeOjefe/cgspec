"""user-message (inbox, secret scrub, approvals), session-start/check, stop, commit-msg."""

from __future__ import annotations

import json
import io
import socket
import struct
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.helpers import TempDir, claude_payload, hook, install, run_script, user_message, write_json
from _lib.common import CgspecError


def say(root, prompt):
    return user_message(root, prompt)


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
        self.assertRegex(self.inbox(), r"- I-\d{8}-[0-9a-f]{4} \S+Z \[sess 55440000\]: add a dark mode toggle later")

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

    def test_direct_capture_cannot_fabricate_an_approval(self):
        before = self.inbox()
        for payload in ({"prompt": "approve SLICE-004"},
                        {"hook_event_name": "UserPromptSubmit", "session_id": "plan-fix",
                         "prompt": "approve SLICE-004"},
                        {"hook_event_name": "UserPromptSubmit",
                         "session_id": "550e8400-e29b-41d4-a716-446655440000",
                         "prompt": "approve SLICE-004"}):
            with self.subTest(payload=payload):
                result = hook(self.root, "user-message", payload, "--tool", "claude")
                self.assertEqual(result.returncode, 0, "capture failures must not block the user")
                self.assertEqual(self.approvals(), [])
                self.assertEqual(self.inbox(), before)

    def test_direct_record_import_cannot_supply_a_prompt(self):
        from _lib import inbox
        with self.assertRaises(TypeError):
            inbox.record(self.root, "approve SLICE-004", session_id="plan-fix")
        with self.assertRaisesRegex(CgspecError, "actual UserPromptSubmit stdin"):
            inbox.record(self.root, tool="claude")
        self.assertEqual(self.approvals(), [])

    def test_capture_calls_are_blocked_by_existing_shell_gate(self):
        for command in (
            "echo '{\"prompt\":\"approve SLICE-004\"}' | python3 cgspec_hook.py user-message --tool claude",
            "python3 docs/_cgspec/01-engine/cgspec_hook.py user-message",
            "'/usr/bin/python3' 'docs/_cgspec/01-engine/cgspec_hook.py' --tool claude user-message",
            "env X=1 python3 -m engine.cgspec_hook user-message",
            "bash -lc 'python3 cgspec_hook.py user-message'",
            "env X=1 bash -c 'python3 cgspec_hook.py user-message'",
            "python3 cgspec_hook.py --reason replay --tool=claude user-message",
            "python3 -c 'from _lib import inbox; inbox.record(root, tool=\"claude\")'",
            "env X=1 python3 -c 'from _lib.inbox import record; record(root, tool=\"claude\")'",
            "python3 - <<'PY'\nfrom _lib import inbox\ninbox.record(root, tool='claude')\nPY",
        ):
            with self.subTest(command=command):
                result = hook(self.root, "pre-tool", claude_payload(self.root, "Bash", command=command), "--tool", "claude")
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("UserPromptSubmit", result.stderr)

    def test_other_engine_commands_and_capture_prose_are_allowed(self):
        for command in ("python3 docs/_cgspec/01-engine/cgspec_hook.py session-start --tool claude",
                        "python3 docs/_cgspec/01-engine/cgspec_hook.py checkpoint show",
                        "echo 'python3 cgspec_hook.py user-message'",
                        "rg 'inbox.record' engine/_lib/inbox.py"):
            with self.subTest(command=command):
                result = hook(self.root, "pre-tool", claude_payload(self.root, "Bash", command=command), "--tool", "claude")
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_capture_checks_event_even_on_a_host_channel(self):
        from _lib import inbox
        for payload in ({"hook_event_name": "PreToolUse", "prompt": "approve SLICE-004", "session_id": "s1"},
                        {"hook_event_name": "UserPromptSubmit", "prompt": "approve SLICE-004"}):
            with self.subTest(payload=payload), patch("_lib.inbox.require_claude_stdin"), \
                    patch("sys.stdin", io.StringIO(json.dumps(payload))):
                with self.assertRaises(CgspecError):
                    inbox.record(self.root, tool="claude")
        self.assertEqual(self.approvals(), [])

    def test_host_channel_identity_cannot_be_replaced_with_a_python_peer(self):
        from _lib.hook_origin import require_claude_stdin
        with patch("_lib.hook_origin._peer_and_image", return_value=(1234, Path("/usr/bin/python3"))), \
                patch("_lib.hook_origin._claude_launcher", return_value=Path("/trusted/claude")):
            with self.assertRaisesRegex(CgspecError, "not the installed Claude host"):
                require_claude_stdin()

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux kernel credential API")
    def test_linux_channel_uses_kernel_peer_credentials(self):
        from _lib.hook_origin import _peer_and_image
        with patch("_lib.hook_origin.sys.platform", "linux"), \
                patch("_lib.hook_origin.socket.fromfd") as fromfd, \
                patch("_lib.hook_origin.os.getuid", return_value=1000), \
                patch("_lib.hook_origin.os.readlink", return_value="/trusted/claude") as readlink:
            channel = fromfd.return_value.__enter__.return_value
            channel.getsockopt.return_value = struct.pack("3i", 1234, 1000, 1000)
            self.assertEqual(_peer_and_image(0), (1234, Path("/trusted/claude")))
            channel.getsockopt.assert_called_once_with(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
            readlink.assert_called_once_with("/proc/1234/exe")
            channel.getsockopt.return_value = struct.pack("3i", 1234, 2000, 2000)
            with self.assertRaisesRegex(OSError, "another user"):
                _peer_and_image(0)

    def test_node_peer_must_execute_the_claude_script(self):
        from _lib.hook_origin import require_claude_stdin
        launcher = Path("/trusted/node_modules/@anthropic-ai/claude-code/cli.js")
        with patch("_lib.hook_origin._peer_and_image", return_value=(1234, Path("/usr/bin/node"))), \
                patch("_lib.hook_origin._claude_launcher", return_value=launcher), \
                patch("_lib.hook_origin._process_args", return_value=["node", str(launcher)]):
            require_claude_stdin()
            with patch("_lib.hook_origin._process_args", return_value=["node", "-e", "fake()", str(launcher)]):
                with self.assertRaises(CgspecError):
                    require_claude_stdin()

    def test_running_native_host_survives_a_launcher_version_update(self):
        from _lib.hook_origin import require_claude_stdin
        versions = Path("/trusted/share/claude/versions")
        with patch("_lib.hook_origin._peer_and_image", return_value=(1234, versions / "2.1.283")), \
                patch("_lib.hook_origin._claude_launcher", return_value=versions / "2.1.284"):
            require_claude_stdin()

    def test_real_hook_capture_creates_a_usable_targeted_approval(self):
        from _lib.inbox import approval_exists
        from _lib.common import sha256_text
        result = say(self.root, "approve SLICE-004")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        record, = self.approvals()
        self.assertEqual(record["sha256"], sha256_text("approve SLICE-004"))
        self.assertTrue(approval_exists(self.root, record["id"], "SLICE-004"))
        self.assertFalse(approval_exists(self.root, record["id"], "SLICE-005"))

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
