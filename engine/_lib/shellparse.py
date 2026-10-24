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


HARMLESS_REDIRECT = re.compile(r"\d*>&\d+|&>\s*/dev/null|\d*>>?\s*/dev/null")
ENGINE_RUN = re.compile(r"^\s*(?:\S*/)?python3?(?:\.\d+)?(?:\s+-[IBEsu]+)*\s+(?:\./)?(?:\S*/)?docs/_cgspec/01-engine/"
                        r"[A-Za-z_]+\.py(?:\s|$)")


def _without_engine_runs(command: str) -> str:
    """Drop segments that only run one of the engine's own scripts: they are the legitimate writers and check
    their own inputs. Writes elsewhere in the command are still seen by write_targets()."""
    parts = re.split(r"(;|&&|\|\||\||\n)", command)
    return "".join("" if ENGINE_RUN.match(part) and ".." not in part and not re.search(r"(?<!\d)>(?!&)", HARMLESS_REDIRECT.sub("", part))
                   else part for part in parts)


DESTRUCTIVE_PUSH_FLAGS = {"--force", "-f", "--force-with-lease"}
GIT_GLOBAL_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}


def _git_subcommand(rest: list[str]) -> list[str]:
    """Skip git's own global options (`-C dir`, `-c k=v`, `--no-pager`, ...) to reach the
    subcommand and its arguments, so `git -C /tmp push --force` is still seen as `push --force`."""
    i = 0
    while i < len(rest) and rest[i].startswith("-"):
        if rest[i] in GIT_GLOBAL_WITH_VALUE or rest[i].split("=", 1)[0] in GIT_GLOBAL_WITH_VALUE:
            i += 1 if "=" in rest[i] else 2
        else:
            i += 1
    return rest[i:]


def destructive_git_reasons(command: str) -> list[str]:
    """Git/GitHub actions the agent must never run itself: force push, history rewrite, a hard
    reset, a forced branch delete, or merging a pull request. The human can still run any of
    these directly; this only stops the agent's own tool calls.

    Scoped to command lines, never heredoc bodies: a commit message explaining an incident
    routinely contains the words "git filter-branch" or "force-pushed" as prose (this file's own
    docstring does), and a heredoc body is indistinguishable from that prose without actually
    running it. A real destructive command smuggled inside a heredoc fed to another shell is a
    known, accepted gap; the commit hook and GitHub's own history remain the backstop for that.
    """
    reasons = []
    for line in split_heredocs(command)[0]:
        for seg in _segments(_tokens(line)):
            args = _strip_prefixes(seg)
            if not args:
                continue
            prog = posixpath.basename(args[0])
            rest = _git_subcommand(args[1:]) if prog == "git" else args[1:]
            sub = rest[0] if rest else ""
            if prog == "git" and sub == "push":
                flags = rest[1:]
                if DESTRUCTIVE_PUSH_FLAGS & set(flags) or any(f.startswith("--force-with-lease=") for f in flags):
                    reasons.append("git push --force/-f/--force-with-lease rewrites remote history; "
                                   "ask the user to run it themselves")
                if any(f.startswith("+") and ":" in f for f in flags):
                    reasons.append("a '+' refspec forces the push; ask the user to run it themselves")
                if {"--delete", "-d"} & set(flags):
                    reasons.append("git push --delete removes a remote branch; ask the user to run it themselves")
            elif prog == "git" and sub in ("filter-branch", "filter-repo"):
                reasons.append(f"git {sub} rewrites history irreversibly; ask the user to run it themselves")
            elif prog in ("git-filter-repo", "filter-repo") and not sub:
                reasons.append("filter-repo rewrites history irreversibly; ask the user to run it themselves")
            elif prog == "git" and sub == "reset" and "--hard" in rest[1:]:
                reasons.append("git reset --hard discards uncommitted and unreachable work; "
                               "ask the user to run it themselves")
            elif prog == "git" and sub == "branch":
                flags = set(rest[1:])
                if "-D" in flags or (({"--delete"} & flags) and ({"--force", "-f"} & flags)):
                    reasons.append("a forced branch delete cannot be undone; ask the user to run it themselves")
            elif prog == "gh" and rest[:2] == ["pr", "merge"]:
                reasons.append("merging a pull request is the user's decision, not the agent's; "
                               "ask the user to merge it themselves")
    return reasons


def mentions(command: str, candidates: list[str]) -> list[str]:
    """Protected paths a command names (full path or file name) when it runs a wrapper and looks like a write."""
    command = _without_engine_runs(HARMLESS_REDIRECT.sub(" ", command))
    if not WRAPPERS.search(command) or not WRITE_HINTS.search(command):
        return []
    found = []
    for c in candidates:
        name = posixpath.basename(c.rstrip("/"))
        if c in command or (name and name in command):
            found.append(c)
    return found
