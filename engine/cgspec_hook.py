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

sys.dont_write_bytecode = True  # never leave caches in the vendored engine
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import tiers  # noqa: E402
from _lib.common import EXIT_BLOCK, EXIT_FAIL, EXIT_INTERNAL, EXIT_OK, CgspecError, resolve_root  # noqa: E402
from _lib.gates import Context, check_write  # noqa: E402
from _lib.shellparse import write_targets  # noqa: E402

WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
AG_WRITE_TOOLS = {"write_to_file", "replace_file_content", "multi_replace_file_content"}
AG_PATH_KEYS = {"TargetFile", "AbsolutePath", "Cwd"}


def _strings(value, skip=frozenset()) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for k, v in value.items() if k not in skip for s in _strings(v, skip)]
    if isinstance(value, list):
        return [s for v in value for s in _strings(v, skip)]
    return []
LATER = {"post-tool"}


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
    if tool == "antigravity":
        call = payload.get("toolCall") or {}
        name, data = call.get("name", ""), call.get("args") or {}
        cwd = (payload.get("workspacePaths") or [None])[0]
        if name in AG_WRITE_TOOLS:
            return {"kind": "write", "paths": [data["TargetFile"]] if data.get("TargetFile") else [],
                    "content": "\n".join(_strings(data, AG_PATH_KEYS)), "cwd": cwd}
        if name == "run_command":
            return {"kind": "shell", "command": data.get("CommandLine", ""), "cwd": data.get("Cwd") or cwd}
        return {"kind": "other"}
    kind = payload.get("tool")
    if kind in ("write", "edit"):
        return {"kind": "write", "paths": payload.get("paths", []), "content": payload.get("content"),
                "cwd": payload.get("cwd")}
    if kind == "shell":
        return {"kind": "shell", "command": payload.get("command", ""), "cwd": payload.get("cwd")}
    return {"kind": "other"}


def shell_reasons(ctx: Context, command: str, cwd: str | None) -> list[str]:
    from _lib.gates import git_tracked, protected_list
    from _lib.shellparse import WRITE_HINTS, mentions
    import posixpath
    targets, deletes, inline, broad = write_targets(command, cwd or str(ctx.root))
    guarded = protected_list(ctx)
    reasons = []
    for raw in targets:
        rel = ctx.relative(raw)
        if rel is not None and rel != ".":
            reasons += check_write(ctx, rel, None)
    for raw in deletes:
        rel = ctx.relative(raw)
        if rel is None or rel == ".":
            continue
        if ctx.protected(rel) or any(p.startswith(rel.rstrip("/") + "/") for p in guarded):
            reasons.append(f"deleting {rel} would remove protected files")
        elif (ctx.root / rel).exists() and git_tracked(ctx.root, rel):
            reasons += check_write(ctx, rel, None, is_new=False)
    for raw in broad:
        rel = ctx.relative(raw)
        if rel is not None and any(rel == "." or p.startswith(rel.rstrip("/") + "/") or p == rel for p in guarded):
            reasons.append(f"this command may change everything under {rel}, including protected files; use the edit tools instead")
    for code in inline:
        if WRITE_HINTS.search(code):
            reasons += [f"inline script writes to protected {p}" for p in guarded
                        if p in code or (not p.endswith("/") and posixpath.basename(p) in code)]
    reasons += [f"command names protected {p} and looks like a write" for p in mentions(command, guarded)]
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
            return block(tool, f"CGSpec blocked (internal error on a protected path): {exc!r}")
        print(f"CGSpec hook internal error (not blocking; commit hook and CI still check): {exc!r}", file=sys.stderr)
        return EXIT_INTERNAL
    if reasons:
        return block(tool, "Blocked by CGSpec:\n- " + "\n- ".join(dict.fromkeys(reasons)))
    return EXIT_OK


def block(tool: str, message: str) -> int:
    """Claude Code reads exit 2 + stderr; Antigravity reads a JSON decision on stdout."""
    if tool == "antigravity":
        print(json.dumps({"decision": "deny", "reason": message}))
        return EXIT_OK
    print(message, file=sys.stderr)
    return EXIT_BLOCK


def staged_doctor(root: Path, doctor) -> list:
    """Run the doctor on exactly what is staged, not on the working tree."""
    import shutil
    import subprocess
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="cgspec-index-"))
    try:
        subprocess.run(["git", "checkout-index", "-a", "-f", f"--prefix={tmp}/"], cwd=root, check=True,
                       capture_output=True)
        return doctor.run_checks(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def pre_commit(root: Path) -> int:
    from _lib.commit_gate import evaluate
    from _lib.gitview import View
    import doctor
    reasons = evaluate(root, View.staged(root))
    findings = [f for f in staged_doctor(root, doctor) if f.is_error]
    reasons += [f"doctor {f.code} {f.path}: {f.message}" for f in findings]
    if reasons:
        print("CGSpec commit check failed:\n- " + "\n- ".join(reasons))
        return EXIT_FAIL
    print("CGSpec commit check passed")
    return EXIT_OK


def ci(root: Path, base: str | None, rerun: bool, args: argparse.Namespace) -> int:
    from _lib import ci_gate
    import doctor
    problems, notes = ci_gate.run(root, base, rerun, Path(args.release_dir) if args.release_dir else None)
    problems += [f"doctor {f.code} {f.path}: {f.message}" for f in doctor.run_checks(root) if f.is_error]
    for note in notes:
        print(note)
    if problems:
        print("CGSpec governance failed:\n- " + "\n- ".join(problems))
        return EXIT_FAIL
    print("CGSpec governance passed")
    return EXIT_OK


def read_payload(raw: str) -> dict:
    try:
        data = json.loads(raw) if raw.strip() else {}
        return data if isinstance(data, dict) else {}
    except ValueError:
        return {}


def doctor_state(root: Path) -> tuple[int, str]:
    import doctor
    findings = doctor.run_checks(root)
    errors = [f for f in findings if f.is_error]
    summary = f"{len(errors)} errors, {len(findings) - len(errors)} warnings"
    if errors:
        summary += " - " + "; ".join(f"{f.code} {f.path}" for f in errors[:5])
    return len(errors), summary


def lifecycle(root: Path, event: str, args: argparse.Namespace, raw: str) -> int:
    from _lib import inbox, session
    if event == "user-message":
        try:
            prompt = read_payload(raw).get("prompt") or ""
            if prompt:
                inbox.record(root, prompt)
        except Exception as exc:  # never block the user's message
            print(f"cgspec_hook: inbox capture failed: {exc!r}", file=sys.stderr)
        return EXIT_OK
    errors, summary = doctor_state(root)
    if event in ("session-start", "pre-compact"):
        print(session.pack(root, summary))
        return EXIT_OK
    if event == "session-check":
        from install import verify_engine
        problems = verify_engine(root)
        print(f"doctor: {summary}" + (f"; engine: {len(problems)} problems" if problems else "; engine OK"))
        return EXIT_FAIL if errors or problems else EXIT_OK
    if event == "stop":
        allow, message = session.stop_decision(root, session.stop_problems(root, errors))
        if args.tool == "antigravity":
            if not allow:
                print(json.dumps({"decision": "continue", "reason": message}))
            elif message:
                print(message, file=sys.stderr)
            return EXIT_OK
        if message:
            print(message, file=sys.stderr)
        return EXIT_OK if allow else EXIT_BLOCK
    if event == "commit-msg":
        from _lib.gates import EMOJI
        if not args.rest:
            raise CgspecError("commit-msg needs the message file path")
        text = Path(args.rest[0]).read_text(encoding="utf-8", errors="replace")
        if EMOJI.search(text):
            print("CGSpec: decorative emoji in the commit message (spec 1)")
            return EXIT_FAIL
        return EXIT_OK
    raise CgspecError(f"unknown event: {event}")


def cmd_tier(root: Path, args: argparse.Namespace) -> int:
    action = args.rest[0] if args.rest else ""
    if action not in ("set", "show", "clear"):
        raise CgspecError("usage: cgspec_hook.py tier set|show|clear")
    if action == "show":
        print(json.dumps(tiers.active(root), indent=2))
        return EXIT_OK
    if action == "clear":
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
    parser.add_argument("rest", nargs="*", help="tier: set|show|clear; commit-msg: message file")
    parser.add_argument("--root")
    parser.add_argument("--tool", default="generic", choices=["claude", "antigravity", "codex", "cursor", "git", "generic"])
    parser.add_argument("--tier", choices=["T0", "T1", "T2", "T3"])
    parser.add_argument("--reason")
    parser.add_argument("--files", help="T0: comma-separated existing files")
    parser.add_argument("--slice", help="T1+: SLICE-NNN")
    parser.add_argument("--base", help="ci: base commit of the range to check")
    parser.add_argument("--no-rerun", action="store_true", help="ci: skip re-running failing-test records")
    parser.add_argument("--release-dir", help="ci: checkout of the CGSpec plugin release to verify engine changes")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_intermixed_args(argv)
    try:
        root = resolve_root(args.root)
        if args.event == "tier":
            return cmd_tier(root, args)
        if args.event == "pre-tool":
            return pre_tool(root, args.tool, sys.stdin.read())
        if args.event == "pre-commit":
            return pre_commit(root)
        if args.event == "ci":
            return ci(root, args.base, not args.no_rerun, args)
        if args.event in ("user-message", "session-start", "session-check", "pre-compact", "stop", "commit-msg"):
            return lifecycle(root, args.event, args, "" if args.event == "commit-msg" else sys.stdin.read())
        if args.event in LATER:
            print(f"cgspec_hook: '{args.event}' is not built yet (build step 2f)", file=sys.stderr)
            return EXIT_INTERNAL
        raise CgspecError(f"unknown event: {args.event}")
    except CgspecError as exc:
        print(f"cgspec_hook: {exc}", file=sys.stderr)
        return EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
