"""Per-command rules for shellparse: which arguments a command writes."""

from __future__ import annotations

import posixpath
import re

from .shellparse import (ALL_ARGS, INTERPRETER, LAST_ARG, MODE_FIRST, REDIRECTS, SHELLS, _option_value,
                         _strip_prefixes)


def _git(rest: list[str], cwd: str) -> tuple[list[str], list[str]]:
    sub = rest[0] if rest else ""
    if sub in ("checkout", "restore") and "--" in rest:
        return rest[rest.index("--") + 1:], []
    if sub == "restore":
        return [a for a in rest[1:] if not a.startswith("-")], []
    if sub in ("apply", "am"):
        return [], [cwd]
    return [], []


def segment(seg: list[str], cwd: str, recurse) -> tuple[list[str], list[str], list[str], list[str]]:
    """(write targets, delete targets, inline code, broad dirs) for one simple command."""
    targets, deletes, inline, broad, args = [], [], [], [], []
    i = 0
    while i < len(seg):
        if REDIRECTS.match(seg[i]) and i + 1 < len(seg):
            targets.append(seg[i + 1])
            i += 2
        elif seg[i] in ("<", "<<", "<<<", "<<-") and i + 1 < len(seg):
            i += 2
        else:
            args.append(seg[i])
            i += 1
    args = _strip_prefixes(args)
    if not args:
        return targets, deletes, inline, broad
    name, rest = posixpath.basename(args[0]), args[1:]
    files = [a for a in rest if not a.startswith("-")]
    if name in SHELLS and _option_value(rest, "-c"):
        sub_t, sub_d, sub_i, sub_b = recurse(_option_value(rest, "-c"), cwd)
        return targets + sub_t, deletes + sub_d, inline + sub_i, broad + sub_b
    if name == "sed" and any(a.startswith("-i") or a == "--in-place" for a in rest):
        targets += files[1:] if not any(a in ("-e", "-f") for a in rest) else files
    elif name in ("perl", "ruby") and any(re.match(r"^-\w*i", a) for a in rest):
        code = _option_value(rest, "-e", "-pe", "-pie", "-ne")
        targets += [f for f in files if f != code]
        inline += [code] if code else []
    elif name in ("awk", "gawk") and "inplace" in rest:
        targets += files[1:]
    elif name in ALL_ARGS:
        (deletes if name in ("rm", "unlink", "rmdir", "shred") else targets).extend(files)
    elif name in MODE_FIRST:
        targets += files[1:]
    elif name in LAST_ARG:
        dest = _option_value(rest, "-t")
        targets.append(dest) if dest else (targets.append(files[-1]) if files else None)
    elif name == "dd":
        targets += [a[3:] for a in rest if a.startswith("of=")]
    elif name == "tar" and any(a.startswith("-x") or a == "x" or (not a.startswith("-") and "x" in a and rest.index(a) == 0) for a in rest):
        broad.append(_option_value(rest, "-C", "--directory") or ".")
    elif name == "find" and any(a in ("-delete", "-exec", "-execdir", "-ok") for a in rest):
        roots = rest[:next((k for k, a in enumerate(rest) if a.startswith("-")), len(rest))] or ["."]
        names = [rest[k + 1] for k, a in enumerate(rest[:-1]) if a in ("-name", "-iname", "-path", "-ipath")]
        broad += [root + ("\0" + "\0".join(names) if names else "") for root in roots]
    elif name == "git":
        found_t, found_b = _git(rest, cwd)
        targets += found_t
        broad += found_b
    elif INTERPRETER.match(name):
        code = _option_value(rest, "-c", "-e", "--eval", "-p")
        inline += [code] if code else []
    return targets, deletes, inline, broad
