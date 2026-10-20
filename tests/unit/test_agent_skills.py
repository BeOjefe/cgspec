"""Antigravity reads workspace skills from .agents/skills/; install copies CGSpec's skills there with working links."""

from __future__ import annotations

import json
import re
import unittest

from tests.helpers import TempDir, doctor, git, run_script


class AgentSkillsTests(unittest.TestCase):
    def test_install_copies_skills_with_working_links_and_uninstall_removes_them(self):
        with TempDir() as root:
            git(root, "init", "-q")
            result = run_script("install.py", "install", "--root", str(root), "--profile", "web-workspace",
                                "--topology", "single", "--tools", "antigravity,git")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            skill = root / ".agents/skills/cgspec-ui-ux/SKILL.md"
            self.assertTrue(skill.is_file())
            self.assertTrue((root / ".agents/skills/_cgspec-docs/METHOD-v0.2.md").is_file())
            for md in (root / ".agents/skills").rglob("*.md"):
                for ref in re.findall(r"\]\(([^)\s#]+)", md.read_text()):
                    if not re.match(r"^[a-z]+:", ref):
                        self.assertTrue((md.parent / ref).resolve().exists(), f"{md}: {ref}")
            self.assertIn("docs/_cgspec/01-engine/CONTRACT.md", skill.read_text())
            self.assertEqual(doctor(root).returncode, 0, doctor(root).stdout)
            out = run_script("install.py", "uninstall", "--root", str(root))
            self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
            self.assertFalse((root / ".agents").exists())

    def test_upgrade_refreshes_antigravity_hook_and_skills_with_backup(self):
        with TempDir() as root:
            git(root, "init", "-q")
            result = run_script("install.py", "install", "--root", str(root), "--profile", "web-workspace",
                                "--topology", "single", "--tools", "antigravity,git")
            self.assertEqual(result.returncode, 0, result.stderr)
            hook = root / ".agents/hooks.json"
            data = json.loads(hook.read_text())
            data["cgspec"]["PreToolUse"][0]["hooks"][0]["command"] = "python3 docs/_cgspec/01-engine/cgspec_hook.py pre-tool --tool antigravity"
            hook.write_text(json.dumps(data))
            skill = root / ".agents/skills/cgspec-ui-ux/SKILL.md"
            skill.write_text(skill.read_text() + "\nLOCAL EDIT\n")
            refreshed = run_script("install.py", "upgrade", "--root", str(root))
            self.assertEqual(refreshed.returncode, 0, refreshed.stdout + refreshed.stderr)
            updated = json.loads(hook.read_text())
            self.assertIn("git rev-parse --show-toplevel", updated["cgspec"]["PreToolUse"][0]["hooks"][0]["command"])
            self.assertNotIn("LOCAL EDIT", skill.read_text())
            backups = list((root / "docs/_cgspec/_archive/agent-skills").rglob("SKILL.md"))
            self.assertTrue(any("LOCAL EDIT" in p.read_text() for p in backups))
            self.assertEqual(doctor(root).returncode, 0, doctor(root).stdout)


if __name__ == "__main__":
    unittest.main()
