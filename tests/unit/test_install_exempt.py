"""Unit tests for install_exempt deletions and renames (issue #51)."""

from __future__ import annotations

import hashlib
import json
import os
import unittest
from pathlib import Path

from tests.helpers import TempDir, git, git_project, make_slice, write_json
from _lib.commit_gate import evaluate
from _lib.commit_trust import install_exempt, is_install_commit
from _lib.gitview import View


class InstallExemptTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git_project(self.root)

    def tearDown(self):
        for p in self.root.rglob("*"):
            if p.is_file() and not p.is_symlink():
                os.chmod(p, 0o644)
        self._tmp.__exit__(None, None, None)

    def test_version_bump_install_commit_with_superseded_skill_deletion_passes(self):
        """A genuine version-bumped install commit deleting a superseded skill passes evaluate."""
        engine_dir = self.root / "docs/_cgspec/01-engine"
        project_file = self.root / "docs/_cgspec/project.json"
        owned_file = engine_dir / "owned-files.json"
        version_file = engine_dir / "VERSION"
        old_skill = self.root / ".agents/skills/_cgspec-docs/METHOD-v0.2.md"
        old_skill.parent.mkdir(parents=True, exist_ok=True)
        old_skill.write_text("# Old Method v0.2\n")

        # Base commit: version 0.2.2 with old skill in owned-files.json
        project_data = json.loads(project_file.read_text())
        project_data["cgspec_version"] = "0.2.2"
        write_json(project_file, project_data)
        version_file.write_text("0.2.2\n")
        owned_data = json.loads(owned_file.read_text())
        owned_data["cgspec_version"] = "0.2.2"
        owned_data.setdefault("adapters", {}).setdefault("antigravity", {})["skills"] = [
            ".agents/skills/_cgspec-docs/METHOD-v0.2.md"
        ]
        write_json(owned_file, owned_data)

        # Update manifest.json so engine changes check passes
        manifest_file = engine_dir / "manifest.json"
        manifest_data = json.loads(manifest_file.read_text())
        manifest_data["cgspec_version"] = "0.2.2"
        manifest_data["files"]["VERSION"] = hashlib.sha256(version_file.read_bytes()).hexdigest()
        write_json(manifest_file, manifest_data)

        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "v0.2.2 baseline")

        # Upgrade commit: version 0.3.0, delete old skill, add new skill
        project_data["cgspec_version"] = "0.3.0"
        write_json(project_file, project_data)
        version_file.write_text("0.3.0\n")

        old_skill.unlink()
        git(self.root, "rm", "-q", ".agents/skills/_cgspec-docs/METHOD-v0.2.md")

        new_skill = self.root / ".agents/skills/_cgspec-docs/METHOD.md"
        new_skill.parent.mkdir(parents=True, exist_ok=True)
        new_skill.write_text("# Method v0.3\n")

        owned_data["cgspec_version"] = "0.3.0"
        owned_data["adapters"]["antigravity"]["skills"] = [
            ".agents/skills/_cgspec-docs/METHOD.md"
        ]
        write_json(owned_file, owned_data)

        manifest_data["cgspec_version"] = "0.3.0"
        manifest_data["files"]["VERSION"] = hashlib.sha256(version_file.read_bytes()).hexdigest()
        write_json(manifest_file, manifest_data)

        git(self.root, "add", "-A")
        view = View.staged(self.root)
        self.assertTrue(is_install_commit(view))
        exempt_paths = install_exempt(view)
        self.assertIn(".agents/skills/_cgspec-docs/METHOD-v0.2.md", exempt_paths)
        self.assertIn(".agents/skills/_cgspec-docs/METHOD.md", exempt_paths)

        reasons = evaluate(self.root, view)
        self.assertEqual(reasons, [])

    def test_version_bump_install_commit_with_owned_deleted_set_passes(self):
        """A genuine version-bumped install commit with files in owned['deleted'] passes evaluate."""
        engine_dir = self.root / "docs/_cgspec/01-engine"
        project_file = self.root / "docs/_cgspec/project.json"
        owned_file = engine_dir / "owned-files.json"
        version_file = engine_dir / "VERSION"
        old_doc = self.root / "docs/OLD-TEMPLATE.md"
        old_doc.write_text("# Old Template\n")

        # Base commit: version 0.2.2
        project_data = json.loads(project_file.read_text())
        project_data["cgspec_version"] = "0.2.2"
        write_json(project_file, project_data)
        version_file.write_text("0.2.2\n")

        manifest_file = engine_dir / "manifest.json"
        manifest_data = json.loads(manifest_file.read_text())
        manifest_data["cgspec_version"] = "0.2.2"
        manifest_data["files"]["VERSION"] = hashlib.sha256(version_file.read_bytes()).hexdigest()
        write_json(manifest_file, manifest_data)

        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "v0.2.2 baseline")

        # Upgrade commit: version 0.3.0, delete old template, record in owned['deleted']
        project_data["cgspec_version"] = "0.3.0"
        write_json(project_file, project_data)
        version_file.write_text("0.3.0\n")

        old_doc.unlink()
        git(self.root, "rm", "-q", "docs/OLD-TEMPLATE.md")

        owned_data = json.loads(owned_file.read_text())
        owned_data["cgspec_version"] = "0.3.0"
        owned_data["deleted"] = {"docs/OLD-TEMPLATE.md": "superseded"}
        write_json(owned_file, owned_data)

        manifest_data["cgspec_version"] = "0.3.0"
        manifest_data["files"]["VERSION"] = hashlib.sha256(version_file.read_bytes()).hexdigest()
        write_json(manifest_file, manifest_data)

        git(self.root, "add", "-A")
        view = View.staged(self.root)
        self.assertTrue(is_install_commit(view))
        exempt_paths = install_exempt(view)
        self.assertIn("docs/OLD-TEMPLATE.md", exempt_paths)

        reasons = evaluate(self.root, view)
        self.assertEqual(reasons, [])

    def test_version_bump_install_commit_with_skill_rename_passes(self):
        """When git detects a rename of a skill during a version bump, it passes evaluate."""
        engine_dir = self.root / "docs/_cgspec/01-engine"
        project_file = self.root / "docs/_cgspec/project.json"
        owned_file = engine_dir / "owned-files.json"
        version_file = engine_dir / "VERSION"
        old_skill = self.root / ".agents/skills/_cgspec-docs/METHOD-v0.2.md"
        old_skill.parent.mkdir(parents=True, exist_ok=True)
        content = "# Method Spec\n" * 20
        old_skill.write_text(content)

        # Baseline v0.2.2
        project_data = json.loads(project_file.read_text())
        project_data["cgspec_version"] = "0.2.2"
        write_json(project_file, project_data)
        version_file.write_text("0.2.2\n")
        owned_data = json.loads(owned_file.read_text())
        owned_data["cgspec_version"] = "0.2.2"
        owned_data.setdefault("adapters", {}).setdefault("antigravity", {})["skills"] = [
            ".agents/skills/_cgspec-docs/METHOD-v0.2.md"
        ]
        write_json(owned_file, owned_data)

        manifest_file = engine_dir / "manifest.json"
        manifest_data = json.loads(manifest_file.read_text())
        manifest_data["cgspec_version"] = "0.2.2"
        manifest_data["files"]["VERSION"] = hashlib.sha256(version_file.read_bytes()).hexdigest()
        write_json(manifest_file, manifest_data)

        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "v0.2.2 baseline")

        # Upgrade commit: git mv to trigger rename status
        git(self.root, "mv", ".agents/skills/_cgspec-docs/METHOD-v0.2.md", ".agents/skills/_cgspec-docs/METHOD.md")
        project_data["cgspec_version"] = "0.3.0"
        write_json(project_file, project_data)
        version_file.write_text("0.3.0\n")

        owned_data["cgspec_version"] = "0.3.0"
        owned_data["adapters"]["antigravity"]["skills"] = [
            ".agents/skills/_cgspec-docs/METHOD.md"
        ]
        write_json(owned_file, owned_data)

        manifest_data["cgspec_version"] = "0.3.0"
        manifest_data["files"]["VERSION"] = hashlib.sha256(version_file.read_bytes()).hexdigest()
        write_json(manifest_file, manifest_data)

        git(self.root, "add", "-A")
        view = View.staged(self.root)
        self.assertTrue(is_install_commit(view))
        # Ensure git detected it as rename
        changes = view.changes()
        rename_change = [c for c in changes if c.status == "R"]
        self.assertTrue(len(rename_change) > 0)

        reasons = evaluate(self.root, view)
        self.assertEqual(reasons, [])

    def test_unrelated_deletion_outside_install_commit_fails_scope_check(self):
        """An unrelated file deletion outside an install commit fails the tier/slice check."""
        make_slice(self.root, status="Approved", scope="src/login/**")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "active slice")

        # Set tier T1 for login slice
        git(self.root, "rev-parse", "HEAD")
        tier_file = self.root / "docs/_cgspec/07-state/tier.json"
        write_json(tier_file, {"active": {"tier": "T1", "slice": "SLICE-001", "reason": "login work"}})

        # Delete an unrelated file outside slice scope (src/a.ts is in src/, not src/login/)
        (self.root / "src/a.ts").unlink()
        git(self.root, "rm", "-q", "src/a.ts")
        git(self.root, "add", "-A")

        view = View.staged(self.root)
        self.assertFalse(is_install_commit(view))
        self.assertEqual(install_exempt(view), set())

        reasons = evaluate(self.root, view)
        self.assertTrue(any("outside the scope of SLICE-001" in r for r in reasons), reasons)

    def test_unrelated_deletion_inside_install_commit_still_fails_scope_check(self):
        """Even inside a version bump commit, deleting arbitrary non-exempt code fails."""
        engine_dir = self.root / "docs/_cgspec/01-engine"
        project_file = self.root / "docs/_cgspec/project.json"
        version_file = engine_dir / "VERSION"

        # Baseline at 0.2.2
        project_data = json.loads(project_file.read_text())
        project_data["cgspec_version"] = "0.2.2"
        write_json(project_file, project_data)
        version_file.write_text("0.2.2\n")

        manifest_file = engine_dir / "manifest.json"
        manifest_data = json.loads(manifest_file.read_text())
        manifest_data["cgspec_version"] = "0.2.2"
        manifest_data["files"]["VERSION"] = hashlib.sha256(version_file.read_bytes()).hexdigest()
        write_json(manifest_file, manifest_data)

        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "v0.2.2 baseline")

        # Upgrade commit: version 0.3.0, but also illegally deletes src/a.ts
        project_data["cgspec_version"] = "0.3.0"
        write_json(project_file, project_data)
        version_file.write_text("0.3.0\n")

        (self.root / "src/a.ts").unlink()
        git(self.root, "rm", "-q", "src/a.ts")

        manifest_data["cgspec_version"] = "0.3.0"
        manifest_data["files"]["VERSION"] = hashlib.sha256(version_file.read_bytes()).hexdigest()
        write_json(manifest_file, manifest_data)

        git(self.root, "add", "-A")
        view = View.staged(self.root)
        self.assertTrue(is_install_commit(view))
        self.assertNotIn("src/a.ts", install_exempt(view))

        reasons = evaluate(self.root, view)
        self.assertTrue(any("no change tier declared for ['src/a.ts']" in r for r in reasons), reasons)


if __name__ == "__main__":
    unittest.main()
