"""post-tool hook (spec 8: mark affected evidence stale, count budget) and document-date upkeep."""

from __future__ import annotations

import json
import unittest

from tests.helpers import TempDir, claude_payload, git, git_project, hook, run_script, write_json

STAMP_RE = r"^Created: (\S+) · Last edited: (\S+)$"


def evidence(root, name, covers, state="Fresh"):
    write_json(root / f"docs/_cgspec/06-evidence/SLICE-001/{name}.json", {
        "schema": 1, "check": name, "revision": "abc1234", "verdict": "PASS", "state": state,
        "covers": covers, "ran_at": "2026-10-19T00:00:00Z", "ran_by": "ci"})


def state_of(root, name):
    return json.loads((root / f"docs/_cgspec/06-evidence/SLICE-001/{name}.json").read_text())["state"]


class PostToolTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git_project(self.root)

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def post(self, tool, **tool_input):
        payload = claude_payload(self.root, tool, **tool_input)
        payload["hook_event_name"] = "PostToolUse"
        return hook(self.root, "post-tool", payload, "--tool", "claude")

    def test_edit_marks_covering_evidence_stale(self):
        evidence(self.root, "unit", ["src/login/**"])
        evidence(self.root, "lint", ["src/other/**"])
        result = self.post("Edit", file_path="src/login/form.ts", old_string="1", new_string="2")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(state_of(self.root, "unit"), "Stale")
        self.assertEqual(state_of(self.root, "lint"), "Fresh")

    def test_shell_write_marks_evidence_stale(self):
        evidence(self.root, "unit", ["src/login/form.ts"])
        self.post("Bash", command="sed -i s/1/2/ src/login/form.ts")
        self.assertEqual(state_of(self.root, "unit"), "Stale")

    def test_evidence_without_covers_is_left_alone(self):
        write_json(self.root / "docs/_cgspec/06-evidence/SLICE-001/review.json", {
            "schema": 1, "check": "review", "revision": "abc1234", "verdict": "PASS", "state": "Fresh",
            "ran_at": "2026-10-19T00:00:00Z", "ran_by": "reviewer"})
        self.post("Edit", file_path="src/login/form.ts", old_string="1", new_string="2")
        data = json.loads((self.root / "docs/_cgspec/06-evidence/SLICE-001/review.json").read_text())
        self.assertEqual(data["state"], "Fresh")

    def test_helper_agents_are_counted_against_the_budget(self):
        write_json(self.root / "docs/_cgspec/07-state/budget.json", {
            "schema": 1, "task": "SLICE-001", "limits": {"helpers": 3, "review_rounds": 3, "research_passes": 2},
            "used": {"helpers": 0, "review_rounds": 0, "research_passes": 0}})
        result = self.post("Task", description="review", prompt="x")
        self.assertEqual(result.returncode, 0)
        used = json.loads((self.root / "docs/_cgspec/07-state/budget.json").read_text())["used"]
        self.assertEqual(used["helpers"], 1)

    def test_budget_overrun_is_reported(self):
        write_json(self.root / "docs/_cgspec/07-state/budget.json", {
            "schema": 1, "task": "SLICE-001", "limits": {"helpers": 1, "review_rounds": 3, "research_passes": 2},
            "used": {"helpers": 1, "review_rounds": 0, "research_passes": 0}})
        result = self.post("Agent", description="another", prompt="x")
        self.assertIn("budget", result.stdout + result.stderr)

    def test_post_tool_never_blocks_on_bad_input(self):
        self.assertEqual(hook(self.root, "post-tool", None, "--tool", "claude").returncode, 0)


class DocSyncTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git_project(self.root)

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def sync(self):
        return run_script("cgspec_hook.py", "doc", "sync", "--root", str(self.root))

    def stamp(self, rel):
        import re
        return re.match(STAMP_RE, (self.root / rel).read_text().splitlines()[1])

    def test_new_document_gets_dates(self):
        (self.root / "docs/adrs/ADR-001-db.md").write_text("# Pick the database\n\n- **Status:** Draft\n")
        self.assertEqual(self.sync().returncode, 0)
        match = self.stamp("docs/adrs/ADR-001-db.md")
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), match.group(2))

    def test_edited_document_gets_a_new_last_edited(self):
        spine = self.root / "docs/spines/01-INTENT.md"
        before = self.stamp("docs/spines/01-INTENT.md").groups()
        spine.write_text(spine.read_text() + "\nInvestors need plain explanations of market moves.\n")
        self.sync()
        after = self.stamp("docs/spines/01-INTENT.md").groups()
        self.assertEqual(before[0], after[0])
        self.assertGreater(after[1], before[1])

    def test_unchanged_document_keeps_its_dates(self):
        before = (self.root / "docs/spines/01-INTENT.md").read_text()
        self.sync()
        self.assertEqual((self.root / "docs/spines/01-INTENT.md").read_text(), before)

    def test_date_only_change_is_reverted(self):
        spine = self.root / "docs/spines/01-INTENT.md"
        original = spine.read_text()
        created = self.stamp("docs/spines/01-INTENT.md").group(1)
        lines = original.splitlines(keepends=True)
        lines[1] = f"Created: {created} · Last edited: 2026-10-19T23:59:59Z\n"
        spine.write_text("".join(lines))
        self.sync()
        self.assertEqual(spine.read_text(), original)

    def test_legacy_document_edit_is_labelled_unknown(self):
        legacy = self.root / "docs/adrs/ADR-002-old.md"
        legacy.write_text("# Old\n\n- **Status:** Draft\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "--no-verify", "-m", "legacy")
        legacy.write_text(legacy.read_text() + "\nMore context.\n")
        self.sync()
        self.assertEqual(self.stamp("docs/adrs/ADR-002-old.md").group(1), "unknown")

    def test_synced_changes_pass_the_commit_check(self):
        (self.root / "docs/adrs/ADR-001-db.md").write_text("# Pick the database\n\n- **Status:** Draft\n")
        spine = self.root / "docs/spines/01-INTENT.md"
        spine.write_text(spine.read_text() + "\nInvestors need plain explanations of market moves.\n")
        idx = self.root / "docs/00-INDEX.md"
        idx.write_text(idx.read_text() + "\n- [ADR-001](adrs/ADR-001-db.md)\n")
        self.sync()
        git(self.root, "add", "-A")
        from _lib.commit_gate import evaluate
        from _lib.gitview import View
        dates = [r for r in evaluate(self.root, View.staged(self.root)) if "date" in r.lower() or "Created" in r]
        self.assertEqual(dates, [])

    def test_stop_hook_syncs_dates(self):
        (self.root / "docs/adrs/ADR-001-db.md").write_text("# Pick the database\n\n- **Status:** Draft\n")
        hook(self.root, "stop", {"hook_event_name": "Stop", "stop_hook_active": False}, "--tool", "claude")
        self.assertIsNotNone(self.stamp("docs/adrs/ADR-001-db.md"))

    def test_frozen_and_append_only_files_are_never_touched(self):
        inbox = self.root / "docs/00-INBOX.md"
        inbox.write_text(inbox.read_text() + "\n- I-20261019-aaaa 2026-10-19T00:00:00Z: idea\n")
        before = inbox.read_text()
        self.sync()
        self.assertEqual(inbox.read_text(), before)


if __name__ == "__main__":
    unittest.main()


class NoGitSyncTests(unittest.TestCase):
    def test_sync_outside_git_never_touches_engine_files(self):
        from tests.helpers import doctor, install
        with TempDir() as root:
            install(root)
            (root / "docs/adrs/ADR-001-db.md").write_text("# Pick the database\n\n- **Status:** Draft\n")
            run_script("cgspec_hook.py", "doc", "sync", "--root", str(root))
            self.assertNotIn("E-ENGINE-HASH", doctor(root).stdout)
            self.assertIn("Created:", (root / "docs/adrs/ADR-001-db.md").read_text())
