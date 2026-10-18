"""Best-effort detection of files a shell command writes to (spec 8: the tool hook is a first
line of defence; the read-only disk lock, commit hook and CI are the real guarantee)."""

from __future__ import annotations

import posixpath
import re
import shlex

SEPARATORS = {";", "&&", "||", "|", "&", "\n"}
REDIRECTS = re.compile(r"^(\d*|&)>>?$")
ALL_ARGS = {"rm", "touch", "truncate", "unlink", "rmdir", "shred", "tee"}
MODE_FIRST = {"chmod", "chown", "chgrp"}
LAST_ARG = {"cp", "mv", "install", "ln", "rsync", "scp"}
INLINE = {"python", "python3", "node", "perl", "ruby", "bash", "sh", "zsh", "deno", "bun"}
WRITE_HINTS = re.compile(r"""(['"]\s*[wax]\+?b?\s*['"]|write|unlink|rename|replace|chmod|remove|rmtree|truncate|>)""")


def _tokens(command: str) -> list[str]:
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|<>")
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        return list(lexer)
    except ValueError:  # unbalanced quotes: fall back to a plain split
        return command.split()


def _segments(tokens: list[str]) -> list[list[str]]:
    out, current = [], []
    for tok in tokens:
        if tok in SEPARATORS:
            if current:
                out.append(current)
            current = []
        else:
            current.append(tok)
    if current:
        out.append(current)
    return out


def _segment_targets(seg: list[str]) -> tuple[list[str], list[str]]:
    """Return (write targets, inline code strings) for one simple command."""
    targets, inline, args = [], [], []
    i = 0
    while i < len(seg):
        tok = seg[i]
        if REDIRECTS.match(tok) and i + 1 < len(seg):
            targets.append(seg[i + 1])
            i += 2
            continue
        if tok in ("<", "<<", "<<<") and i + 1 < len(seg):
            i += 2
            continue
        args.append(tok)
        i += 1
    while args and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", args[0]):  # leading VAR=value
        args = args[1:]
    if args and args[0] in ("sudo", "env", "nice", "time", "command", "exec"):
        args = args[1:]
    if not args:
        return targets, inline
    name, rest = posixpath.basename(args[0]), args[1:]
    files = [a for a in rest if not a.startswith("-")]
    if name == "sed" and any(a.startswith("-i") or a == "--in-place" for a in rest):
        targets += files[1:] if not any(a in ("-e", "-f") for a in rest) else files
    elif name in ALL_ARGS:
        targets += files
    elif name in MODE_FIRST:
        targets += files[1:]
    elif name in LAST_ARG:
        if "-t" in rest and rest.index("-t") + 1 < len(rest):
            targets.append(rest[rest.index("-t") + 1])
        elif files:
            targets.append(files[-1])
    elif name == "dd":
        targets += [a[3:] for a in rest if a.startswith("of=")]
    elif name == "git" and rest[:1] in (["checkout"], ["restore"]):
        targets += [a for a in files[1:] if a != "--"]
    elif re.match(r"^(python|python3(\.\d+)?|node|perl|ruby|bash|sh|zsh|deno|bun)$", name):
        for flag in ("-c", "-e", "--eval"):
            if flag in rest and rest.index(flag) + 1 < len(rest):
                inline.append(rest[rest.index(flag) + 1])
    return targets, inline


def write_targets(command: str, cwd: str = ".") -> tuple[list[str], list[str]]:
    """Paths (normalised against cwd, following `cd`) the command may write, plus inline code."""
    targets, inline = [], []
    here = cwd
    for seg in _segments(_tokens(command)):
        if seg and seg[0] == "cd":
            dest = seg[1] if len(seg) > 1 else "~"
            here = dest if dest.startswith(("/", "~")) else posixpath.normpath(posixpath.join(here, dest))
            continue
        found, code = _segment_targets(seg)
        targets += [t if t.startswith(("/", "~")) else posixpath.normpath(posixpath.join(here, t)) for t in found]
        inline += code
    return targets, inline


def inline_writes(code: str, candidates: list[str]) -> list[str]:
    """Protected paths an inline script mentions, when it also looks like it writes."""
    if not WRITE_HINTS.search(code):
        return []
    return [c for c in candidates if c in code or posixpath.basename(c) in code]
