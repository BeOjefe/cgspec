"""Antigravity reads workspace skills from .agents/skills/; install copies CGSpec's skills there with working links."""

from __future__ import annotations

import json
import re
import unittest

from tests.helpers import REPO, TempDir, doctor, git, run_script


class AgentSkillsTests(unittest.TestCase):
    def test_install_copies_skills_with_working_links_and_uninstall_removes_them(self):
        with TempDir() as root:
            git(root, "init", "-q")
            result = run_script("install.py", "install", "--root", str(root), "--profile", "web-workspace",
                                "--topology", "single", "--tools", "antigravity,git")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            skill = root / ".agents/skills/cgspec-ui-ux/SKILL.md"
            self.assertTrue(skill.is_file())
            self.assertTrue((root / ".agents/skills/_cgspec-docs/METHOD.md").is_file())
            for md in (root / ".agents/skills").rglob("*.md"):
                text = md.read_text()
                for ref in re.findall(r"\]\(([^)\s#]+)", text):
                    self.assertFalse(ref.startswith("file:"), f"{md} contains non-portable file:// link: {ref}")
                    if not re.match(r"^[a-z]+:", ref):
                        self.assertTrue((md.parent / ref).resolve().exists(), f"{md}: {ref}")
            self.assertIn("docs/_cgspec/01-engine/CONTRACT.md", skill.read_text())
            self.assertEqual(doctor(root).returncode, 0, doctor(root).stdout)
            out = run_script("install.py", "uninstall", "--root", str(root))
            self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
            self.assertFalse((root / ".agents").exists())

    def test_plugin_docs_and_skills_have_no_broken_or_workstation_links(self):
        for folder in (REPO / "skills", REPO / "docs", REPO / "engine"):
            for md in folder.rglob("*.md"):
                rel = md.relative_to(REPO).as_posix()
                if any(rel.startswith(p) for p in ("docs/_cgspec/02-research/Design", "docs/_cgspec/02-research/scrollcraft")):
                    continue
                text = md.read_text(encoding="utf-8")
                for ref in re.findall(r"\]\(([^)\s#]+)", text):
                    self.assertFalse(ref.startswith("file:"), f"{rel} has non-portable file:// link: {ref}")
                    if not re.match(r"^[a-z][a-z0-9+.-]*:", ref, re.I):
                        self.assertTrue((md.parent / ref).resolve().exists(), f"{rel} has broken link: {ref}")

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
            (root / ".agents/skills/foreign.js").write_text("console.log('foreign');\n")
            checked = doctor(root)
            self.assertEqual(checked.returncode, 0, checked.stdout)
            self.assertNotIn("docs/_cgspec/_archive/agent-skills", checked.stdout)
            self.assertNotIn("W-SCRIPT-OUTSIDE .agents/skills/cgspec-ui-ux", checked.stdout)
            self.assertIn("W-SCRIPT-OUTSIDE .agents/skills/foreign.js", checked.stdout)


if __name__ == "__main__":
    unittest.main()
