"""Governance edits are caught before tool use and at the staged commit gate."""

from __future__ import annotations

import os
import unittest
from pathlib import Path

from tests.helpers import ENGINE, TempDir, claude_payload, git, git_project, hook


class GovernancePathTests(unittest.TestCase):
    def test_fixed_floor_cannot_be_narrowed_by_project_classes(self):
        from _lib.gates import Context
        from _lib.gates import protected_list
        from _lib.governance_paths import governance_path

        with TempDir() as root:
            ctx = Context(root, project={"path_classes": {}})
            for rel in (".github/workflows/ci.yml", ".github/workflows/another.yaml",
                        ".github/actions/check/action.yml", ".github/cgspec-select.sh",
                        ".githooks/pre-commit", ".git/hooks/pre-push", ".git/config",
                        ".claude/settings.json", ".agents/hooks.json", ".github/CODEOWNERS"):
                with self.subTest(rel=rel):
                    self.assertTrue(governance_path(rel))
                    self.assertIsNotNone(ctx.protected(rel))
            self.assertFalse(governance_path("src/ordinary.ts"))
            self.assertIsNone(ctx.protected("src/ordinary.ts"))
            self.assertIn(".github/workflows/", protected_list(ctx))

    def test_staged_add_edit_delete_and_rename_are_blocked(self):
        from _lib.commit_gate import evaluate
        from _lib.gitview import View

        def blocked(message):
            git(root, "add", "-A")
            staged_blocked = any("APPROVAL_REQUIRED" in r for r in evaluate(root, View.staged(root)))
            git(root, "commit", "-q", "-m", message)  # bypass the hook to set up each probe
            head = git(root, "rev-parse", "HEAD").stdout.strip()
            commit_blocked = any("APPROVAL_REQUIRED" in r for r in evaluate(root, View.commit(root, head)))
            return staged_blocked and commit_blocked

        with TempDir() as root:
            git_project(root)
            path = root / ".github/workflows/ci.yml"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("name: ci\n")
            self.assertTrue(blocked("add workflow"))
            path.write_text("name: changed\n")
            self.assertTrue(blocked("change workflow"))
            git(root, "mv", ".github/workflows/ci.yml", ".github/workflows/other.yml")
            self.assertTrue(blocked("rename workflow"))
            git(root, "rm", "-q", ".github/workflows/other.yml")
            self.assertTrue(blocked("delete workflow"))

    def test_pretool_shell_cannot_rewrite_workflow(self):
        with TempDir() as root:
            git_project(root)
            payload = claude_payload(root, "Bash", command="echo 'exit 0' > .github/workflows/ci.yml")
            result = hook(root, "pre-tool", payload, "--tool", "claude")
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

    def test_project_deletion_then_restore_does_not_reset_bootstrap(self):
        from _lib.ci_gate import run
        from _lib.commit_gate import evaluate
        from _lib.gitview import View

        with TempDir() as root:
            git_project(root)
            workflow = root / ".github/workflows/ci.yml"
            workflow.parent.mkdir(parents=True, exist_ok=True)
            workflow.write_text("name: baseline\n")
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "existing workflow")
            base = git(root, "rev-parse", "HEAD").stdout.strip()
            project = root / "docs/_cgspec/project.json"
            original = project.read_bytes()
            git(root, "rm", "-q", "docs/_cgspec/project.json")
            git(root, "commit", "-q", "-m", "delete project")
            deleted = git(root, "rev-parse", "HEAD").stdout.strip()
            self.assertTrue(any("cannot be deleted" in r for r in evaluate(root, View.commit(root, deleted))))
            project.write_bytes(original)
            workflow.write_text("name: skip checks\n")
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "restore project and weaken workflow")
            restored = git(root, "rev-parse", "HEAD").stdout.strip()
            reasons = evaluate(root, View.commit(root, restored))
            self.assertTrue(any("not a new installation" in r for r in reasons), reasons)
            self.assertTrue(any("APPROVAL_REQUIRED" in r for r in reasons), reasons)
            problems, _ = run(root, base, release_dir=ENGINE.parent)
            self.assertTrue(any("APPROVAL_REQUIRED" in p for p in problems), problems)

    def test_release_authority_and_codeowners_require_separate_approval(self):
        import json
        from _lib.commit_gate import evaluate
        from _lib.gitview import View

        with TempDir() as root:
            git_project(root)
            project = root / "docs/_cgspec/project.json"
            data = json.loads(project.read_text())
            data["plugin_source"] = "/tmp/untrusted-plugin"
            project.write_text(json.dumps(data) + "\n")
            owners = root / ".github/CODEOWNERS"
            owners.parent.mkdir(parents=True, exist_ok=True)
            owners.write_text("# no ownership rules\n")
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "change trust controls")
            head = git(root, "rev-parse", "HEAD").stdout.strip()
            reasons = evaluate(root, View.commit(root, head))
            self.assertTrue(any("plugin_source" in r and "APPROVAL_REQUIRED" in r for r in reasons), reasons)
            self.assertTrue(any("CODEOWNERS" in r and "APPROVAL_REQUIRED" in r for r in reasons), reasons)

    def test_commit_msg_demands_trailer_for_governance_change(self):
        with TempDir() as root:
            git_project(root)
            workflow = root / ".github/workflows/ci.yml"
            workflow.parent.mkdir(parents=True, exist_ok=True)
            workflow.write_text("name: ci\n")
            git(root, "add", "-A")
            message = root / "msg.txt"
            message.write_text("change workflow\n")
            refused = hook(root, "commit-msg", None, str(message))
            self.assertEqual(refused.returncode, 1, refused.stdout + refused.stderr)
            self.assertIn("Approved-by", refused.stdout)
            message.write_text("change workflow\n\nApproved-by: Me <me@example.com>\n")
            accepted = hook(root, "commit-msg", None, str(message))
            self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)

    def test_signed_trailer_from_a_trusted_key_authorizes_governance_change(self):
        import json
        import subprocess
        from _lib.commit_gate import evaluate
        from _lib.gitview import View

        with TempDir() as root:
            git_project(root)
            key = root.parent / f"{root.name}-approver"
            subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True)
            pub = Path(str(key) + ".pub").read_text().strip()
            project = root / "docs/_cgspec/project.json"
            os.chmod(project, 0o644)
            data = json.loads(project.read_text())
            data["approver_keys"] = [pub]
            project.write_text(json.dumps(data, indent=2) + "\n")
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "trust approver key")
            workflow = root / ".github/workflows/ci.yml"
            workflow.parent.mkdir(parents=True, exist_ok=True)
            workflow.write_text("name: ci\n")
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "unsigned\n\nApproved-by: Me <me@example.com>")
            unsigned = git(root, "rev-parse", "HEAD").stdout.strip()
            reasons = evaluate(root, View.commit(root, unsigned))
            self.assertTrue(any("APPROVAL_REQUIRED" in r for r in reasons), reasons)
            git(root, "reset", "-q", "--soft", "HEAD~1")
            git(root, "-c", "gpg.format=ssh", "-c", f"user.signingkey={key}", "commit", "-q", "-S",
                "-m", "signed\n\nApproved-by: Me <me@example.com>")
            signed = git(root, "rev-parse", "HEAD").stdout.strip()
            reasons = evaluate(root, View.commit(root, signed))
            self.assertFalse(any("APPROVAL_REQUIRED" in r for r in reasons), reasons)

    def test_canonical_adapter_refresh_is_allowed_while_weakening_is_blocked(self):
        import json
        from _lib.commit_gate import evaluate
        from _lib.gitview import View
        from tests.helpers import run_script

        with TempDir() as root:
            git_project(root)
            claude_settings = root / ".claude/settings.json"
            data = json.loads(claude_settings.read_text())
            del data["hooks"]["PreToolUse"]
            claude_settings.write_text(json.dumps(data, indent=2) + "\n")
            git(root, "add", ".claude/settings.json")
            self.assertTrue(any("APPROVAL_REQUIRED" in r for r in evaluate(root, View.staged(root))))
            git(root, "commit", "-q", "-m", "older adapter missing PreToolUse")
            res = run_script("install.py", "upgrade", "--root", str(root))
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            git(root, "add", ".claude/settings.json")
            reasons = evaluate(root, View.staged(root))
            self.assertFalse(any("APPROVAL_REQUIRED" in r for r in reasons), reasons)


if __name__ == "__main__":
    unittest.main()
