"""Test helpers: import path for the engine and throwaway project trees."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENGINE = REPO / "engine"
if str(ENGINE) not in sys.path:
    sys.path.insert(0, str(ENGINE))

PY = sys.executable


def run_script(script: str, *args: str, cwd: Path | None = None, stdin: str | None = None):
    return subprocess.run(
        [PY, str(ENGINE / script), *args],
        cwd=cwd, input=stdin, capture_output=True, text=True, timeout=60,
    )


class TempDir:
    def __enter__(self) -> Path:
        self.path = Path(tempfile.mkdtemp(prefix="cgspec-test-"))
        return self.path

    def __exit__(self, *exc) -> None:
        shutil.rmtree(self.path, ignore_errors=True)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def snapshot_tree(root: Path) -> dict[str, bytes]:
    """Map of every file (relative path) to its bytes, ignoring caches."""
    out = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            out[path.relative_to(root).as_posix()] = path.read_bytes()
    return out


def install(root: Path, profile: str = "web-workspace", topology: str = "single", *extra: str):
    return run_script("install.py", "install", "--root", str(root), "--profile", profile,
                      "--topology", topology, "--tools", "claude,git", *extra)


def doctor(root: Path, *extra: str):
    return run_script("doctor.py", "--root", str(root), *extra)


def hook(root: Path, event: str, payload: dict | None = None, *extra: str):
    import json as _json
    return run_script("cgspec_hook.py", event, "--root", str(root), *extra,
                      stdin=_json.dumps(payload) if payload is not None else "")


def claude_payload(root: Path, tool: str, **tool_input) -> dict:
    for key in ("file_path", "notebook_path"):
        if key in tool_input and not str(tool_input[key]).startswith("/"):
            tool_input[key] = str(root / tool_input[key])
    return {"session_id": "s1", "cwd": str(root), "hook_event_name": "PreToolUse",
            "tool_name": tool, "tool_input": tool_input}


def git(root: Path, *args: str, check: bool = True):
    result = subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=t@example.com",
                             "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *args],
                            cwd=root, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {result.stderr}")
    return result


def git_project(root: Path, profile: str = "web-workspace") -> None:
    """Installed project in a git repo with one initial commit."""
    git(root, "init", "-q", "-b", "main")
    install(root, profile)
    (root / "src").mkdir(exist_ok=True)
    (root / "src/a.ts").write_text("export const a = 1;\n")
    (root / "src/login").mkdir(exist_ok=True)
    (root / "src/login/form.ts").write_text("export const f = 1;\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "init")


def approve(root: Path, text: str = "approved, go ahead") -> str:
    """Record an approval the way the user-message hook does and return its id."""
    import json as _json
    hook(root, "user-message", {"hook_event_name": "UserPromptSubmit", "prompt": text}, "--tool", "claude")
    data = _json.loads((root / "docs/_cgspec/07-state/approvals.json").read_text())
    return data["approvals"][-1]["id"]


def make_slice(root: Path, status: str = "Approved", scope: str = "src/login/**", approval: str | None = None,
               number: str = "001", index: bool = True) -> Path:
    approval = approval if approval is not None else approve(root)
    path = root / f"docs/slices/SLICE-{number}-login.md"
    lines = [f"# SLICE-{number}: Login", "", f"- **Status:** {status}", f"- **Scope:** {scope}"]
    if approval:
        lines.append(f"- **Approval:** {approval}")
    path.write_text("\n".join(lines) + "\n")
    idx = root / "docs/00-INDEX.md"
    entry = f"- [SLICE-{number}](slices/{path.name})"
    if index and entry not in idx.read_text():
        idx.write_text(idx.read_text() + "\n" + entry + "\n")
    return path


def set_test_command(root: Path, command: list[str]) -> None:
    """Set project.json test_command with a fresh approval from the user, ready to commit."""
    import json as _json
    import os as _os
    ref = approve(root, "approve the test command " + " ".join(command))
    pj = root / "docs/_cgspec/project.json"
    _os.chmod(pj, 0o644)
    data = _json.loads(pj.read_text())
    data.update(test_command=command, test_command_approval=ref)
    write_json(pj, data)
