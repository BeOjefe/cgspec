"""Recovery must preserve state and make missing/changed observations explicit."""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from tests.helpers import TempDir, git, git_project, hook, install, run_script, user_message, write_json
from _lib import session
from _lib.common import STATE_DIR


class CheckpointRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TempDir()
        self.root = self.tmp.__enter__()
        install(self.root)
        self.path = self.root / STATE_DIR / "checkpoint.json"

    def tearDown(self):
        self.tmp.__exit__(None, None, None)

    def cmd(self, *args, stdin=None):
        return run_script("cgspec_hook.py", "checkpoint", "--root", str(self.root), *args, stdin=stdin)

    def read(self):
        return json.loads(self.path.read_text())

    def test_corrupt_or_invalid_state_is_never_overwritten(self):
        for raw in ('{"pending": [', '[]', 'null', '{"schema": 1}'):
            with self.subTest(raw=raw):
                self.path.write_text(raw)
                result = self.cmd("--next", "resume")
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(self.path.read_text(), raw)

    def test_missing_checkpoint_is_not_silently_recreated(self):
        self.path.unlink()
        self.assertEqual(self.cmd("--next", "resume").returncode, 1)
        self.assertFalse(self.path.exists())

    def test_contradictory_transitions_preserve_state(self):
        before = self.path.read_bytes()
        for args in (("--in-flight", "x", "--done"), ("--done", "--blocked", "why"),
                     ("--in-flight", "x", "--blocked", "why")):
            self.assertNotEqual(self.cmd(*args).returncode, 0)
            self.assertEqual(self.path.read_bytes(), before)

    def test_patch_replaces_only_named_fields_and_clear_values_are_explicit(self):
        cp = self.read()
        cp.update(constraints=["keep history"], owners={"src/a": "agent-a"}, pending=["old"], revision="baseline")
        write_json(self.path, cp)
        result = self.cmd("--update-file", "-", stdin=json.dumps({"pending": [], "wakeup": None}))
        self.assertEqual(result.returncode, 0, result.stderr)
        cp = self.read()
        self.assertEqual(cp["pending"], [])
        self.assertEqual(cp["constraints"], ["keep history"])
        self.assertEqual(cp["owners"], {"src/a": "agent-a"})
        self.assertEqual(cp["revision"], "baseline")

    def test_patch_rejects_unknown_derived_and_invalid_fields_atomically(self):
        before = self.path.read_bytes()
        for patch in ({"source": {}}, {"updated": "tomorrow"}, {"schema": 2},
                      {"unresolved_stop": {}}, {"unknown": 1}, {"pending": None},
                      {"stages": {"web": "magic"}}, []):
            result = self.cmd("--update-file", "-", stdin=json.dumps(patch))
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(self.path.read_bytes(), before)

    def test_done_does_not_discard_pending_or_claim_project_completion(self):
        cp = self.read()
        cp.update(in_flight="work", pending=["independent review"], open_issues=["risk"])
        write_json(self.path, cp)
        result = self.cmd("--done")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNone(self.read()["in_flight"])
        self.assertEqual(self.read()["pending"], ["independent review"])
        self.assertEqual(self.read()["open_issues"], ["risk"])
        self.assertNotIn("project complete", result.stdout.lower())

    def test_pack_surfaces_existing_recovery_fields_without_writing(self):
        cp = self.read()
        cp.update(constraints=["no deployment"], pending=["run review"], evidence_done=["tests/log"],
                  owners={"src/a": "agent-a"}, revision="reviewed-sha")
        write_json(self.path, cp)
        before = self.path.read_bytes()
        result = session.pack(self.root, "0 errors")
        for value in ("no deployment", "run review", "tests/log", "agent-a", "reviewed-sha"):
            self.assertIn(value, result)
        self.assertIn("source observation unavailable", result)
        self.assertEqual(self.path.read_bytes(), before)

    def test_checkpoint_and_retry_state_are_protected_but_cli_is_allowed(self):
        for rel in ("checkpoint.json", "stop-retries.json"):
            target = str(self.root / STATE_DIR / rel)
            result = hook(self.root, "pre-tool", {"tool": "write", "paths": [target], "content": "{}"})
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        command = "python3 docs/_cgspec/01-engine/cgspec_hook.py checkpoint --next resume"
        result = hook(self.root, "pre-tool", {"tool": "shell", "command": command, "cwd": str(self.root)})
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_stop_escape_retains_reasons_without_refreshing_semantic_time(self):
        cp = self.read()
        cp.update(in_flight="unfinished", pending=["review"])
        write_json(self.path, cp)
        for expected in (False, False, True):
            allow, _ = session.stop_decision(self.root, ["unfinished work", "stale checkpoint"])
            self.assertEqual(allow, expected)
        after = self.read()
        self.assertEqual(after["updated"], cp["updated"])
        self.assertEqual(after["in_flight"], "unfinished")
        self.assertEqual(after["pending"], ["review"])
        self.assertEqual(after["unresolved_stop"]["problems"], ["unfinished work", "stale checkpoint"])
        self.assertIn("stale checkpoint", session.pack(self.root, "0 errors"))

    def test_corrupt_checkpoint_stop_escape_persists_fallback_and_still_exits(self):
        self.path.write_text('{"broken":')
        for _ in range(3):
            allow, message = session.stop_decision(self.root, ["cannot recover"])
        self.assertTrue(allow)
        self.assertIn("SAVE FAILED", message)
        self.assertEqual(self.path.read_text(), '{"broken":')
        retry = json.loads((self.root / STATE_DIR / "stop-retries.json").read_text())
        self.assertEqual(retry["unresolved_stop"]["problems"], ["cannot recover"])
        self.assertIn("cannot recover", session.pack(self.root, "1 error"))

    def test_clean_stop_does_not_touch_clean_checkpoint(self):
        before = self.path.read_bytes()
        session.stop_decision(self.root, [])
        self.assertEqual(self.path.read_bytes(), before)

    def test_clean_stop_clears_only_derived_stop_record(self):
        session.stop_decision(self.root, ["x"])
        session.stop_decision(self.root, ["x"])
        session.stop_decision(self.root, ["x"])
        cp = self.read()
        cp.update(open_issues=["keep issue"])
        write_json(self.path, cp)
        session.stop_decision(self.root, [])
        self.assertNotIn("unresolved_stop", self.read())
        self.assertEqual(self.read()["open_issues"], ["keep issue"])
        self.assertEqual(self.read()["updated"], cp["updated"])

    def test_schema_invalid_checkpoint_does_not_crash_stop_protocol(self):
        cp = self.read()
        cp["updated"] = []
        write_json(self.path, cp)
        ledger = self.root / "docs/_memlog.md"
        ledger.write_text(ledger.read_text() + "\n### [M-20261021-abcd] 2026-10-21T00:00:00Z | tags: work\n")
        for expected in (2, 2, 0):
            result = hook(self.root, "stop", {}, "--tool", "claude")
            self.assertEqual(result.returncode, expected, result.stderr)
        self.assertEqual(self.read()["updated"], [])

    def test_upgrade_preserves_extended_state_exactly(self):
        self.assertEqual(self.cmd("--capture").returncode, 0)
        cp = self.read()
        cp.update(pending=["review"], owners={"src/a.ts": "agent-a"})
        write_json(self.path, cp)
        for _ in range(3):
            session.stop_decision(self.root, ["pending review"])
        before = self.path.read_bytes()
        for _ in range(2):
            result = run_script("install.py", "upgrade", "--root", str(self.root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(self.path.read_bytes(), before)
        result = run_script("doctor.py", "--root", str(self.root))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class SourceRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TempDir()
        self.root = self.tmp.__enter__()
        git_project(self.root)
        self.path = self.root / STATE_DIR / "checkpoint.json"

    def tearDown(self):
        self.tmp.__exit__(None, None, None)

    def capture(self):
        return run_script("cgspec_hook.py", "checkpoint", "--capture", "--root", str(self.root))

    def test_capture_and_pack_detect_same_head_changed_bytes_without_refreshing_baseline(self):
        p = self.root / "src/a.ts"
        p.write_text("first\n")
        self.assertEqual(self.capture().returncode, 0)
        saved = self.path.read_bytes()
        self.assertNotIn("changed since capture", session.pack(self.root, "0 errors"))
        p.write_text("other\n")
        text = session.pack(self.root, "0 errors")
        self.assertIn("changed since capture", text)
        self.assertIn("src/a.ts", text)
        self.assertEqual(self.path.read_bytes(), saved)

    def test_capture_tracks_deletion_untracked_file_and_rename(self):
        git(self.root, "mv", "src/a.ts", "src/renamed.ts")
        (self.root / "src/login/form.ts").unlink()
        (self.root / "new.txt").write_text("new\n")
        self.assertEqual(self.capture().returncode, 0)
        source = json.loads(self.path.read_text())["source"]
        paths = {e["path"] for e in source["entries"]}
        self.assertTrue({"src/a.ts", "src/renamed.ts", "src/login/form.ts", "new.txt"} <= paths)

    def test_capture_does_not_hash_or_name_sensitive_files_or_follow_symlinks(self):
        (self.root / ".env.local").write_text("PASSWORD=short\n")
        (self.root / "client_secret_named.json").write_text("1234")
        (self.root / "link").symlink_to(self.root / ".env.local")
        self.assertEqual(self.capture().returncode, 0)
        cp = json.loads(self.path.read_text())["source"]
        raw = json.dumps(cp)
        for value in ("PASSWORD", ".env.local", "client_secret_named.json"):
            self.assertNotIn(value, raw)
        self.assertFalse(cp["complete"])
        self.assertTrue(cp["gaps"])

    def test_hook_activity_does_not_create_false_drift(self):
        self.assertEqual(self.capture().returncode, 0)
        self.assertEqual(user_message(self.root, "hello").returncode, 0)
        self.assertIn("hello", (self.root / "docs/00-INBOX.md").read_text())
        write_json(self.root / STATE_DIR / "budget.json", {"schema": 1})
        session.stop_decision(self.root, [])
        self.assertNotIn("changed since capture", session.pack(self.root, "0 errors"))

    def test_precompact_observes_source_without_inventing_semantic_progress(self):
        before = json.loads(self.path.read_text())
        result = hook(self.root, "pre-compact", {}, "--tool", "antigravity")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("injectSteps", json.loads(result.stdout))
        after = json.loads(self.path.read_text())
        self.assertIn("source", after)
        for key in ("goal", "updated", "next_action", "in_flight"):
            self.assertEqual(before[key], after[key])


class SourceLimitsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TempDir()
        self.root = self.tmp.__enter__()
        git_project(self.root)

    def tearDown(self):
        self.tmp.__exit__(None, None, None)

    def test_bounds_are_partial_not_a_complete_claim(self):
        from _lib.source_state import observe
        for name in ("a.txt", "b.txt", "c.txt"):
            (self.root / name).write_text("0123456789")
        with patch("_lib.source_state.MAX_FILES", 2), patch("_lib.source_state.MAX_BYTES", 4):
            result = observe(self.root)
        self.assertFalse(result["complete"])
        self.assertEqual(len(result["entries"]), 2)
        self.assertIn("hash byte limit", result["gaps"])
        self.assertTrue(any("1 entries omitted" in g for g in result["gaps"]))

    def test_untracked_directory_is_explicitly_incomplete(self):
        from _lib.source_state import observe
        (self.root / "new-tree").mkdir()
        (self.root / "new-tree/file.txt").write_text("data")
        result = observe(self.root)
        self.assertFalse(result["complete"])
        self.assertIn("untracked directory not enumerated", result["gaps"])

    def test_real_dependency_lock_is_observed(self):
        from _lib.source_state import observe
        (self.root / "Cargo.lock").write_text("version = 3")
        result = observe(self.root)
        self.assertIn("Cargo.lock", [e["path"] for e in result["entries"]])

    def test_unavailable_git_is_explicit_not_invented(self):
        from _lib.source_state import observe
        with patch("_lib.source_state._git", side_effect=OSError("unavailable")):
            result = observe(self.root)
        self.assertFalse(result["complete"])
        self.assertIsNone(result["head"])
        self.assertTrue(any("Git information unavailable" in g for g in result["gaps"]))

    def test_both_disk_saves_failing_do_not_trap_a_stop(self):
        for _ in range(2):
            session.stop_decision(self.root, ["unfinished"])
        with patch("_lib.checkpoint_cmd.write_json", side_effect=OSError("read only")), \
             patch("_lib.stop_state.write_json", side_effect=OSError("read only")):
            allow, message = session.stop_decision(self.root, ["unfinished"])
        self.assertTrue(allow)
        self.assertIn("SAVE FAILED", message)
        self.assertIn("unfinished", message)

    def test_precompact_failed_capture_preserves_saved_checkpoint(self):
        from _lib.common import CgspecError
        path = self.root / STATE_DIR / "checkpoint.json"
        before = path.read_bytes()
        with patch("_lib.checkpoint_cmd.capture_only", side_effect=CgspecError("cannot capture")):
            session.capture_before_compact(self.root)
        self.assertEqual(path.read_bytes(), before)
