"""Unit tests for code atomicity and decomposed-return gate checks."""
from __future__ import annotations

import unittest
from tests.helpers import REPO
from _lib.code_atomicity import (
    CODE_SUFFIXES,
    JS_SUFFIXES,
    MAX_CODE_ONLY_LINES,
    MAX_FILE_LINES,
    MAX_FUNCTION_LINES,
    MAX_RETURN_LINES,
    MIN_COMMENTED_FILE_LINES,
    MIN_COMMENTED_FUNC_LINES,
    check_code_quality,
)


class CodeAtomicityTests(unittest.TestCase):
    def test_sticky_note_bad_snippet_fails_and_decomposed_passes(self):
        bad_snippet = (
            "// StickyNote component with inline logic\n"
            "import React from 'react';\n"
            "\n"
            "export function StickyNote({ r }: Props) {\n"
            "  return (\n"
            "    <div className=\"note\">\n"
            "      <button onClick={(e) => { e.preventDefault(); e.stopPropagation(); togglePlaceCollapse(r.id); }}>\n"
            "        {r.isCollapsed ? (<button>Expand</button>) : (<span />)}\n"
            "      </button>\n"
            "    </div>\n"
            "  );\n"
            "}\n"
        )
        bad_issues = check_code_quality("src/components/StickyNote.tsx", bad_snippet)
        self.assertTrue(
            any("inline multi-statement callback in JSX" in issue for issue in bad_issues),
            f"Expected inline JSX callback failure, got: {bad_issues}",
        )
        self.assertTrue(
            any("nested inline callbacks or ternaries" in issue for issue in bad_issues),
            f"Expected nested ternary/callback return failure, got: {bad_issues}",
        )

        decomposed_snippet = (
            "// StickyNote component with decomposed atomic handlers\n"
            "import React from 'react';\n"
            "\n"
            "export function StickyNote({ r }: Props) {\n"
            "  const handleToggle = (e: React.MouseEvent) => {\n"
            "    e.preventDefault();\n"
            "    e.stopPropagation();\n"
            "    togglePlaceCollapse(r.id);\n"
            "  };\n"
            "  const chevron = r.isCollapsed ? <button>Expand</button> : <span />;\n"
            "  const row = (\n"
            "    <div className=\"note\">\n"
            "      <button onClick={handleToggle}>\n"
            "        {chevron}\n"
            "      </button>\n"
            "    </div>\n"
            "  );\n"
            "  return row;\n"
            "}\n"
        )
        good_issues = check_code_quality("src/components/StickyNote.tsx", decomposed_snippet)
        self.assertEqual(good_issues, [], f"Decomposed snippet should pass, got: {good_issues}")

    def test_functions_over_60_lines_fail(self):
        py_func = (
            "# Top comment\n"
            "def huge_py():\n"
            + "".join(f"    val_{i} = {i}\n" for i in range(65))
            + "    return val_0\n"
        )
        py_issues = check_code_quality("pkg/mod.py", py_func)
        self.assertTrue(
            any("function 'huge_py' is 67 lines (limit 60, spec 7b)" in issue for issue in py_issues),
            f"Expected >60 lines error for python function, got: {py_issues}",
        )

        tsx_func = (
            "// Top header\n"
            "export function hugeTsx() {\n"
            + "".join(f"  const val_{i} = {i};\n" for i in range(65))
            + "  return 0;\n"
            "}\n"
        )
        tsx_issues = check_code_quality("src/huge.tsx", tsx_func)
        self.assertTrue(
            any("function 'hugeTsx' is 68 lines (limit 60, spec 7b)" in issue for issue in tsx_issues),
            f"Expected >60 lines error for TSX function, got: {tsx_issues}",
        )

    def test_files_over_400_lines_fail(self):
        big_py = "# Top doc\n" + "".join(f"X_{i} = {i}\n" for i in range(405))
        issues_py = check_code_quality("big.py", big_py)
        self.assertTrue(
            any("exceeds 400 lines (spec 7b)" in issue for issue in issues_py),
            f"Expected file > 400 lines error, got: {issues_py}",
        )

        big_tsx = "// Header\n" + "".join(f"export const V_{i} = {i};\n" for i in range(405))
        issues_tsx = check_code_quality("big.tsx", big_tsx)
        self.assertTrue(
            any("exceeds 400 lines (spec 7b)" in issue for issue in issues_tsx),
            f"Expected file > 400 lines error, got: {issues_tsx}",
        )

    def test_files_over_350_non_comment_lines_fail(self):
        lines_py = ["# Comment line\n"] + [f"x_{i} = {i}\n" for i in range(360)]
        issues_py = check_code_quality("many_code.py", "".join(lines_py))
        self.assertTrue(
            any("has 360 non-comment code lines (limit 350)" in issue for issue in issues_py),
            f"Expected > 350 code lines error, got: {issues_py}",
        )

        lines_tsx = ["// Comment header\n"] + [f"export const c_{i} = {i};\n" for i in range(360)]
        issues_tsx = check_code_quality("many_code.tsx", "".join(lines_tsx))
        self.assertTrue(
            any("has 360 non-comment code lines (limit 350)" in issue for issue in issues_tsx),
            f"Expected > 350 code lines error, got: {issues_tsx}",
        )

    def test_files_over_15_code_lines_without_header_fail(self):
        uncommented_py = "".join(f"a_{i} = {i}\n" for i in range(20))
        issues_py = check_code_quality("no_head.py", uncommented_py)
        self.assertTrue(
            any("missing top-of-file docstring or header comment" in issue for issue in issues_py),
            f"Expected missing header comment, got: {issues_py}",
        )

        short_py = "x = 1\ny = 2\n"
        self.assertEqual(check_code_quality("short.py", short_py), [])

        uncommented_tsx = "".join(f"export const a_{i} = {i};\n" for i in range(20))
        issues_tsx = check_code_quality("no_head.tsx", uncommented_tsx)
        self.assertTrue(
            any("missing top-of-file docstring or header comment" in issue for issue in issues_tsx),
            f"Expected missing header comment for tsx, got: {issues_tsx}",
        )

        short_tsx = "export const a = 1;\n"
        self.assertEqual(check_code_quality("short.tsx", short_tsx), [])

    def test_functions_over_20_lines_without_comment_fail(self):
        uncommented_fn_py = (
            "# Top comment\n"
            "\n\n\n\n"  # keep the header out of the function's leading-comment window
            "def fn_without_doc():\n"
            + "".join(f"    v_{i} = {i}\n" for i in range(22))
            + "    return v_0\n"
        )
        issues_py = check_code_quality("undoc.py", uncommented_fn_py)
        self.assertTrue(
            any("lacks a docstring or leading comment" in issue for issue in issues_py),
            f"Expected function comment warning, got: {issues_py}",
        )

        commented_fn_py = (
            "# Top comment\n"
            "def fn_with_doc():\n"
            "    \"\"\"This is a valid docstring.\"\"\"\n"
            + "".join(f"    v_{i} = {i}\n" for i in range(22))
            + "    return v_0\n"
        )
        self.assertEqual(check_code_quality("doc.py", commented_fn_py), [])

        uncommented_fn_tsx = (
            "// Top header\n"
            "\n\n\n\n"
            "export function fnWithoutComment() {\n"
            + "".join(f"  const v_{i} = {i};\n" for i in range(22))
            + "  return 0;\n"
            "}\n"
        )
        issues_tsx = check_code_quality("undoc.tsx", uncommented_fn_tsx)
        self.assertTrue(
            any("lacks a leading comment or JSDoc" in issue for issue in issues_tsx),
            f"Expected TSX function comment warning, got: {issues_tsx}",
        )

        commented_fn_tsx = (
            "// Top header\n"
            "// Valid leading helper comment\n"
            "export function fnWithComment() {\n"
            + "".join(f"  const v_{i} = {i};\n" for i in range(22))
            + "  return 0;\n"
            "}\n"
        )
        self.assertEqual(check_code_quality("doc.tsx", commented_fn_tsx), [])

    def test_return_statement_length_and_nested_logic(self):
        long_return_py = (
            "# Module header\n"
            "def test_ret():\n"
            "    return (\n"
            + "".join(f"        {i} +\n" for i in range(14))
            + "        0\n"
            "    )\n"
        )
        issues_long_ret = check_code_quality("ret.py", long_return_py)
        self.assertTrue(
            any("return statement spans 17 lines (limit 12)" in issue for issue in issues_long_ret),
            f"Expected return spans >12 lines error, got: {issues_long_ret}",
        )

        nested_ifexp_py = (
            "# Module header\n"
            "def test_nested(a, b, c):\n"
            "    return (\n"
            "        1 if a\n"
            "        else 2 if b\n"
            "        else 3\n"
            "    )\n"
        )
        issues_ifexp = check_code_quality("ifexp.py", nested_ifexp_py)
        self.assertTrue(
            any("return statement contains nested inline logic" in issue for issue in issues_ifexp),
            f"Expected nested inline logic return error, got: {issues_ifexp}",
        )

        nested_comp_py = (
            "# Module header\n"
            "def test_comp(matrix):\n"
            "    return [\n"
            "        [cell * 2 for cell in row]\n"
            "        for row in matrix\n"
            "    ]\n"
        )
        issues_comp = check_code_quality("comp.py", nested_comp_py)
        self.assertTrue(
            any("return statement contains nested inline logic" in issue for issue in issues_comp),
            f"Expected nested comprehension return error, got: {issues_comp}",
        )

    def test_non_code_files_ignored(self):
        self.assertEqual(check_code_quality("data.json", '{"key": "value"}'), [])
        self.assertEqual(check_code_quality("docs.md", "# Documentation\nMore info"), [])


if __name__ == "__main__":
    unittest.main()
