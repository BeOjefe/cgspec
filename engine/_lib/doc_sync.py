"""Keep visible document dates true without the agent hand-editing them (spec 2).

Compares each human-readable CGSpec document with its version at HEAD:
new documents get Created/Last edited now; edited ones keep Created and get a newer Last edited;
date-only changes are reverted; edited legacy documents are labelled Created: unknown.
Run at the end of a turn (stop hook) and by `cgspec_hook.py doc sync`.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from .common import atomic_write_text, utc_now
from .document_dates import STAMP, managed_doc, stamp_import, stamp_new, touch


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, capture_output=True)


def changed_docs(root: Path) -> list[str]:
    """Managed documents that differ from HEAD (modified or untracked)."""
    out = _git(root, "status", "--porcelain", "-z", "--untracked-files=all", "--", "docs")
    if out.returncode != 0:  # not a git repository: only documents that have no dates yet
        found = [p.relative_to(root).as_posix() for p in (root / "docs").rglob("*.md")]
        return sorted(p for p in found if managed_doc(p))
    paths, items = [], out.stdout.decode("utf-8", "replace").split("\0")
    i = 0
    while i < len(items) and items[i]:
        status, path = items[i][:2], items[i][3:]
        if "R" in status:
            i += 1  # skip the original name
        if "D" not in status:
            paths.append(path)
        i += 1
    return sorted(p for p in paths if managed_doc(p))


def _split(text: str) -> tuple[list[str], object]:
    lines = text.splitlines(keepends=True)
    match = STAMP.fullmatch(lines[1].rstrip("\n")) if len(lines) > 1 else None
    return lines, match


def _without_stamp(text: str) -> str:
    lines, match = _split(text)
    return lines[0] + "".join(lines[2:]) if match else text


def sync_text(head: str | None, current: str, now: str) -> str:
    if not current.startswith("# "):
        return current  # not a CGSpec document shape; the commit check reports it
    if head is None:
        return current if _split(current)[1] else stamp_new(current, now)
    head_lines, head_match = _split(head)
    if head_match is None:
        if _without_stamp(current) == head:
            return head
        return stamp_import(_without_stamp(current), now)
    body_now, body_head = _without_stamp(current), _without_stamp(head)
    if body_now == body_head:
        return head  # date-only change: keep the previous dates
    lines = body_now.splitlines(keepends=True)
    restored = lines[0] + head_lines[1] + "".join(lines[1:])
    return touch(restored, now)


def sync(root: Path) -> list[str]:
    changed, now = [], utc_now()
    for rel in changed_docs(root):
        path = root / rel
        if not path.is_file() or path.is_symlink():
            continue
        current = path.read_text(encoding="utf-8", errors="replace")
        shown = _git(root, "show", f"HEAD:{rel}")
        head = shown.stdout.decode("utf-8", "replace") if shown.returncode == 0 else None
        updated = sync_text(head, current, now)
        if updated != current:
            atomic_write_text(path, updated)
            changed.append(rel)
    return changed
