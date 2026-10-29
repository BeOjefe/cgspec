"""Wire the hook into each AI tool, git and CI (spec 8 per-tool table), and unwire on uninstall.

Every change is recorded in owned-files.json under "adapters" so uninstall removes exactly
what install added and leaves the user's own settings and hooks alone.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil

from .ci_visual import VISUAL_WORKFLOW
from .common import CgspecError, STATE_DIR, utc_now, write_json
from . import git_hooks

HOOK = "docs/_cgspec/01-engine/cgspec_hook.py"
MARK = "cgspec_hook.py"

CLAUDE_EVENTS = {
    "PreToolUse": ("Write|Edit|MultiEdit|NotebookEdit|Bash", "pre-tool"),
    "PostToolUse": ("Write|Edit|MultiEdit|NotebookEdit|Bash|Task|Agent", "post-tool"),
    "UserPromptSubmit": (None, "user-message"),
    "SessionStart": (None, "session-start"),
    "PreCompact": (None, "pre-compact"),
    "Stop": (None, "stop"),
}
AG_EVENTS = {
    "PreToolUse": ("write_to_file|replace_file_content|multi_replace_file_content|client_edit_file|client_create_file|run_command", "pre-tool"),
    "PostToolUse": ("write_to_file|replace_file_content|multi_replace_file_content|client_edit_file|client_create_file|run_command|invoke_subagent|call_mcp_tool", "post-tool"),
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
permissions:
  contents: read
jobs:
  governance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683
        with:
          fetch-depth: 0
      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065
        with:
          python-version: "3.12"
      - name: Pick the base and a trusted engine (never the engine inside this commit)
        env:
          EVENT_BASE: ${{{{ github.event.pull_request.base.sha || github.event.before }}}}
          EVENT_NAME: ${{{{ github.event_name }}}}
          EVENT_REF: ${{{{ github.ref }}}}
          DEFAULT_BRANCH: ${{{{ github.event.repository.default_branch }}}}
        run: |
          set -eu
          # Run the selection script as it was BEFORE this change, so a change cannot rewrite its own judge.
          B="$EVENT_BASE"
          if [ -n "$B" ] && [ "$B" != "$(git rev-parse HEAD)" ] &&
             git cat-file -e "$B:.github/cgspec-select.sh" 2>/dev/null; then
            TRUSTED="$B"
            git show "$B:.github/cgspec-select.sh" > "$RUNNER_TEMP/cgspec-select.sh"
          else
            # A default-branch push with no usable before SHA has no older trust root.
            if [ "$EVENT_NAME" != "push" ] || [ -z "$DEFAULT_BRANCH" ] ||
               [ "$EVENT_REF" = "refs/heads/$DEFAULT_BRANCH" ]; then
              echo "CGSpec: no trusted selector before this change; refusing this push" >&2
              exit 1
            fi
            # Do not read FETCH_HEAD after a failed fetch: it may name a stale object.
            if ! git fetch -q origin "refs/heads/$DEFAULT_BRANCH"; then
              echo "CGSpec: cannot fetch the default branch selector" >&2
              exit 1
            fi
            TRUSTED="$(git rev-parse 'FETCH_HEAD^{{commit}}')"
            if [ "$TRUSTED" = "$(git rev-parse HEAD)" ] ||
               ! git cat-file -e "$TRUSTED:.github/cgspec-select.sh" 2>/dev/null; then
              echo "CGSpec: default branch has no prior trusted selector" >&2
              exit 1
            fi
            git show "$TRUSTED:.github/cgspec-select.sh" > "$RUNNER_TEMP/cgspec-select.sh"
          fi
          CGSPEC_TRUST_BASE="$TRUSTED" sh "$RUNNER_TEMP/cgspec-select.sh"
      - name: CGSpec governance (cannot be skipped)
        id: proof
        env:
          CGSPEC_PROOF_DIR: ${{{{ runner.temp }}}}/cgspec-proof
        run: python3 "$CGSPEC_RELEASE/engine/cgspec_hook.py" ci --root "$GITHUB_WORKSPACE" --base "$CGSPEC_BASE" --release-dir "$CGSPEC_RELEASE" --tool git
      - name: Retain structured proof on success or failure
        if: ${{{{ always() && steps.proof.outcome != 'skipped' }}}}
        uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02  # v4.6.2
        with:
          name: cgspec-ci-proof
          # Only engine-written red/green files; the proof directory is hidden from the
          # candidate's own processes so a test cannot write a forged result beside them.
          path: |
            ${{{{ runner.temp }}}}/cgspec-proof/*-red.json
            ${{{{ runner.temp }}}}/cgspec-proof/*-green.json
          if-no-files-found: ignore
          retention-days: 14
      # CGSPEC_VISUAL_JOB
"""
SELECT = """#!/bin/sh
# Installed by CGSpec. Chooses the range base and downloads the plugin release used to judge it.
# Version = the newer of trusted selector commit and HEAD; source = that trusted commit.
set -eu
TRUST_BASE="${CGSPEC_TRUST_BASE:-${EVENT_BASE:-}}"
if [ -z "$TRUST_BASE" ] ||
   ! git cat-file -e "$TRUST_BASE:.github/cgspec-select.sh" 2>/dev/null ||
   ! git cat-file -e "$TRUST_BASE:docs/_cgspec/project.json" 2>/dev/null; then
  echo "CGSpec: no trusted selector and plugin source before this change" >&2
  exit 1
fi
BASE="${EVENT_BASE:-}"
if [ -z "$BASE" ] || ! git cat-file -e "$BASE:docs/_cgspec/project.json" 2>/dev/null; then
  BASE="$(git merge-base HEAD "$TRUST_BASE" 2>/dev/null || true)"
fi
if [ -z "$BASE" ] || [ "$BASE" = "$(git rev-parse HEAD)" ]; then
  echo "CGSpec: cannot establish a trusted range base before HEAD" >&2
  exit 1
fi
read_at() { git show "$1:$2" 2>/dev/null || true; }
field() { python3 -c "import json,sys; d=sys.stdin.read(); print(json.loads(d).get('$1','') if d.strip() else '')"; }
HEAD_VERSION="$(read_at HEAD docs/_cgspec/01-engine/VERSION | tr -d '[:space:]')"
TRUST_VERSION="$(read_at "$TRUST_BASE" docs/_cgspec/01-engine/VERSION | tr -d '[:space:]')"
SOURCE="$(read_at "$TRUST_BASE" docs/_cgspec/project.json | field plugin_source)"
if [ -z "$TRUST_VERSION" ] || [ -z "$SOURCE" ]; then
  echo "CGSpec: trusted selector lacks a version or plugin source" >&2
  exit 1
fi
VERSION="$(printf '%s\\n%s\\n' "$TRUST_VERSION" "$HEAD_VERSION" | grep . | sort -t. -k1,1n -k2,2n -k3,3n | tail -1)"
RELEASE="${RUNNER_TEMP:-/tmp}/cgspec-release"
rm -rf "$RELEASE"
git clone -q --depth 1 --branch "v$VERSION" "$SOURCE" "$RELEASE"
echo "CGSPEC_BASE=$BASE" >> "$GITHUB_ENV"
echo "CGSPEC_RELEASE=$RELEASE" >> "$GITHUB_ENV"
echo "CGSpec: base ${BASE:-none}, release v$VERSION from $SOURCE"
"""
GITHUB_STEPS = """To make the CGSpec check impossible to bypass, do this once on GitHub (spec 8, trust root):
  1. Settings > Branches (or Rules): protect your main branch, require the 'governance' status check.
  2. Require your review for changes to .github/, docs/_cgspec/ and docs/slices/
     (CODEOWNERS with your account, plus 'Require review from Code Owners').
  3. Do not give the AI agent your GitHub admin credentials.
  4. For squash/rebase proof, configure a protected CI SSH signing identity in project.json
     proof_signers and run `cgspec_hook.py proof seal|map` only in a trusted job after candidate
     processes have ended. Keep the private key outside the checkout and never expose it to tests.
  Optional: sign approvals with a hardware key that needs your touch and list it in
  project.json approver_keys."""
CURSOR_RULE = """---
description: CGSpec project rules
alwaysApply: true
---
This project uses CGSpec. Read docs/_cgspec/01-engine/CONTRACT.md before acting. Cursor has no
hooks, so the git hooks and CI enforce the rules; run doctor.py before ending a task.
"""


def _command(event: str, tool: str) -> str:
    if tool == "claude":
        base = '"$CLAUDE_PROJECT_DIR"/'
    elif tool == "antigravity":
        # Antigravity starts hooks in .agents/ on some hosts, not the repo root.
        # A Git root handles nested working directories; the fallback covers installs before git init.
        base = '"$(git rev-parse --show-toplevel 2>/dev/null || { [ -f ' + HOOK + ' ] && pwd || (cd .. && pwd); })"/'
    else:
        base = ""
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


def _wire_one(fd: int, event: str, owns_already: bool) -> tuple[str, bool]:
    """Write one hook through the bound directory fd. Returns (note, claimed): claimed is True
    only when this checkout may now consider the event its own (a fresh slot, or one it already
    owned); an existing foreign-looking hook in an unconfirmed shared directory is never claimed."""
    kind = git_hooks.entry_kind(fd, event)
    if kind == "symlink":
        return f"left symlinked git {event} hook alone", False
    if kind == "other":
        return f"left existing git {event} hook alone; add the CGSpec call to it yourself", False
    expected = git_hooks.expected_hook_bytes(GIT_HOOK, HOOK, event)
    if kind == "file":
        if git_hooks.read_hook(fd, event) != expected:
            return f"left existing git {event} hook alone; add the CGSpec call to it yourself", False
        if not owns_already:
            return (f"left existing git {event} hook alone; shared hooks directory not yet "
                    "confirmed as this checkout's own"), False
        return f"git {event} hook already matches", True
    git_hooks.write_hook(fd, event, expected, 0o755)
    return f"wired git {event} hook", True


def _wire_git(root: Path, record: dict) -> list[str]:
    hooks, reason, needs_owner_record = git_hooks.directory(root)
    if hooks is None:
        msg = f"{reason}; add the CGSpec call yourself" if "add the CGSpec call" not in reason else reason
        return [msg]
    owns_already = not needs_owner_record or git_hooks.check_ownership(root, hooks, record) is None
    try:
        hooks.mkdir(parents=True, exist_ok=True)
        fd = git_hooks.open_hooks_dir(hooks)
    except (OSError, CgspecError) as exc:
        return [f"cannot prepare git hooks directory ({exc}): add the CGSpec call yourself"]
    notes, claimed_any = [], False
    try:
        for event in ("pre-commit", "commit-msg"):
            note, claimed = _wire_one(fd, event, owns_already)
            notes.append(note)
            if claimed:
                claimed_any = True
                if event not in record.get("git_hooks", []):
                    record.setdefault("git_hooks", []).append(event)
    finally:
        os.close(fd)
    if needs_owner_record and claimed_any:
        git_hooks.bind_ownership(root, hooks, record)
    return notes


def wire(root: Path, tools: list[str], owned: dict, profile: str = "") -> list[str]:
    notes, record = [], owned.setdefault("adapters", {})
    if "claude" in tools:
        record["claude"] = {"path": ".claude/settings.json", "created": _merge_json(root / ".claude/settings.json", _claude)}
        launcher = shutil.which("claude")
        record["claude"]["launcher"] = str(Path(launcher).absolute()) if launcher else None
        notes.append("wired .claude/settings.json")
    if "antigravity" in tools:
        record["antigravity"] = {"path": ".agents/hooks.json", "created": _merge_json(root / ".agents/hooks.json", _antigravity)}
        notes.append("wired .agents/hooks.json (Antigravity sends no user message to hooks: inbox capture unavailable there)")
        from .agent_skills import install as install_skills
        skills = install_skills(root, Path(__file__).resolve().parents[2])
        if skills:
            record["antigravity"]["skills"] = skills
            notes.append(f"copied {sum(1 for f in skills if f.endswith('SKILL.md'))} CGSpec skills into .agents/skills/")
    if "git" in tools:
        notes += _wire_git(root, record)
    if "ci" in tools:
        rel, select = ".github/workflows/cgspec.yml", ".github/cgspec-select.sh"
        visual_job = VISUAL_WORKFLOW.rstrip() if profile in {"website", "web-workspace", "mobile", "small"} else ""
        workflow = WORKFLOW.format().replace("      # CGSPEC_VISUAL_JOB", visual_job)
        ok, note = _write_new(root, rel, workflow)
        ok2, note2 = _write_new(root, select, SELECT, 0o755)
        notes += [note, note2]
        if ok and ok2:
            record["ci"] = rel
            record["ci_select"] = select
            _freeze_workflow(root, rel)
            _freeze_workflow(root, select)
            notes.append(GITHUB_STEPS)
    if "cursor" in tools:
        ok, note = _write_new(root, ".cursor/rules/cgspec.mdc", CURSOR_RULE)
        notes.append(note)
        if ok:
            record["cursor"] = ".cursor/rules/cgspec.mdc"
    return notes


def refresh(root: Path, owned: dict) -> list[str]:
    """Refresh installed AI-host adapters without changing unrelated user hooks."""
    record, notes = owned.get("adapters", {}), []
    notes += git_hooks.migrate(root, record, GIT_HOOK, HOOK)
    if "claude" in record:
        path = root / ".claude/settings.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            hooks = data.get("hooks", {})
            for event in list(hooks):
                hooks[event] = [entry for entry in hooks[event] if MARK not in json.dumps(entry)]
                if not hooks[event]:
                    del hooks[event]
            _claude(data)
            write_json(path, data)
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            raise CgspecError(f"cannot refresh Claude hooks: {exc}") from exc
        notes.append("refreshed Claude hooks")
        launcher = shutil.which("claude")
        record["claude"]["launcher"] = str(Path(launcher).absolute()) if launcher else None
    if "antigravity" in record:
        path = root / ".agents/hooks.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or "cgspec" not in data:
                raise ValueError("CGSpec hook block is missing")
        except (OSError, ValueError) as exc:
            raise CgspecError(f"cannot refresh Antigravity hooks: {exc}") from exc
        from .agent_skills import refresh as refresh_skills
        files, backups = refresh_skills(root, Path(__file__).resolve().parents[2],
                                        record["antigravity"].get("skills", []))
        _antigravity(data)
        write_json(path, data)
        record["antigravity"]["skills"] = files
        notes.append(f"refreshed Antigravity hooks and {len(files)} skill files; archived {backups} old copies")
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


def unwire(root: Path, owned: dict) -> list[str]:
    record = owned.get("adapters", {})
    notes = git_hooks.remove(root, record, GIT_HOOK, HOOK)
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
        from .agent_skills import uninstall as uninstall_skills
        uninstall_skills(root, record["antigravity"].get("skills", []))
    paths = [root / record[k] for k in ("ci", "ci_select", "cursor") if k in record]
    for path in paths:
        if path.is_file() and not path.is_symlink() and (MARK in path.read_text(errors="replace") or "CGSpec" in path.read_text(errors="replace")):
            os.chmod(path, 0o644)
            path.unlink()
    for rel in (".claude", ".agents", ".cursor/rules", ".cursor", ".github/workflows", ".github"):
        try:
            (root / rel).rmdir()
        except OSError:
            pass
    return notes
