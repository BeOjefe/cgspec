"""Enforce code atomicity, size limits, header comments, and decomposed returns."""
from __future__ import annotations

import ast
from pathlib import Path
import re

BRACE_SUFFIXES = {
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
    ".go", ".rs", ".java", ".kt", ".kts", ".swift",
    ".c", ".cc", ".cpp", ".h", ".hpp", ".cs", ".php",
    ".dart", ".scala", ".zig", ".vue", ".svelte",
}
SCRIPT_SUFFIXES = {".rb", ".sh", ".bash"}
JS_SUFFIXES = BRACE_SUFFIXES
CODE_SUFFIXES = {".py"} | BRACE_SUFFIXES | SCRIPT_SUFFIXES
PAIRS = {"(": ")", "{": "}", "[": "]"}
MAX_FILE_LINES, MAX_CODE_ONLY_LINES = 400, 350
MAX_FUNCTION_LINES, MAX_RETURN_LINES = 60, 12
MIN_COMMENTED_FILE_LINES, MIN_COMMENTED_FUNC_LINES = 15, 20
FUNC_PATS = (
    re.compile(r"(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)"),
    re.compile(r"\bfunc\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)\s*(?:\[[^\]]*\])?\s*\("),
    re.compile(r"\b(?:fn|fun)\s+(?:<[^>]*>\s*)?([A-Za-z_]\w*)\s*(?:<[^>]*>)?\s*\("),
    re.compile(r"(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:<[^>]*>)?(?:\([^{]*\)|[A-Za-z_$][\w$]*)\s*=>\s*\{"),
)


def _count_code_lines(lines: list[str]) -> int:
    """Count non-blank, non-comment lines of code."""
    pfx = ("#", "//", "/*", "*", "*/", "<!--", "-->")
    return sum(1 for ln in lines if ln.strip() and not ln.strip().startswith(pfx))


def _has_py_header(lines: list[str], tree: ast.AST | None) -> bool:
    """Verify presence of a Python module docstring or top-of-file comment."""
    if tree is not None and ast.get_docstring(tree):
        return True
    top = [ln.strip() for ln in lines if ln.strip()][:5]
    return any(ln.startswith("#") and not ln.startswith("#!") for ln in top)


def _has_brace_header(lines: list[str]) -> bool:
    """Verify presence of a top-of-file header comment in non-Python source."""
    skip = {"use strict", "<?php"}
    filtered = [
        s for s in (ln.strip() for ln in lines)
        if s and not s.startswith("#!") and s.rstrip(";").strip("\"'") not in skip
    ][:8]
    return any(ln.startswith(("//", "/*", "#", "<!--")) for ln in filtered)


def _has_nested_py_return_logic(val: ast.AST) -> bool:
    """Detect nested ternary expressions, nested comprehensions, or lambdas."""
    comps = (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)
    for node in ast.walk(val):
        if isinstance(node, ast.Lambda):
            return True
        if isinstance(node, ast.IfExp):
            if any(any(isinstance(s, ast.IfExp) for s in ast.walk(c)) for c in (node.test, node.body, node.orelse)):
                return True
        if isinstance(node, comps):
            if any(any(isinstance(s, comps) for s in ast.walk(c)) for c in ast.iter_child_nodes(node)):
                return True
    return False


def _check_py(rel: str, content: str, lines: list[str], code_lines: int, check_comments: bool, out: list[str]) -> None:
    """Parse and check Python file for atomicity, comments, and decomposed returns."""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return
    if check_comments and code_lines > MIN_COMMENTED_FILE_LINES and not _has_py_header(lines, tree):
        out.append(f"{rel}: missing top-of-file docstring or header comment explaining its atomic responsibility")
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and getattr(node, "end_lineno", None):
            length = node.end_lineno - node.lineno + 1
            if length > MAX_FUNCTION_LINES:
                out.append(f"{rel}:{node.lineno}: function '{node.name}' is {length} lines (limit {MAX_FUNCTION_LINES}, spec 7b); extract atomic helpers")
            if check_comments and length > MIN_COMMENTED_FUNC_LINES:
                first_ln = node.decorator_list[0].lineno if node.decorator_list else node.lineno
                pre = lines[max(0, first_ln - 4) : max(0, first_ln - 1)]
                hdr = lines[node.lineno - 1 : node.body[0].lineno - 1] if node.body else []
                if not (ast.get_docstring(node) or any(ln.strip().startswith("#") for ln in pre + hdr)):
                    out.append(f"{rel}:{node.lineno}: function '{node.name}' ({length} lines) lacks a docstring or leading comment")
        elif isinstance(node, ast.Return) and node.value is not None and getattr(node, "end_lineno", None):
            ret_len = node.end_lineno - node.lineno + 1
            if ret_len > MAX_RETURN_LINES:
                out.append(f"{rel}:{node.lineno}: return statement spans {ret_len} lines (limit {MAX_RETURN_LINES}); decompose into named intermediate variables first, then return only the composed variable")
            elif ret_len > 3 and _has_nested_py_return_logic(node.value):
                out.append(f"{rel}:{node.lineno}: return statement contains nested inline logic; decompose into named intermediate variables first, then return only the composed variable")


def _find_balanced(text: str, start: int, open_ch: str, close_ch: str) -> int:
    """Find matching closing character respecting strings and comments."""
    depth, i, n, in_str = 0, start, len(text), None
    while i < n:
        c = text[i]
        if in_str:
            in_str = None if c == in_str and (i == 0 or text[i - 1] != "\\") else in_str
        elif c in ("'", '"', "`"):
            in_str = c
        elif c == "/" and i + 1 < n and text[i + 1] in ("/", "*"):
            end_c = "\n" if text[i + 1] == "/" else "*/"
            pos = text.find(end_c, i + 2)
            i = n if pos == -1 else pos + len(end_c)
            continue
        elif c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _check_jsx_callbacks(rel: str, content: str, out: list[str]) -> None:
    """Flag inline multi-statement callbacks inside JSX handler attributes."""
    for m in re.finditer(r"\bon[A-Z]\w*\s*=\s*\{", content):
        b_close = _find_balanced(content, m.end() - 1, "{", "}")
        if b_close == -1:
            continue
        val = content[m.end() : b_close]
        arrow_m = re.search(r"=>\s*\{", val)
        if arrow_m:
            body_close = _find_balanced(val, arrow_m.end() - 1, "{", "}")
            if body_close != -1 and val[arrow_m.end() : body_close].count(";") >= 2:
                ln = content[: m.start()].count("\n") + 1
                out.append(f"{rel}:{ln}: inline multi-statement callback in JSX; extract a named handler variable before the return")


def _find_js_return_end(text: str, start: int) -> int:
    """Find end index of a JS return statement by balancing delimiters."""
    n, i = len(text), start
    while i < n and text[i] in (" ", "\t"):
        i += 1
    if i >= n or text[i] in (";", "\n"):
        return i + 1 if i < n and text[i] == ";" else i
    depth, in_str, seen_open = 0, None, False
    while i < n:
        c = text[i]
        if in_str:
            in_str = None if c == in_str and (i == 0 or text[i - 1] != "\\") else in_str
        elif c in ("'", '"', "`"):
            in_str = c
        elif c in PAIRS:
            depth += 1
            seen_open = True
        elif c in PAIRS.values() and depth > 0:
            depth -= 1
            if depth == 0 and seen_open:
                j = i + 1
                while j < n and text[j] in (" ", "\t"):
                    j += 1
                return j + 1 if j < n and text[j] == ";" else j
        elif not depth and (c == ";" or (c == "\n" and not seen_open)):
            return i + 1 if c == ";" else i
        i += 1
    return n


def _check_js_returns(rel: str, content: str, out: list[str]) -> None:
    """Check line count and nested callbacks/ternaries in JS return statements."""
    n, i, in_str = len(content), 0, None
    while i < n:
        c = content[i]
        if in_str:
            in_str = None if c == in_str and (i == 0 or content[i - 1] != "\\") else in_str
        elif c in ("'", '"', "`"):
            in_str = c
        elif c == "/" and i + 1 < n and content[i + 1] in ("/", "*"):
            end_c = "\n" if content[i + 1] == "/" else "*/"
            pos = content.find(end_c, i + 2)
            i = n if pos == -1 else pos + len(end_c)
            continue
        elif content.startswith("return", i):
            prev_ok = (i == 0) or (not (content[i - 1].isalnum() or content[i - 1] in "_$"))
            next_ok = (i + 6 >= n) or (not (content[i + 6].isalnum() or content[i + 6] in "_$"))
            if prev_ok and next_ok:
                ln = content[:i].count("\n") + 1
                ret_end = _find_js_return_end(content, i + 6)
                snippet = content[i:ret_end]
                ret_len = snippet.count("\n") + 1
                if ret_len > MAX_RETURN_LINES:
                    out.append(f"{rel}:{ln}: return statement spans {ret_len} lines (limit {MAX_RETURN_LINES}); decompose into named intermediate variables first, then return only the composed variable")
                elif ret_len > 3 and (re.search(r"=>\s*\{", snippet) or re.search(r"\?[\s\S]*:", snippet) or re.search(r"\.map\s*\(", snippet)):
                    out.append(f"{rel}:{ln}: return statement contains nested inline callbacks or ternaries; decompose into named intermediate variables first, then return only the composed variable")
                i = ret_end
                continue
        i += 1


def _check_js_functions(rel: str, content: str, lines: list[str], check_comments: bool, out: list[str]) -> None:
    """Validate brace-language function lengths and header comment presence."""
    seen: set[tuple[str, int]] = set()
    arrow_idx = len(FUNC_PATS) - 1
    for idx, pat in enumerate(FUNC_PATS):
        for m in pat.finditer(content):
            name, b_open = m.group(1), -1
            if idx != arrow_idx:
                p_open = content.find("(", m.end() - 1)
                if p_open != -1:
                    p_close = _find_balanced(content, p_open, "(", ")")
                    b_open = content.find("{", p_close) if p_close != -1 else -1
            else:
                b_open = m.end() - 1
            if b_open == -1:
                continue
            b_close = _find_balanced(content, b_open, "{", "}")
            if b_close == -1:
                continue
            ln = content[: m.start()].count("\n") + 1
            if (name, ln) in seen:
                continue
            seen.add((name, ln))
            length = content[:b_close].count("\n") - ln + 2
            if length > MAX_FUNCTION_LINES:
                out.append(f"{rel}:{ln}: function '{name}' is {length} lines (limit {MAX_FUNCTION_LINES}, spec 7b); split into smaller atomic functions")
            if check_comments and length > MIN_COMMENTED_FUNC_LINES:
                pre = lines[max(0, ln - 4) : max(0, ln - 1)]
                b_ln = content[:b_open].count("\n") + 1
                inside = lines[b_ln : min(len(lines), b_ln + 2)]
                if not any(("//" in l or "/*" in l or "*/" in l or l.strip().startswith("#")) for l in pre + inside):
                    out.append(f"{rel}:{ln}: function '{name}' ({length} lines) lacks a leading comment or JSDoc")


def check_code_quality(rel: str, content: str, check_comments: bool = True) -> list[str]:
    """Check code atomicity, line counts, comment coverage, and returns."""
    suffix = Path(rel).suffix.lower()
    if suffix not in CODE_SUFFIXES:
        return []
    lines = content.splitlines()
    reasons: list[str] = []
    if len(lines) > MAX_FILE_LINES:
        reasons.append(f"{rel} exceeds {MAX_FILE_LINES} lines (spec 7b); split into smaller single-purpose files")
    code_lines = _count_code_lines(lines)
    if code_lines > MAX_CODE_ONLY_LINES:
        reasons.append(f"{rel} has {code_lines} non-comment code lines (limit {MAX_CODE_ONLY_LINES}); split into smaller atomic modules")
    if suffix == ".py":
        _check_py(rel, content, lines, code_lines, check_comments, reasons)
    elif suffix in BRACE_SUFFIXES:
        if check_comments and code_lines > MIN_COMMENTED_FILE_LINES and not _has_brace_header(lines):
            reasons.append(f"{rel}: missing top-of-file docstring or header comment explaining its atomic responsibility")
        _check_jsx_callbacks(rel, content, reasons)
        _check_js_returns(rel, content, reasons)
        _check_js_functions(rel, content, lines, check_comments, reasons)
    elif suffix in SCRIPT_SUFFIXES:
        if check_comments and code_lines > MIN_COMMENTED_FILE_LINES and not _has_py_header(lines, None):
            reasons.append(f"{rel}: missing top-of-file docstring or header comment explaining its atomic responsibility")
    return reasons
