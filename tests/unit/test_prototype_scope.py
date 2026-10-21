"""Executable prototype changes obey scope in hooks and CI; prose stays cheap."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from tests.helpers import (
    TempDir, approve, claude_payload, git, git_project, hook, make_slice, run_script,
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
        for suffix in ("js", "mjs", "tsx", "html", "css", "svg", "json",
                       "txt", "wasm", "webmanifest", ""):
            with self.subTest(suffix=suffix):
                result = self.pretool("docs/prototypes/files/new" + ("." + suffix if suffix else ""))
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

    def test_shell_rename_to_prose_still_checks_source_scope(self):
        rel = "docs/prototypes/files/app.js"
        self.put(rel)
        for command in (
            f"mv {rel} docs/prototypes/files/README.md",
            f"mv -t docs/spines {rel}",
            f"mv --target-directory=docs/spines {rel}",
        ):
            with self.subTest(command=command):
                result = hook(self.root, "pre-tool",
                              claude_payload(self.root, "Bash", command=command),
                              "--tool", "claude")
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn("tier", result.stderr)

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

    def test_journey_tests_do_not_require_tests_of_their_own(self):
        self.tier()
        self.put("docs/prototypes/files/journeys/open.json",
                 '{"name":"open","url":"index.html","steps":[]}\n')
        result = self.commit_gate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_new_archive_code_requires_test_evidence(self):
        self.tier(scope="docs/prototypes/_archive/**")
        self.put("docs/prototypes/_archive/old/app.js")
        result = self.commit_gate()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("without a failing-test record", result.stdout)

    def test_modified_archive_code_requires_test_evidence(self):
        rel = "docs/prototypes/_archive/old/app.js"
        self.put(rel, "export const ready = false;\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "baseline historical source")
        self.tier(scope="docs/prototypes/_archive/**")
        self.put(rel)
        result = self.commit_gate()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("without a failing-test record", result.stdout)

    def test_unknown_prototype_suffix_cannot_bypass_commit_scope(self):
        self.put("docs/prototypes/files/logic.txt", "document.title = 'changed';\n")
        result = self.commit_gate()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("no change tier", result.stdout)

    def test_mixed_case_markdown_requires_scope_in_all_gates(self):
        for suffix in ("MD", "Md"):
            with self.subTest(suffix=suffix):
                result = self.pretool("docs/prototypes/files/logic." + suffix)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.put("docs/prototypes/files/logic.MD")
        result = self.commit_gate()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("no change tier", result.stdout)
        git(self.root, "commit", "-q", "-m", "bypass hook with uppercase extension")
        result = hook(self.root, "ci", None, "--tool", "git", "--base", self.base)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("no change tier", result.stdout)

    def assert_asset_cannot_become_archived_code_without_evidence(self, old):
        new = "docs/prototypes/_archive/files/logic.js"
        self.put(old)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "baseline asset")
        self.tier(scope="docs/prototypes/**")
        (self.root / new).parent.mkdir(parents=True, exist_ok=True)
        (self.root / old).rename(self.root / new)
        result = self.commit_gate()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("without a failing-test record", result.stdout)

    def test_reference_asset_cannot_launder_archive_test_exemption(self):
        self.assert_asset_cannot_become_archived_code_without_evidence("docs/prototypes/files/logic.png")

    def test_journey_cannot_launder_archive_test_exemption(self):
        self.assert_asset_cannot_become_archived_code_without_evidence("docs/prototypes/files/journeys/logic.json")

    def test_unchanged_rename_count_ignores_environment_rename_setting(self):
        old = "docs/prototypes/files/style.css"
        new = "docs/prototypes/_archive/files/style.css"
        self.put(old, "".join(f".item-{i} {{ color: red; }}\n" for i in range(2000)))
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "baseline stylesheet")
        self.tier(scope="docs/prototypes/**")
        (self.root / new).parent.mkdir(parents=True, exist_ok=True)
        (self.root / old).rename(self.root / new)
        with patch.dict("os.environ", {"GIT_CONFIG_COUNT": "1",
                                     "GIT_CONFIG_KEY_0": "diff.renames",
                                     "GIT_CONFIG_VALUE_0": "false"}):
            result = self.commit_gate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unchanged_archive_rename_preserves_history_without_new_test(self):
        old = "docs/prototypes/files/app.js"
        new = "docs/prototypes/_archive/files/app.js"
        self.put(old)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "baseline prototype")
        self.tier(scope="docs/prototypes/**")
        (self.root / new).parent.mkdir(parents=True, exist_ok=True)
        (self.root / old).rename(self.root / new)
        result = self.commit_gate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_snapshot_cut_can_commit_with_explicit_snapshot_scope(self):
        self.put("docs/prototypes/files/index.html", "<main>Ready</main>\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "baseline prototype")
        self.tier(scope="docs/prototypes/files/**, docs/prototypes/_snapshots/files-v*.html")
        ref = approve(self.root, "approved, lock layer 2")
        result = run_script("bundle_prototype.py", "files", "--root", str(self.root),
                            "--layer", "2", "--approval", ref)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = self.commit_gate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_deleting_or_renaming_prototype_needs_scope(self):
        rel = "docs/prototypes/files/app.js"
        self.put(rel)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "baseline prototype")
        (self.root / rel).rename(self.root / "docs/prototypes/files/README.md")
        result = self.commit_gate()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("no change tier", result.stdout)

    def test_modified_rename_cannot_bypass_t1_line_limit_in_commit_or_ci(self):
        old = "docs/prototypes/_archive/old.css"
        new = "docs/prototypes/_archive/new.css"
        lines = [f".item-{i} {{ color: red; }}\n" for i in range(2000)]
        self.put(old, "".join(lines))
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "baseline historical stylesheet")
        self.tier(scope="docs/prototypes/_archive/**")
        (self.root / old).rename(self.root / new)
        lines[:250] = [f".item-{i} {{ color: blue; }}\n" for i in range(250)]
        self.put(new, "".join(lines))
        result = self.commit_gate()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("T1 allows 400", result.stdout)
        git(self.root, "commit", "-q", "-m", "bypass local hook with oversized rename")
        result = hook(self.root, "ci", None, "--tool", "git", "--base", self.base)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("T1 allows 400", result.stdout)


if __name__ == "__main__":
    unittest.main()
