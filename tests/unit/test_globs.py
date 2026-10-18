from __future__ import annotations

import unittest

from tests import helpers  # noqa: F401
from _lib.globs import match, match_any


class GlobTests(unittest.TestCase):
    CASES = [
        ("src/**", "src/a.ts", True),
        ("src/**", "src/deep/x/a.ts", True),
        ("src/**", "srcx/a.ts", False),
        ("**/auth/**", "src/auth/login.ts", True),
        ("**/auth/**", "auth/x.py", True),
        ("**/*.test.*", "src/a.test.ts", True),
        ("**/*.test.*", "a.test.ts", True),
        ("package.json", "package.json", True),
        ("package.json", "apps/web/package.json", False),
        ("requirements*.txt", "requirements-dev.txt", True),
        ("docs/*.md", "docs/a.md", True),
        ("docs/*.md", "docs/x/a.md", False),
        ("packages/*/src/**", "packages/api/src/a.ts", True),
    ]

    def test_cases(self):
        for pattern, path, expected in self.CASES:
            with self.subTest(pattern=pattern, path=path):
                self.assertEqual(match(path, pattern), expected)

    def test_match_any(self):
        self.assertTrue(match_any("src/a.ts", ["lib/**", "src/**"]))
        self.assertFalse(match_any("src/a.ts", []))


if __name__ == "__main__":
    unittest.main()
