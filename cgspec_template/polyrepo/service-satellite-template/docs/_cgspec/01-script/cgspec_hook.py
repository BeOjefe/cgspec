#!/usr/bin/env python3
"""
CGSpec Universal Lifecycle Hook & Integrity Dispatcher (Reformed CGSpec v0.2)
Universal cross-agent lifecycle and quality enforcement engine.
Supports:
- Antigravity: Lifecycle JSON stdin/stdout protocol (SessionStart, PreToolUse, PostToolUse, Stop)
- Claude Code / Cursor / Aider / Copilot / Humans: Native Git Pre-Commit & Pre-Push hooks
- CI/CD & Automated Pipelines: CLI check mode (`cgspec_hook.py check`)
- Automated Setup: Single-command installer (`cgspec_hook.py install`)

Deterministically enforces:
- Law 3: UI/UX & Vertical Slice contracts precede production code
- Law 10: Strict zero decorative Unicode emojis in files
- Law 11: Disk-first capture & zero-drift loop termination via doctor.py
"""

import sys
import os
import json
import re
import argparse
import subprocess
from pathlib import Path

# Strict emoji regex matching pictographs, decorative symbols, and status emojis
EMOJI_PATTERN = re.compile(
    r"[\U00010000-\U0010ffff]|"
    r"[\u2600-\u27bf]|"
    r"[\u2300-\u23ff]|"
    r"[\u2b50-\u2b55]"
)

CODE_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".cpp", ".c", ".rb", ".php"
}

CODE_DIRS = {
    "src", "app", "lib", "backend", "frontend", "packages", "pkg", "services"
}


def resolve_workspace(payload: dict | None = None, explicit_repo: str | None = None) -> Path:
    if explicit_repo:
        return Path(explicit_repo).resolve()
    if payload:
        ws_list = payload.get("workspacePaths", [])
        if ws_list:
            return Path(ws_list[0]).resolve()
    # Check current working directory or traverse upward to find docs/
    cwd = Path.cwd().resolve()
    cur = cwd
    while cur != cur.parent:
        if (cur / "docs").exists() or (cur / ".git").exists():
            return cur
        cur = cur.parent
    return cwd


# ==============================================================================
# 1. Antigravity JSON Stdin/Stdout Handlers
# ==============================================================================

def handle_session_start(payload: dict, ws: Path) -> dict:
    memlog_path = ws / "docs" / "_memlog.md"
    if not memlog_path.exists():
        for fallback in ("docs/MEMLOG.md", "docs/.memlog.md", "_memlog.md"):
            candidate = ws / fallback
            if candidate.exists():
                memlog_path = candidate
                break

    last_milestone = "None"
    if memlog_path.exists():
        try:
            for line in memlog_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("### [M-"):
                    last_milestone = line.split("|")[0].strip("# ").strip()
                    break
        except Exception:
            pass

    index_path = ws / "docs" / "00-INDEX.md"
    index_status = "present" if index_path.exists() else "missing"

    msg = (
        f"Reformed CGSpec v0.2 Active.\n"
        f"- Workspace: {ws.resolve()}\n"
        f"- Master Index: docs/00-INDEX.md ({index_status})\n"
        f"- Active Milestone: {last_milestone}\n"
        f"- Invariants: Model 1 spines (docs/spines/), strict zero emojis (Law 10), disk capture (Law 11)."
    )

    return {
        "injectSteps": [
            {"ephemeralMessage": msg}
        ]
    }


def handle_pre_tool_use(payload: dict, ws: Path) -> dict:
    tool_call = payload.get("toolCall", {})
    name = tool_call.get("name", "")
    args = tool_call.get("args", {})

    content = ""
    if "CodeContent" in args:
        content = str(args.get("CodeContent") or "")
    elif "ReplacementContent" in args:
        content = str(args.get("ReplacementContent") or "")
    elif "ReplacementChunks" in args:
        chunks = args.get("ReplacementChunks") or []
        content = "\n".join(str(c.get("ReplacementContent", "")) for c in chunks if isinstance(c, dict))

    target_file = str(args.get("TargetFile") or "")

    # 1. Law 10 Check: Strict Zero Emojis
    if content and EMOJI_PATTERN.search(content):
        return {
            "decision": "deny",
            "reason": (
                "CGSpec Law 10 Violation: Decorative Unicode emojis are strictly forbidden "
                "in all documentation and source files. Use clean ASCII identifiers or markdown labels."
            )
        }

    # 2. Law 3 Check: Code requires active vertical slice
    if target_file:
        target_path = Path(target_file)
        if not target_path.is_absolute():
            target_path = ws / target_path

        try:
            rel_path = target_path.relative_to(ws)
            first_part = rel_path.parts[0] if rel_path.parts else ""
        except ValueError:
            first_part = ""

        is_code_file = target_path.suffix.lower() in CODE_EXTENSIONS
        is_code_dir = first_part in CODE_DIRS

        if is_code_file and is_code_dir:
            slices_dir = ws / "docs" / "slices"
            legacy_slices_dir = ws / "docs" / "_cgspec" / "06-slice"
            
            slice_files = []
            if slices_dir.exists():
                slice_files = [f for f in slices_dir.glob("SLICE-*.md") if f.name != "SLICE-TEMPLATE.md"]
            if not slice_files and legacy_slices_dir.exists():
                slice_files = [f for f in legacy_slices_dir.glob("SLICE-*.md") if f.name != "SLICE-TEMPLATE.md"]

            if not slice_files:
                return {
                    "decision": "deny",
                    "reason": (
                        "CGSpec Law 3 Violation: Production code in application directories "
                        f"('{first_part}/') cannot be created or modified before an atomic vertical slice "
                        "contract is drafted and approved in 'docs/slices/SLICE-NNN.md'."
                    )
                }

        # 3. Rogue Script Check: Block ad-hoc regex replacer scripts
        file_name = target_path.name
        if re.match(r"^(apply|patch|fix|overhaul)_.*\.py$", file_name) or "scratch" in target_path.parts:
            if target_path.suffix == ".py":
                return {
                    "decision": "deny",
                    "reason": (
                        "CGSpec Invariant: Ad-hoc Python string-patch scripts in scratch/ are strictly forbidden. "
                        "Modify component files directly or use bundle_prototype.py with modular partials."
                    )
                }

    return {"decision": "allow"}



def handle_pre_tool_use_command(payload: dict, ws: Path) -> dict:
    tool_call = payload.get("toolCall", {})
    args = tool_call.get("args", {})
    cmd = str(args.get("CommandLine") or "")

    if "git commit" in cmd:
        doctor_path = ws / "docs" / "_cgspec" / "01-script" / "doctor.py"
        if not doctor_path.exists():
            doctor_path = ws / "scripts" / "doctor.py"

        if doctor_path.exists():
            try:
                res = subprocess.run(
                    [sys.executable, str(doctor_path), "--repo", str(ws), "--strict-emojis"],
                    capture_output=True,
                    text=True,
                    timeout=20,
                    cwd=str(ws)
                )
                if res.returncode != 0:
                    return {
                        "decision": "deny",
                        "reason": (
                            "CGSpec Pre-Commit Gate: doctor.py failed with errors. "
                            "Resolve all specification drift and emoji leaks before committing:\n"
                            f"{res.stdout.strip()}\n{res.stderr.strip()}"
                        )
                    }
            except Exception as e:
                return {
                    "decision": "ask",
                    "reason": f"CGSpec Pre-Commit Warning: doctor.py check encountered an error: {e}"
                }

    return {"decision": "allow"}


def handle_post_tool_use(payload: dict, ws: Path) -> dict:
    return {}


def handle_stop(payload: dict, ws: Path) -> dict:
    doctor_path = ws / "docs" / "_cgspec" / "01-script" / "doctor.py"
    if not doctor_path.exists():
        doctor_path = ws / "scripts" / "doctor.py"

    if doctor_path.exists():
        try:
            res = subprocess.run(
                [sys.executable, str(doctor_path), "--repo", str(ws), "--strict-emojis"],
                capture_output=True,
                text=True,
                timeout=25,
                cwd=str(ws)
            )
            if res.returncode != 0:
                clean_output = res.stdout.strip()
                return {
                    "decision": "continue",
                    "reason": (
                        "CGSpec Invariant Failure: doctor.py detected specification drift or errors. "
                        "You must resolve all errors, sync docs/00-INDEX.md, and record milestones before finishing:\n"
                        f"{clean_output}"
                    )
                }
        except Exception:
            pass

    return {"decision": "allow"}


# ==============================================================================
# 2. Universal Git Hooks & Standalone Checks (Claude, Cursor, Aider, CI/CD)
# ==============================================================================

def run_git_pre_commit(ws: Path) -> int:
    """
    Native Git Pre-Commit Hook.
    Executes whenever ANY AI tool or human executes `git commit`.
    """
    print("[CGSpec Git Hook] Validating staged changes and specification integrity...")
    errors = []

    # 1. Inspect staged files
    try:
        staged_files_output = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            cwd=str(ws),
            text=True
        ).strip()
        staged_files = [f for f in staged_files_output.splitlines() if f.strip()]
    except Exception as e:
        staged_files = []

    has_code_changes = False
    code_dirs_touched = set()

    for rel_path_str in staged_files:
        rel_path = Path(rel_path_str)
        first_part = rel_path.parts[0] if rel_path.parts else ""

        # Read staged content to check for emojis
        try:
            staged_blob = subprocess.check_output(
                ["git", "show", f":{rel_path_str}"],
                cwd=str(ws),
                text=True,
                errors="ignore"
            )
            if EMOJI_PATTERN.search(staged_blob):
                errors.append(f"Law 10 Violation: Staged file '{rel_path_str}' contains forbidden Unicode emojis.")
        except Exception:
            pass

        # Check if code file
        if rel_path.suffix.lower() in CODE_EXTENSIONS and first_part in CODE_DIRS:
            has_code_changes = True
            code_dirs_touched.add(first_part)

    # 2. Law 3 Check: If code files are staged, ensure a slice exists
    if has_code_changes:
        slices_dir = ws / "docs" / "slices"
        legacy_slices_dir = ws / "docs" / "_cgspec" / "06-slice"

        slice_files = []
        if slices_dir.exists():
            slice_files = [f for f in slices_dir.glob("SLICE-*.md") if f.name != "SLICE-TEMPLATE.md"]
        if not slice_files and legacy_slices_dir.exists():
            slice_files = [f for f in legacy_slices_dir.glob("SLICE-*.md") if f.name != "SLICE-TEMPLATE.md"]

        if not slice_files:
            dirs_str = ", ".join(sorted(code_dirs_touched))
            errors.append(
                f"Law 3 Violation: Code files staged in application directories ({dirs_str}), "
                "but no active vertical slice contract exists in 'docs/slices/SLICE-NNN.md'."
            )

    # 3. Doctor Integrity Check
    doctor_path = ws / "docs" / "_cgspec" / "01-script" / "doctor.py"
    if not doctor_path.exists():
        doctor_path = ws / "scripts" / "doctor.py"

    if doctor_path.exists():
        res = subprocess.run(
            [sys.executable, str(doctor_path), "--repo", str(ws), "--strict-emojis"],
            capture_output=True,
            text=True,
            cwd=str(ws)
        )
        if res.returncode != 0:
            errors.append(f"CGSpec doctor.py check failed:\n{res.stdout.strip()}")

    if errors:
        print("\n" + "=" * 60)
        print("FAIL: CGSpec Pre-Commit Gate Blocked Commit")
        print("=" * 60)
        for err in errors:
            print(f"- {err}")
        print("\nFix these violations before committing.")
        return 1

    print("[CGSpec Git Hook] All checks passed cleanly. Commit approved.")
    return 0


def run_standalone_check(ws: Path) -> int:
    """Runs full pre-flight verification (for CI/CD or any AI CLI check)."""
    print(f"[CGSpec Universal Check] Inspecting {ws.resolve()}...")
    doctor_path = ws / "docs" / "_cgspec" / "01-script" / "doctor.py"
    if not doctor_path.exists():
        doctor_path = ws / "scripts" / "doctor.py"

    if not doctor_path.exists():
        print(f"FAIL: doctor.py not found in {ws}")
        return 1

    res = subprocess.run(
        [sys.executable, str(doctor_path), "--repo", str(ws), "--strict-emojis"],
        cwd=str(ws)
    )
    return res.returncode


def install_hooks(ws: Path) -> int:
    """
    Configures hooks for all AI tools and Git:
    - Creates .githooks/pre-commit and configures core.hooksPath
    - Installs .git/hooks/pre-commit
    - Ensures .agents/hooks.json for Antigravity
    - Ensures CLAUDE.md and .cursorrules point to AGENTS.md
    """
    print(f"[CGSpec Installer] Setting up universal hooks in {ws.resolve()}...")

    # 1. Setup .githooks and .git/hooks
    githooks_dir = ws / ".githooks"
    githooks_dir.mkdir(parents=True, exist_ok=True)

    hook_script_content = """#!/bin/sh
# CGSpec Universal Pre-Commit Hook (Version Controlled)
# Intercepts commits from all AI agents (Claude Code, Cursor, Aider, Antigravity) and humans.

if [ -f docs/_cgspec/01-script/cgspec_hook.py ]; then
    exec python3 docs/_cgspec/01-script/cgspec_hook.py git-pre-commit
elif [ -f scripts/cgspec_hook.py ]; then
    exec python3 scripts/cgspec_hook.py git-pre-commit
fi
exit 0
"""
    pre_commit_file = githooks_dir / "pre-commit"
    pre_commit_file.write_text(hook_script_content, encoding="utf-8")
    pre_commit_file.chmod(0o755)
    print("  Created: .githooks/pre-commit")

    # Direct .git/hooks installation if .git directory exists
    git_dir = ws / ".git"
    if git_dir.is_dir():
        local_git_hook = git_dir / "hooks" / "pre-commit"
        local_git_hook.parent.mkdir(parents=True, exist_ok=True)
        local_git_hook.write_text(hook_script_content, encoding="utf-8")
        local_git_hook.chmod(0o755)
        print("  Installed: .git/hooks/pre-commit")

        # Configure core.hooksPath
        try:
            subprocess.run(["git", "config", "core.hooksPath", ".githooks"], cwd=str(ws), check=True)
            print("  Git configured: core.hooksPath = .githooks")
        except Exception:
            pass

    # 2. Antigravity Configuration: .agents/hooks.json
    agents_dir = ws / ".agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    hooks_json_path = agents_dir / "hooks.json"

    hooks_json_data = {
        "cgspec-lifecycle": {
            "enabled": True,
            "SessionStart": [
                {
                    "type": "command",
                    "command": "python3 docs/_cgspec/01-script/cgspec_hook.py --event SessionStart",
                    "timeout": 10
                }
            ],
            "PreToolUse": [
                {
                    "matcher": "write_to_file|replace_file_content|multi_replace_file_content",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "python3 docs/_cgspec/01-script/cgspec_hook.py --event PreToolUse",
                            "timeout": 15
                        }
                    ]
                },
                {
                    "matcher": "run_command",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "python3 docs/_cgspec/01-script/cgspec_hook.py --event PreToolUseCommand",
                            "timeout": 15
                        }
                    ]
                }
            ],
            "PostToolUse": [
                {
                    "matcher": "write_to_file|replace_file_content|multi_replace_file_content",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "python3 docs/_cgspec/01-script/cgspec_hook.py --event PostToolUse",
                            "timeout": 15
                        }
                    ]
                }
            ],
            "Stop": [
                {
                    "type": "command",
                    "command": "python3 docs/_cgspec/01-script/cgspec_hook.py --event Stop",
                    "timeout": 30
                }
            ]
        }
    }
    hooks_json_path.write_text(json.dumps(hooks_json_data, indent=2) + "\n", encoding="utf-8")
    print("  Created: .agents/hooks.json (Antigravity Lifecycle Hook)")

    # 3. Multi-AI Links: CLAUDE.md & .cursorrules
    claude_md = ws / "CLAUDE.md"
    if not claude_md.exists():
        claude_md.write_text("# CLAUDE.md\n\nRead and strictly follow all instructions in [`./AGENTS.md`](./AGENTS.md).\n", encoding="utf-8")
        print("  Created: CLAUDE.md -> AGENTS.md")

    cursor_rules = ws / ".cursorrules"
    if not cursor_rules.exists():
        cursor_rules.write_text("# Cursor Rules\n\nRead and strictly follow all instructions in `./AGENTS.md` and `./docs/00-INDEX.md`.\nStrictly enforce Model 1 spines, zero Unicode emojis, and vertical slice contracts.\n", encoding="utf-8")
        print("  Created: .cursorrules -> AGENTS.md")

    print("[CGSpec Installer] Universal multi-AI hook installation complete.")
    return 0


# ==============================================================================
# 3. Main Dispatcher
# ==============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(description="CGSpec Universal Multi-AI Lifecycle Hook Runner")
    parser.add_argument("command", nargs="?", default=None, choices=["git-pre-commit", "check", "install"], help="CLI command mode")
    parser.add_argument("--event", default=None, help="Antigravity hook event type")
    parser.add_argument("--repo", default=None, help="Explicit repository root")
    args = parser.parse_args()

    # Route CLI commands
    if args.command == "git-pre-commit":
        ws = resolve_workspace(explicit_repo=args.repo)
        return run_git_pre_commit(ws)
    elif args.command == "check":
        ws = resolve_workspace(explicit_repo=args.repo)
        return run_standalone_check(ws)
    elif args.command == "install":
        ws = resolve_workspace(explicit_repo=args.repo)
        return install_hooks(ws)

    # Route Antigravity JSON events
    if args.event:
        try:
            raw_input = sys.stdin.read()
            payload = json.loads(raw_input) if raw_input.strip() else {}
        except Exception:
            payload = {}

        ws = resolve_workspace(payload=payload, explicit_repo=args.repo)

        if args.event == "SessionStart":
            output = handle_session_start(payload, ws)
        elif args.event == "PreToolUse":
            output = handle_pre_tool_use(payload, ws)
        elif args.event == "PreToolUseCommand":
            output = handle_pre_tool_use_command(payload, ws)
        elif args.event == "PostToolUse":
            output = handle_post_tool_use(payload, ws)
        elif args.event == "Stop":
            output = handle_stop(payload, ws)
        else:
            output = {}

        print(json.dumps(output))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
