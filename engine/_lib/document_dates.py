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


FUTURE_SLACK = timedelta(minutes=10)
RECORD_KEY = re.compile(r"^((?:ADR|SLICE|RES|COUNCIL)-(?:\d{3}|draft))-")


def _parse(text: str) -> tuple[list[str], re.Match | None]:
    lines = text.splitlines(keepends=True)
    match = STAMP.fullmatch(lines[1].rstrip("\n")) if len(lines) > 1 else None
    return lines, match


def _body(lines: list[str]) -> str:
    """Everything except the provenance line, to tell content edits from date-only edits."""
    return lines[0] + "".join(lines[2:]) if len(lines) > 1 else "".join(lines)


def created_of(text: str | None) -> str | None:
    if not text:
        return None
    match = _parse(text)[1]
    return match.group(1) if match else None


def rename_key(path: str, text: str | None) -> str | None:
    """How an added document is matched to a deleted one when git does not detect the rename."""
    name = path.rsplit("/", 1)[-1]
    found = RECORD_KEY.match(name)
    if found:
        return path.rsplit("/", 1)[0] + "/" + found.group(1)
    first = (text or "").splitlines()[:1]
    return ("title:" + first[0].strip()) if first and first[0].startswith("# ") else None


def _check_times(created: str, edited: str, lines: list[str], now: datetime | None) -> list[str]:
    try:
        moments = [_time(edited)] + ([] if created == "unknown" else [_time(created)])
        if created != "unknown" and _time(created) > _time(edited):
            return ["Created is later than Last edited"]
    except ValueError:
        return ["invalid date; use ISO-8601 UTC"]
    if created == "unknown" and len(lines) > 2 and lines[2].startswith("First seen in available Git history:"):
        seen = FIRST_SEEN.fullmatch(lines[2].rstrip("\n"))
        try:
            moments.append(_time(seen.group(1)) if seen else None)
        except ValueError:
            return ["invalid first-seen date"]
        if not seen:
            return ["invalid first-seen date"]
    if now is not None and any(m > now + FUTURE_SLACK for m in moments):
        return ["date is in the future; use the real current UTC time"]
    return []


def validate_change(old: str | None, new: str, now: datetime | None = None, floor: str | None = None,
                    allow_unknown: bool = False, renamed_from_created: str | None = None) -> list[str]:
    """Check a new or changed document without trusting filesystem timestamps.

    now: the checker's wall clock (dates later than now + 10 min are refused).
    floor: when CGSpec was installed; a new document cannot claim to be older.
    allow_unknown: an install/upgrade change may write Created: unknown on new documents.
    renamed_from_created: Created of the deleted document this one replaces (detected rename).
    """
    try:
        lines = _lines(new)
    except ValueError as exc:
        return [str(exc)]
    lines, match = _parse(new)
    if not match:
        return ["missing Created / Last edited line directly below the title"]
    created, edited = match.groups()
    problems = _check_times(created, edited, lines, now)
    if problems:
        return problems
    if old is None:
        if renamed_from_created is not None:
            return [] if created == renamed_from_created else ["Created changed; preserve it across edits and renames"]
        if created == "unknown" and not allow_unknown:
            return ["a new document cannot claim Created: unknown; use the current UTC time"]
        if created != "unknown" and floor and _time(created) < _time(floor):
            return ["Created is before CGSpec was installed in this project; a new document cannot be older"]
        return []
    old_lines, previous = _parse(old)
    if previous is None:
        if old != new and created != "unknown" and not allow_unknown:
            return ["this document existed before dates were tracked; write Created: unknown, not an invented date"]
        return []
    if previous.group(1) != created:
        return ["Created changed; preserve it across edits and renames"]
    if _body(old_lines) == _body(lines) and old != new:
        return ["Last edited changed without a content change; keep the previous dates"]
    if old != new and _time(edited) <= _time(previous.group(2)):
        return ["Last edited was not advanced after this document changed"]
    return []
