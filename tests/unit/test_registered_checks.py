"""Registered project checks (spec 8 script registration): propose, approve, register, run as a gate."""

from __future__ import annotations

import json
import os
import unittest

from tests.helpers import TempDir, approve, git, git_project, hook, run_script

NO_HEX = ("import re, sys\n"
          "bad = [f for f in sys.argv[1:] if re.search(r'#[0-9a-fA-F]{6}', open(f).read())]\n"
          "print('\\n'.join(bad)); sys.exit(1 if bad else 0)\n")


def check(root, *args):
    return run_script("cgspec_hook.py", "check", *args, "--root", str(root))


class RegisteredCheckTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git_project(self.root)
        proposal = self.root / ".cgspec-scratch/checks/no_hex.py"
        proposal.parent.mkdir(parents=True)
        proposal.write_text(NO_HEX)

    def tearDown(self):
        for p in self.root.rglob("*"):
            if p.is_file() and not p.is_symlink():
                os.chmod(p, 0o644)
        self._tmp.__exit__(None, None, None)

    def register(self, approval=None):
        approval = approval if approval is not None else approve(self.root, "approve CHK-001")
        return check(self.root, "register", "--file", ".cgspec-scratch/checks/no_hex.py", "--applies-to", "src/**",
                     "--description", "no raw hex colors in source", "--approval", approval)

    def manifest(self):
        return json.loads((self.root / "docs/_cgspec/04-checks/manifest.json").read_text())

    def test_register_copies_the_check_and_records_its_hash(self):
        result = self.register()
        self.assertEqual(result.returncode, 0, result.stderr)
        entry = self.manifest()["checks"][0]
        self.assertEqual(entry["id"], "CHK-001")
        self.assertEqual(entry["path"], "docs/_cgspec/04-checks/no_hex.py")
        self.assertTrue((self.root / entry["path"]).is_file())
        self.assertEqual(entry["approval"]["source"], "message-hook")
        self.assertEqual(run_script("doctor.py", "--root", str(self.root)).returncode, 0)

    def test_register_needs_a_real_approval(self):
        result = self.register(approval="A-20261019-ffff")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.manifest()["checks"], [])

    def test_register_refuses_files_outside_the_scratch_proposals(self):
        (self.root / "src/evil.py").write_text("print(1)\n")
        result = check(self.root, "register", "--file", "src/evil.py", "--applies-to", "src/**",
                       "--description", "x", "--approval", approve(self.root, "approve CHK-001"))
        self.assertEqual(result.returncode, 1)

    def test_run_passes_and_fails_with_evidence(self):
        self.register()
        self.assertEqual(check(self.root, "run", "--files", "src/a.ts").returncode, 0)
        evidence = json.loads((self.root / "docs/_cgspec/06-evidence/checks/CHK-001.json").read_text())
        self.assertEqual(evidence["verdict"], "PASS")
        self.assertEqual(evidence["covers"], ["src/**"])
        (self.root / "src/a.ts").write_text("export const color = '#ff0000';\n")
        failed = check(self.root, "run", "--files", "src/a.ts")
        self.assertEqual(failed.returncode, 1)
        self.assertIn("src/a.ts", failed.stdout)
        evidence = json.loads((self.root / "docs/_cgspec/06-evidence/checks/CHK-001.json").read_text())
        self.assertEqual(evidence["verdict"], "FAIL")

    def test_check_only_runs_on_matching_files(self):
        self.register()
        (self.root / "docs/spines/01-INTENT.md").write_text("# Intent\n\n#ff0000\n")
        result = check(self.root, "run", "--files", "docs/spines/01-INTENT.md")
        self.assertEqual(result.returncode, 0)
        self.assertIn("no registered check applies", result.stdout)

    def test_tampered_check_does_not_run(self):
        self.register()
        target = self.root / "docs/_cgspec/04-checks/no_hex.py"
        os.chmod(target, 0o644)
        target.write_text("import sys; sys.exit(0)\n")
        result = check(self.root, "run", "--files", "src/a.ts")
        self.assertEqual(result.returncode, 1)
        self.assertIn("changed since approval", result.stdout)

    def test_pre_commit_runs_registered_checks_on_staged_files(self):
        self.register()
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "--no-verify", "-m", "register check")
        run_script("cgspec_hook.py", "tier", "set", "--tier", "T0", "--reason", "change a color", "--files",
                   "src/a.ts", "--root", str(self.root))
        (self.root / "src/a.ts").write_text("export const color = '#ff0000';\n")
        git(self.root, "add", "-A")
        result = hook(self.root, "pre-commit", None, "--tool", "git")
        self.assertEqual(result.returncode, 1)
        self.assertIn("CHK-001", result.stdout)

    def test_ci_runs_registered_checks_on_the_range(self):
        self.register()
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "--no-verify", "-m", "register check")
        base = git(self.root, "rev-parse", "HEAD").stdout.strip()
        run_script("cgspec_hook.py", "tier", "set", "--tier", "T0", "--reason", "change a color", "--files",
                   "src/a.ts", "--root", str(self.root))
        (self.root / "src/a.ts").write_text("export const color = '#ff0000';\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "--no-verify", "-m", "raw hex")
        result = hook(self.root, "ci", None, "--tool", "git", "--base", base)
        self.assertEqual(result.returncode, 1)
        self.assertIn("CHK-001", result.stdout)


if __name__ == "__main__":
    unittest.main()
