"""Spec 7b code rules applied to the engine itself: files <= 400 lines, functions <= 60, stdlib only."""

from __future__ import annotations

import ast
import sys
import unittest

from tests.helpers import ENGINE

STDLIB = set(sys.stdlib_module_names) | {"_lib"}


class CodeRuleTests(unittest.TestCase):
    def files(self):
        return [p for p in ENGINE.rglob("*.py") if "__pycache__" not in p.parts]

    def test_file_length(self):
        for path in self.files():
            with self.subTest(file=path.name):
                self.assertLessEqual(len(path.read_text().splitlines()), 400)

    def test_function_length(self):
        for path in self.files():
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    with self.subTest(function=f"{path.name}:{node.name}"):
                        self.assertLessEqual(node.end_lineno - node.lineno + 1, 60)

    def test_stdlib_only(self):
        local = {p.stem for p in ENGINE.glob("*.py")}
        for path in self.files():
            for node in ast.walk(ast.parse(path.read_text())):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    names = [node.module.split(".")[0]]
                for name in names:
                    with self.subTest(file=path.name, module=name):
                        self.assertIn(name, STDLIB | local)


if __name__ == "__main__":
    unittest.main()


class SourceHygieneTests(unittest.TestCase):
    def test_engine_source_has_no_emoji_characters(self):
        from _lib.gates import EMOJI
        for path in ENGINE.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix in (".py", ".md", ".json"):
                with self.subTest(file=path.name):
                    self.assertIsNone(EMOJI.search(path.read_text(encoding="utf-8")))


class PackageHygieneTests(unittest.TestCase):
    def test_portable_plugin_matches_engine_and_claude_version(self):
        import json
        from tests.helpers import REPO
        portable = json.loads((REPO / "plugin.json").read_text())
        claude = json.loads((REPO / ".claude-plugin/plugin.json").read_text())
        market = json.loads((REPO / ".agents/plugins/marketplace.json").read_text())
        version = (REPO / "engine/VERSION").read_text().strip()
        self.assertEqual(portable["version"], claude["version"])
        self.assertEqual(portable["version"], version)
        self.assertEqual(portable["name"], market["plugins"][0]["name"])
        self.assertEqual(market["plugins"][0]["source"], {"source": "local", "path": "./"})

    def test_no_symlinks_are_tracked_in_the_plugin(self):
        import subprocess
        from tests.helpers import REPO
        out = subprocess.run(["git", "ls-files", "-s"], cwd=REPO, capture_output=True, text=True).stdout
        links = [line.split("\t", 1)[1] for line in out.splitlines() if line.startswith("120000")]
        self.assertEqual(links, [], "spec 11 bans symlinks in the plugin")

    def test_skills_carry_no_copies_of_engine_scripts(self):
        from tests.helpers import REPO
        copies = [p.relative_to(REPO).as_posix() for p in (REPO / "skills").rglob("*.py")]
        self.assertEqual(copies, [], "skills call the engine; they never contain copies of it (spec 11)")
