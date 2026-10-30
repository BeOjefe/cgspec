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
        spine.write_text("# Intent\n\n[a](https://example.com) [b](#top) [c](02-OOUX.md#nouns) `[x](nope.md)`\n")
        self.assertPasses()

    def test_bare_path_dangling_absolute_path_warns(self):
        spine = self.root / "docs/spines/01-INTENT.md"
        spine.write_text("# Intent\n\nSee `/home/outside/some_file.md` and `~/outside/plan.json`.\n")
        result = doctor(self.root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("W-BARE-PATH", result.stdout)
        self.assertIn("dangling bare path: /home/outside/some_file.md", result.stdout)
        self.assertIn("dangling bare path: ~/outside/plan.json", result.stdout)

    def test_bare_path_dangling_relative_path_warns(self):
        spine = self.root / "docs/spines/01-INTENT.md"
        spine.write_text("# Intent\n\n- **Supersedes:** `master_plan.md:14-35`\n- **Ref:** `../missing/file.json`\n")
        result = doctor(self.root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("W-BARE-PATH", result.stdout)
        self.assertIn("dangling bare path: master_plan.md:14-35", result.stdout)
        self.assertIn("dangling bare path: ../missing/file.json", result.stdout)

    def test_bare_path_legitimate_relative_and_known_refs_pass(self):
        spine = self.root / "docs/spines/01-INTENT.md"
        spine.write_text(
            "# Intent\n\n"
            "Relative in-repo: `docs/00-INDEX.md` and `02-OOUX.md`\n"
            "Reference patterns: `SLICE-NNN`, `ADR-NNN`, `SLICE-001`, `ADR-001`, `CAP-github-browser`\n"
            "URL pattern: `https://example.com/plan.md`\n"
        )
        result = doctor(self.root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("W-BARE-PATH", result.stdout)

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

    def test_fixture_backed_integration_pass_is_rejected(self):
        write_json(self.root / "docs/_cgspec/06-evidence/manual/integration.json", {
            "schema": 1, "check": "create-team", "revision": "abc1234", "verdict": "PASS",
            "claim": "integration", "data_source": "fixture",
            "ran_at": "2026-10-24T00:00:00Z", "ran_by": "tester"})
        self.assertFails("E-EVIDENCE-SOURCE")

    def test_missing_project_json_is_reported(self):
        (self.root / "docs/_cgspec/project.json").unlink()
        result = doctor(self.root)
        self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main()


class DoctorHardeningTests(DoctorTests):
    """Regressions from the step-2 independent review."""

    def test_template_text_without_marker_is_still_empty(self):
        for spine in (self.root / "docs/spines").glob("*.md"):
            spine.write_text(spine.read_text().replace("<!-- cgspec:empty -->\n", ""))
        set_stage(self.root, "coding")
        self.assertFails("E-SPINE-EMPTY")

    def test_unknown_stage_value_is_an_error(self):
        set_stage(self.root, "Coding")
        self.assertFails("E-SCHEMA")

    def test_unlisted_snapshot_fails(self):
        (self.root / "docs/prototypes/_snapshots/home-v2.html").write_text("<html>sneaky</html>")
        self.assertFails("E-FROZEN-UNLISTED")

    def test_frozen_path_outside_root_is_rejected_and_never_touched(self):
        victim = self.root.parent / f"{self.root.name}-victim.txt"
        victim.write_text("outside\n")
        os.chmod(victim, 0o644)
        try:
            path = self.root / "docs/_cgspec/07-state/frozen.json"
            data = json.loads(path.read_text())
            data["entries"].append({"path": f"../{victim.name}", "sha256": hashlib.sha256(b"outside\n").hexdigest(),
                                    "kind": "snapshot", "added": "2026-10-18T00:00:00Z", "reason": "escape"})
            write_json(path, data)
            self.assertFails("E-SCHEMA", "--fix")
            self.assertTrue(victim.stat().st_mode & 0o200, "--fix must not chmod outside the project")
        finally:
            victim.unlink()

    def test_unregistered_script_variants_fail(self):
        for name in ("gen.PY", "gen.pyw", "notebook.ipynb", "run.BAT"):
            with self.subTest(name=name):
                target = self.root / "docs/prototypes" / name
                target.write_text("x\n")
                self.assertFails("E-SCRIPT-UNREGISTERED")
                target.unlink()

    def test_extensionless_shebang_script_fails(self):
        target = self.root / "docs/prototypes/regen"
        target.write_text("#!/usr/bin/env python3\nprint('x')\n")
        self.assertFails("E-SCRIPT-UNREGISTERED")

    def test_prototype_browser_js_is_allowed(self):
        screen = self.root / "docs/prototypes/home"
        screen.mkdir()
        (screen / "index.html").write_text("<html></html>")
        (screen / "components.js").write_text("export const x = 1;\n")
        self.assertPasses()

    def test_script_outside_allowed_places_warns(self):
        (self.root / "tools").mkdir()
        (self.root / "tools/hack.py").write_text("print('x')\n")
        result = self.assertPasses()
        self.assertIn("W-SCRIPT-OUTSIDE", result.stdout)

    def test_nested_folder_in_records_fails(self):
        (self.root / "docs/adrs/sub").mkdir()
        (self.root / "docs/adrs/sub/anything.md").write_text("x\n")
        self.assertFails("E-LAYOUT-UNKNOWN")

    def test_method_doc_not_allowed_in_projects(self):
        (self.root / "docs/METHOD.md").write_text("x\n")
        self.assertFails("E-LAYOUT-UNKNOWN")

    def test_link_variants(self):
        spines = self.root / "docs/spines"
        (spines / "my file.md").write_text("x\n")
        (spines / "f(1).md").write_text("x\n")
        ok = "[a](<my file.md>) [b](my%20file.md) [c](f(1).md) [d][ref]\n\n[ref]: 02-OOUX.md\n"
        (spines / "01-INTENT.md").write_text("# Intent\n\n" + ok)
        result = doctor(self.root)
        self.assertNotIn("E-LINK", result.stdout)
        for bad in ("[a](<missing file.md>)", "[c][r]\n\n[r]: ./nope.md", '<a href="gone.html">x</a>'):
            with self.subTest(bad=bad):
                (spines / "01-INTENT.md").write_text("# Intent\n\n" + bad + "\n")
                self.assertFails("E-LINK")

    def test_one_bad_file_does_not_hide_other_findings(self):
        (self.root / "docs/adrs/ADR-001-bad.md").write_bytes(b"\xff\xfe\x00 not utf8")
        (self.root / "docs/random.md").write_text("x\n")
        result = self.assertFails("E-ENCODING")
        self.assertIn("E-LAYOUT-UNKNOWN", result.stdout)
        self.assertNotIn("internal error", result.stderr)

    def test_malformed_engine_manifest_is_a_finding(self):
        write_json(self.root / "docs/_cgspec/01-engine/manifest.json", {"schema": 1, "files": []})
        result = self.assertFails("E-ENGINE-HASH")
        self.assertNotIn("Traceback", result.stderr)


class DoctorRecheckTests(unittest.TestCase):
    """Regressions from the step-2 re-verification."""

    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        install(self.root)

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def fails(self, code):
        result = doctor(self.root)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn(code, result.stdout)

    def no_errors(self):
        result = doctor(self.root)
        self.assertEqual(result.returncode, 0, result.stdout)
        return result

    def test_placeholder_spines_are_empty(self):
        for spine in (self.root / "docs/spines").glob("*.md"):
            spine.write_text(spine.read_text().replace("<!-- cgspec:empty -->", "TBD"))
        set_stage(self.root, "coding")
        self.fails("E-SPINE-EMPTY")

    def test_real_spine_content_counts(self):
        set_stage(self.root, "design")
        text = ("# Intent\n\nMEOCE helps retail investors in Casablanca read BRVM and BVC market data quickly, "
                "with plain explanations and alerts they can trust.\n")
        (self.root / "docs/spines/01-INTENT.md").write_text(text)
        (self.root / "docs/spines/02-OOUX.md").write_text(
            "# Domain\n\nNouns: Instrument (ticker, market, sector), Quote (price, time), Watchlist (owner, "
            "instruments), Alert (rule, channel). A Watchlist belongs to one User.\n")
        self.no_errors()

    def test_node_script_in_screen_folder_fails(self):
        screen = self.root / "docs/prototypes/home"
        screen.mkdir()
        (screen / "generate_v15_screenshots.js").write_text(
            "const { chromium } = require('playwright');\n(async () => { await chromium.launch(); })();\n")
        self.fails("E-SCRIPT-UNREGISTERED")

    def test_node_import_in_screen_folder_fails(self):
        screen = self.root / "docs/prototypes/home"
        screen.mkdir()
        (screen / "shot.mjs").write_text("import fs from 'node:fs';\nfs.writeFileSync('x', 'y');\n")
        self.fails("E-SCRIPT-UNREGISTERED")

    def test_browser_ts_and_vision_assets_pass(self):
        screen = self.root / "docs/prototypes/home"
        screen.mkdir()
        (screen / "app.ts").write_text("export const title: string = 'Home';\n")
        (self.root / "docs/prototypes/_vision/clip.js").write_text("document.body.classList.add('x');\n")
        self.no_errors()

    def test_executable_non_script_files_are_fine(self):
        for rel in ("docs/00-INBOX.md", "docs/_cgspec/07-state/tier.json"):
            os.chmod(self.root / rel, 0o755)
        self.no_errors()

    def test_stray_files_in_prototypes_root_and_evidence_fail(self):
        (self.root / "docs/prototypes/random.txt").write_text("x\n")
        self.fails("E-LAYOUT-UNKNOWN")
        (self.root / "docs/prototypes/random.txt").unlink()
        (self.root / "docs/_cgspec/06-evidence/x").mkdir()
        (self.root / "docs/_cgspec/06-evidence/x/blob.bin").write_bytes(b"\x00\x01")
        self.fails("E-LAYOUT-UNKNOWN")

    def test_footnotes_are_not_links(self):
        (self.root / "docs/spines/01-INTENT.md").write_text("# Intent\n\nA claim.[^1]\n\n[^1]: Source is the 2025 report.\n")
        result = doctor(self.root)
        self.assertNotIn("E-LINK", result.stdout)

    def test_each_finding_reported_once(self):
        (self.root / "docs/adrs/ADR-001-bad.md").write_bytes(b"\xff\xfe not utf8")
        result = doctor(self.root)
        self.assertEqual(result.stdout.count("E-ENCODING docs/adrs/ADR-001-bad.md"), 1)


class PrototypeCodeRuleTests(unittest.TestCase):
    """Grey prototypes are plain browser pages: imports must be relative paths or full URLs."""

    EVASIONS = [
        "const { chromium } = await import(`playwright`);",
        'const m = await import("play" + "wright");',
        'import sharp from "sharp";',
        'globalThis["process"].exit(0);',
        "Bun.write('x', 'y');",
        "Deno.writeTextFile('x', 'y');",
        "const p = require('path');",
        "import { pathToRegexp } from 'path-to-regexp';",
    ]
    ALLOWED = [
        "import { render } from './render.js';",
        "import '../shared/shell.js';",
        "import { h } from 'https://esm.sh/preact@10.19.3';",
        "export { x } from './x.js';",
        "const mod = await import('./lazy.js');",
        "document.querySelector('#app').textContent = 'process the order';",
    ]

    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        install(self.root)
        (self.root / "docs/prototypes/home").mkdir()

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def check(self, code):
        (self.root / "docs/prototypes/home/app.js").write_text(code + "\n")
        return doctor(self.root)

    def test_node_or_package_code_is_a_script(self):
        for code in self.EVASIONS:
            with self.subTest(code=code):
                result = self.check(code)
                self.assertIn("E-SCRIPT-UNREGISTERED", result.stdout)

    def test_plain_browser_code_passes(self):
        for code in self.ALLOWED:
            with self.subTest(code=code):
                result = self.check(code)
                self.assertNotIn("E-SCRIPT-UNREGISTERED", result.stdout)
