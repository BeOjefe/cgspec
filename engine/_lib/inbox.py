"""The user-message hook: scrub likely secrets, save to the inbox, capture approvals (spec 8)."""

from __future__ import annotations

import json
import time
import re
from pathlib import Path

from .common import STATE_DIR, new_id, sha256_text, utc_now, write_json

INBOX = Path("docs/00-INBOX.md")
APPROVALS = STATE_DIR / "approvals.json"
MAX_INBOX_CHARS = 2000
MAX_APPROVAL_CHARS = 200

SECRETS = [
    ("private-key", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?(-----END [A-Z0-9 ]*PRIVATE KEY-----|\Z)", re.S)),
    ("github-token", re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,})\b")),
    ("aws-key", re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("api-key", re.compile(r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("slack-token", re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}\b")),
    ("google-key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("url-password", re.compile(r"(?<=://)([^:/@\s]+):([^@\s]+)(?=@)")),  # cgspec:test-fixture (matches itself)
]
ASSIGNMENT = re.compile(r"(?i)\b((?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|client[_-]?secret)\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|\S+)")

APPROVAL = re.compile(
    r"(?i)^\s*(?:yes[,.!]?\s*)?(?:"
    r"approved?|i approve|lgtm|ship it|go(?: ahead)?|ok(?:ay)?[,]?\s*go|yes|oui|valid(?:e|é|ated?)|"
    r"(?:ok\s+)?on valide|je valide|d'accord|on y va|c'est bon"
    r")\b(?!.*\?\s*$)")
DIRECT_TARGET = re.compile(r"((?:SLICE|ADR|CHK)-\d{3})\s*[.!]?", re.I)
TEST_COMMAND = re.compile(r"test[ -]command\s*[.!]?", re.I)
TEST_RUNNERS = re.compile(r"test[ -]runners\s*[.!]?", re.I)
DECISION = re.compile(r"decision\s*:\s*(\S.*)", re.I)


def scrub(text: str) -> str:
    for kind, pattern in SECRETS:
        if kind == "url-password":
            text = pattern.sub(lambda m: f"{m.group(1)}:[REDACTED:password]", text)
        else:
            text = pattern.sub(f"[REDACTED:{kind}]", text)
    return ASSIGNMENT.sub(lambda m: f"{m.group(1)}[REDACTED:secret]", text)


def contains_secret(text: str) -> str | None:
    """First secret-like pattern found in text, or None. Shared by the write and commit gates."""
    for kind, pattern in SECRETS:
        if pattern.search(text):
            return kind
    return "secret" if ASSIGNMENT.search(text) else None


def is_approval(text: str) -> bool:
    first = text.strip().splitlines()[0] if text.strip() else ""
    return bool(APPROVAL.match(first))


def approval_target(text: str) -> str | None:
    """Return an explicitly approved record, or None for unbound/ambiguous words.

    The commit gate must compare this with the record being changed. Capturing a
    generic acknowledgment in the inbox is not authorization for any record.
    """
    # The committed excerpt has a 200-character limit. Longer or multi-line
    # messages can hide a contradictory clause from the commit gate.
    if len(text) > MAX_APPROVAL_CHARS or len(text.strip().splitlines()) != 1 or not is_approval(text):
        return None
    first = text.strip().splitlines()[0]
    rest = first[APPROVAL.match(first).end():].strip()
    rest = re.sub(r"(?i)^the\s+", "", rest)
    if match := DIRECT_TARGET.fullmatch(rest):
        return match.group(1).upper()
    if TEST_COMMAND.fullmatch(rest):
        return "test_command"
    if TEST_RUNNERS.fullmatch(rest):
        return "test_runners"
    if match := DECISION.fullmatch(rest):
        summary = " ".join(match.group(1).split()).casefold()
        return f"decision:{summary}"
    return None


def record(root: Path, prompt: str, session_id: str | None = None) -> tuple[str, str | None]:
    """Append the scrubbed prompt to the inbox; return (inbox id, approval id or None).

    A repo can have several agent sessions open on it at once (parallel Claude Code
    sessions, or another tool entirely); every one of them shares this one file. The
    short session tag is just so a reader can tell entries apart by session, never a
    scoping or filtering mechanism - the inbox itself stays one shared, repo-wide file.
    """
    clean = scrub(prompt)
    whole_line = " / ".join(part.strip() for part in clean.splitlines() if part.strip())
    one_line = whole_line[:MAX_INBOX_CHARS]
    inbox_id = new_id("I")
    path = root / INBOX
    existing = path.read_text(encoding="utf-8") if path.is_file() else "# Inbox\n"
    sep = "" if existing.endswith("\n") else "\n"
    tag = f" [sess {session_id[-8:]}]" if session_id else ""
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{sep}- {inbox_id} {utc_now()}{tag}: {one_line}\n")
    approval_id = None
    if (is_approval(prompt) and len(prompt) <= MAX_APPROVAL_CHARS and
            len(whole_line) <= MAX_APPROVAL_CHARS and len(clean.strip().splitlines()) == 1):
        approvals_path = root / APPROVALS
        try:
            data = json.loads(approvals_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {"schema": 1, "approvals": []}
        approval_id = new_id("A")
        data.setdefault("approvals", []).append({"id": approval_id, "at": utc_now(), "captured_ns": time.time_ns(), "excerpt": one_line[:200],
                                                 "sha256": sha256_text(prompt)})
        write_json(approvals_path, data)
    return inbox_id, approval_id


def approval_record(root: Path, approval_id: str, target: str | None = None) -> dict | None:
    try:
        data = json.loads((root / APPROVALS).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return next((a for a in data.get("approvals", []) if isinstance(a, dict) and a.get("id") == approval_id and
                 (target is None or approval_target(str(a.get("excerpt", ""))) == target)), None)


def approval_exists(root: Path, approval_id: str, target: str | None = None) -> bool:
    return approval_record(root, approval_id, target) is not None
