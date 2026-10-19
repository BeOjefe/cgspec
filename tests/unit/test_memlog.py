"""memlog.py: collision-free IDs, locking, duplicate detection, permissions, legacy compatibility."""

from __future__ import annotations

import os
import re
import stat
import subprocess
import sys
import threading
import unittest
from pathlib import Path

from tests.helpers import TempDir, run_script, write_json

NEW_ID = re.compile(r"^### \[(M-\d{8}-[0-9a-f]{4})\]", re.M)
ANY_ID = re.compile(r"^### \[([^\]]+)\]", re.M)

LEGACY = """# Project Memory Log (_memlog.md)

### [M-001] 2026-09-01T10:00:00Z | tags: setup | owner: @a | perms: public
- **Summary:** first

### [M-002] 2026-09-02T10:00:00Z | tags: design | owner: @a | perms: public
- **Summary:** second

### [M-002] 2026-09-03T10:00:00Z | tags: design | owner: @b | perms: public
- **Summary:** duplicate written by the old counter bug

### [M-003] broken header without fields
- **Summary:** malformed
"""


def make_project(root: Path) -> None:
    write_json(root / "docs/_cgspec/project.json", {"schema": 1})


def add(root: Path, *extra: str):
    return run_script("memlog.py", "--root", str(root), "add", "--summary", "s", "--tags", "t", *extra)


class MemlogTests(unittest.TestCase):
    def test_add_creates_file_with_new_style_id(self):
        with TempDir() as root:
            make_project(root)
            result = add(root, "--details", "why", "--status", "Delegated", "--links", "ADR-004")
            self.assertEqual(result.returncode, 0, result.stderr)
            text = (root / "docs/_memlog.md").read_text()
            self.assertEqual(len(NEW_ID.findall(text)), 1)
            self.assertIn("- **Status:** Delegated", text)
            self.assertIn("- **Links:** ADR-004", text)

    def test_ids_unique_across_many_adds(self):
        with TempDir() as root:
            make_project(root)
            for _ in range(25):
                self.assertEqual(add(root).returncode, 0)
            ids = NEW_ID.findall((root / "docs/_memlog.md").read_text())
            self.assertEqual(len(ids), 25)
            self.assertEqual(len(set(ids)), 25)

    def test_parallel_adds_do_not_lose_or_duplicate_entries(self):
        with TempDir() as root:
            make_project(root)
            results = []
            threads = [threading.Thread(target=lambda: results.append(add(root))) for _ in range(8)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            self.assertTrue(all(r.returncode == 0 for r in results), [r.stderr for r in results])
            ids = NEW_ID.findall((root / "docs/_memlog.md").read_text())
            self.assertEqual(len(ids), 8)
            self.assertEqual(len(set(ids)), 8)

    def test_add_to_legacy_log_never_reuses_an_id(self):
        # Regression: the live counter used len(entries)+1 and produced duplicates.
        with TempDir() as root:
            make_project(root)
            (root / "docs").mkdir(exist_ok=True)
            (root / "docs/_memlog.md").write_text(LEGACY)
            self.assertEqual(add(root).returncode, 0)
            ids = ANY_ID.findall((root / "docs/_memlog.md").read_text())
            self.assertEqual(ids.count(ids[-1]), 1)
            self.assertRegex(ids[-1], r"^M-\d{8}-[0-9a-f]{4}$")

    def test_check_reports_duplicates_and_malformed_headers(self):
        with TempDir() as root:
            make_project(root)
            (root / "docs").mkdir(exist_ok=True)
            (root / "docs/_memlog.md").write_text(LEGACY)
            result = run_script("memlog.py", "--root", str(root), "check")
            self.assertEqual(result.returncode, 1)
            self.assertIn("duplicate id M-002", result.stdout)
            self.assertIn("malformed header", result.stdout)

    def test_check_passes_on_clean_log(self):
        with TempDir() as root:
            make_project(root)
            add(root)
            add(root)
            result = run_script("memlog.py", "--root", str(root), "check")
            self.assertEqual(result.returncode, 0, result.stdout)

    def test_keeps_file_permissions(self):
        with TempDir() as root:
            make_project(root)
            add(root)
            log = root / "docs/_memlog.md"
            os.chmod(log, 0o640)
            add(root)
            self.assertEqual(stat.S_IMODE(log.stat().st_mode), 0o640)

    def test_leftover_lock_file_does_not_block(self):
        # A crashed writer leaves the file but no OS lock; the next writer proceeds.
        with TempDir() as root:
            make_project(root)
            lock = root / "docs/.memlog.lock"
            lock.parent.mkdir(parents=True, exist_ok=True)
            lock.write_text("999999")
            self.assertEqual(add(root).returncode, 0)

    def test_held_lock_blocks_with_timeout(self):
        with TempDir() as root:
            make_project(root)
            (root / "docs").mkdir(exist_ok=True)
            holder = subprocess.Popen([sys.executable, "-c", (
                "import fcntl,sys,time;f=open(sys.argv[1],'a');fcntl.flock(f,fcntl.LOCK_EX);"
                "print('held',flush=True);time.sleep(5)"), str(root / "docs/.memlog.lock")],
                stdout=subprocess.PIPE, text=True)
            try:
                self.assertEqual(holder.stdout.readline().strip(), "held")
                result = run_script("memlog.py", "--root", str(root), "add", "--summary", "s",
                                    "--tags", "t", "--lock-timeout", "0.5")
                self.assertEqual(result.returncode, 3)
                self.assertIn("locked", result.stderr)
            finally:
                holder.kill()
                holder.wait()

    def test_rejects_newlines_in_header_fields(self):
        with TempDir() as root:
            make_project(root)
            result = run_script("memlog.py", "--root", str(root), "add", "--summary", "s", "--tags", "a\n### [M-1]")
            self.assertEqual(result.returncode, 1)
            self.assertFalse((root / "docs/_memlog.md").exists())

    def test_rejects_pipe_in_tags(self):
        with TempDir() as root:
            make_project(root)
            self.assertEqual(add(root, "--owner", "@a | perms: secret").returncode, 1)

    def test_rejects_unknown_status(self):
        with TempDir() as root:
            make_project(root)
            self.assertEqual(add(root, "--status", "Maybe").returncode, 2)  # argparse usage error

    def test_export_since_id(self):
        with TempDir() as root:
            make_project(root)
            add(root)
            first = NEW_ID.findall((root / "docs/_memlog.md").read_text())[0]
            add(root)
            add(root)
            out = root / "export.md"
            result = run_script("memlog.py", "--root", str(root), "export", "--since", first, "--out", str(out))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(NEW_ID.findall(out.read_text())), 2)

    def test_missing_project_is_an_error(self):
        with TempDir() as root:
            result = run_script("memlog.py", "add", "--summary", "s", "--tags", "t", cwd=root)
            self.assertEqual(result.returncode, 1)
            self.assertIn("project.json", result.stderr)


if __name__ == "__main__":
    unittest.main()


class MemlogHardeningTests(unittest.TestCase):
    def test_details_cannot_inject_entries(self):
        with TempDir() as root:
            make_project(root)
            forged = "x\n### [M-20261018-dead] 2026-10-18T00:00:00Z | tags: t | owner: @you | perms: public"
            result = add(root, "--details", forged)
            self.assertEqual(result.returncode, 1)
            self.assertFalse((root / "docs/_memlog.md").exists())

    def test_details_cannot_forge_field_lines(self):
        with TempDir() as root:
            make_project(root)
            self.assertEqual(add(root, "--details", "x\n- **Status:** Approved").returncode, 1)

    def test_multiline_details_are_indented(self):
        with TempDir() as root:
            make_project(root)
            self.assertEqual(add(root, "--details", "line one\nline two").returncode, 0)
            text = (root / "docs/_memlog.md").read_text()
            self.assertIn("- **Details:** line one\n  line two\n", text)
            self.assertEqual(run_script("memlog.py", "--root", str(root), "check").returncode, 0)

    def test_bad_repo_prefix_rejected(self):
        with TempDir() as root:
            make_project(root)
            self.assertEqual(add(root, "--repo-prefix", "API").returncode, 1)
            self.assertEqual(add(root, "--repo-prefix", "a]b").returncode, 1)
            self.assertEqual(add(root, "--repo-prefix", "api").returncode, 0)

    def test_approved_status_needs_an_approval_reference(self):
        with TempDir() as root:
            make_project(root)
            self.assertEqual(add(root, "--status", "Approved").returncode, 1)
            write_json(root / "docs/_cgspec/07-state/approvals.json", {"schema": 1, "approvals": [
                {"id": "A-20261018-aaaa", "at": "2026-10-18T00:00:00Z", "excerpt": "approve decision: s",
                 "sha256": "0" * 64}]})
            ok = add(root, "--status", "Approved", "--approval-ref", "A-20261018-aaaa")
            self.assertEqual(ok.returncode, 0, ok.stderr)
            self.assertIn("- **Approval:** A-20261018-aaaa", (root / "docs/_memlog.md").read_text())

    def test_unrelated_approval_cannot_create_approved_decision(self):
        with TempDir() as root:
            make_project(root)
            write_json(root / "docs/_cgspec/07-state/approvals.json", {"schema": 1, "approvals": [
                {"id": "A-20261018-aaaa", "at": "2026-10-18T00:00:00Z", "excerpt": "yes, rename README",
                 "sha256": "0" * 64}]})
            bad = add(root, "--status", "Approved", "--approval-ref", "A-20261018-aaaa")
            self.assertEqual(bad.returncode, 1)
            self.assertIn("decision: s", bad.stderr)
            self.assertFalse((root / "docs/_memlog.md").exists())

    def test_read_only_ledger_reports_cleanly(self):
        with TempDir() as root:
            make_project(root)
            add(root)
            log = root / "docs/_memlog.md"
            os.chmod(log, 0o444)
            result = add(root)
            os.chmod(log, 0o644)
            self.assertEqual(result.returncode, 3)
            self.assertNotIn("Traceback", result.stderr)
