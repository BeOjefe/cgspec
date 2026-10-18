"""Second enforcement re-check: approvals are fresh and single-use, trailers need a trusted signature,
test proofs use the project's own test command, the engine folder hides nothing, cleanup is allowed."""

from __future__ import annotations

import json
import os
import unittest

from tests.helpers import (TempDir, approve, claude_payload, git, git_project, hook, make_slice, run_script,
                           write_json)


def commit(root, message):
    git(root, "add", "-A")
    git(root, "commit", "-q", "--no-verify", "-m", message)


def head(root):
    return git(root, "rev-parse", "HEAD").stdout.strip()


class Round2Tests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git_project(self.root)
        self.base = head(self.root)

    def tearDown(self):
        for p in self.root.rglob("*"):
            if p.is_file() and not p.is_symlink():
                os.chmod(p, 0o644)
        self._tmp.__exit__(None, None, None)

    def ci(self):
        return hook(self.root, "ci", None, "--tool", "git", "--base", self.base)

    def assertCiFails(self, needle):
        result = self.ci()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn(needle, result.stdout)

    def set_project(self, **fields):
        pj = self.root / "docs/_cgspec/project.json"
        os.chmod(pj, 0o644)
        data = json.loads(pj.read_text())
        data.update(fields)
        write_json(pj, data)

    # --- approvals: fresh and single-use ----------------------------------------------------
    def test_old_approval_cannot_approve_a_new_slice(self):
        old = approve(self.root, "yes, go ahead and rename the README heading")
        commit(self.root, "unrelated approval")
        self.base = head(self.root)
        make_slice(self.root, scope="**", approval=old)
        commit(self.root, "slice reusing an old approval")
        self.assertCiFails("not given in this change")

    def test_one_approval_cannot_approve_two_records(self):
        ref = approve(self.root, "approved")
        make_slice(self.root, approval=ref, number="001")
        make_slice(self.root, approval=ref, number="002")
        commit(self.root, "two slices, one approval")
        self.assertCiFails("already cited")

    def test_approval_naming_another_record_cannot_be_used(self):
        ref = approve(self.root, "approve SLICE-007")
        make_slice(self.root, approval=ref, number="001")
        commit(self.root, "mismatched approval")
        self.assertCiFails("names SLICE-007")

    def test_fresh_approval_in_the_same_change_passes(self):
        ref = approve(self.root, "approve SLICE-001")
        make_slice(self.root, approval=ref, number="001")
        commit(self.root, "slice with its approval")
        result = self.ci()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_scope_change_with_another_old_approval_fails(self):
        first = approve(self.root, "approved")
        spare = approve(self.root, "yes")
        path = make_slice(self.root, approval=first)
        commit(self.root, "slice")
        self.base = head(self.root)
        path.write_text(path.read_text().replace("src/login/**", "**").replace(first, spare))
        commit(self.root, "widen with a spare approval")
        self.assertCiFails("not given in this change")

    # --- trailer needs a trusted signature ----------------------------------------------------
    def test_unsigned_trailer_is_rejected(self):
        make_slice(self.root, approval="trailer")
        commit(self.root, "approve\n\nApproved-by: agent-wrote-this")
        self.assertCiFails("signed")

    # --- test proofs use the project's test command -------------------------------------------
    def prepare_fix(self, command):
        ref = approve(self.root, "approve SLICE-001")
        make_slice(self.root, scope="src/login/**, tests/**", approval=ref)
        commit(self.root, "slice")
        run_script("cgspec_hook.py", "tier", "set", "--tier", "T1", "--reason", "login fix", "--slice", "SLICE-001",
                   "--root", str(self.root))
        (self.root / "tests").mkdir()
        (self.root / "tests/test_login.py").write_text("import pathlib\nassert pathlib.Path('src/login/fixed.txt').exists()\n")
        commit(self.root, "failing test")
        failed_at = head(self.root)
        (self.root / "src/login/fixed.txt").write_text("ok\n")
        write_json(self.root / "docs/_cgspec/06-evidence/tests/login.json", {
            "schema": 1, "test_id": "login", "test_file": "tests/test_login.py", "command": command,
            "failed_at": failed_at, "passed_at": None, "covers": ["src/login/fixed.txt"], "slice": "SLICE-001",
            "recorded": "2026-10-18T00:00:00Z"})
        commit(self.root, "fix")

    def test_proof_without_a_project_test_command_fails(self):
        self.prepare_fix(["python3", "tests/test_login.py"])
        self.assertCiFails("test_command")

    def test_proof_must_use_the_project_test_command(self):
        ref = approve(self.root, "approve the test command python3 {test_file}")
        self.set_project(test_command=["python3", "{test_file}"], test_command_approval=ref)
        commit(self.root, "set test command")
        self.base = head(self.root)
        self.prepare_fix(["sh", "-c", "test -f tests/test_login.py"])
        self.assertCiFails("project test_command")

    def test_honest_proof_with_project_command_passes(self):
        ref = approve(self.root, "approve the test command python3 {test_file}")
        self.set_project(test_command=["python3", "{test_file}"], test_command_approval=ref)
        commit(self.root, "set test command")
        self.base = head(self.root)
        self.prepare_fix(["python3", "tests/test_login.py"])
        result = self.ci()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_test_command_change_needs_fresh_approval(self):
        self.set_project(test_command=["true", "{test_file}"])
        commit(self.root, "weaken test command")
        self.assertCiFails("test_command")

    def test_test_file_must_exist_where_it_failed(self):
        ref = approve(self.root, "approve the test command python3 {test_file}")
        self.set_project(test_command=["python3", "{test_file}"], test_command_approval=ref)
        commit(self.root, "set test command")
        self.base = head(self.root)
        failed_at = head(self.root)  # test file does not exist yet here
        ref2 = approve(self.root, "approve SLICE-001")
        make_slice(self.root, scope="src/login/**, tests/**", approval=ref2)
        run_script("cgspec_hook.py", "tier", "set", "--tier", "T1", "--reason", "login fix", "--slice", "SLICE-001",
                   "--root", str(self.root))
        (self.root / "tests").mkdir()
        (self.root / "tests/test_login.py").write_text("pass\n")
        (self.root / "src/login/fixed.txt").write_text("ok\n")
        write_json(self.root / "docs/_cgspec/06-evidence/tests/login.json", {
            "schema": 1, "test_id": "login", "test_file": "tests/test_login.py", "command": ["python3", "tests/test_login.py"],
            "failed_at": failed_at, "passed_at": None, "covers": ["src/login/fixed.txt"], "slice": "SLICE-001",
            "recorded": "2026-10-18T00:00:00Z"})
        commit(self.root, "fix with a test that never failed")
        self.assertCiFails("did not exist at")

    # --- engine folder hides nothing ----------------------------------------------------------
    def test_cache_files_cannot_be_committed_anywhere(self):
        cache = self.root / "docs/_cgspec/01-engine/__pycache__"
        cache.mkdir()
        (cache / "generate_v15_screenshots.py").write_text("print('x')\n")
        git(self.root, "add", "-f", str(cache / "generate_v15_screenshots.py"))
        git(self.root, "commit", "-q", "--no-verify", "-m", "hide a script")
        self.assertCiFails("__pycache__")

    # --- cleanup is allowed -------------------------------------------------------------------
    def test_find_delete_of_unrelated_files_is_allowed(self):
        payload = claude_payload(self.root, "Bash", command="find . -name '*.log' -delete")
        self.assertEqual(hook(self.root, "pre-tool", payload, "--tool", "claude").returncode, 0)
        payload = claude_payload(self.root, "Bash", command="find . -name '*.json' -delete")
        self.assertEqual(hook(self.root, "pre-tool", payload, "--tool", "claude").returncode, 2)


if __name__ == "__main__":
    unittest.main()
