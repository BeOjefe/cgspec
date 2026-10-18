"""Approval through the commit trailer `Approved-by:` (spec 8, tools without a message hook)."""

from __future__ import annotations

import os
import subprocess
import unittest

from pathlib import Path

from tests.helpers import TempDir, git, git_project, hook, make_slice, run_script


def commit(root, message):
    git(root, "add", "-A")
    git(root, "commit", "-q", "--no-verify", "-m", message)


class TrailerApprovalTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git_project(self.root)
        self.base = git(self.root, "rev-parse", "HEAD").stdout.strip()

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def ci(self):
        return hook(self.root, "ci", None, "--tool", "git", "--base", self.base)

    def signing_key(self, name="me"):
        key = self.root.parent / f"{self.root.name}-{name}"
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True)
        return key, (key.with_suffix(".pub") if key.with_suffix(".pub").exists() else Path(str(key) + ".pub")).read_text().strip()

    def signed_commit(self, key, message):
        git(self.root, "add", "-A")
        git(self.root, "-c", "gpg.format=ssh", "-c", f"user.signingkey={key}", "commit", "-q", "--no-verify",
            "-S", "-m", message)

    def trust_key(self, pub):
        import json
        pj = self.root / "docs/_cgspec/project.json"
        os.chmod(pj, 0o644)
        data = json.loads(pj.read_text())
        data["approver_keys"] = [pub]
        pj.write_text(json.dumps(data, indent=2) + "\n")
        commit(self.root, "trust my signing key")
        self.base = git(self.root, "rev-parse", "HEAD").stdout.strip()

    def set_keys(self, keys):
        import json
        pj = self.root / "docs/_cgspec/project.json"
        os.chmod(pj, 0o644)
        data = json.loads(pj.read_text())
        data["approver_keys"] = keys
        pj.write_text(json.dumps(data, indent=2) + "\n")

    def test_slice_approved_by_signed_trailer_passes(self):
        key, pub = self.signing_key()
        self.trust_key(pub)
        make_slice(self.root, approval="trailer")
        self.signed_commit(key, "Approve login slice\n\nApproved-by: Ojefe <me@example.com>")
        result = self.ci()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_trailer_signed_by_an_unknown_key_fails(self):
        _, pub = self.signing_key("me")
        other, _ = self.signing_key("agent")
        self.trust_key(pub)
        make_slice(self.root, approval="trailer")
        self.signed_commit(other, "Approve login slice\n\nApproved-by: Ojefe <me@example.com>")
        result = self.ci()
        self.assertEqual(result.returncode, 1)
        self.assertIn("not signed by a key", result.stdout)

    def test_self_added_key_cannot_approve_its_own_commit(self):
        agent, agent_pub = self.signing_key("agent")
        self.set_keys([agent_pub])
        make_slice(self.root, approval="trailer")
        self.signed_commit(agent, "Approve login slice\n\nApproved-by: agent")
        result = self.ci()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("not signed by a key", result.stdout)
        self.assertIn("approver_keys changed", result.stdout)

    def test_unsigned_key_rotation_is_rejected(self):
        _, old_pub = self.signing_key("old")
        _, new_pub = self.signing_key("new")
        self.trust_key(old_pub)
        self.set_keys([new_pub])
        commit(self.root, "replace signing key")
        result = self.ci()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("approver_keys changed", result.stdout)

    def test_existing_key_can_sign_rotation(self):
        old, old_pub = self.signing_key("old")
        _, new_pub = self.signing_key("new")
        self.trust_key(old_pub)
        self.set_keys([new_pub])
        self.signed_commit(old, "rotate signing key")
        result = self.ci()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_new_key_cannot_sign_its_own_rotation(self):
        _, old_pub = self.signing_key("old")
        new, new_pub = self.signing_key("new")
        self.trust_key(old_pub)
        self.set_keys([new_pub])
        self.signed_commit(new, "rotate signing key")
        result = self.ci()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("approver_keys changed", result.stdout)

    def test_trailer_claim_without_trailer_fails(self):
        make_slice(self.root, approval="trailer")
        commit(self.root, "Approve login slice")
        result = self.ci()
        self.assertEqual(result.returncode, 1)
        self.assertIn("Approved-by", result.stdout)

    def test_commit_msg_hook_checks_the_trailer(self):
        make_slice(self.root, approval="trailer")
        git(self.root, "add", "-A")
        msg = self.root / ".git/COMMIT_EDITMSG"
        msg.write_text("Approve login slice\n")
        self.assertEqual(run_script("cgspec_hook.py", "commit-msg", str(msg), "--root", str(self.root)).returncode, 1)
        msg.write_text("Approve login slice\n\nApproved-by: Ojefe <me@example.com>\n")
        self.assertEqual(run_script("cgspec_hook.py", "commit-msg", str(msg), "--root", str(self.root)).returncode, 0)

    def test_tier_accepts_a_trailer_approved_slice(self):
        key, pub = self.signing_key()
        self.trust_key(pub)
        make_slice(self.root, approval="trailer")
        self.signed_commit(key, "Approve\n\nApproved-by: Ojefe <me@example.com>")
        result = run_script("cgspec_hook.py", "tier", "set", "--tier", "T1", "--reason", "login work",
                            "--slice", "SLICE-001", "--root", str(self.root))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_ledger_approved_entry_needs_valid_approval_in_ci(self):
        log = self.root / "docs/_memlog.md"
        log.write_text(log.read_text() + "\n### [M-20261018-beef] 2026-10-18T00:00:00Z | tags: decision | owner: @agent | perms: public\n"
                       "- **Summary:** pick postgres\n- **Status:** Approved\n- **Approval:** A-20261018-ffff\n")
        commit(self.root, "forged decision approval")
        result = self.ci()
        self.assertEqual(result.returncode, 1)
        self.assertIn("A-20261018-ffff", result.stdout)


if __name__ == "__main__":
    unittest.main()
