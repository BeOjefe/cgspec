"""Antigravity reads workspace skills from .agents/skills/; install copies CGSpec's skills there with working links."""

from __future__ import annotations

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
            self.assertTrue((root / ".agents/skills/_cgspec-docs/METHOD-v2.md").is_file())
            for md in (root / ".agents/skills").rglob("*.md"):
                for ref in re.findall(r"\]\(([^)\s#]+)", md.read_text()):
                    if not re.match(r"^[a-z]+:", ref):
                        self.assertTrue((md.parent / ref).resolve().exists(), f"{md}: {ref}")
            self.assertIn("docs/_cgspec/01-engine/CONTRACT.md", skill.read_text())
            self.assertEqual(doctor(root).returncode, 0, doctor(root).stdout)
            out = run_script("install.py", "uninstall", "--root", str(root))
            self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
            self.assertFalse((root / ".agents").exists())


if __name__ == "__main__":
    unittest.main()
