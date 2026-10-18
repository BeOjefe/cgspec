"""The user-message hook: scrub likely secrets, save to the inbox, capture approvals (spec 8)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .common import STATE_DIR, new_id, sha256_text, utc_now, write_json

INBOX = Path("docs/00-INBOX.md")
APPROVALS = STATE_DIR / "approvals.json"
MAX_INBOX_CHARS = 2000

SECRETS = [
    ("private-key", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?(-----END [A-Z0-9 ]*PRIVATE KEY-----|\Z)", re.S)),
    ("github-token", re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,})\b")),
    ("aws-key", re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("api-key", re.compile(r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("slack-token", re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}\b")),
    ("google-key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("url-password", re.compile(r"(?<=://)([^:/@\s]+):([^@\s]+)(?=@)")),
]
ASSIGNMENT = re.compile(r"(?i)\b((?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|client[_-]?secret)\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|\S+)")

APPROVAL = re.compile(
    r"(?i)^\s*(?:yes[,.!]?\s*)?(?:"
    r"approved?|i approve|lgtm|ship it|go(?: ahead)?|ok(?:ay)?[,]?\s*go|yes|oui|valid(?:e|é|ated?)|"
    r"(?:ok\s+)?on valide|je valide|d'accord|on y va|c'est bon"
    r")\b(?!.*\?\s*$)")
NEGATION = re.compile(r"(?i)\b(not|don't|do not|no|pas|never|jamais)\b")


def scrub(text: str) -> str:
    for kind, pattern in SECRETS:
        if kind == "url-password":
            text = pattern.sub(lambda m: f"{m.group(1)}:[REDACTED:password]", text)
        else:
            text = pattern.sub(f"[REDACTED:{kind}]", text)
    return ASSIGNMENT.sub(lambda m: f"{m.group(1)}[REDACTED:secret]", text)


def is_approval(text: str) -> bool:
    first = text.strip().splitlines()[0] if text.strip() else ""
    return bool(APPROVAL.match(first)) and not NEGATION.search(first.split(".")[0])


def record(root: Path, prompt: str) -> tuple[str, str | None]:
    """Append the scrubbed prompt to the inbox; return (inbox id, approval id or None)."""
    clean = scrub(prompt)
    one_line = " / ".join(part.strip() for part in clean.splitlines() if part.strip())[:MAX_INBOX_CHARS]
    inbox_id = new_id("I")
    path = root / INBOX
    existing = path.read_text(encoding="utf-8") if path.is_file() else "# Inbox\n"
    sep = "" if existing.endswith("\n") else "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{sep}- {inbox_id} {utc_now()}: {one_line}\n")
    approval_id = None
    if is_approval(prompt):
        approvals_path = root / APPROVALS
        try:
            data = json.loads(approvals_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {"schema": 1, "approvals": []}
        approval_id = new_id("A")
        data.setdefault("approvals", []).append({"id": approval_id, "at": utc_now(), "excerpt": one_line[:200],
                                                 "sha256": sha256_text(prompt)})
        write_json(approvals_path, data)
    return inbox_id, approval_id


def approval_exists(root: Path, approval_id: str) -> bool:
    try:
        data = json.loads((root / APPROVALS).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return any(a.get("id") == approval_id for a in data.get("approvals", []))
