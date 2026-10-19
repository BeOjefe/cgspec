"""Visible document provenance is truthful and survives ordinary edits."""

from __future__ import annotations

import unittest

from tests.helpers import TempDir, doctor, git, git_project, install


class DocumentDateTests(unittest.TestCase):
    def test_fresh_install_stamps_human_readable_docs(self):
        with TempDir() as root:
            self.assertEqual(install(root).returncode, 0)
            for rel in ("docs/00-INDEX.md", "docs/spines/01-INTENT.md", "docs/spines/05-DELIVERY.md"):
                text = (root / rel).read_text()
                self.assertRegex(text.splitlines()[1],
                                 r"^Created: \d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ · Last edited: "
                                 r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_touch_preserves_creation_and_changes_last_edit(self):
        from _lib.document_dates import stamp_new, touch, validate_change
        first = stamp_new("# Intent\n\nHello\n", "2026-10-18T10:00:00Z")
        changed = touch(first.replace("Hello", "Goodbye"), "2026-10-19T10:00:00Z")
        self.assertIn("Created: 2026-10-18T10:00:00Z · Last edited: 2026-10-19T10:00:00Z", changed)
        self.assertEqual(validate_change(first, changed), [])
        self.assertTrue(validate_change(first, first.replace("Hello", "Goodbye")))

    def test_import_does_not_invent_creation(self):
        from _lib.document_dates import stamp_import
        result = stamp_import("# Old decision\n\nPrior text\n", "2026-10-19T10:00:00Z",
                              first_seen="2024-05-02T12:00:00Z")
        self.assertIn("Created: unknown · Last edited: 2026-10-19T10:00:00Z", result)
        self.assertIn("First seen in available Git history: 2024-05-02T12:00:00Z", result)

    def test_doctor_index_rebuild_advances_last_edit(self):
        from _lib.document_dates import STAMP, stamp_new
        with TempDir() as root:
            self.assertEqual(install(root).returncode, 0)
            index = root / "docs/00-INDEX.md"
            before = index.read_text()
            from _lib.common import utc_now
            (root / "docs/adrs/ADR-001-choice.md").write_text(stamp_new(
                "# Choice\n\n- **Status:** Draft\n", utc_now()))
            self.assertEqual(doctor(root, "--fix").returncode, 0)
            after = index.read_text()
            old = STAMP.fullmatch(before.splitlines()[1])
            new = STAMP.fullmatch(after.splitlines()[1])
            self.assertEqual(old.group(1), new.group(1))
            self.assertGreater(new.group(2), old.group(2))

    def test_commit_rejects_missing_or_stale_dates(self):
        from _lib.commit_gate import evaluate
        from _lib.gitview import View
        with TempDir() as root:
            git_project(root)
            record = root / "docs/adrs/ADR-001-choice.md"
            record.write_text("# Choice\n\n- **Status:** Draft\n")
            git(root, "add", "docs/adrs/ADR-001-choice.md")
            self.assertTrue(any("Last edited" in reason for reason in evaluate(root, View.staged(root))))
            from _lib.document_dates import stamp_new
            from _lib.common import utc_now
            record.write_text(stamp_new(record.read_text(), utc_now()))
            git(root, "add", "docs/adrs/ADR-001-choice.md")
            self.assertFalse(any("Last edited" in reason for reason in evaluate(root, View.staged(root))))
            git(root, "commit", "-q", "-m", "add decision")
            record.write_text(record.read_text() + "\nChanged text.\n")
            git(root, "add", "docs/adrs/ADR-001-choice.md")
            self.assertTrue(any("Last edited" in reason for reason in evaluate(root, View.staged(root))))

    def test_doctor_warns_of_legacy_unstamped_record(self):
        with TempDir() as root:
            self.assertEqual(install(root).returncode, 0)
            (root / "docs/adrs/ADR-001-choice.md").write_text("# Choice\n\n- **Status:** Draft\n")
            result = doctor(root)
            self.assertIn("W-DOC-DATES", result.stdout)


if __name__ == "__main__":
    unittest.main()
