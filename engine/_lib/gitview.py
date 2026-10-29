"""Read-only views of a change in git: the staged index (pre-commit) or one commit (CI)."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


def git(root: Path, *args: str, binary: bool = False, timeout: float | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-c", "core.quotepath=off", *args], cwd=root, capture_output=True,
                          text=not binary, timeout=timeout)


@dataclass
class Change:
    status: str  # A, M, D, R (rename), C (copy), T (type)
    path: str
    old_path: str | None = None


class View:
    """`new` is either ':' (index) or a commit; `old` is a commit or None (no parent)."""

    def __init__(self, root: Path, new: str, old: str | None) -> None:
        self.root, self.new, self.old = root, new, old

    @classmethod
    def staged(cls, root: Path) -> "View":
        head = git(root, "rev-parse", "--verify", "-q", "HEAD")
        return cls(root, ":", head.stdout.strip() if head.returncode == 0 else None)

    @classmethod
    def commit(cls, root: Path, commit: str) -> "View":
        parent = git(root, "rev-parse", "--verify", "-q", f"{commit}^")
        return cls(root, commit, parent.stdout.strip() if parent.returncode == 0 else None)

    def _diff_args(self) -> list[str]:
        if self.new == ":":
            return ["diff", "--cached"] + ([self.old] if self.old else ["--root"])
        return ["diff", self.old, self.new] if self.old else ["diff-tree", "--root", "-r", self.new]

    def changes(self) -> list[Change]:
        out = git(self.root, *self._diff_args(), "--name-status", "-z", "-M").stdout.split("\0")
        items, i = [], 0
        while i < len(out) and out[i]:
            status = out[i][0]
            if status in "RC":
                items.append(Change(status, out[i + 2], out[i + 1]))
                i += 3
            else:
                items.append(Change(status, out[i + 1]))
                i += 2
        return items

    def added_lines(self) -> dict[str, list[str]]:
        text = git(self.root, *self._diff_args(), "-U0", "--no-color").stdout
        result: dict[str, list[str]] = {}
        current = None
        for line in text.splitlines():
            if line.startswith("+++ "):
                raw = line[4:]
                if raw.startswith('"') and raw.endswith('"'):
                    raw = raw[1:-1].encode("utf-8").decode("unicode_escape")
                current = raw[2:] if raw.startswith("b/") else None
            elif line.startswith("+") and current:
                result.setdefault(current, []).append(line[1:])
        return result

    def changed_line_count(self, paths: set[str]) -> int:
        total = 0
        rows = git(self.root, *self._diff_args(), "--numstat", "-z", "-M").stdout.split("\0")
        i = 0
        while i < len(rows):
            parts = rows[i].split("\t", 2)
            i += 1
            if len(parts) != 3:
                continue
            names = {parts[2]}
            if parts[2] == "" and i + 1 < len(rows):
                # -z emits a rename as counts<TAB><NUL>old<NUL>new<NUL>.
                names = {rows[i], rows[i + 1]}
                i += 2
            if names & paths and parts[0] != "-":
                total += int(parts[0]) + int(parts[1])
        return total

    def read_new(self, path: str) -> bytes | None:
        spec = f":{path}" if self.new == ":" else f"{self.new}:{path}"
        result = git(self.root, "show", spec, binary=True)
        return result.stdout if result.returncode == 0 else None

    def read_old(self, path: str) -> bytes | None:
        if not self.old:
            return None
        result = git(self.root, "show", f"{self.old}:{path}", binary=True)
        return result.stdout if result.returncode == 0 else None

    def files_new(self, prefix: str) -> list[str]:
        if self.new == ":":
            out = git(self.root, "ls-files", "-z", "--", prefix).stdout
        else:
            out = git(self.root, "ls-tree", "-r", "-z", "--name-only", self.new, "--", prefix).stdout
        return [p for p in out.split("\0") if p]

    def files_old(self, prefix: str) -> list[str]:
        if not self.old:
            return []
        out = git(self.root, "ls-tree", "-r", "-z", "--name-only", self.old, "--", prefix).stdout
        return [p for p in out.split("\0") if p]

    def commit_exists(self, rev: str) -> bool:
        return git(self.root, "cat-file", "-e", f"{rev}^{{commit}}").returncode == 0

    def is_ancestor(self, rev: str, of: str) -> bool:
        return git(self.root, "merge-base", "--is-ancestor", rev, of).returncode == 0
