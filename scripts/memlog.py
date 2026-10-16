#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
cgspec-memlog: Append-only decision & memory log CLI for CGSpec.
Portable across all AI agents (Hermes, Claude Code, Codex, Cursor, Antigravity).
"""

from __future__ import annotations

import argparse
import getpass
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HEADER_TEMPLATE = """# Project Memory Log (.memlog.md)
> Append-only chronological log. Canonical spines (`00-INDEX.md` .. `05-EXPERIENCE.md`) are derived from this log.

"""

ENTRY_REGEX = re.compile(
    r"^### \[(M-\d{3,})\] ([^|]+)\| tags: ([^|]+)\| owner: ([^|]+)\| perms: ([^\n]+)\n(.*?)(?=^### \[M-\d{3,}\]|\Z)",
    re.MULTILINE | re.DOTALL,
)


def default_owner() -> str:
    try:
        out = subprocess.check_output(
            ["git", "config", "user.name"], stderr=subprocess.DEVNULL, text=True
        ).strip()
        if out:
            return f"@{out.lower().replace(' ', '_')}"
    except Exception:
        pass
    return f"@{getpass.getuser()}"


def parse_entries(content: str) -> list[dict[str, str]]:
    entries = []
    for match in ENTRY_REGEX.finditer(content):
        entries.append(
            {
                "id": match.group(1).strip(),
                "timestamp": match.group(2).strip(),
                "tags": [t.strip() for t in match.group(3).split(",") if t.strip()],
                "owner": match.group(4).strip(),
                "perms": match.group(5).strip(),
                "body": match.group(6).strip(),
            }
        )
    return entries


def cmd_add(args: argparse.Namespace) -> int:
    path = Path(args.memlog_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(HEADER_TEMPLATE, encoding="utf-8")

    content = path.read_text(encoding="utf-8")
    entries = parse_entries(content)
    entry_id = f"M-{len(entries) + 1:03d}"
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    owner = args.owner or default_owner()

    lines = [
        f"### [{entry_id}] {now_iso} | tags: {args.tags} | owner: {owner} | perms: {args.perms}",
        f"- **Summary:** {args.summary}",
    ]
    if args.details:
        lines.append(f"- **Details:** {args.details}")
    lines.append("")

    with path.open("a", encoding="utf-8") as f:
        if not content.endswith("\n\n"):
            f.write("\n")
        f.write("\n".join(lines) + "\n")

    print(f"logged {entry_id} ({args.tags}) -> {path}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    path = Path(args.memlog_path)
    if not path.exists():
        print(f"status: missing ({path})")
        return 0

    entries = parse_entries(path.read_text(encoding="utf-8"))
    tag_counts: dict[str, int] = {}
    for e in entries:
        for t in e["tags"]:
            tag_counts[t] = tag_counts.get(t, 0) + 1

    latest_id = entries[-1]["id"] if entries else "none"
    print(f"file: {path}")
    print(f"total_entries: {len(entries)} (latest: {latest_id})")
    for tag, count in sorted(tag_counts.items()):
        print(f"  tag[{tag}]: {count}")
    return 0


def cmd_entries(args: argparse.Namespace) -> int:
    path = Path(args.memlog_path)
    if not path.exists():
        return 0

    entries = parse_entries(path.read_text(encoding="utf-8"))
    filter_tags = (
        {t.strip() for t in args.tags.split(",") if t.strip()} if args.tags else set()
    )

    for e in entries:
        if filter_tags and not filter_tags.intersection(e["tags"]):
            continue
        tags_str = ", ".join(e["tags"])
        print(
            f"### [{e['id']}] {e['timestamp']} | tags: {tags_str} | owner: {e['owner']} | perms: {e['perms']}"
        )
        print(e["body"])
        print()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="CGSpec .memlog.md CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="Append atomic decision/event entry")
    p_add.add_argument("memlog_path", help="Path to docs/.memlog.md")
    p_add.add_argument("--tags", required=True, help="Comma-separated tags")
    p_add.add_argument("--summary", required=True, help="Concise 1-line summary")
    p_add.add_argument("--details", default="", help="Optional rationale")
    p_add.add_argument("--owner", default="", help="Resource Owner ID (defaults to git user)")
    p_add.add_argument(
        "--perms",
        default="read,invoke,propose_edit",
        help="Granular permissions (read,invoke,propose_edit,write,share,admin)",
    )
    p_add.set_defaults(func=cmd_add)

    p_status = sub.add_parser("status", help="Show .memlog.md summary")
    p_status.add_argument("memlog_path", help="Path to docs/.memlog.md")
    p_status.set_defaults(func=cmd_status)

    p_entries = sub.add_parser("entries", help="Filter and print entries")
    p_entries.add_argument("memlog_path", help="Path to docs/.memlog.md")
    p_entries.add_argument("--tags", default="", help="Filter by comma-separated tags")
    p_entries.set_defaults(func=cmd_entries)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
