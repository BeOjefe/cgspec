"""Wire the hook into each AI tool, git and CI (spec 8 per-tool table), and unwire on uninstall.

Every change is recorded in owned-files.json under "adapters" so uninstall removes exactly
what install added and leaves the user's own settings and hooks alone.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .common import STATE_DIR, utc_now, write_json

HOOK = "docs/_cgspec/01-engine/cgspec_hook.py"
MARK = "cgspec_hook.py"

CLAUDE_EVENTS = {
    "PreToolUse": ("Write|Edit|MultiEdit|NotebookEdit|Bash", "pre-tool"),
    "UserPromptSubmit": (None, "user-message"),
    "SessionStart": (None, "session-start"),
    "PreCompact": (None, "pre-compact"),
    "Stop": (None, "stop"),
}
AG_EVENTS = {
    "PreToolUse": ("write_to_file|replace_file_content|multi_replace_file_content|run_command", "pre-tool"),
    "SessionStart": (None, "session-start"),
    "Stop": (None, "stop"),
}
GIT_HOOK = """#!/bin/sh
# Installed by CGSpec. Remove with: python3 docs/_cgspec/01-engine/install.py uninstall
exec python3 "$(git rev-parse --show-toplevel)/{hook}" {event} --tool git "$@"
"""
WORKFLOW = """name: cgspec-governance
on:
  push:
  pull_request:
jobs:
  governance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: CGSpec governance (cannot be skipped)
        run: |
          BASE="${{{{ github.event.pull_request.base.sha || github.event.before }}}}"
          if [ -z "$BASE" ] || [ "$BASE" = "0000000000000000000000000000000000000000" ] || ! git cat-file -e "$BASE^{{commit}}" 2>/dev/null; then
            BASE="$(git rev-list --max-parents=0 HEAD | tail -1)"
          fi
          python3 {hook} ci --base "$BASE" --tool git
"""
CURSOR_RULE = """---
description: CGSpec project rules
alwaysApply: true
---
This project uses CGSpec. Read docs/_cgspec/01-engine/CONTRACT.md before acting. Cursor has no
hooks, so the git hooks and CI enforce the rules; run doctor.py before ending a task.
"""


def _command(event: str, tool: str) -> str:
    base = '"$CLAUDE_PROJECT_DIR"/' if tool == "claude" else ""
    return f"python3 {base}{HOOK} {event} --tool {tool}"


def _merge_json(path: Path, add) -> bool:
    data = {}
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            return False  # never overwrite a file we cannot parse
    created = not path.exists()
    add(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, data)
    return created


def _claude(data: dict) -> None:
    hooks = data.setdefault("hooks", {})
    for event, (matcher, name) in CLAUDE_EVENTS.items():
        entry = {"hooks": [{"type": "command", "command": _command(name, "claude")}]}
        if matcher:
            entry["matcher"] = matcher
        if MARK not in json.dumps(hooks.get(event, [])):
            hooks.setdefault(event, []).append(entry)


def _antigravity(data: dict) -> None:
    block = {}
    for event, (matcher, name) in AG_EVENTS.items():
        handler = {"type": "command", "command": _command(name, "antigravity"), "timeout": 30}
        block[event] = [{"matcher": matcher, "hooks": [handler]}] if matcher else [handler]
    data["cgspec"] = block


def _write_new(root: Path, rel: str, text: str, mode: int | None = None) -> tuple[bool, str]:
    path = root / rel
    if path.exists() and MARK not in path.read_text(encoding="utf-8", errors="replace") and "CGSpec" not in path.read_text(encoding="utf-8", errors="replace"):
        return False, f"left existing {rel} alone; add the CGSpec call to it yourself"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if mode:
        os.chmod(path, mode)
    return True, f"wired {rel}"


def _freeze_workflow(root: Path, rel: str) -> None:
    frozen_path = root / STATE_DIR / "frozen.json"
    data = json.loads(frozen_path.read_text(encoding="utf-8"))
    if rel not in [e.get("path") for e in data["entries"]]:
        digest = hashlib.sha256((root / rel).read_bytes()).hexdigest()
        data["entries"].append({"path": rel, "sha256": digest, "kind": "ci", "added": utc_now(),
                                "reason": "CGSpec governance workflow (spec 8 trust root)"})
        write_json(frozen_path, data)


def wire(root: Path, tools: list[str], owned: dict) -> list[str]:
    notes, record = [], owned.setdefault("adapters", {})
    if "claude" in tools:
        record["claude"] = {"path": ".claude/settings.json", "created": _merge_json(root / ".claude/settings.json", _claude)}
        notes.append("wired .claude/settings.json")
    if "antigravity" in tools:
        record["antigravity"] = {"path": ".agents/hooks.json", "created": _merge_json(root / ".agents/hooks.json", _antigravity)}
        notes.append("wired .agents/hooks.json (Antigravity sends no user message to hooks: inbox capture unavailable there)")
    if "git" in tools:
        if (root / ".git").is_dir():
            for event in ("pre-commit", "commit-msg"):
                ok, note = _write_new(root, f".git/hooks/{event}", GIT_HOOK.format(hook=HOOK, event=event), 0o755)
                notes.append(note)
                if ok:
                    record.setdefault("git", []).append(f".git/hooks/{event}")
        else:
            notes.append("no .git folder: git hooks not installed (run install.py upgrade after git init)")
    if "ci" in tools:
        rel = ".github/workflows/cgspec.yml"
        ok, note = _write_new(root, rel, WORKFLOW.format(hook=HOOK))
        notes.append(note)
        if ok:
            record["ci"] = rel
            _freeze_workflow(root, rel)
    if "cursor" in tools:
        ok, note = _write_new(root, ".cursor/rules/cgspec.mdc", CURSOR_RULE)
        notes.append(note)
        if ok:
            record["cursor"] = ".cursor/rules/cgspec.mdc"
    return notes


def _strip_claude(path: Path, created: bool) -> None:
    if not path.is_file():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    hooks = data.get("hooks", {})
    for event in list(hooks):
        hooks[event] = [e for e in hooks[event] if MARK not in json.dumps(e)]
        if not hooks[event]:
            del hooks[event]
    if not hooks:
        data.pop("hooks", None)
    if created and not data:
        path.unlink()
    else:
        write_json(path, data)


def unwire(root: Path, owned: dict) -> None:
    record = owned.get("adapters", {})
    if "claude" in record:
        _strip_claude(root / ".claude/settings.json", record["claude"].get("created", False))
    if "antigravity" in record:
        path = root / ".agents/hooks.json"
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            data.pop("cgspec", None)
            if data or not record["antigravity"].get("created"):
                write_json(path, data)
            else:
                path.unlink()
    for rel in record.get("git", []) + [record[k] for k in ("ci", "cursor") if k in record]:
        path = root / rel
        if path.is_file() and not path.is_symlink() and (MARK in path.read_text(errors="replace") or "CGSpec" in path.read_text(errors="replace")):
            os.chmod(path, 0o644)
            path.unlink()
    for rel in (".claude", ".agents", ".cursor/rules", ".cursor", ".github/workflows", ".github"):
        try:
            (root / rel).rmdir()
        except OSError:
            pass
