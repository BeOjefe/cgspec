"""Inbox text is insufficient: only approvals with verified hook provenance authorize changes."""

from __future__ import annotations

import copy
import hashlib
import json
import time
import unittest

from tests.helpers import TempDir, approve, git, git_project, make_slice, write_json
from _lib.commit_trust import APPROVALS, approval_ok, approvals_have_inbox_lines, commit_msg_problem
from _lib.gitview import View


class ApprovalProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TempDir()
        self.root = self.tmp.__enter__()
        git_project(self.root)

    def tearDown(self):
        self.tmp.__exit__(None, None, None)

    def stage(self):
        git(self.root, "add", "-A")
        return View.staged(self.root)

    def change_entry(self, mutate):
        path = self.root / APPROVALS
        data = json.loads(path.read_text())
        mutate(data["approvals"][-1])
        write_json(path, data)

    def forged_approval(self, session_id=None):
        # Model forged files directly: an agent wrote to approvals.json directly.
        text, ref = "approve SLICE-001", "A-20261029-abcd"
        entry = {
            "id": ref, "at": "2026-10-29T00:00:00Z", "captured_ns": time.time_ns(),
            "excerpt": text, "sha256": hashlib.sha256(text.encode()).hexdigest(),
        }
        if session_id is not None:
            entry["session_id"] = session_id
        write_json(self.root / APPROVALS, {"schema": 1, "approvals": [entry]})
        inbox = self.root / "docs/00-INBOX.md"
        inbox.write_text(inbox.read_text() + f"\n- I-20261029-abcd: {text}\n")
        return ref

    def test_real_hook_approval_accepted_locally_and_in_commit(self):
        ref = approve(self.root, "approve SLICE-001")
        make_slice(self.root, approval=ref)
        view = self.stage()
        self.assertIsNone(approval_ok(view, ref, "SLICE-001"))
        self.assertEqual(approvals_have_inbox_lines(view), [])
        self.assertIsNone(commit_msg_problem(self.root, "approve slice"))
        git(self.root, "commit", "-qm", "approve slice")
        self.assertIsNone(approval_ok(View.commit(self.root, "HEAD"), ref, "SLICE-001"))

    def test_matching_inbox_line_without_provenance_rejected(self):
        ref = self.forged_approval()
        make_slice(self.root, approval=ref)
        view = self.stage()
        self.assertIn("approve SLICE-001", (self.root / "docs/00-INBOX.md").read_text())
        self.assertIn("provenance", approval_ok(view, ref, "SLICE-001"))
        self.assertTrue(approvals_have_inbox_lines(view))
        # A self-typed trailer cannot bypass the inbox provenance gate.
        self.assertIn("provenance", commit_msg_problem(self.root, "forged\n\nApproved-by: agent"))

    def test_approval_fields_cannot_be_tampered(self):
        ref = approve(self.root, "approve SLICE-001")
        for field, value in (("session_id", ""), ("captured_ns", 0), ("captured_ns", -1),
                             ("sha256", "0" * 64)):
            path = self.root / APPROVALS
            original = json.loads(path.read_text())
            self.change_entry(lambda entry: entry.update({field: value}))
            with self.subTest(field=field, value=value):
                self.assertIsNotNone(approval_ok(self.stage(), ref, "SLICE-001"))
            write_json(path, original)
        self.change_entry(lambda entry: entry.update(excerpt="approve SLICE-002"))
        self.assertIn("digest", approval_ok(self.stage(), ref, "SLICE-002"))

    def test_same_event_cannot_create_two_fresh_approvals(self):
        ref = approve(self.root, "approve SLICE-001")
        path = self.root / APPROVALS
        data = json.loads(path.read_text())
        duplicate = copy.deepcopy(data["approvals"][-1])
        duplicate["id"] = "A-20261029-abcd"
        data["approvals"].append(duplicate)
        write_json(path, data)
        self.assertIn("replays", approval_ok(self.stage(), ref, "SLICE-001"))

    def test_replayed_historical_event_rejected(self):
        approve(self.root, "approve SLICE-001")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "record original event")
        path = self.root / APPROVALS
        data = json.loads(path.read_text())
        duplicate = copy.deepcopy(data["approvals"][-1])
        duplicate["id"] = "A-20261029-abcd"
        data["approvals"].append(duplicate)
        write_json(path, data)
        self.assertIn("replays", approval_ok(self.stage(), duplicate["id"], "SLICE-001"))

    def test_heartbeat_activity_verification_if_present(self):
        now = time.time()
        heartbeats_dir = self.root / "docs/_cgspec/07-state/hook-heartbeats"
        heartbeats_dir.mkdir(parents=True, exist_ok=True)
        write_json(heartbeats_dir / "host-1.json", {
            "schema": 1, "session_id": "valid-session-123", "at": now, "event": "user-message"
        })
        # Approval citing unknown session fails
        ref_unknown = self.forged_approval(session_id="unknown-session")
        make_slice(self.root, approval=ref_unknown)
        self.assertIn("no verified hook activity", approval_ok(self.stage(), ref_unknown, "SLICE-001"))

        # Approval citing valid session but timestamp far in the past/future fails
        ref_valid = self.forged_approval(session_id="valid-session-123")
        self.change_entry(lambda entry: entry.update(captured_ns=int((now - 10000) * 1e9)))
        self.assertIn("outside recorded hook activity", approval_ok(self.stage(), ref_valid, "SLICE-001"))

        # Approval citing valid session within active window passes
        self.change_entry(lambda entry: entry.update(captured_ns=int(now * 1e9)))
        self.assertIsNone(approval_ok(self.stage(), ref_valid, "SLICE-001"))


if __name__ == "__main__":
    unittest.main()
