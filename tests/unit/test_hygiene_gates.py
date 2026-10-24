"""Hygiene gates and template checks derived from RES-007 (Claude Code hook taxonomy)."""

from __future__ import annotations

import json
import os
import subprocess
import unittest
from pathlib import Path

from tests.helpers import REPO, TempDir, claude_payload, git, git_project, hook, install, run_script, write_json

BLOCK = 2


class WriteHygieneGateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        install(self.root)
        (self.root / "src").mkdir(exist_ok=True)
        (self.root / "src/a.ts").write_text("export const a = 1;\n")
        run_script("cgspec_hook.py", "tier", "set", "--tier", "T0", "--reason", "test hygiene",
                   "--files", "src/a.ts", "--root", str(self.root))

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def write_call(self, rel: str, content: str):
        payload = claude_payload(self.root, "Write", file_path=rel, content=content)
        return hook(self.root, "pre-tool", payload, "--tool", "claude")

    def edit_call(self, rel: str, old: str, new: str):
        payload = claude_payload(self.root, "Edit", file_path=rel, old_string=old, new_string=new)
        return hook(self.root, "pre-tool", payload, "--tool", "claude")

    def test_crlf_line_endings_in_written_content_are_blocked(self):
        result = self.edit_call("src/a.ts", "1", "2\r\nexport const b = 3;\r\n")
        self.assertEqual(result.returncode, BLOCK)
        self.assertIn("CRLF", result.stderr)

    def test_code_file_exceeding_400_lines_is_blocked_unless_legacy_exempt(self):
        big = "".join(f"export const v{i} = {i};\n" for i in range(405))
        result = self.edit_call("src/a.ts", "1", big)
        self.assertEqual(result.returncode, BLOCK)
        self.assertIn("400 lines", result.stderr)
        # Legacy-exempt files may still be edited until migrated
        write_json(self.root / "docs/_cgspec/07-state/legacy-baseline.json", {
            "schema": 1, "files": {"src/a.ts": "0" * 64}})
        allowed = self.edit_call("src/a.ts", "1", big)
        self.assertEqual(allowed.returncode, 0, allowed.stderr)

    def test_hardcoded_host_paths_in_code_are_blocked(self):
        for sample in ('const p = "/home/alice/project/db.sqlite";\n',
                       'const p = "/Users/alice/project/db.sqlite";\n',
                       'const p = "C:\\\\Users\\\\alice\\\\project\\\\db.sqlite";\n'):
            with self.subTest(sample=sample):
                result = self.edit_call("src/a.ts", "1", sample)
                self.assertEqual(result.returncode, BLOCK)
                self.assertIn("host path", result.stderr)

    def test_antigravity_replace_file_content_exceeding_400_lines_is_blocked(self):
        big = "".join(f"export const v{i} = {i};\n" for i in range(398))
        (self.root / "src/a.ts").write_text("export const a = 1;\n" + big)
        ag_payload = {
            "workspacePaths": [str(self.root)],
            "toolCall": {
                "name": "replace_file_content",
                "args": {
                    "TargetFile": str(self.root / "src/a.ts"),
                    "TargetContent": "export const a = 1;",
                    "ReplacementContent": "export const a = 1;\nexport const extra_1 = 2;\nexport const extra_2 = 3;\nexport const extra_3 = 4;\n",
                },
            },
        }
        res = hook(self.root, "pre-tool", ag_payload, "--tool", "antigravity")
        self.assertEqual(res.returncode, 0)
        self.assertIn('"deny"', res.stdout)
        self.assertIn("400 lines", res.stdout)


class CommitHygieneGateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git_project(self.root)
        run_script("cgspec_hook.py", "tier", "set", "--tier", "T0", "--reason", "test commit hygiene",
                   "--files", "src/a.ts", "--root", str(self.root))

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def test_commit_gate_blocks_crlf_in_staged_file(self):
        (self.root / "src/a.ts").write_bytes(b"export const a = 2;\r\n")
        git(self.root, "add", "-A")
        result = hook(self.root, "pre-commit", None, "--tool", "git")
        self.assertEqual(result.returncode, 1)
        self.assertIn("CRLF", result.stdout + result.stderr)

    def test_commit_gate_blocks_hardcoded_host_path_in_staged_code(self):
        (self.root / "src/a.ts").write_text('export const a = "/home/bob/secret/config.json";\n')
        git(self.root, "add", "-A")
        result = hook(self.root, "pre-commit", None, "--tool", "git")
        self.assertEqual(result.returncode, 1)
        self.assertIn("host path", result.stdout + result.stderr)

    def test_commit_gate_blocks_file_exceeding_400_lines_in_staged_code(self):
        long_content = "".join(f"export const v{i} = {i};\n" for i in range(405))
        (self.root / "src/a.ts").write_text(long_content)
        git(self.root, "add", "-A")
        result = hook(self.root, "pre-commit", None, "--tool", "git")
        self.assertEqual(result.returncode, 1)
        self.assertIn("400 lines per file limit", result.stdout + result.stderr)



class BlockedDeflectionGateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        install(self.root)

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def block_with(self, reason: str):
        return run_script("cgspec_hook.py", "checkpoint", "--blocked", reason, "--root", str(self.root))

    def test_vague_deflection_without_evidence_is_refused(self):
        for excuse in ("pre-existing issue", "out of scope for now", "defer to later", "not from my changes"):
            with self.subTest(excuse=excuse):
                result = self.block_with(excuse)
                self.assertEqual(result.returncode, 1)
                self.assertIn("concrete", result.stderr)

    def test_specific_technical_blocker_is_accepted(self):
        result = self.block_with("src/login/form.ts:42 fails E-SCHEMA because OAuth provider credentials are missing")
        self.assertEqual(result.returncode, 0, result.stderr)


class ShippedTemplateChecksTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def run_template(self, script_name: str, *files: str):
        script = REPO / "templates/checks" / script_name
        return subprocess.run(["python3", str(script), *files], cwd=self.root, capture_output=True, text=True)

    def test_every_template_check_has_a_companion_markdown_guide(self):
        checks_dir = REPO / "templates/checks"
        scripts = sorted(checks_dir.glob("*.py"))
        self.assertGreaterEqual(len(scripts), 4)
        for script in scripts:
            guide = script.with_suffix(".md")
            self.assertTrue(guide.is_file(), f"missing companion guide for {script.name}")
            self.assertGreater(len(guide.read_text(encoding="utf-8").strip()), 40)

    def test_code_size_and_crlf_check_catches_crlf_long_files_and_long_functions(self):
        (self.root / "clean.py").write_text("def ok():\n    return 1\n", encoding="utf-8")
        self.assertEqual(self.run_template("code_size_and_crlf.py", "clean.py").returncode, 0)

        (self.root / "crlf.py").write_bytes(b"x = 1\r\ny = 2\r\n")
        res_crlf = self.run_template("code_size_and_crlf.py", "crlf.py")
        self.assertEqual(res_crlf.returncode, 1)
        self.assertIn("CRLF", res_crlf.stdout)

        long_fn = "def huge():\n" + "".join(f"    x{i} = {i}\n" for i in range(65))
        (self.root / "long_fn.py").write_text(long_fn, encoding="utf-8")
        res_fn = self.run_template("code_size_and_crlf.py", "long_fn.py")
        self.assertEqual(res_fn.returncode, 1)
        self.assertIn("60 lines", res_fn.stdout)

        long_file = "".join(f"X_{i} = {i}\n" for i in range(405))
        (self.root / "long_file.py").write_text(long_file, encoding="utf-8")
        res_file = self.run_template("code_size_and_crlf.py", "long_file.py")
        self.assertEqual(res_file.returncode, 1)
        self.assertIn("400 lines", res_file.stdout)

    def test_no_host_paths_check_catches_workstation_paths(self):
        (self.root / "ok.ts").write_text('const p = process.env.APP_ROOT || "./data";\n', encoding="utf-8")
        self.assertEqual(self.run_template("no_host_paths.py", "ok.ts").returncode, 0)

        (self.root / "bad.ts").write_text('const p = "/home/developer/app/data";\n', encoding="utf-8")
        res = self.run_template("no_host_paths.py", "bad.ts")
        self.assertEqual(res.returncode, 1)
        self.assertIn("/home/developer", res.stdout)

    def test_no_deferred_todos_check_requires_ticket_or_slice_reference(self):
        (self.root / "linked.ts").write_text("// TODO(SLICE-004): wire pagination\nexport const x = 1;\n", encoding="utf-8")
        self.assertEqual(self.run_template("no_deferred_todos.py", "linked.ts").returncode, 0)

        (self.root / "unlinked.ts").write_text("// TODO: fix this later\nexport const x = 1;\n", encoding="utf-8")
        res = self.run_template("no_deferred_todos.py", "unlinked.ts")
        self.assertEqual(res.returncode, 1)
        self.assertIn("unlinked", res.stdout.lower())


if __name__ == "__main__":
    unittest.main()
