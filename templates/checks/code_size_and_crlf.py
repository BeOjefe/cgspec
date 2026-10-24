#!/usr/bin/env python3
"""Verify Spec 7b code rules on changed files: no CRLF, files <= 400 lines, Python functions <= 60 lines.

Registered with --applies-to naming code globs (for example 'src/**'); the engine passes changed file paths.
Exit 0 when all checked files conform, 1 when any rule is violated, 2 when arguments or files cannot be read.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

MAX_FILE_LINES = 400
MAX_FUNCTION_LINES = 60


def check_file(path: Path) -> list[str]:
    raw = path.read_bytes()
    problems = []
    if b"\r\n" in raw:
        problems.append(f"{path.as_posix()}: contains CRLF line endings; convert to LF")
    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines()
    if len(lines) > MAX_FILE_LINES:
        problems.append(f"{path.as_posix()}: {len(lines)} lines exceeds the {MAX_FILE_LINES} lines per file limit (spec 7b)")
    if path.suffix.lower() == ".py":
        try:
            tree = ast.parse(text, filename=path.as_posix())
        except SyntaxError as exc:
            problems.append(f"{path.as_posix()}:{exc.lineno or 1}: syntax error prevents function-length check: {exc.msg}")
            return problems
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and getattr(node, "end_lineno", None):
                length = node.end_lineno - node.lineno + 1
                if length > MAX_FUNCTION_LINES:
                    problems.append(
                        f"{path.as_posix()}:{node.lineno}: function '{node.name}' is {length} lines, "
                        f"exceeding the {MAX_FUNCTION_LINES} lines limit (spec 7b)"
                    )
    return problems


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: code_size_and_crlf.py <file>...", file=sys.stderr)
        return 2
    failures = []
    for raw in argv[1:]:
        target = Path(raw)
        if not target.is_file():
            continue
        try:
            failures.extend(check_file(target))
        except OSError as exc:
            print(f"cannot read {raw}: {exc}", file=sys.stderr)
            return 2
    for item in failures:
        print(item)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
