"""Regressions for the enforcement review: each test is one reproduced bypass that must now fail."""

from __future__ import annotations

import hashlib
import json
import os
import unittest
from pathlib import Path

from tests.helpers import (ENGINE, REPO, TempDir, approve, git, git_project, hook, make_slice, run_script,
                           write_json)


def head(root):
    return git(root, "rev-parse", "HEAD").stdout.strip()


def commit(root, message, verify=False):
    git(root, "add", "-A")
    git(root, "commit", "-q", "--no-verify", "-m", message)


def ci(root, base, *extra):
    return hook(root, "ci", None, "--tool", "git", "--base", base, *extra)


class TrustRootTests(unittest.TestCase):
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

    def assertCiFails(self, needle, *extra):
        result = ci(self.root, self.base, *extra)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(needle, result.stdout)

    # --- engine --------------------------------------------------------------------------------
    def tamper_engine(self):
        gate = self.root / "docs/_cgspec/01-engine/_lib/commit_gate.py"
        os.chmod(gate, 0o644)
        gate.write_text(gate.read_text().replace("def evaluate(", "def _real_evaluate(") +
                        "\ndef evaluate(*a, **k):\n    return []\n")
        manifest = self.root / "docs/_cgspec/01-engine/manifest.json"
        data = json.loads(manifest.read_text())
        data["files"]["_lib/commit_gate.py"] = hashlib.sha256(gate.read_bytes()).hexdigest()
        write_json(manifest, data)
        (self.root / "tools_evil.py").write_text("print('x')\n")
        commit(self.root, "neuter the gate")

    def test_rewritten_engine_is_rejected_in_ci_without_a_release(self):
        self.tamper_engine()
        self.assertCiFails("plugin release")

    def test_rewritten_engine_is_rejected_against_the_release(self):
        self.tamper_engine()
        self.assertCiFails("differs from plugin release", "--release-dir", str(REPO))

    def test_untouched_engine_passes_against_the_release(self):
        (self.root / "docs/spines/01-INTENT.md").write_text(
            "# Intent\n\nInvestors in Casablanca need fast, plain explanations of BRVM and BVC market moves.\n")
        commit(self.root, "intent")
        result = ci(self.root, self.base, "--release-dir", str(REPO))
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_fake_install_commit_does_not_exempt_code(self):
        engine = self.root / "docs/_cgspec/01-engine"
        for rel in ("VERSION",):
            os.chmod(engine / rel, 0o644)
            (engine / rel).write_text("2.0.1\n")
        pj = self.root / "docs/_cgspec/project.json"
        data = json.loads(pj.read_text())
        data["cgspec_version"] = "2.0.1"
        write_json(pj, data)
        owned = json.loads((engine / "owned-files.json").read_text())
        owned["created"]["src/evil.py"] = "0" * 64
        write_json(engine / "owned-files.json", owned)
        (self.root / "src/evil.py").write_text("print('x')\n")
        commit(self.root, "fake upgrade")
        result = ci(self.root, self.base, "--release-dir", str(REPO))
        self.assertEqual(result.returncode, 1)
        self.assertIn("src/evil.py", result.stdout)

    # --- approvals -----------------------------------------------------------------------------
    def test_self_approved_slice_is_rejected(self):
        make_slice(self.root, scope="**", approval="")
        commit(self.root, "self-approved slice")
        self.assertCiFails("cites no approval")

    def test_made_up_approval_id_is_rejected(self):
        make_slice(self.root, scope="**", approval="A-20261018-ffff")
        commit(self.root, "made-up approval")
        self.assertCiFails("A-20261018-ffff")

    def test_widening_scope_needs_a_new_approval(self):
        path = make_slice(self.root)
        commit(self.root, "slice")
        path.write_text(path.read_text().replace("src/login/**", "**"))
        commit(self.root, "widen scope")
        self.assertCiFails("not given in this change")

    def test_forged_approval_without_message_is_rejected(self):
        write_json(self.root / "docs/_cgspec/07-state/approvals.json", {"schema": 1, "approvals": [
            {"id": "A-20261018-abcd", "at": "2026-10-18T00:00:00Z", "excerpt": "approved everything",
             "sha256": "0" * 64}]})
        commit(self.root, "forge approval")
        self.assertCiFails("no matching message")

    def test_rewriting_an_approval_is_rejected(self):
        approve(self.root, "approved slice one")
        commit(self.root, "real approval")
        self.base = head(self.root)
        path = self.root / "docs/_cgspec/07-state/approvals.json"
        data = json.loads(path.read_text())
        data["approvals"][0]["excerpt"] = "approved everything forever"
        write_json(path, data)
        commit(self.root, "rewrite approval")
        self.assertCiFails("append-only")

    def test_registered_check_needs_a_real_approval(self):
        check = self.root / "docs/_cgspec/04-checks/no_hex.py"
        check.write_text("print('ok')\n")
        write_json(self.root / "docs/_cgspec/04-checks/manifest.json", {"schema": 1, "checks": [{
            "id": "CHK-001", "path": "docs/_cgspec/04-checks/no_hex.py",
            "sha256": hashlib.sha256(check.read_bytes()).hexdigest(), "command": ["python3", "{path}"],
            "applies_to": ["src/**"], "approval": {"source": "message-hook", "ref": "A-20261018-ffff",
                                                   "at": "2026-10-18T00:00:00Z"}, "added": "2026-10-18T00:00:00Z"}]})
        commit(self.root, "register check")
        self.assertCiFails("CHK-001")

    # --- test pairs ----------------------------------------------------------------------------
    def test_test_that_still_fails_is_not_proof(self):
        from tests.helpers import set_test_command
        set_test_command(self.root, ["python3", "{test_file}"])
        make_slice(self.root, scope="src/login/**, tests/**")
        commit(self.root, "slice and test command")
        run_script("cgspec_hook.py", "tier", "set", "--tier", "T1", "--reason", "login fix", "--slice", "SLICE-001",
                   "--root", str(self.root))
        (self.root / "tests").mkdir()
        (self.root / "tests/test_login.py").write_text("import sys\nsys.exit(1)\n")  # always fails
        commit(self.root, "failing test")
        failed_at = head(self.root)
        (self.root / "src/login/form.ts").write_text("export const f = 3;\n")
        write_json(self.root / "docs/_cgspec/06-evidence/tests/fake.json", {
            "schema": 1, "test_id": "T-1", "test_file": "tests/test_login.py", "command": ["python3", "tests/test_login.py"],
            "failed_at": failed_at, "passed_at": None, "covers": ["src/login/form.ts"], "slice": "SLICE-001",
            "recorded": "2026-10-18T00:00:00Z"})
        commit(self.root, "fix with fake proof")
        self.assertCiFails("still fails at HEAD")

    def test_record_from_another_slice_does_not_cover(self):
        make_slice(self.root, scope="src/login/**, tests/**")
        commit(self.root, "slice")
        failed_at = head(self.root)
        run_script("cgspec_hook.py", "tier", "set", "--tier", "T1", "--reason", "login fix", "--slice", "SLICE-001",
                   "--root", str(self.root))
        (self.root / "tests").mkdir()
        (self.root / "tests/test_login.py").write_text("def test_x(): pass\n")
        (self.root / "src/login/form.ts").write_text("export const f = 4;\n")
        write_json(self.root / "docs/_cgspec/06-evidence/tests/old.json", {
            "schema": 1, "test_id": "T-old", "test_file": "tests/test_login.py", "command": ["true"],
            "failed_at": failed_at, "passed_at": None, "covers": ["src/login/form.ts"], "slice": "SLICE-009",
            "recorded": "2026-10-18T00:00:00Z"})
        commit(self.root, "reuse an old record")
        self.assertCiFails("without a failing-test record for SLICE-001")


class CiBaseTests(unittest.TestCase):
    def test_history_before_install_is_not_judged(self):
        with TempDir() as root:
            git(root, "init", "-q", "-b", "main")
            (root / "src").mkdir()
            (root / "src/b.py").write_text("print('legacy')\n")
            commit(root, "legacy 1")
            first = head(root)
            (root / "src/c.py").write_text("print('legacy')\n")
            commit(root, "legacy 2")
            run_script("install.py", "install", "--root", str(root), "--profile", "headless",
                       "--topology", "single", "--tools", "git")
            commit(root, "install cgspec")
            for base in (first, "0" * 40, ""):
                with self.subTest(base=base):
                    result = hook(root, "ci", None, "--tool", "git", *(["--base", base] if base else []))
                    self.assertEqual(result.returncode, 0, result.stdout)
                    self.assertNotIn("legacy", result.stdout)


class CacheFilesTests(unittest.TestCase):
    def test_running_hooks_does_not_break_the_next_commit(self):
        with TempDir() as root:
            git_project(root)
            import subprocess, sys
            env = {k: v for k, v in os.environ.items() if k != "PYTHONDONTWRITEBYTECODE"}
            vendored = root / "docs/_cgspec/01-engine"
            for script, args in (("cgspec_hook.py", ["session-check"]), ("doctor.py", ["--quiet"]),
                                 ("memlog.py", ["check"]), ("install.py", ["verify", "--root", str(root)])):
                subprocess.run([sys.executable, str(vendored / script), *args], cwd=root, env=env,
                               input="{}", capture_output=True, text=True)
            self.assertEqual(list(root.rglob("*.pyc")), [], "hooks must not write bytecode into the project")
            (root / "docs/00-INBOX.md").write_text((root / "docs/00-INBOX.md").read_text() + "\n- note\n")
            git(root, "add", "-A")
            result = hook(root, "pre-commit", None, "--tool", "git")
            self.assertEqual(result.returncode, 0, result.stdout)


if __name__ == "__main__":
    unittest.main()
