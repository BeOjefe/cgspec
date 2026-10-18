"""Best-effort detection of files a shell command writes to (spec 8: the tool hook is a first
line of defence; the read-only disk lock, commit hook and CI are the real guarantee).

write_targets() returns (targets, inline_code, broad_dirs):
  targets     paths the command writes or deletes, normalised against cwd (following `cd`)
  inline_code code strings passed to interpreters (-c/-e, heredocs) to scan for protected paths
  broad_dirs  folders a command may change wholesale (tar -x, git apply, find -delete/-exec)
"""

from __future__ import annotations

import posixpath
import re
import shlex

SEPARATORS = {";", "&&", "||", "|", "&"}
REDIRECTS = re.compile(r"^(\d*|&)>>?$")
ALL_ARGS = {"rm", "touch", "truncate", "unlink", "rmdir", "shred", "tee"}
DELETES = {"rm", "unlink", "rmdir", "shred"}
MODE_FIRST = {"chmod", "chown", "chgrp"}
LAST_ARG = {"cp", "mv", "install", "ln", "rsync", "scp"}
SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
INTERPRETER = re.compile(r"^(python(\d(\.\d+)?)?|node|nodejs|perl|ruby|deno|bun|php|lua)$")
WRAPPERS = re.compile(r"(^|[\s;&|(`])(python\d?(\.\d+)?|node|perl|ruby|deno|bun|php|xargs|find|awk|gawk|eval|bash|sh|zsh)\b")
WRITE_HINTS = re.compile(r"""(['"]\s*[wax]\+?b?\s*['"]|write|unlink|rename|replace|chmod|remove|rmtree|truncate|>|-delete|-exec|\brm\b|\bmv\b|\bcp\b|-i\b)""")
HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")


def _tokens(command: str) -> list[str]:
    command = command.replace(">|", ">")
    command = re.sub(r"\$\(|`|\(|\)", " ; ", command)  # subshells and substitutions run commands too
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
    return out + ([current] if current else [])


def split_heredocs(command: str) -> tuple[list[str], list[str]]:
    """Command lines, and heredoc bodies (treated as inline code)."""
    lines, bodies, i = command.split("\n"), [], 0
    out = []
    while i < len(lines):
        line = lines[i]
        out.append(line)
        marker = HEREDOC.search(line)
        i += 1
        if marker:
            body = []
            while i < len(lines) and lines[i].strip() != marker.group(2):
                body.append(lines[i])
                i += 1
            bodies.append("\n".join(body))
            i += 1
    return out, bodies


def _strip_prefixes(args: list[str]) -> list[str]:
    while args and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", args[0]):  # leading VAR=value
        args = args[1:]
    while args and args[0] in ("sudo", "env", "nice", "time", "command", "exec", "nohup"):
        args = args[1:]
    return args


def _option_value(rest: list[str], *flags: str) -> str | None:
    for flag in flags:
        if flag in rest and rest.index(flag) + 1 < len(rest):
            return rest[rest.index(flag) + 1]
    return None


def _norm(path: str, here: str) -> str:
    return path if path.startswith(("/", "~")) else posixpath.normpath(posixpath.join(here, path))


def write_targets(command: str, cwd: str = ".") -> tuple[list[str], list[str], list[str], list[str]]:
    """(write targets, delete targets, inline code, broad dirs), paths normalised against cwd."""
    from .shellparse_cmds import segment
    lines, bodies = split_heredocs(command)
    targets, deletes, inline, broad = [], [], list(bodies), []
    here = cwd
    for line in lines:
        for seg in _segments(_tokens(line)):
            if seg and seg[0] == "cd":
                dest = seg[1] if len(seg) > 1 else "~"
                here = dest if dest.startswith(("/", "~")) else posixpath.normpath(posixpath.join(here, dest))
                continue
            t, d, code, b = segment(seg, here, write_targets)
            targets += [_norm(p, here) for p in t]
            deletes += [_norm(p, here) for p in d]
            for item in b:
                path, _, patterns = item.partition("\0")
                broad.append(_norm(path, here) + ("\0" + patterns if patterns else ""))
            inline += code
    return targets, deletes, inline, broad


def mentions(command: str, candidates: list[str]) -> list[str]:
    """Protected paths a command names (full path or file name) when it runs a wrapper and looks like a write."""
    if not WRAPPERS.search(command) or not WRITE_HINTS.search(command):
        return []
    found = []
    for c in candidates:
        name = posixpath.basename(c.rstrip("/"))
        if c in command or (name and name in command):
            found.append(c)
    return found
