"""impact.py (spec 9 change flow): plain-code impact map from index links, read-only."""

from __future__ import annotations

import hashlib
import json
import os
import unittest

from tests.helpers import TempDir, git_project, make_slice, run_script, snapshot_tree, write_json


def impact(root, *args):
    return run_script("impact.py", *args, "--root", str(root), "--json")


class ImpactTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.root = r = self._tmp.__enter__()
        git_project(r)
        (r / "docs/spines/02-OOUX.md").write_text("# OOUX\n\n## Invoice\n\nAn invoice has lines.\n")
        (r / "docs/spines/03-EXPERIENCE.md").write_text(
            "# Experience\n\nThe [invoice](02-OOUX.md#invoice) screen lists lines; see ADR-001.\n")
        (r / "docs/adrs").mkdir(exist_ok=True)
        (r / "docs/adrs/ADR-001-storage.md").write_text("# ADR-001: Storage\n\nInvoices are stored as rows.\n")
        (r / "docs/adrs/ADR-002-unrelated.md").write_text("# ADR-002: Fonts\n\nUse system fonts.\n")
        (r / "docs/slices").mkdir(exist_ok=True)
        make_slice(r, scope="src/invoice/**", index=False)
        slice_path = r / "docs/slices/SLICE-001-login.md"
        slice_path.write_text(slice_path.read_text() + "\nImplements [the screen](../spines/03-EXPERIENCE.md).\n")
        (r / "src/invoice").mkdir(parents=True, exist_ok=True)
        (r / "src/invoice/list.ts").write_text("export const x = 1;\n")
        (r / "src/other.ts").write_text("export const y = 2;\n")
        write_json(r / "docs/_cgspec/06-evidence/review/invoice-ui.json",
                   {"schema": 1, "check": "invoice-ui", "verdict": "PASS", "state": "Fresh",
                    "covers": ["src/invoice/**"]})
        write_json(r / "docs/_cgspec/06-evidence/review/fonts.json",
                   {"schema": 1, "check": "fonts", "verdict": "PASS", "state": "Fresh", "covers": ["src/fonts/**"]})
        snap = r / "docs/prototypes/_snapshots/invoice-v1.html"
        snap.parent.mkdir(parents=True, exist_ok=True)
        snap.write_text("<html>v1</html>")
        frozen = r / "docs/_cgspec/07-state/frozen.json"
        data = json.loads(frozen.read_text()) if frozen.exists() else {"schema": 1, "entries": []}
        data["entries"].append({"path": "docs/prototypes/_snapshots/invoice-v1.html",
                                "sha256": hashlib.sha256(snap.read_bytes()).hexdigest(), "kind": "snapshot",
                                "added": "2026-10-19T00:00:00Z", "reason": "milestone 1"})
        os.chmod(frozen, 0o644) if frozen.exists() else None
        write_json(frozen, data)

    def tearDown(self):
        for p in self.root.rglob("*"):
            if p.is_file() and not p.is_symlink():
                os.chmod(p, 0o644)
        self._tmp.__exit__(None, None, None)

    def map(self, *args):
        result = impact(self.root, *args)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_changed_noun_reaches_linked_records_code_and_evidence(self):
        data = self.map("docs/spines/02-OOUX.md")
        records = {r["path"] for r in data["records"]}
        self.assertIn("docs/spines/03-EXPERIENCE.md", records)
        self.assertIn("docs/slices/SLICE-001-login.md", records)  # links to experience (2 hops)
        self.assertNotIn("docs/adrs/ADR-002-unrelated.md", records)
        self.assertIn("src/invoice/list.ts", data["code"])
        self.assertNotIn("src/other.ts", data["code"])
        self.assertEqual([e["path"] for e in data["evidence"]], ["docs/_cgspec/06-evidence/review/invoice-ui.json"])

    def test_record_id_seed_follows_id_mentions(self):
        data = self.map("ADR-001")
        self.assertIn("docs/spines/03-EXPERIENCE.md", {r["path"] for r in data["records"]})
        self.assertEqual(data["seeds"], ["docs/adrs/ADR-001-storage.md"])

    def test_term_seed_finds_documents_naming_the_noun(self):
        data = self.map("--term", "invoice")
        seeds = set(data["seeds"])
        self.assertTrue({"docs/spines/02-OOUX.md", "docs/adrs/ADR-001-storage.md"} <= seeds)
        self.assertNotIn("docs/adrs/ADR-002-unrelated.md", seeds)

    def test_code_seed_reaches_slice_evidence_and_frozen_baselines_for_screen(self):
        data = self.map("src/invoice/list.ts", "--screen", "invoice")
        self.assertIn("docs/slices/SLICE-001-login.md", {r["path"] for r in data["records"]})
        self.assertEqual([f["path"] for f in data["frozen"]], ["docs/prototypes/_snapshots/invoice-v1.html"])
        self.assertIn("docs/_cgspec/06-evidence/review/invoice-ui.json", {e["path"] for e in data["evidence"]})

    def test_depth_limits_hops(self):
        data = self.map("docs/spines/02-OOUX.md", "--depth", "1")
        self.assertNotIn("docs/slices/SLICE-001-login.md", {r["path"] for r in data["records"]})

    def test_read_only_and_human_output(self):
        before = snapshot_tree(self.root)
        human = run_script("impact.py", "docs/spines/02-OOUX.md", "--root", str(self.root))
        self.assertEqual(human.returncode, 0, human.stderr)
        self.assertIn("Impact map", human.stdout)
        self.assertIn("03-EXPERIENCE.md", human.stdout)
        self.assertEqual(snapshot_tree(self.root), before)

    def test_unknown_seed_is_an_error(self):
        result = impact(self.root, "ADR-999")
        self.assertEqual(result.returncode, 1)
        self.assertIn("ADR-999", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
