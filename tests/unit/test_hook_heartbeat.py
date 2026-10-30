"""Hook coverage is a live-process check, never a self-seeded project status."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import time
import unittest
from dataclasses import replace
from unittest.mock import patch

from tests.helpers import TempDir, git, git_project, hook, write_json
from _lib import hook_heartbeat as H
import cgspec_hook


class HeartbeatTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TempDir()
        self.root = self.tmp.__enter__()
        self.host = H.Host("claude", 12345, hashlib.sha256(b"live host").hexdigest(), time.time() - 3600, True)
        self.witness = self.root / "private" / "project"
        self.patches = [patch.object(H, "host_process", side_effect=lambda: self.host),
                        patch.object(H, "witness_directory", return_value=self.witness)]
        for p in self.patches:
            p.start()
        git(self.root, "init", "-q")
        (self.root / "src").mkdir()
        (self.root / "src/a.py").write_text("value = 1\n")
        git(self.root, "add", "src")
        git(self.root, "commit", "-qm", "baseline")

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.__exit__(None, None, None)

    def receipt_path(self):
        return self.root / H.RECEIPTS / f"{self.host.identity}.json"

    def record(self, event="pre-tool"):
        return H.record(self.root, event, "claude", {"hook_event_name": H.EVENTS[event], "session_id": "s1"})

    def check_cli(self, event="session-check"):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
                patch.object(cgspec_hook, "doctor_state", return_value=(0, "0 errors")), \
                patch("install.verify_engine", return_value=[]):
            code = cgspec_hook.main([event, "--root", str(self.root)])
        return code, out.getvalue(), err.getvalue()

    def test_real_activity_passes_and_check_does_not_refresh_it(self):
        self.assertTrue(self.record())
        before = self.receipt_path().read_bytes()
        self.assertEqual(H.problems(self.root), [])
        code, out, err = self.check_cli()
        self.assertEqual(code, 0, err)
        self.assertIn("hooks: verified", out)
        self.assertEqual(before, self.receipt_path().read_bytes())

    def test_zero_activity_after_hours_and_many_edits_fails_loudly(self):
        self.host = replace(self.host, started=time.time() - 12 * 3600)
        for i in range(50):
            (self.root / "src" / f"file{i}.py").write_text("unguarded = True\n")
        code, out, err = self.check_cli()
        self.assertEqual(code, 1)
        self.assertIn("HOOK COVERAGE FAILURE", err)
        self.assertIn("no authenticated hook activity", err)
        self.assertIn("running 43200s", err)
        self.assertIn("Relaunch", err)
        self.assertFalse(self.witness.exists(), "diagnostics must not seed their own proof")

    def test_commit_backstop_fails_with_zero_lifecycle_activity(self):
        code, out, err = self.check_cli("pre-commit")
        self.assertEqual(code, 1)
        self.assertIn("HOOK COVERAGE FAILURE", err)
        self.assertFalse(self.witness.exists())

    def test_handwritten_plausible_heartbeat_without_witness_fails(self):
        write_json(self.receipt_path(), {"schema": 1, "event": "pre-tool", "at": time.time(),
                                        "pid": self.host.pid, "host": self.host.identity, "sequence": 50})
        self.assertIn("no authenticated hook activity", H.problems(self.root)[0])

    def test_timestamp_tampering_and_unkeyed_hash_fail(self):
        self.record()
        data = json.loads(self.receipt_path().read_text())
        data["at"] = time.time()
        data["mac"] = hashlib.sha256(H._canonical({k: v for k, v in data.items() if k != "mac"})).hexdigest()
        write_json(self.receipt_path(), data)
        self.assertIn("authentication/witness mismatch", H.problems(self.root)[0])

    def test_signed_old_receipt_cannot_be_replayed(self):
        self.record()
        first = self.receipt_path().read_bytes()
        self.record("post-tool")
        second = json.loads(self.receipt_path().read_text())
        self.assertEqual(second["sequence"], 2)
        self.assertEqual(second["previous"], json.loads(first)["mac"])
        self.receipt_path().write_bytes(first)
        self.assertIn("authentication/witness mismatch", H.problems(self.root)[0])

    def test_previous_process_or_concurrent_host_cannot_cover_this_process(self):
        self.record()
        original = self.host
        self.host = replace(self.host, identity=hashlib.sha256(b"other process start ticks").hexdigest())
        self.assertIn("no authenticated hook activity", H.problems(self.root)[0])
        self.record()
        self.assertEqual(H.problems(self.root), [])
        self.host = original
        self.assertEqual(H.problems(self.root), [])

    def test_stale_hook_with_subsequent_edits_fails(self):
        with patch.object(H.time, "time", return_value=time.time() - 600):
            self.record()
        (self.root / "src/a.py").write_text("value = 2\n")
        problems = H.problems(self.root)
        self.assertIn("heartbeat is 600s old", problems[0])
        self.assertIn("edited/deleted paths", problems[0])
        self.assertEqual(self.check_cli()[0], 1)

    def test_idle_session_is_not_mistaken_for_missing_hooks(self):
        with patch.object(H.time, "time", return_value=time.time() - 600):
            self.record()
        # Keep the test-only witness out of Git status just as the real external witness is.
        (self.root / ".git/info/exclude").write_text("private/\n")
        self.assertEqual(H.problems(self.root), [])

    def test_stale_deleted_file_fails(self):
        with patch.object(H.time, "time", return_value=time.time() - 600):
            self.record()
        (self.root / "src/a.py").unlink()
        self.assertTrue(H.problems(self.root))

    def test_stale_check_with_unavailable_git_fails_loudly(self):
        with patch.object(H.time, "time", return_value=time.time() - 600):
            self.record()
        with patch("_lib.source_state._git", side_effect=subprocess.TimeoutExpired("git", 2)):
            code, out, err = self.check_cli()
        self.assertEqual(code, 1)
        self.assertIn("HOOK COVERAGE FAILURE", err)
        self.assertIn("cannot be verified", err)

    def test_broken_recorder_blocks_pre_tool_but_not_user_message(self):
        for event, expected in (("pre-tool", 2), ("user-message", 0)):
            payload = {"hook_event_name": H.EVENTS[event]}
            err = io.StringIO()
            with patch.object(sys, "stdin", io.StringIO(json.dumps(payload))), \
                    patch.object(H, "record", side_effect=OSError("witness unavailable")), \
                    contextlib.redirect_stderr(err):
                code = cgspec_hook.main([event, "--root", str(self.root), "--tool", "claude"])
            self.assertEqual(code, expected)
            self.assertIn("HOOK COVERAGE FAILURE", err.getvalue())

    def test_wrong_event_tool_or_nested_manual_invocation_cannot_seed(self):
        self.assertFalse(H.record(self.root, "session-check", "claude", {}))
        self.assertFalse(H.record(self.root, "pre-tool", "claude", {"hook_event_name": "SessionStart"}))
        self.assertFalse(H.record(self.root, "pre-tool", "generic", {"hook_event_name": "PreToolUse"}))
        self.host = replace(self.host, direct=False)
        self.assertFalse(self.record())
        self.assertFalse(self.witness.exists())

    def test_no_supported_process_is_explicitly_unverified(self):
        with patch.object(H, "host_process", return_value=None):
            code, out, err = self.check_cli()
            self.assertEqual(code, 0, err)
            self.assertIn("UNVERIFIED", out)
            self.assertTrue(H.problems(self.root, "claude"))

    def test_every_callback_dispatch_records_and_preserves_its_payload(self):
        for event, host_event in H.EVENTS.items():
            with self.subTest(event=event):
                payload = {"hook_event_name": host_event, "session_id": "s1", "prompt": "hello"}
                with patch.object(sys, "stdin", io.StringIO(json.dumps(payload))), \
                        patch.object(cgspec_hook, "lifecycle", return_value=0) as lifecycle, \
                        patch.object(cgspec_hook, "pre_tool", return_value=0), \
                        patch.object(cgspec_hook, "post_tool", return_value=0):
                    self.assertEqual(cgspec_hook.main([event, "--root", str(self.root), "--tool", "claude"]), 0)
                data = json.loads(self.receipt_path().read_text())
                self.assertEqual(data["event"], event)
                self.assertEqual(data["session_id"], "s1")
                if event not in ("pre-tool", "post-tool"):
                    self.assertEqual(json.loads(lifecycle.call_args.args[3]), payload)

    def test_symlinked_mirror_and_unsafe_witness_fail_visibly(self):
        self.record()
        original = self.receipt_path().read_text()
        self.receipt_path().unlink()
        target = self.root / "forged.json"
        target.write_text(original)
        self.receipt_path().symlink_to(target)
        self.assertIn("symlinked", H.problems(self.root)[0])
        self.receipt_path().unlink()
        self.receipt_path().write_text(original)
        self.witness.chmod(0o755)
        self.assertIn("unsafe hook witness", H.problems(self.root)[0])

    def test_edit_tools_and_shell_cannot_write_evidence_or_read_witness(self):
        for payload in (
            {"tool_name": "Write", "tool_input": {"file_path": str(self.receipt_path()), "content": "{}"}},
            {"tool_name": "Bash", "tool_input": {"command": "cat /tmp/cgspec-hook-witness-1000/project/key"}},
        ):
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(cgspec_hook.pre_tool(self.root, "claude", json.dumps(payload)), 2)

    def test_interactive_tty_stdin_does_not_block_and_does_not_seed_receipt(self):
        with patch.object(sys.stdin, "isatty", return_value=True), contextlib.redirect_stdout(io.StringIO()):
            code = cgspec_hook.main(["session-start", "--root", str(self.root), "--tool", "claude"])
            self.assertEqual(code, 0)
            self.assertFalse(self.receipt_path().exists())


@unittest.skipUnless(sys.platform.startswith("linux"), "live process identity currently requires Linux /proc")
class LiveHostHeartbeatTests(unittest.TestCase):
    def test_callback_and_check_in_real_process_tree(self):
        with TempDir() as root:
            git_project(root)
            host = root / "claude"
            host.symlink_to(sys.executable)
            # Synthetic host, real kernel ancestry, subprocess dispatch, MAC and installed layout.
            driver = '''
import json, sys
from pathlib import Path
from tests.helpers import hook, git_live
from _lib.hook_heartbeat import witness_directory
root = Path(sys.argv[1])
before = hook(root, "session-check", {})
commit = git_live(root, "commit", "--allow-empty", "-m", "uncovered session", check=False)
started = hook(root, "session-start", {"hook_event_name": "SessionStart", "session_id": "live"}, "--tool", "claude")
after = hook(root, "session-check", {})
print(json.dumps({"before": [before.returncode, before.stderr], "start": [started.returncode, started.stderr],
                  "commit": [commit.returncode, commit.stdout, commit.stderr],
                  "after": [after.returncode, after.stdout, after.stderr], "witness": str(witness_directory(root))}))
'''
            child = subprocess.run([str(host), "-c", driver, str(root)], capture_output=True, text=True, timeout=60)
            self.assertEqual(child.returncode, 0, child.stderr)
            data = json.loads(child.stdout)
            try:
                self.assertEqual(data["before"][0], 1, data)
                self.assertIn("HOOK COVERAGE FAILURE", data["before"][1])
                self.assertNotEqual(data["commit"][0], 0, data)
                self.assertIn("HOOK COVERAGE FAILURE", data["commit"][2])
                self.assertEqual(data["start"][0], 0, data)
                self.assertEqual(data["after"][0], 0, data)
                self.assertIn("hooks: verified", data["after"][1])
            finally:
                shutil.rmtree(data["witness"], ignore_errors=True)
            # Diagnostic outside a host (or inside an uncovered host) cannot falsely advertise verified activity.
            out = hook(root, "session-check", {}).stdout
            self.assertTrue("UNVERIFIED" in out or "hooks: FAILED" in out)
            self.assertNotIn("hooks: verified", out)

    def test_antigravity_cli_real_process_tree(self):
        with TempDir() as root:
            git_project(root)
            host = root / "agy"
            host.symlink_to(sys.executable)
            driver = '''
import json, sys
from pathlib import Path
from tests.helpers import hook
from _lib.hook_heartbeat import witness_directory
root = Path(sys.argv[1])
started = hook(root, "session-start", {"hook_event_name": "SessionStart", "session_id": "live-agy"}, "--tool", "antigravity")
after = hook(root, "session-check", {})
print(json.dumps({"start": [started.returncode, started.stderr],
                  "after": [after.returncode, after.stdout, after.stderr], "witness": str(witness_directory(root))}))
'''
            child = subprocess.run([str(host), "-c", driver, str(root)], capture_output=True, text=True, timeout=60)
            self.assertEqual(child.returncode, 0, child.stderr)
            data = json.loads(child.stdout)
            try:
                self.assertEqual(data["start"][0], 0, data)
                self.assertEqual(data["after"][0], 0, data)
                self.assertIn("hooks: verified", data["after"][1])
            finally:
                shutil.rmtree(data["witness"], ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
