"""Registered project checks (spec 8 script registration): propose, approve, register, run as a gate."""

from __future__ import annotations

import json
import os
import subprocess
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
        self.guide = self.root / ".cgspec-scratch/checks/no_hex.md"
        self.guide.write_text("# Fix the source cause\n\nDo not hide it with an exception.\n")

    def tearDown(self):
        for p in self.root.rglob("*"):
            if p.is_file() and not p.is_symlink():
                os.chmod(p, 0o644)
        self._tmp.__exit__(None, None, None)

    def register(self, approval=None, guide=False):
        approval = approval if approval is not None else approve(self.root, "approve CHK-001")
        args = ["register", "--file", ".cgspec-scratch/checks/no_hex.py", "--applies-to", "src/**",
                "--description", "no raw hex colors in source", "--approval", approval]
        if guide: args += ["--guide", ".cgspec-scratch/checks/no_hex.md"]
        return check(self.root, *args)

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

    def test_register_copies_and_hashes_the_guide(self):
        result = self.register(guide=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        entry = self.manifest()["checks"][0]
        self.assertEqual(entry["guide"], "docs/_cgspec/04-checks/no_hex.md")
        self.assertEqual(entry["guide_sha256"], __import__("hashlib").sha256(
            (self.root / entry["guide"]).read_bytes()).hexdigest())

    def test_register_refuses_a_guide_outside_scratch(self):
        result = check(self.root, "register", "--file", ".cgspec-scratch/checks/no_hex.py", "--applies-to", "src/**",
                       "--description", "x", "--approval", approve(self.root), "--guide", "AGENTS.md")
        self.assertEqual(result.returncode, 1)

    def test_failure_prints_guide_and_tampered_guide_skips_check(self):
        self.register(guide=True)
        (self.root / "src/a.ts").write_text("const x = '#ff0000';\n")
        failed = check(self.root, "run", "--files", "src/a.ts")
        self.assertIn("How to fix this well (CHK-001 guide):", failed.stdout)
        self.assertIn("Fix the source cause", failed.stdout)
        path = self.root / "docs/_cgspec/04-checks/no_hex.md"
        path.write_text("tampered")
        tampered = check(self.root, "run", "--files", "src/a.ts")
        self.assertIn("changed since approval", tampered.stdout)
        self.assertNotIn("failed (no raw hex", tampered.stdout)

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
                   "src/a.ts", "--verify", "registered project checks", "--root", str(self.root))
        (self.root / "src/a.ts").write_text("export const color = '#ff0000';\n")
        git(self.root, "add", "-A")
        result = hook(self.root, "pre-commit", None, "--tool", "git")
        self.assertEqual(result.returncode, 1)
        self.assertIn("CHK-001", result.stdout)

    def test_pre_commit_accepts_the_newly_registered_check_script(self):
        """The real commit gate, not --no-verify, must accept the script `register` just wrote.

        Every other test in this file commits a freshly registered check with
        --no-verify, which bypasses the gate under test and let a real block
        through: `_script_allowed` only ever allowed `.cgspec-scratch/` and a
        handful of code/prototype locations, never `docs/_cgspec/04-checks/**`
        itself, so the commit gate refused the very file `register` approves.
        """
        self.register()
        git(self.root, "add", "-A")
        result = hook(self.root, "pre-commit", None, "--tool", "git")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_pre_commit_accepts_newly_registered_check_and_guide(self):
        self.register(guide=True)
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)
        result = subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=t@example.com",
                                 "commit", "-m", "register check guide"], cwd=self.root,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_ci_runs_registered_checks_on_the_range(self):
        self.register()
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "--no-verify", "-m", "register check")
        base = git(self.root, "rev-parse", "HEAD").stdout.strip()
        run_script("cgspec_hook.py", "tier", "set", "--tier", "T0", "--reason", "change a color", "--files",
                   "src/a.ts", "--verify", "registered project checks", "--root", str(self.root))
        (self.root / "src/a.ts").write_text("export const color = '#ff0000';\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "--no-verify", "-m", "raw hex")
        result = hook(self.root, "ci", None, "--tool", "git", "--base", base)
        self.assertEqual(result.returncode, 1)
        self.assertIn("CHK-001", result.stdout)



def real_commit(root, message):
    """git commit with the installed hooks active (no --no-verify, no hooksPath override)."""
    return subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=t@example.com",
                           "-c", "commit.gpgsign=false", "commit", "-m", message], cwd=root,
                          capture_output=True, text=True)


class GuideIntegrityTests(unittest.TestCase):
    """A registered guide is verified on every gate path, whether or not its check applies."""

    register = RegisteredCheckTests.register
    tearDown = RegisteredCheckTests.tearDown

    def setUp(self):
        RegisteredCheckTests.setUp(self)
        self.assertEqual(self.register(guide=True).returncode, 0)
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)
        committed = real_commit(self.root, "register check guide")
        self.assertEqual(committed.returncode, 0, committed.stdout + committed.stderr)
        self.base = git(self.root, "rev-parse", "HEAD").stdout.strip()
        self.guide_path = self.root / "docs/_cgspec/04-checks/no_hex.md"

    def edit_guide(self):
        import time
        from _lib.common import utc_now
        from _lib.document_dates import touch
        time.sleep(1.1)  # Last edited must advance, so only the guide hash rule can object
        text = self.guide_path.read_text().replace("Do not hide it with an exception.",
                                                   "Adding an exception to the baseline is fine.")
        self.guide_path.write_text(touch(text, utc_now()))

    def test_pre_commit_refuses_a_guide_only_edit(self):
        self.edit_guide()
        git(self.root, "add", "docs/_cgspec/04-checks/no_hex.md")
        result = real_commit(self.root, "soften the guide")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("no_hex.md", result.stdout + result.stderr)
        self.assertEqual(git(self.root, "rev-parse", "HEAD").stdout.strip(), self.base)

    def test_pre_commit_refuses_a_guide_deletion(self):
        git(self.root, "rm", "-q", "docs/_cgspec/04-checks/no_hex.md")
        result = real_commit(self.root, "drop the guide")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("no_hex.md", result.stdout + result.stderr)
        self.assertEqual(git(self.root, "rev-parse", "HEAD").stdout.strip(), self.base)

    def test_ci_refuses_a_guide_only_edit(self):
        self.edit_guide()
        git(self.root, "add", "docs/_cgspec/04-checks/no_hex.md")
        git(self.root, "commit", "-q", "-m", "soften the guide")  # pushed past the local hook
        result = hook(self.root, "ci", None, "--tool", "git", "--base", self.base)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("no_hex.md", result.stdout)

    def test_ci_refuses_a_guide_deletion(self):
        git(self.root, "rm", "-q", "docs/_cgspec/04-checks/no_hex.md")
        git(self.root, "commit", "-q", "-m", "drop the guide")
        result = hook(self.root, "ci", None, "--tool", "git", "--base", self.base)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("no_hex.md", result.stdout)

    def test_doctor_reports_a_changed_guide(self):
        self.guide_path.write_text("# Fix it\n\ntampered\n")
        result = run_script("doctor.py", "--root", str(self.root))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no_hex.md", result.stdout + result.stderr)

    def test_check_run_on_unrelated_files_still_verifies_the_guide(self):
        self.guide_path.unlink()
        result = check(self.root, "run", "--files", "docs/spines/01-INTENT.md")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("no_hex.md", result.stdout)


class CheckIntegrityAcrossCommitsTests(unittest.TestCase):
    """CI must verify every registered script against each commit's OWN manifest (its own tree),
    not only the final tree: a commit that tampers with an approved check and a later commit that
    undoes the tamper byte-for-byte must still fail CI for the range."""

    register = RegisteredCheckTests.register
    tearDown = RegisteredCheckTests.tearDown

    def setUp(self):
        RegisteredCheckTests.setUp(self)
        self.assertEqual(self.register().returncode, 0)
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)
        committed = real_commit(self.root, "register check")
        self.assertEqual(committed.returncode, 0, committed.stdout + committed.stderr)
        self.base = git(self.root, "rev-parse", "HEAD").stdout.strip()
        self.script_path = self.root / "docs/_cgspec/04-checks/no_hex.py"

    def ci(self):
        return hook(self.root, "ci", None, "--tool", "git", "--base", self.base)

    def test_ci_catches_a_script_deleted_then_restored_across_commits(self):
        original = self.script_path.read_bytes()
        git(self.root, "rm", "-q", "docs/_cgspec/04-checks/no_hex.py")
        git(self.root, "commit", "-q", "-m", "drop the check")  # pushed past the local hook
        self.script_path.write_bytes(original)
        git(self.root, "add", "docs/_cgspec/04-checks/no_hex.py")
        git(self.root, "commit", "-q", "-m", "restore the check")
        result = self.ci()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("no_hex.py", result.stdout)

    def test_ci_catches_a_script_modified_then_restored_across_commits(self):
        original = self.script_path.read_bytes()
        self.script_path.write_bytes(original + b"\n# tampered\n")
        git(self.root, "add", "docs/_cgspec/04-checks/no_hex.py")
        git(self.root, "commit", "-q", "-m", "neuter the check")  # pushed past the local hook
        self.script_path.write_bytes(original)
        git(self.root, "add", "docs/_cgspec/04-checks/no_hex.py")
        git(self.root, "commit", "-q", "-m", "restore the check")
        result = self.ci()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("no_hex.py", result.stdout)


if __name__ == "__main__":
    unittest.main()
