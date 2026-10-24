#!/usr/bin/env python3
"""Verify Spec 7b rules: no CRLF, size limits, atomicity, comments, returns."""
from __future__ import annotations

import ast
from pathlib import Path
import re
import sys

JS_SUFFIXES = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
CODE_SUFFIXES = JS_SUFFIXES | {".py"}
PAIRS = {"(": ")", "{": "}", "[": "]"}
MAX_FILE_LINES, MAX_CODE_ONLY_LINES, MAX_FUNCTION_LINES, MAX_RETURN_LINES = 400, 350, 60, 12
MIN_COMMENTED_FILE_LINES, MIN_COMMENTED_FUNC_LINES = 15, 20
DECOMPOSE_MSG = "; decompose into named intermediate variables first, then return only the composed variable"

def _count_code_lines(lines: list[str]) -> int:
    """Count non-blank, non-comment lines of code."""
    pfx = ("#", "//", "/*", "*", "*/")
    return sum(1 for ln in lines if ln.strip() and not ln.strip().startswith(pfx))

def _has_header(path: Path, lines: list[str], tree: ast.AST | None) -> bool:
    """Verify presence of a top-of-file docstring or comment header."""
    if path.suffix.lower() == ".py":
        return bool(tree and ast.get_docstring(tree)) or any(l.strip().startswith("#") and not l.strip().startswith("#!") for l in lines[:8] if l.strip())
    top = [s for s in (l.strip() for l in lines) if s and not s.startswith("#!") and s.rstrip(";").strip("\"'") != "use strict"][:5]
    return any(l.startswith(("//", "/*")) for l in top)

def _has_nested_py_return_logic(val: ast.AST) -> bool:
    """Detect nested ternary expressions, nested comprehensions, or lambdas."""
    comps = (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)
    for n in ast.walk(val):
        if isinstance(n, ast.Lambda):
            return True
        if isinstance(n, ast.IfExp) and any(any(isinstance(s, ast.IfExp) for s in ast.walk(c)) for c in (n.test, n.body, n.orelse)):
            return True
        if isinstance(n, comps) and any(any(isinstance(s, comps) for s in ast.walk(c)) for c in ast.iter_child_nodes(n)):
            return True
    return False

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
        elif c == close_ch and depth:
            depth -= 1
            if not depth:
                return i
        i += 1
    return -1

def _check_py(path: Path, content: str, lines: list[str], code_lines: int, out: list[str]) -> None:
    """Parse and check Python file for atomicity, comments, and decomposed returns."""
    try:
        tree = ast.parse(content, filename=path.as_posix())
    except SyntaxError as exc:
        out.append(f"{path.as_posix()}:{exc.lineno or 1}: syntax error prevents check: {exc.msg}")
        return
    if code_lines > MIN_COMMENTED_FILE_LINES and not _has_header(path, lines, tree):
        out.append(f"{path.as_posix()}: missing top-of-file docstring or header comment explaining its atomic responsibility")
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and getattr(node, "end_lineno", None):
            length = node.end_lineno - node.lineno + 1
            if length > MAX_FUNCTION_LINES:
                out.append(f"{path.as_posix()}:{node.lineno}: function '{node.name}' is {length} lines, exceeding the 60 lines limit (spec 7b)")
            if length > MIN_COMMENTED_FUNC_LINES:
                first_ln = node.decorator_list[0].lineno if node.decorator_list else node.lineno
                hdr = lines[max(0, first_ln - 4) : (node.body[0].lineno - 1 if node.body else node.lineno)]
                if not (ast.get_docstring(node) or any(ln.strip().startswith("#") for ln in hdr)):
                    out.append(f"{path.as_posix()}:{node.lineno}: function '{node.name}' ({length} lines) lacks a docstring or leading comment")
        elif isinstance(node, ast.Return) and node.value is not None and getattr(node, "end_lineno", None):
            ret_len = node.end_lineno - node.lineno + 1
            if ret_len > MAX_RETURN_LINES:
                out.append(f"{path.as_posix()}:{node.lineno}: return statement spans {ret_len} lines (limit 12){DECOMPOSE_MSG}")
            elif ret_len > 3 and _has_nested_py_return_logic(node.value):
                out.append(f"{path.as_posix()}:{node.lineno}: return statement contains nested inline logic{DECOMPOSE_MSG}")

def _find_js_return_end(text: str, start: int) -> int:
    """Find end index of a JS return statement by balancing delimiters."""
    n, i = len(text), start
    while i < n and text[i] in (" ", "\t"):
        i += 1
    if i >= n or text[i] in (";", "\n"):
        return i + 1 if i < n and text[i] == ";" else i
    depth, in_str, seen = 0, None, False
    while i < n:
        c = text[i]
        if in_str:
            in_str = None if c == in_str and (i == 0 or text[i - 1] != "\\") else in_str
        elif c in ("'", '"', "`"):
            in_str = c
        elif c in PAIRS:
            depth, seen = depth + 1, True
        elif c in PAIRS.values() and depth > 0:
            depth -= 1
            if depth == 0 and seen:
                m = re.match(r"[ \t]*;?", text[i + 1 :])
                return i + 1 + (m.end() if m else 0)
        elif not depth and (c == ";" or (c == "\n" and not seen)):
            return i + 1 if c == ";" else i
        i += 1
    return n

def _check_js_tokens(path: Path, content: str, out: list[str]) -> None:
    """Check JSX callbacks and return statements in JS/TS source."""
    for m in re.finditer(r"\bon[A-Z]\w*\s*=\s*\{", content):
        b_close = _find_balanced(content, m.end() - 1, "{", "}")
        if b_close != -1:
            val = content[m.end() : b_close]
            arr = re.search(r"=>\s*\{", val)
            b_end = _find_balanced(val, arr.end() - 1, "{", "}") if arr else -1
            if b_end != -1 and val[arr.end() : b_end].count(";") >= 2:
                ln = content[: m.start()].count("\n") + 1
                out.append(f"{path.as_posix()}:{ln}: inline multi-statement callback in JSX; extract a named handler variable before the return")
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
        elif content.startswith("return", i) and (i == 0 or not (content[i - 1].isalnum() or content[i - 1] in "_$")) and (i + 6 >= n or not (content[i + 6].isalnum() or content[i + 6] in "_$")):
            ln = content[:i].count("\n") + 1
            ret_end = _find_js_return_end(content, i + 6)
            snip, ret_len = content[i:ret_end], content[i:ret_end].count("\n") + 1
            if ret_len > MAX_RETURN_LINES:
                out.append(f"{path.as_posix()}:{ln}: return statement spans {ret_len} lines (limit 12){DECOMPOSE_MSG}")
            elif ret_len > 3 and (re.search(r"=>\s*\{", snip) or re.search(r"\?[\s\S]*:", snip) or re.search(r"\.map\s*\(", snip)):
                out.append(f"{path.as_posix()}:{ln}: return statement contains nested inline callbacks or ternaries{DECOMPOSE_MSG}")
            i = ret_end
            continue
        i += 1

def _check_js_funcs(path: Path, content: str, lines: list[str], out: list[str]) -> None:
    """Validate JS/TS function lengths and comment coverage."""
    pats = [
        re.compile(r"(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)"),
        re.compile(r"(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:<[^>]*>)?(?:\([^{]*\)|[A-Za-z_$][\w$]*)\s*=>\s*\{"),
    ]
    seen: set[tuple[str, int]] = set()
    for idx, pat in enumerate(pats):
        for m in pat.finditer(content):
            name = m.group(1)
            p_open = content.find("(", m.end()) if idx == 0 else -1
            p_close = _find_balanced(content, p_open, "(", ")") if p_open != -1 else -1
            b_open = content.find("{", p_close) if p_close != -1 else (m.end() - 1 if idx != 0 else -1)
            b_close = _find_balanced(content, b_open, "{", "}") if b_open != -1 else -1
            if b_close == -1:
                continue
            ln = content[: m.start()].count("\n") + 1
            if (name, ln) in seen:
                continue
            seen.add((name, ln))
            length = content[:b_close].count("\n") - ln + 2
            if length > MAX_FUNCTION_LINES:
                out.append(f"{path.as_posix()}:{ln}: function '{name}' is {length} lines, exceeding the 60 lines limit (spec 7b)")
            if length > MIN_COMMENTED_FUNC_LINES:
                hdr = lines[max(0, ln - 4) : min(len(lines), content[:b_open].count("\n") + 3)]
                if not any(("//" in l or "/*" in l or "*/" in l) for l in hdr):
                    out.append(f"{path.as_posix()}:{ln}: function '{name}' ({length} lines) lacks a leading comment or JSDoc")

def check_file(path: Path) -> list[str]:
    """Check a file for CRLF endings, size limits, and code atomicity."""
    raw = path.read_bytes()
    problems = [f"{path.as_posix()}: contains CRLF line endings; convert to LF"] if b"\r\n" in raw else []
    text, suffix = raw.decode("utf-8", errors="replace"), path.suffix.lower()
    if suffix not in CODE_SUFFIXES:
        return problems
    lines, code_lines = text.splitlines(), _count_code_lines(text.splitlines())
    if len(lines) > MAX_FILE_LINES:
        problems.append(f"{path.as_posix()}: {len(lines)} lines exceeds the 400 lines per file limit (spec 7b)")
    if code_lines > MAX_CODE_ONLY_LINES:
        problems.append(f"{path.as_posix()}: {code_lines} non-comment code lines exceeds limit of 350")
    if suffix == ".py":
        _check_py(path, text, lines, code_lines, problems)
    elif suffix in JS_SUFFIXES:
        if code_lines > MIN_COMMENTED_FILE_LINES and not _has_header(path, lines, None):
            problems.append(f"{path.as_posix()}: missing top-of-file docstring or header comment explaining its atomic responsibility")
        _check_js_tokens(path, text, problems)
        _check_js_funcs(path, text, lines, problems)
    return problems

def main(argv: list[str]) -> int:
    """CLI entrypoint processing files passed as arguments."""
    if len(argv) < 2:
        print("usage: code_size_and_crlf.py <file>...", file=sys.stderr)
        return 2
    failures: list[str] = []
    for raw in argv[1:]:
        t = Path(raw)
        if t.is_file():
            try:
                failures.extend(check_file(t))
            except OSError as exc:
                print(f"cannot read {raw}: {exc}", file=sys.stderr)
                return 2
    for item in failures:
        print(item)
    return 1 if failures else 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
