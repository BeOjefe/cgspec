"""Path globs with '**' (any depth), '*' (within one segment) and '?'. Paths use '/'."""

from __future__ import annotations

import re
from functools import lru_cache


@lru_cache(maxsize=1024)
def _compile(pattern: str) -> re.Pattern[str]:
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append(r"(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(r".*")
            i += 2
        elif pattern[i] == "*":
            out.append(r"[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append(r"[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def normalize(path: str) -> str:
    path = path.replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    return path


def match(path: str, pattern: str) -> bool:
    return bool(_compile(pattern).match(normalize(path)))


def match_any(path: str, patterns: list[str]) -> bool:
    return any(match(path, p) for p in patterns)
