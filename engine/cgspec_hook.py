#!/usr/bin/env python3
"""cgspec_hook.py: the one entry point every tool adapter calls (contract: FORMATS.md).

  cgspec_hook.py tier set|show|clear ...     declare the change tier before editing (spec 3)
  cgspec_hook.py pre-tool --tool claude       gate a write or shell call; payload on stdin

Exit codes: 0 allow, 1 failed, 2 blocked (reason on stderr), 3 internal error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import tiers  # noqa: E402
from _lib.common import EXIT_BLOCK, EXIT_FAIL, EXIT_INTERNAL, EXIT_OK, CgspecError, resolve_root  # noqa: E402
from _lib.gates import Context, check_write  # noqa: E402
from _lib.shellparse import inline_writes, write_targets  # noqa: E402

WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
LATER = {"session-start", "session-check", "user-message", "post-tool", "pre-compact", "stop",
         "pre-commit", "commit-msg", "ci"}


def normalize(payload: dict, tool: str) -> dict:
    """Turn a tool-specific payload into {kind: write|shell|other, paths, content, command, cwd}."""
    if tool == "claude":
        name, data = payload.get("tool_name", ""), payload.get("tool_input") or {}
        if name in WRITE_TOOLS:
            path = data.get("file_path") or data.get("notebook_path")
            edits = data.get("edits") or []
            content = data.get("content") or data.get("new_string") or data.get("new_source") or \
                "\n".join(e.get("new_string", "") for e in edits if isinstance(e, dict))
            return {"kind": "write", "paths": [path] if path else [], "content": content,
                    "new": name == "Write" and None, "cwd": payload.get("cwd")}
        if name == "Bash":
            return {"kind": "shell", "command": data.get("command", ""), "cwd": payload.get("cwd")}
        return {"kind": "other"}
    kind = payload.get("tool")
    if kind in ("write", "edit"):
        return {"kind": "write", "paths": payload.get("paths", []), "content": payload.get("content"),
                "cwd": payload.get("cwd")}
    if kind == "shell":
        return {"kind": "shell", "command": payload.get("command", ""), "cwd": payload.get("cwd")}
    return {"kind": "other"}


def shell_reasons(ctx: Context, command: str, cwd: str | None) -> list[str]:
    base = cwd or str(ctx.root)
    targets, inline = write_targets(command, base)
    reasons = []
    for raw in targets:
        rel = ctx.relative(raw)
        if rel is not None and rel != ".":
            reasons += check_write(ctx, rel, None)
    protected = sorted(ctx.frozen | ctx.checks)
    for code in inline:
        for rel in inline_writes(code, protected):
            reasons.append(f"inline script writes to protected {rel}")
    return reasons


def pre_tool(root: Path, tool: str, raw: str) -> int:
    ctx, touched = None, []
    try:
        ctx = Context.load(root)
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("payload is not a JSON object")
        call = normalize(payload, tool)
        if call["kind"] == "other":
            return EXIT_OK
        if call["kind"] == "shell":
            reasons = shell_reasons(ctx, call["command"], call.get("cwd"))
        else:
            reasons = []
            for raw_path in call["paths"]:
                rel = ctx.relative(raw_path, call.get("cwd"))
                if rel is not None:
                    touched.append(rel)
                    reasons += check_write(ctx, rel, call.get("content"))
    except Exception as exc:  # fail closed only where it matters
        if ctx and any(ctx.protected(rel) for rel in touched):
            print(f"CGSpec blocked (internal error on a protected path): {exc!r}", file=sys.stderr)
            return EXIT_BLOCK
        print(f"CGSpec hook internal error (not blocking; commit hook and CI still check): {exc!r}", file=sys.stderr)
        return EXIT_INTERNAL
    if reasons:
        print("Blocked by CGSpec:\n- " + "\n- ".join(dict.fromkeys(reasons)), file=sys.stderr)
        return EXIT_BLOCK
    return EXIT_OK


def cmd_tier(root: Path, args: argparse.Namespace) -> int:
    if args.action == "show":
        print(json.dumps(tiers.active(root), indent=2))
        return EXIT_OK
    if args.action == "clear":
        tiers.clear(root)
        print("tier cleared")
        return EXIT_OK
    if not args.tier or not args.reason:
        raise CgspecError("tier set needs --tier and --reason")
    ctx = Context.load(root)
    files = [f.strip() for f in (args.files or "").split(",") if f.strip()]
    entry = tiers.set_tier(root, args.tier, args.reason, files, args.slice, ctx.classes, ctx.protected)
    from memlog import main as memlog_main
    detail = ", ".join(files) if files else entry.get("slice", "")
    memlog_main(["--root", str(root), "add", "--tags", "tier", "--summary",
                 f"tier {entry['tier']} {entry['id']}: {entry['reason']} ({detail})"])
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cgspec_hook.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("event", help="tier, pre-tool, or a later hook event")
    parser.add_argument("action", nargs="?", choices=["set", "show", "clear"])
    parser.add_argument("--root")
    parser.add_argument("--tool", default="generic", choices=["claude", "antigravity", "codex", "cursor", "git", "generic"])
    parser.add_argument("--tier", choices=["T0", "T1", "T2", "T3"])
    parser.add_argument("--reason")
    parser.add_argument("--files", help="T0: comma-separated existing files")
    parser.add_argument("--slice", help="T1+: SLICE-NNN")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        root = resolve_root(args.root)
        if args.event == "tier":
            return cmd_tier(root, args)
        if args.event == "pre-tool":
            return pre_tool(root, args.tool, sys.stdin.read())
        if args.event in LATER:
            print(f"cgspec_hook: '{args.event}' is not built yet (build step 2f)", file=sys.stderr)
            return EXIT_INTERNAL
        raise CgspecError(f"unknown event: {args.event}")
    except CgspecError as exc:
        print(f"cgspec_hook: {exc}", file=sys.stderr)
        return EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
