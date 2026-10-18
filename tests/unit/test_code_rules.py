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
