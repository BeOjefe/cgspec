"""Lab finding (2026-10-19): agents were blocked from running the engine's own scripts because `2>&1`
looked like a write. Running engine scripts must work; real writes to protected paths must still be caught."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "engine"))
from _lib.shellparse import mentions  # noqa: E402

PROTECTED = ["docs/_cgspec/01-engine/", "docs/_cgspec/project.json", "docs/_cgspec/07-state/tier.json"]


class EngineCommandTests(unittest.TestCase):
    def test_running_engine_scripts_is_allowed(self):
        for cmd in ("python3 docs/_cgspec/01-engine/doctor.py 2>&1 | tail -30",
                    "python3 -I docs/_cgspec/01-engine/doctor.py 2>&1 | tail -20",
                    'python3 docs/_cgspec/01-engine/cgspec_hook.py tier set --tier T0 --reason "Remove hooks" '
                    '--files src/a.ts 2>&1; echo "exit=$?"',
                    "ls docs/_cgspec/01-engine && python3 docs/_cgspec/01-engine/memlog.py list >/dev/null"):
            self.assertEqual(mentions(cmd, PROTECTED), [], cmd)

    def test_real_writes_still_caught(self):
        for cmd in ("python3 -c \"open('docs/_cgspec/project.json','w').write('x')\"",
                    "python3 docs/_cgspec/01-engine/doctor.py > docs/_cgspec/project.json",
                    "python3 tools/evil.py docs/_cgspec/07-state/tier.json --write",
                    "python3 docs/_cgspec/01-engine/../../../evil.py docs/_cgspec/project.json -i"):
            self.assertTrue(mentions(cmd, PROTECTED), cmd)


if __name__ == "__main__":
    unittest.main()


class GuardTests(unittest.TestCase):
    """Lab finding: asked to 'remove the hooks', an agent emptied .claude/settings.json and deleted the git hooks."""

    def setUp(self):
        from tests.helpers import TempDir, git, install
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git(self.root, "init", "-q")
        install(self.root)

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def pre_tool(self, tool, **tool_input):
        from tests.helpers import hook
        return hook(self.root, "pre-tool", {"tool_name": tool, "tool_input": tool_input, "cwd": str(self.root)},
                    "--tool", "claude")

    def test_agent_cannot_disable_its_guards(self):
        for cmd in ("printf '{}' > .claude/settings.json", "rm .git/hooks/pre-commit",
                    "python3 docs/_cgspec/01-engine/install.py uninstall --root .",
                    "python3 ~/cgspec/engine/install.py upgrade --root ."):
            self.assertEqual(self.pre_tool("Bash", command=cmd).returncode, 2, cmd)
        self.assertEqual(self.pre_tool("Write", file_path=str(self.root / ".claude/settings.json"),
                                       content="{}").returncode, 2)

    def test_reading_guards_and_verifying_install_still_allowed(self):
        for cmd in ("cat .claude/settings.json", "ls .git/hooks", "python3 docs/_cgspec/01-engine/install.py verify"):
            self.assertEqual(self.pre_tool("Bash", command=cmd).returncode, 0, cmd)
