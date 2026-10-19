"""Approval words must identify exactly one target before they can authorize a record."""

from __future__ import annotations

import unittest

from engine._lib.inbox import approval_target


class ApprovalBindingTests(unittest.TestCase):
    def test_explicit_targets(self):
        examples = {
            "approve SLICE-004": "SLICE-004",
            "approved CHK-012": "CHK-012",
            "yes, approve SLICE-001": "SLICE-001",
            "approve SLICE-001.": "SLICE-001",
            "approve the test command": "test_command",
            "approve decision: Use SQLite for the local cache": "decision:use sqlite for the local cache",
            "approve decision: Use after-tax pricing": "decision:use after-tax pricing",
            "approve decision: No data retention": "decision:no data retention",
        }
        for words, target in examples.items():
            with self.subTest(words=words):
                self.assertEqual(approval_target(words), target)

    def test_unrelated_or_ambiguous_words_have_no_target(self):
        for words in (
            "yes", "ok go", "approved", "yes, go ahead and rename the README",
            "approve the design and mention SLICE-004 later",
            "approve SLICE-004 and CHK-012", "approve test command for SLICE-004",
            "approve SLICE-004 and the test command", "approve test command and decision: ship",
            "approve decision", "approve decision: ", "approve SLICE-004?",
            "do not approve SLICE-004", "approve SLICE-004. No, wait",
            "approve SLICE-004 only if the tests pass", "approve SLICE-004\nBut not yet",
            "approve SLICE-004 pending security review", "approve SLICE-004 only when tests pass",
            "approve SLICE-004 and continue", "approve test command pending review",
            "approve the test command python3 -m unittest",
            "approve SLICE-004" + " " * 190 + "and CHK-012",
        ):
            with self.subTest(words=words):
                self.assertIsNone(approval_target(words))


if __name__ == "__main__":
    unittest.main()
