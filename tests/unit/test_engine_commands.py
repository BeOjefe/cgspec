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
