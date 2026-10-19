"""Review of the document-date feature: dates cannot be invented, reset or bumped without an edit."""

from __future__ import annotations

import json
import os
import unittest

from tests.helpers import TempDir, doctor, git, git_project, install


def reasons(root):
    from _lib.commit_gate import evaluate
    from _lib.gitview import View
    return [r for r in evaluate(root, View.staged(root)) if "Created" in r or "Last edited" in r or "date" in r]


def stamped(title, created, edited, body="Text that says something.\n"):
    return f"# {title}\nCreated: {created} · Last edited: {edited}\n\n- **Status:** Draft\n\n{body}"


class DateReviewTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git_project(self.root)
        from _lib.common import utc_now
        self.now = utc_now()
        owned = json.loads((self.root / "docs/_cgspec/01-engine/owned-files.json").read_text())
        self.installed = owned["installed_at"]

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def stage(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        git(self.root, "add", "-A")

    def commit(self, msg="c"):
        git(self.root, "commit", "-q", "--no-verify", "-m", msg)

    def test_future_dates_are_rejected(self):
        self.stage("docs/adrs/ADR-001-x.md", stamped("X", "2099-01-01T00:00:00Z", "2099-01-01T00:00:00Z"))
        self.assertTrue(any("future" in r for r in reasons(self.root)), reasons(self.root))

    def test_new_document_cannot_claim_unknown_creation(self):
        self.stage("docs/adrs/ADR-001-x.md", stamped("X", "unknown", self.now))
        self.assertTrue(any("unknown" in r for r in reasons(self.root)), reasons(self.root))

    def test_new_document_cannot_be_backdated_before_install(self):
        self.stage("docs/adrs/ADR-001-x.md", stamped("X", "2001-01-01T00:00:00Z", self.now))
        self.assertTrue(any("before CGSpec was installed" in r for r in reasons(self.root)), reasons(self.root))

    def test_honest_new_document_passes(self):
        self.stage("docs/adrs/ADR-001-x.md", stamped("X", self.now, self.now))
        self.assertEqual(reasons(self.root), [])

    def test_date_only_edit_is_rejected(self):
        self.stage("docs/adrs/ADR-001-x.md", stamped("X", self.now, self.now))
        self.commit()
        text = (self.root / "docs/adrs/ADR-001-x.md").read_text()
        self.stage("docs/adrs/ADR-001-x.md", text.replace(f"Last edited: {self.now}", "Last edited: " + self.bump(self.now)))
        self.assertTrue(any("without a content change" in r for r in reasons(self.root)), reasons(self.root))

    def bump(self, stamp):
        from datetime import datetime, timedelta
        moment = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ") - timedelta(seconds=0)
        return (moment + timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

    def test_legacy_document_gets_unknown_not_an_invented_date(self):
        self.stage("docs/adrs/ADR-001-x.md", "# X\n\n- **Status:** Draft\n\nOld text.\n")
        self.commit()
        self.stage("docs/adrs/ADR-001-x.md", stamped("X", "2020-05-05T00:00:00Z", self.now, "Old text, edited.\n"))
        self.assertTrue(any("unknown" in r for r in reasons(self.root)), reasons(self.root))
        self.stage("docs/adrs/ADR-001-x.md", stamped("X", "unknown", self.now, "Old text, edited.\n"))
        self.assertEqual(reasons(self.root), [])

    def test_rename_keeps_creation(self):
        self.stage("docs/adrs/ADR-001-x.md", stamped("X", self.now, self.now))
        self.commit()
        git(self.root, "mv", "docs/adrs/ADR-001-x.md", "docs/adrs/ADR-001-renamed.md")
        self.assertEqual(reasons(self.root), [])
        path = self.root / "docs/adrs/ADR-001-renamed.md"
        path.write_text(path.read_text().replace(f"Created: {self.now}", "Created: unknown"))
        git(self.root, "add", "-A")
        self.assertTrue(any("Created changed" in r for r in reasons(self.root)), reasons(self.root))

    def test_doctor_flags_future_dates(self):
        (self.root / "docs/adrs/ADR-001-x.md").write_text(stamped("X", "2099-01-01T00:00:00Z", "2099-01-01T00:00:00Z"))
        result = doctor(self.root)
        self.assertIn("E-DOC-DATES", result.stdout)


if __name__ == "__main__":
    unittest.main()
