"""Write gates shared by the pre-tool hook and (later) the commit hook. Pure decisions, no writes."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import layout as L
from . import tiers
from .common import ENGINE_DIR, MEMLOG_FILE, PROJECT_FILE, STATE_DIR
from .globs import match_any
from .governance_paths import GOVERNANCE_DIRS, GOVERNANCE_FILES, governance_path
from .inbox import contains_secret
from .path_policy import needs_tier

MAX_CODE_LINES = 400
HOST_PATH = re.compile(
    r"(?<![A-Za-z0-9_])(?:"
    r"/home/[A-Za-z0-9_.-]+/"
    r"|/Users/[A-Za-z0-9_.-]+/"
    r"|[A-Za-z]:\\\\Users\\\\[A-Za-z0-9_.-]+\\\\"
    r"|[A-Za-z]:\\Users\\[A-Za-z0-9_.-]+\\"
    r")"
)
EMOJI = re.compile(
    "[\\U0001F000-\\U0001FAFF]"  # pictographs, emoticons, transport, flags
    "|[\\u2614\\u2615\\u2648-\\u2653\\u267F\\u2693\\u26A1\\u26AA\\u26AB\\u26BD\\u26BE\\u26C4\\u26C5\\u26CE\\u26D4\\u26EA"
    "\\u26F2\\u26F3\\u26F5\\u26FA\\u26FD\\u2705\\u270A\\u270B\\u2728\\u274C\\u274E\\u2753-\\u2755\\u2757\\u2795-\\u2797"
    "\\u27B0\\u27BF\\u2B1B\\u2B1C\\u2B50\\u2B55]"  # symbols shown as emoji by default
    "|.\\uFE0F"  # any symbol forced into emoji presentation
)
ALWAYS_PROTECTED = [
    PROJECT_FILE.as_posix(),
    (STATE_DIR / "checkpoint.json").as_posix(),
    (STATE_DIR / "stop-retries.json").as_posix(),
    (STATE_DIR / "frozen.json").as_posix(),
    (STATE_DIR / "tier.json").as_posix(),
    (STATE_DIR / "approvals.json").as_posix(),
    "docs/_cgspec/04-checks/manifest.json",
    "docs/prototypes/_baselines/active.json",
    MEMLOG_FILE.as_posix(),
]
GUARD_FILES = [".claude/settings.json", ".agents/hooks.json"]  # lab finding: an agent disabled its own hooks
GUARD_DIRS = [".git/hooks/", ".agents/skills/"]
# lab finding: a sub-agent ran `cat ~/.bash_history | grep ...` looking for a credential it had seen earlier.
CREDENTIAL_STORE_HINTS = (".bash_history", ".zsh_history", ".fish_history", "fish/fish_history",
                           ".ssh/id_", ".ssh/authorized_keys", ".aws/credentials", ".netrc", ".git-credentials",
                           ".docker/config.json")


def credential_read_reasons(command: str) -> list[str]:
    lowered = command.lower()
    return [f"command references {hint}, a credential store; use the environment variables already provided "
            "instead of reading secrets from disk" for hint in CREDENTIAL_STORE_HINTS if hint in lowered]


@dataclass
class Context:
    root: Path
    project: dict = field(default_factory=dict)
    frozen: set[str] = field(default_factory=set)
    checks: set[str] = field(default_factory=set)
    legacy: set[str] = field(default_factory=set)

    @classmethod
    def load(cls, root: Path) -> "Context":
        def read(rel: str) -> dict:
            try:
                data = json.loads((root / rel).read_text(encoding="utf-8"))
                return data if isinstance(data, dict) else {}
            except (OSError, ValueError):
                return {}
        frozen = {e.get("path", "") for e in read((STATE_DIR / "frozen.json").as_posix()).get("entries", [])}
        checks = {p for c in read("docs/_cgspec/04-checks/manifest.json").get("checks", [])
                  for p in (c.get("path", ""), c.get("guide", "")) if p}
        legacy_files = read((STATE_DIR / "legacy-baseline.json").as_posix()).get("files", {})
        legacy = set(legacy_files) if isinstance(legacy_files, dict) else set()
        return cls(root, read(PROJECT_FILE.as_posix()), frozen, checks, legacy)

    @property
    def classes(self) -> dict:
        value = self.project.get("path_classes", {})
        return value if isinstance(value, dict) else {}

    def protected(self, rel: str) -> str | None:
        if governance_path(rel):
            return "governance path; an authenticated approval for this exact change is required"
        if rel == ENGINE_DIR.as_posix() or rel.startswith(ENGINE_DIR.as_posix() + "/"):
            return "the vendored engine changes only through install.py upgrade"
        if rel in ALWAYS_PROTECTED:
            return "this state file is written only by the engine"
        if rel.startswith("docs/_cgspec/05-runs/"):
            return "run records are created and managed only through cgspec_hook.py run commands"
        if rel in GUARD_FILES or any(rel.startswith(d) or rel + "/" == d for d in GUARD_DIRS):
            return ("CGSpec's hooks and skills are installed here; an agent never changes its own guards or method. "
                    "The user changes them with install.py upgrade or uninstall")
        if rel in self.frozen:
            return "this file is frozen (07-state/frozen.json); cut a new version instead"
        if rel in self.checks:
            return "registered checks change only through the registration flow"
        return None

    def relative(self, raw: str, cwd: str | None = None) -> str | None:
        """Project-relative posix path, or None when the path is outside the project."""
        base = Path(cwd) if cwd else self.root
        path = Path(os.path.expanduser(raw))
        full = Path(os.path.realpath(path if path.is_absolute() else base / path))
        try:
            return full.relative_to(os.path.realpath(self.root)).as_posix()
        except ValueError:
            return None


def _git_ok(root: Path, *args: str) -> bool:
    import subprocess
    try:
        return subprocess.run(["git", *args], cwd=root, capture_output=True, timeout=10).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def git_ignored(root: Path, rel: str) -> bool:
    return _git_ok(root, "check-ignore", "-q", "--", rel)


def git_tracked(root: Path, rel: str) -> bool:
    """True when rel, or anything under it, is tracked by git."""
    import subprocess
    try:
        out = subprocess.run(["git", "ls-files", "--", rel], cwd=root, capture_output=True, text=True, timeout=10)
        return out.returncode == 0 and bool(out.stdout.strip())
    except (OSError, subprocess.TimeoutExpired):
        return True  # unknown: be careful


def protected_list(ctx: "Context") -> list[str]:
    return sorted(ctx.frozen | ctx.checks | set(ALWAYS_PROTECTED) | set(GUARD_FILES) |
                  GOVERNANCE_FILES) + [ENGINE_DIR.as_posix() + "/"] + GUARD_DIRS + list(GOVERNANCE_DIRS)


def _is_script_name(rel: str, content: str | None) -> bool:
    return Path(rel).suffix.lower() in L.SCRIPT_SUFFIXES or bool(content and content.startswith("#!"))


def _script_allowed(ctx: Context, rel: str, content: str | None) -> bool:
    if rel.startswith(".cgspec-scratch/"):
        return True
    if rel in ctx.checks:
        return True  # already approved and registered (spec 8); its hash is pinned in the manifest
    # Registration creates an approved Markdown guide beside the registered script.
    if rel.startswith("docs/_cgspec/04-checks/") and Path(rel).suffix.lower() == ".md":
        return rel in ctx.checks
    if not rel.startswith("docs/"):
        return match_any(rel, ctx.classes.get("code", []) + ctx.classes.get("tests", []) + L.CONFIG_GLOBS)
    from .doctor_checks import _browser_code_only  # local import keeps gates light
    in_proto = rel.startswith("docs/prototypes/") and rel.count("/") >= 3 and "/_snapshots/" not in rel
    return in_proto and Path(rel).suffix.lower() in L.PROTOTYPE_ASSET_SUFFIXES and _browser_code_only(content or "")


def _tier_reason(ctx: Context, rel: str, is_new: bool) -> str | None:
    if not needs_tier(rel) or git_ignored(ctx.root, rel):
        return None
    tier = tiers.active(ctx.root)
    hint = "declare it first: python3 docs/_cgspec/01-engine/cgspec_hook.py tier set --tier T0|T1|T2|T3 ..."
    if not tier:
        return f"no change tier declared for {rel}; {hint}"
    if tier["tier"] == "T0":
        if is_new:
            return f"T0 cannot create files ({rel}); use T1 with a slice"
        if rel not in tier.get("files", []):
            return f"{rel} is not in the T0 file list {tier.get('files', [])}; widen the tier"
        return None
    found = tiers.find_slice(ctx.root, tier.get("slice", ""))
    if not found or found[1] not in tiers.WORKING_SLICE:
        return f"slice {tier.get('slice')} is missing or not Approved/In progress"
    if not match_any(rel, found[2]):
        return f"{rel} is outside the scope of {tier.get('slice')} ({', '.join(found[2])})"
    return None


def _hygiene_reasons(ctx: Context, rel: str, content: str) -> list[str]:
    reasons = []
    if "\r\n" in content:
        reasons.append(f"CRLF line endings in content for {rel}; use LF (\\n) only")
    in_code = match_any(rel, ctx.classes.get("code", []))
    if in_code and rel not in ctx.legacy and len(content.splitlines()) > MAX_CODE_LINES:
        reasons.append(f"{rel} exceeds {MAX_CODE_LINES} lines (spec 7b); split into smaller single-purpose files")
    if (in_code or match_any(rel, L.CONFIG_GLOBS)) and HOST_PATH.search(content):
        reasons.append(f"content for {rel} contains a hardcoded host path; use project-relative paths or environment variables")
    return reasons


def project_content(root: Path, rel: str, payload: dict, tool: str, fallback: str | None) -> str | None:
    """Project the resulting file content after a tool edit or write."""
    target = root / rel
    if tool == "antigravity":
        args = (payload.get("toolCall") or {}).get("args") or {}
        name = (payload.get("toolCall") or {}).get("name", "")
        if name in ("replace_file_content", "multi_replace_file_content") and target.is_file():
            chunks = args.get("ReplacementChunks") or [
                {"TargetContent": args.get("TargetContent", ""), "ReplacementContent": args.get("ReplacementContent", "")}
            ]
            try:
                orig = target.read_text(encoding="utf-8", errors="replace")
                replaced = orig
                for c in chunks:
                    t, r = c.get("TargetContent", ""), c.get("ReplacementContent", "")
                    if t and t in replaced:
                        replaced = replaced.replace(t, r, 1)
                if replaced != orig:
                    return replaced
            except OSError:
                return fallback
        elif name == "write_to_file":
            if args.get("Append") and target.is_file():
                try:
                    return target.read_text(encoding="utf-8", errors="replace") + (args.get("CodeContent") or "")
                except OSError:
                    return fallback
            if args.get("CodeContent") is not None:
                return args.get("CodeContent")
    elif tool == "claude":
        name, data = payload.get("tool_name", ""), payload.get("tool_input") or {}
        if name in ("Edit", "MultiEdit") and target.is_file():
            edits = data.get("edits") or [{"old_string": data.get("old_string", ""), "new_string": data.get("new_string", "")}]
            try:
                orig = target.read_text(encoding="utf-8", errors="replace")
                replaced = orig
                for e in edits:
                    o, n = e.get("old_string", ""), e.get("new_string", "")
                    if o and o in replaced:
                        replaced = replaced.replace(o, n, 1)
                if replaced != orig:
                    return replaced
            except OSError:
                return fallback
        if name == "Write" and data.get("content") is not None:
            return data.get("content")
    return fallback



def check_write(ctx: Context, rel: str, content: str | None, is_new: bool | None = None) -> list[str]:
    """Reasons to refuse writing `rel` (project-relative). Empty list means allowed."""
    reasons = []
    is_new = not (ctx.root / rel).exists() if is_new is None else is_new
    why = ctx.protected(rel)
    if why:
        reasons.append(f"{rel} is protected: {why}")
    from . import runs
    unit_why = runs.check_unit_scope(ctx.root, rel)
    if unit_why:
        reasons.append(unit_why)
    if is_new and _is_script_name(rel, content) and not _script_allowed(ctx, rel, content):
        reasons.append(f"new script {rel} is not allowed here; scripts live in src/, tests, "
                       ".cgspec-scratch/ or a registered check (spec 8)")
    if content and EMOJI.search(content):
        reasons.append(f"decorative emoji in content for {rel} (spec 1: no emojis)")
    if content and (kind := contains_secret(content)):
        reasons.append(f"content for {rel} looks like a {kind} (spec 1: no secrets in files; "
                       "use environment variables, and reference them by name only)")
    if content:
        reasons += _hygiene_reasons(ctx, rel, content)
    elif (ctx.root / rel).is_file() and match_any(rel, ctx.classes.get("code", [])) and rel not in ctx.legacy:
        try:
            cnt = len((ctx.root / rel).read_text(encoding="utf-8", errors="replace").splitlines())
            if cnt > MAX_CODE_LINES:
                reasons.append(f"{rel} ({cnt} lines) exceeds {MAX_CODE_LINES} lines (spec 7b); split into smaller single-purpose files")
        except OSError:
            pass
    tier_why = None if why else _tier_reason(ctx, rel, is_new)
    if tier_why:
        reasons.append(tier_why)
    return reasons
