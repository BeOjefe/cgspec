"""Visible provenance for human-readable CGSpec Markdown documents."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

STAMP = re.compile(r"^Created: (unknown|\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ) · "
                   r"Last edited: (\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)$")
FIRST_SEEN = re.compile(r"^First seen in available Git history: "
                        r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)$")


def managed_doc(path: str) -> bool:
    return (path.startswith("docs/") and path.endswith(".md")
            and path not in {"docs/00-INBOX.md", "docs/_memlog.md"}
            and not path.startswith(("docs/_cgspec/_archive/", "docs/_cgspec/01-engine/")))


def _time(value: str) -> datetime:
    parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    return parsed.replace(tzinfo=timezone.utc)


def _lines(text: str) -> list[str]:
    lines = text.splitlines(keepends=True)
    if not lines or not lines[0].startswith("# "):
        raise ValueError("CGSpec Markdown document needs a top-level title")
    return lines


def _stamp_line(created: str, edited: str) -> str:
    if created != "unknown":
        _time(created)
    _time(edited)
    return f"Created: {created} · Last edited: {edited}\n"


def stamp_new(text: str, now: str) -> str:
    lines = _lines(text)
    if len(lines) > 1 and STAMP.fullmatch(lines[1].rstrip("\n")):
        return text
    return lines[0] + _stamp_line(now, now) + "".join(lines[1:])


def stamp_import(text: str, now: str, first_seen: str | None = None) -> str:
    lines = _lines(text)
    if len(lines) > 1 and STAMP.fullmatch(lines[1].rstrip("\n")):
        return text
    history = ""
    if first_seen:
        _time(first_seen)
        history = f"First seen in available Git history: {first_seen}\n"
    return lines[0] + _stamp_line("unknown", now) + history + "".join(lines[1:])


def touch(text: str, now: str) -> str:
    lines = _lines(text)
    if len(lines) < 2 or not (match := STAMP.fullmatch(lines[1].rstrip("\n"))):
        raise ValueError("CGSpec document has no valid provenance line")
    previous = _time(match.group(2))
    current = _time(now)
    if current <= previous:
        current = previous + timedelta(seconds=1)
    lines[1] = _stamp_line(match.group(1), current.strftime("%Y-%m-%dT%H:%M:%SZ"))
    return "".join(lines)


def validate_change(old: str | None, new: str) -> list[str]:
    """Check a new or changed document without trusting filesystem timestamps."""
    try:
        lines = _lines(new)
    except ValueError as exc:
        return [str(exc)]
    match = STAMP.fullmatch(lines[1].rstrip("\n")) if len(lines) > 1 else None
    if not match:
        return ["missing Created / Last edited line directly below the title"]
    try:
        created, edited = match.groups()
        if created != "unknown" and _time(created) > _time(edited):
            return ["Created is later than Last edited"]
        _time(edited)
    except ValueError:
        return ["invalid date; use ISO-8601 UTC"]
    if created == "unknown" and len(lines) > 2 and lines[2].startswith("First seen in available Git history:"):
        seen = FIRST_SEEN.fullmatch(lines[2].rstrip("\n"))
        if not seen:
            return ["invalid first-seen date"]
        try:
            _time(seen.group(1))
        except ValueError:
            return ["invalid first-seen date"]
    if old is None:
        return []
    old_lines = old.splitlines(keepends=True)
    previous = STAMP.fullmatch(old_lines[1].rstrip("\n")) if len(old_lines) > 1 else None
    if previous and previous.group(1) != created:
        return ["Created changed; preserve it across edits and renames"]
    if previous and _time(edited) <= _time(previous.group(2)) and old != new:
        return ["Last edited was not advanced after this document changed"]
    return []
