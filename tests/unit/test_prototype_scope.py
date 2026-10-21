"""Executable prototype changes obey scope in hooks and CI; prose stays cheap."""
from __future__ import annotations

import unittest

from tests.helpers import (
    TempDir, claude_payload, git, git_project, hook, make_slice, run_script,
    set_test_command, write_json,
)


class PrototypeScopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TempDir()
        self.root = self.tmp.__enter__()
        git_project(self.root)
        self.base = git(self.root, "rev-parse", "HEAD").stdout.strip()

    def tearDown(self):
        self.tmp.__exit__(None, None, None)

    def put(self, rel, text="export const ready = true;\n"):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def tier(self, kind="T1", scope="docs/prototypes/files/**, tests/**"):
        if kind == "T0":
            return run_script("cgspec_hook.py", "tier", "set", "--root", str(self.root),
                              "--tier", kind, "--reason", "correct prototype style",
                              "--files", "docs/prototypes/files/style.css")
        make_slice(self.root, scope=scope)
        return run_script("cgspec_hook.py", "tier", "set", "--root", str(self.root),
                          "--tier", kind, "--reason", "prototype behavior", "--slice", "SLICE-001")

    def pretool(self, rel, tool="Write"):
        payload = claude_payload(self.root, tool, file_path=rel,
                                content="export const ready = true;",
                                old_string="false", new_string="true")
        return hook(self.root, "pre-tool", payload, "--tool", "claude")

    def commit_gate(self):
        git(self.root, "add", "-A")
        return hook(self.root, "pre-commit", None, "--tool", "git")

    def test_new_prototype_assets_need_scope_before_write(self):
        for suffix in ("js", "mjs", "tsx", "html", "css", "svg", "json"):
            with self.subTest(suffix=suffix):
                result = self.pretool("docs/prototypes/files/new." + suffix)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn("tier", result.stderr)

    def test_existing_prototype_edit_and_shell_write_need_scope(self):
        rel = "docs/prototypes/files/app.js"
        self.put(rel)
        self.assertEqual(self.pretool(rel, "Edit").returncode, 2)
        result = hook(self.root, "pre-tool",
                      claude_payload(self.root, "Bash", command="echo changed > " + rel),
                      "--tool", "claude")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

    def test_t1_allows_only_declared_prototype_paths(self):
        self.assertEqual(self.tier().returncode, 0)
        self.assertEqual(self.pretool("docs/prototypes/files/app.js").returncode, 0)
        result = self.pretool("docs/prototypes/other/app.js")
        self.assertEqual(result.returncode, 2)
        self.assertIn("outside the scope", result.stderr)

    def test_t0_existing_style_edit_is_allowed_but_new_asset_is_not(self):
        self.put("docs/prototypes/files/style.css", "body { color: black; }\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "baseline prototype style")
        self.assertEqual(self.tier("T0").returncode, 0)
        self.assertEqual(self.pretool("docs/prototypes/files/style.css", "Edit").returncode, 0)
        self.assertEqual(self.pretool("docs/prototypes/files/new.js").returncode, 2)
        self.put("docs/prototypes/files/style.css", "body { color: navy; }\n")
        result = self.commit_gate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_prose_and_scratch_remain_exempt(self):
        for rel in ("docs/spines/01-INTENT.md", "docs/prototypes/files/README.md",
                    ".cgspec-scratch/probe.js"):
            with self.subTest(rel=rel):
                self.assertEqual(self.pretool(rel).returncode, 0)

    def test_unscoped_prototype_commit_is_blocked(self):
        self.put("docs/prototypes/files/app.js")
        result = self.commit_gate()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("no change tier", result.stdout)

    def test_ci_rejects_prototype_commit_that_bypassed_local_hook(self):
        self.put("docs/prototypes/files/app.js")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "unscoped prototype")
        result = hook(self.root, "ci", None, "--tool", "git", "--base", self.base)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("no change tier", result.stdout)

    def test_prototype_t1_requires_behavior_test_evidence(self):
        self.tier()
        self.put("docs/prototypes/files/app.js")
        result = self.commit_gate()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("without a failing-test record", result.stdout)

    def test_honest_prototype_test_pair_passes_commit_and_ci(self):
        self.tier()
        set_test_command(self.root, ["python3", "{test_file}"])
        self.put("tests/check_prototype.py",
                 "from pathlib import Path\nassert Path('docs/prototypes/files/index.html').exists()\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "approved scope and failing behavior check")
        failed_at = git(self.root, "rev-parse", "HEAD").stdout.strip()
        write_json(self.root / "docs/_cgspec/06-evidence/tests/prototype.json", {
            "schema": 1, "test_id": "prototype-ready", "test_file": "tests/check_prototype.py",
            "command": ["python3", "tests/check_prototype.py"], "failed_at": failed_at,
            "passed_at": None, "covers": ["docs/prototypes/files/index.html"],
            "slice": "SLICE-001", "recorded": "2026-10-21T00:00:00Z",
        })
        self.put("docs/prototypes/files/index.html", "<main>Ready</main>\n")
        result = self.commit_gate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        git(self.root, "commit", "-q", "-m", "implement prototype with evidence")
        result = hook(self.root, "ci", None, "--tool", "git", "--base", self.base)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("proved", result.stdout)

    def test_archive_and_vision_scripts_are_not_scope_bypasses(self):
        for rel in ("docs/prototypes/_archive/old/app.js",
                    "docs/prototypes/_vision/variations/app.js"):
            with self.subTest(rel=rel):
                self.assertEqual(self.pretool(rel).returncode, 2)

    def test_deleting_or_renaming_prototype_needs_scope(self):
        rel = "docs/prototypes/files/app.js"
        self.put(rel)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "baseline prototype")
        (self.root / rel).rename(self.root / "docs/prototypes/files/README.md")
        result = self.commit_gate()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("no change tier", result.stdout)


if __name__ == "__main__":
    unittest.main()
