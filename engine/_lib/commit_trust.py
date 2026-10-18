"""Trust-root rules for commits (spec 8): frozen files, append-only manifests, the engine,
approvals. Pure functions over a git View; used by the commit hook and by CI."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from . import tiers
from .common import ENGINE_DIR, PROJECT_FILE, STATE_DIR
from .gitview import View

FROZEN = (STATE_DIR / "frozen.json").as_posix()
CHECKS = "docs/_cgspec/04-checks/manifest.json"
APPROVALS = (STATE_DIR / "approvals.json").as_posix()
INBOX = "docs/00-INBOX.md"
ENGINE = ENGINE_DIR.as_posix() + "/"
ENGINE_BOOKKEEPING = {"manifest.json", "owned-files.json"}
ADAPTER_PATHS = {".claude/settings.json", ".agents/hooks.json", ".github/workflows/cgspec.yml", ".github/cgspec-select.sh",
                 ".cursor/rules/cgspec.mdc", ".gitignore", "AGENTS.md", "CLAUDE.md"}
APPROVAL_FIELD = re.compile(tiers.FIELD % "Approval", re.M | re.I)
TRAILER = re.compile(r"^Approved-by:\s*\S", re.M | re.I)
TRAILER_REF = "trailer"


def commit_message(view: View) -> str | None:
    """The message of the commit being judged; None for a staged change (commit-msg checks it)."""
    if view.new == ":":
        return None
    from .gitview import git
    return git(view.root, "log", "-1", "--format=%B", view.new).stdout


def approval_ok(view: View, ref: str, ids: set[str]) -> str | None:
    """None when ref is a valid approval for this change, else the reason."""
    if ref in ids:
        return None
    if ref == TRAILER_REF:
        message = commit_message(view)
        if message is None or TRAILER.search(message):
            return None
        return "cites the commit trailer but the commit has no 'Approved-by:' line"
    return f"cites approval {ref!r}, which is not in {APPROVALS}"


def load(raw: bytes | None) -> dict:
    try:
        data = json.loads(raw.decode("utf-8")) if raw else {}
        return data if isinstance(data, dict) else {}
    except (UnicodeDecodeError, ValueError):
        return {}


def engine_file(rel: str) -> str | None:
    """Engine-relative name of a tracked engine file, ignoring bookkeeping and caches."""
    if not rel.startswith(ENGINE):
        return None
    name = rel[len(ENGINE):]
    if name in ENGINE_BOOKKEEPING or "__pycache__/" in name or name.endswith(".pyc"):
        return None
    return name


def append_only(view: View) -> list[str]:
    reasons = []
    for rel, key, ident in ((FROZEN, "entries", "path"), (CHECKS, "checks", "id"), (APPROVALS, "approvals", "id")):
        old = {e.get(ident): e for e in load(view.read_old(rel)).get(key, []) if isinstance(e, dict)}
        new = {e.get(ident): e for e in load(view.read_new(rel)).get(key, []) if isinstance(e, dict)}
        reasons += [f"{rel} is append-only: existing entry {k} was changed or removed"
                    for k, entry in old.items() if new.get(k) != entry]
    return reasons


def frozen_touched(view: View, changes) -> list[str]:
    frozen_old = {e.get("path") for e in load(view.read_old(FROZEN)).get("entries", [])}
    return [f"{rel} is frozen and was changed ({c.status})"
            for c in changes for rel in filter(None, (c.path, c.old_path)) if rel in frozen_old]


def engine_changes(view: View, changes, release_dir: Path | None, strict: bool) -> list[str]:
    """Engine files may change only to match a published plugin release (CI) or, locally, the manifest."""
    if not any(engine_file(c.path) or engine_file(c.old_path or "") for c in changes):
        return []
    names = [n for n in (engine_file(p) for p in view.files_new(ENGINE_DIR.as_posix())) if n]
    if release_dir is not None:
        source = release_dir / "engine"
        reasons = [f"engine file {n} differs from plugin release at {release_dir}" for n in names
                   if not (source / n).is_file() or (source / n).read_bytes() != (view.read_new(ENGINE + n) or b"")]
        expected = {p.relative_to(source).as_posix() for p in source.rglob("*")
                    if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}
        reasons += [f"engine file {n} from the release is missing" for n in sorted(expected - set(names))]
        return reasons
    if strict:
        return ["the engine changed; CI must verify it against the plugin release (--release-dir)"]
    manifest = load(view.read_new(ENGINE + "manifest.json")).get("files", {})
    return [f"engine file {n} does not match the engine manifest; only install.py upgrade changes the engine"
            for n in names if manifest.get(n) != hashlib.sha256(view.read_new(ENGINE + n) or b"").hexdigest()]


def is_install_commit(view: View) -> bool:
    old = load(view.read_old(PROJECT_FILE.as_posix())).get("cgspec_version")
    new = load(view.read_new(PROJECT_FILE.as_posix())).get("cgspec_version")
    version = (view.read_new(ENGINE + "VERSION") or b"").decode("utf-8", "replace").strip()
    return bool(new) and new != old and new == version


def install_exempt(view: View) -> set[str]:
    """Files an install/upgrade commit may add without a tier: template docs and adapter files only."""
    if not is_install_commit(view):
        return set()
    owned = load(view.read_new(ENGINE + "owned-files.json"))
    paths = set(owned.get("created", {})) | set(owned.get("replaced", {}))
    return {p for p in paths if p.startswith("docs/")} | ADAPTER_PATHS


def approval_ids(view: View) -> set[str]:
    return {a.get("id") for a in load(view.read_new(APPROVALS)).get("approvals", []) if isinstance(a, dict)}


def approvals_have_inbox_lines(view: View) -> list[str]:
    old = {a.get("id") for a in load(view.read_old(APPROVALS)).get("approvals", []) if isinstance(a, dict)}
    inbox = (view.read_new(INBOX) or b"").decode("utf-8", "replace")
    reasons = []
    for entry in load(view.read_new(APPROVALS)).get("approvals", []):
        if isinstance(entry, dict) and entry.get("id") not in old:
            excerpt = str(entry.get("excerpt", ""))[:80]
            if not excerpt or excerpt not in inbox:
                reasons.append(f"approval {entry.get('id')} has no matching message in {INBOX}")
    return reasons


def check_approvals(view: View) -> list[str]:
    ids = approval_ids(view)
    old_ids = {c.get("id") for c in load(view.read_old(CHECKS)).get("checks", []) if isinstance(c, dict)}
    reasons = []
    for check in load(view.read_new(CHECKS)).get("checks", []):
        if isinstance(check, dict) and check.get("id") not in old_ids:
            ref = str((check.get("approval") or {}).get("ref", ""))
            problem = approval_ok(view, ref, ids)
            if problem:
                reasons.append(f"registered check {check.get('id')} {problem}")
    return reasons


def slice_fields(text: str) -> tuple[str, str, str]:
    def field(name):
        match = re.search(tiers.FIELD % name, text, re.M | re.I)
        return match.group(1).strip().strip("`").strip() if match else ""
    return field("Status"), field("Scope"), field("Approval")


def slice_approvals(view: View, changes) -> list[str]:
    """Approved slices must cite a real approval; a changed Scope needs a new one."""
    ids, reasons = approval_ids(view), []
    for change in changes:
        if not change.path.startswith("docs/slices/") or change.status == "D":
            continue
        new = slice_fields((view.read_new(change.path) or b"").decode("utf-8", "replace"))
        if new[0] not in ("Approved", "In progress", "Done"):
            continue
        problem = approval_ok(view, new[2], ids) if new[2] else "cites no approval from your messages"
        if problem:
            reasons.append(f"{change.path} is {new[0]} but {problem}")
            continue
        old = slice_fields((view.read_old(change.old_path or change.path) or b"").decode("utf-8", "replace"))
        if old[0] and old[1] != new[1] and old[2] == new[2]:
            reasons.append(f"{change.path}: Scope changed without a new approval")
    return reasons


def ledger_approvals(view: View) -> list[str]:
    """Ledger lines added in this change that claim an approval must cite a valid one."""
    ids = approval_ids(view)
    added = view.added_lines().get("docs/_memlog.md", [])
    reasons = []
    for line in added:
        match = APPROVAL_FIELD.match(line)
        if match:
            problem = approval_ok(view, match.group(1).strip().strip("`"), ids)
            if problem:
                reasons.append(f"docs/_memlog.md: an entry {problem}")
    return reasons


def staged_trailer_refs(view: View) -> bool:
    """True when the staged change cites the commit trailer anywhere (commit-msg must then see one)."""
    for path, lines in view.added_lines().items():
        if path.startswith("docs/slices/") or path == "docs/_memlog.md":
            if any((m := APPROVAL_FIELD.match(l)) and m.group(1).strip().strip("`") == TRAILER_REF for l in lines):
                return True
    return False
