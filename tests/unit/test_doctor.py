"""doctor.py: passes a clean install, fails on every seeded defect, read-only unless --fix."""

from __future__ import annotations

import hashlib
import json
import os
import unittest
from pathlib import Path

from tests.helpers import TempDir, doctor, install, snapshot_tree, write_json

ADR = "# ADR-001: Pick the database\n\n- **Status:** Proposed\n\nContext.\n"
SLICE = "# SLICE-001: Login\n\n- **Status:** Approved\n\nScope: src/login/**\n"


def add_adr(root: Path, name: str = "ADR-001-database.md", body: str = ADR, index: bool = True) -> None:
    (root / "docs/adrs" / name).write_text(body)
    if index:
        idx = root / "docs/00-INDEX.md"
        idx.write_text(idx.read_text() + f"\n- [{name}](adrs/{name})\n")


def set_stage(root: Path, stage: str) -> None:
    path = root / "docs/_cgspec/07-state/checkpoint.json"
    data = json.loads(path.read_text())
    data["stages"] = {"web": stage}
    write_json(path, data)


def freeze(root: Path, rel: str, content: str) -> None:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    path = root / "docs/_cgspec/07-state/frozen.json"
    data = json.loads(path.read_text())
    data["entries"].append({"path": rel, "sha256": hashlib.sha256(content.encode()).hexdigest(),
                            "kind": "snapshot", "added": "2026-10-18T00:00:00Z", "reason": "layer 3 locked"})
    write_json(path, data)
    os.chmod(target, 0o444)


class DoctorTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        result = install(self.root)
        self.assertEqual(result.returncode, 0, result.stderr)

    def tearDown(self):
        for path in self.root.rglob("*"):
            if path.is_file() and not path.is_symlink():
                os.chmod(path, 0o644)
        self._tmp.__exit__(None, None, None)

    def assertFails(self, code: str, *extra: str):
        result = doctor(self.root, *extra)
        self.assertEqual(result.returncode, 1, f"expected failure {code}\n{result.stdout}{result.stderr}")
        self.assertIn(code, result.stdout)
        return result

    def assertPasses(self):
        result = doctor(self.root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    # --- clean cases -------------------------------------------------------------------
    def test_clean_project_with_records_passes(self):
        add_adr(self.root)
        (self.root / "docs/slices/SLICE-001-login.md").write_text(SLICE)
        idx = self.root / "docs/00-INDEX.md"
        idx.write_text(idx.read_text() + "- [SLICE-001](slices/SLICE-001-login.md)\n")
        self.assertPasses()

    def test_empty_spines_are_only_a_warning_while_brainstorming(self):
        result = self.assertPasses()
        self.assertIn("W-SPINE-EMPTY", result.stdout)

    def test_read_only_by_default(self):
        add_adr(self.root, index=False)
        before = snapshot_tree(self.root)
        doctor(self.root)
        self.assertEqual(snapshot_tree(self.root), before)

    def test_json_output(self):
        result = doctor(self.root, "--json")
        data = json.loads(result.stdout)
        self.assertEqual(data["errors"], 0)
        self.assertIsInstance(data["findings"], list)

    # --- seeded defects (smoke test item 2) -------------------------------------------
    def test_empty_spine_past_its_stage_fails(self):
        set_stage(self.root, "architecture")
        self.assertFails("E-SPINE-EMPTY")

    def test_duplicate_ledger_ids_fail(self):
        log = self.root / "docs/_memlog.md"
        entry = "\n### [M-20261018-aaaa] 2026-10-18T00:00:00Z | tags: x | owner: @a | perms: public\n- **Summary:** s\n"
        log.write_text(log.read_text() + entry + entry)
        self.assertFails("E-MEMLOG")

    def test_index_only_adr_fails(self):
        idx = self.root / "docs/00-INDEX.md"
        idx.write_text(idx.read_text() + "\n- [ADR-009](adrs/ADR-009-ghost.md)\n")
        self.assertFails("E-INDEX-ORPHAN")

    def test_adr_missing_from_index_fails_and_fix_repairs_it(self):
        add_adr(self.root, index=False)
        self.assertFails("E-INDEX-MISSING")
        fixed = doctor(self.root, "--fix")
        self.assertEqual(fixed.returncode, 0, fixed.stdout)
        self.assertIn("adrs/ADR-001-database.md", (self.root / "docs/00-INDEX.md").read_text())
        self.assertPasses()

    def test_broken_link_fails(self):
        spine = self.root / "docs/spines/01-INTENT.md"
        spine.write_text("# Intent\n\nSee [the brief](../missing/brief.md).\n")
        self.assertFails("E-LINK")

    def test_links_to_urls_and_anchors_are_fine(self):
        spine = self.root / "docs/spines/01-INTENT.md"
        spine.write_text("# Intent\n\n[a](https://example.com) [b](#top) [c](02-DOMAIN.md#nouns) `[x](nope.md)`\n")
        self.assertPasses()

    def test_edited_frozen_snapshot_fails(self):
        rel = "docs/prototypes/_snapshots/home-v1.html"
        freeze(self.root, rel, "<html>v1</html>")
        self.assertPasses()
        os.chmod(self.root / rel, 0o644)
        (self.root / rel).write_text("<html>edited by an agent</html>")
        self.assertFails("E-FROZEN-HASH")

    def test_missing_frozen_file_fails(self):
        rel = "docs/prototypes/_snapshots/home-v1.html"
        freeze(self.root, rel, "<html>v1</html>")
        os.chmod(self.root / rel, 0o644)
        (self.root / rel).unlink()
        self.assertFails("E-FROZEN-MISSING")

    def test_writable_frozen_file_warns(self):
        rel = "docs/prototypes/_snapshots/home-v1.html"
        freeze(self.root, rel, "<html>v1</html>")
        os.chmod(self.root / rel, 0o644)
        result = self.assertPasses()
        self.assertIn("W-FROZEN-WRITABLE", result.stdout)

    def test_unregistered_script_in_docs_fails(self):
        # The CortexGate incident: an ad-hoc generator dropped into the docs tree.
        (self.root / "docs/prototypes/generate_v15_screenshots.py").write_text("print('x')\n")
        self.assertFails("E-SCRIPT-UNREGISTERED")

    def test_unregistered_check_fails(self):
        (self.root / "docs/_cgspec/04-checks/no_hex.py").write_text("print('x')\n")
        self.assertFails("E-SCRIPT-UNREGISTERED")

    def test_registered_check_with_wrong_hash_fails(self):
        check = self.root / "docs/_cgspec/04-checks/no_hex.py"
        check.write_text("print('x')\n")
        manifest = self.root / "docs/_cgspec/04-checks/manifest.json"
        write_json(manifest, {"schema": 1, "checks": [{
            "id": "CHK-001", "path": "docs/_cgspec/04-checks/no_hex.py", "sha256": "0" * 64,
            "command": ["python3", "{path}"], "applies_to": ["src/**"],
            "approval": {"source": "commit-trailer", "ref": "abc1234", "at": "2026-10-18T00:00:00Z"},
            "added": "2026-10-18T00:00:00Z"}]})
        self.assertFails("E-CHECK-HASH")

    def test_tampered_engine_fails(self):
        engine = self.root / "docs/_cgspec/01-engine/doctor.py"
        engine.write_text(engine.read_text() + "\n# skip everything\n")
        self.assertFails("E-ENGINE-HASH")

    def test_invalid_state_file_fails(self):
        write_json(self.root / "docs/_cgspec/07-state/tier.json", {"schema": 1, "active": {"tier": "T9"}})
        self.assertFails("E-SCHEMA")

    def test_corrupt_json_fails(self):
        (self.root / "docs/_cgspec/07-state/frozen.json").write_text("{not json")
        self.assertFails("E-SCHEMA")

    def test_unknown_entry_in_docs_fails(self):
        (self.root / "docs/random-notes.md").write_text("x\n")
        self.assertFails("E-LAYOUT-UNKNOWN")

    def test_unknown_state_file_fails(self):
        (self.root / "docs/_cgspec/07-state/notes.txt").write_text("x\n")
        self.assertFails("E-LAYOUT-UNKNOWN")

    def test_missing_required_file_fails(self):
        (self.root / "docs/00-INBOX.md").unlink()
        self.assertFails("E-LAYOUT-MISSING")

    def test_symlink_fails(self):
        os.symlink(self.root / "docs/00-INDEX.md", self.root / "docs/_cgspec/02-research/link.md")
        self.assertFails("E-SYMLINK")

    def test_bad_record_name_fails(self):
        add_adr(self.root, name="adr-1-db.md")
        self.assertFails("E-NAME")

    def test_duplicate_adr_number_fails(self):
        add_adr(self.root)
        add_adr(self.root, name="ADR-001-other.md")
        self.assertFails("E-ID-DUP")

    def test_invalid_status_fails(self):
        add_adr(self.root, body="# ADR-001\n\n- **Status:** Maybe\n")
        self.assertFails("E-STATUS")

    def test_missing_status_fails(self):
        add_adr(self.root, body="# ADR-001\n\nNo status line.\n")
        self.assertFails("E-STATUS")

    def test_invalid_run_json_fails(self):
        write_json(self.root / "docs/_cgspec/05-runs/R-20261018-abcd/run.json", {"schema": 1, "run_id": "x"})
        self.assertFails("E-SCHEMA")

    def test_blocked_evidence_is_counted(self):
        write_json(self.root / "docs/_cgspec/06-evidence/SLICE-001/review.json", {
            "schema": 1, "check": "review", "revision": "abc1234", "verdict": "BLOCKED",
            "ran_at": "2026-10-18T00:00:00Z", "ran_by": "reviewer"})
        result = self.assertPasses()
        self.assertIn("W-BLOCKED", result.stdout)
        self.assertIn("1 unresolved", result.stdout)

    def test_missing_project_json_is_reported(self):
        (self.root / "docs/_cgspec/project.json").unlink()
        result = doctor(self.root)
        self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main()
