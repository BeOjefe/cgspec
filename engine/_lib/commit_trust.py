"""Trust-root rules for commits (spec 8): frozen files, append-only manifests, the engine,
approvals. Pure functions over a git View; used by the commit hook and by CI."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from . import tiers
from .common import ENGINE_DIR, PROJECT_FILE, STATE_DIR
from .gitview import View
from .inbox import approval_target

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


def trusted_signature(view: View) -> bool:
    """Verify the judged commit against approver keys already trusted by its parent.

    A key introduced by the judged commit cannot establish trust in that same commit.
    Staged changes have no commit signature yet; CI verifies the final commit.
    """
    keys = load(view.read_old(PROJECT_FILE.as_posix())).get("approver_keys", [])
    if not isinstance(keys, list) or not keys or view.new == ":":
        return False
    import tempfile
    from .gitview import git
    ssh_keys = [k for k in keys if k.startswith(("ssh-", "ecdsa-", "sk-"))]
    with tempfile.NamedTemporaryFile("w", suffix=".allowed", delete=False) as handle:
        handle.write("".join(f"approver {k}\n" for k in ssh_keys))
        allowed = handle.name
    try:
        out = git(view.root, "-c", f"gpg.ssh.allowedSignersFile={allowed}", "log", "-1",
                  "--format=%G?%n%GF%n%GP", view.new).stdout.split("\n")
    finally:
        Path(allowed).unlink(missing_ok=True)
    if out[0] != "G":
        return False
    signed_fingerprint = out[1].strip() if len(out) > 1 else ""
    for key in ssh_keys:
        try:
            blob = base64.b64decode(key.split()[1], validate=True)
        except (IndexError, ValueError, binascii.Error):
            continue
        digest = base64.b64encode(hashlib.sha256(blob).digest()).decode().rstrip("=")
        if signed_fingerprint == "SHA256:" + digest:
            return True
    return signed_fingerprint in {k for k in keys if k not in ssh_keys}


def approver_key_change(view: View) -> list[str]:
    """Key changes require a signature made with a key trusted before the change.

    The first key must be established in the protected installation baseline or by
    separately verified GitHub review; this local check cannot attest to a review.
    """
    old = load(view.read_old(PROJECT_FILE.as_posix())).get("approver_keys", [])
    new = load(view.read_new(PROJECT_FILE.as_posix())).get("approver_keys", [])
    if old == new or view.new == ":":
        return []
    if trusted_signature(view):
        return []
    return ["project.json approver_keys changed without a commit signature from a previously trusted key; "
            "bootstrap requires a protected installation baseline or separately verified GitHub review"]


def fresh_approvals(view: View) -> dict[str, dict]:
    """Approvals added in this change: only these may be cited by records changed here."""
    old = {a.get("id") for a in load(view.read_old(APPROVALS)).get("approvals", []) if isinstance(a, dict)}
    return {a["id"]: a for a in load(view.read_new(APPROVALS)).get("approvals", [])
            if isinstance(a, dict) and a.get("id") and a["id"] not in old}


RECORD_ID = re.compile(r"\b((?:SLICE|ADR|CHK)-\d{3})\b", re.I)


def approval_ok(view: View, ref: str, record_id: str | None = None) -> str | None:
    """None when ref validly approves the record changed in this commit, else the reason."""
    if ref == TRAILER_REF:
        message = commit_message(view)
        if message is None:
            return None  # staged: commit-msg checks the trailer, CI checks the signature
        if not TRAILER.search(message):
            return "cites the commit trailer but the commit has no 'Approved-by:' line"
        if not trusted_signature(view):
            return "cites the commit trailer but the commit is not signed by a key in project.json approver_keys"
        return None
    fresh = fresh_approvals(view)
    if ref not in fresh:
        known = ref in approval_ids(view)
        return (f"cites approval {ref!r}, which was not given in this change (approvals are single-use and fresh)"
                if known else f"cites approval {ref!r}, which is not in {APPROVALS}")
    target = approval_target(str(fresh[ref].get("excerpt", "")))
    if target != record_id:
        if target and target.startswith(("SLICE-", "ADR-", "CHK-")):
            return f"cites approval {ref}, but your message names {target}, not {record_id}"
        return f"cites approval {ref}, but your message does not name {record_id or 'an approval target'}"
    return None


def citation_counts(view: View) -> dict[str, int]:
    counts: dict[str, int] = {}
    def add(ref):
        if ref and ref != TRAILER_REF:
            counts[ref] = counts.get(ref, 0) + 1
    for rel in view.files_new("docs/slices"):
        add(slice_fields((view.read_new(rel) or b"").decode("utf-8", "replace"))[2])
    for check in load(view.read_new(CHECKS)).get("checks", []):
        if isinstance(check, dict):
            add(str((check.get("approval") or {}).get("ref", "")))
    for line in (view.read_new("docs/_memlog.md") or b"").decode("utf-8", "replace").splitlines():
        match = APPROVAL_FIELD.match(line)
        add(match.group(1).strip().strip("`") if match else "")
    add(load(view.read_new(PROJECT_FILE.as_posix())).get("test_command_approval", ""))
    return counts


def single_use(view: View) -> list[str]:
    return [f"approval {ref} is already cited by another record; each approval approves one thing"
            for ref, n in citation_counts(view).items() if n > 1]


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
    skills = set(((owned.get("adapters") or {}).get("antigravity") or {}).get("skills", []))
    return {p for p in paths if p.startswith("docs/")} | ADAPTER_PATHS | skills


def approval_ids(view: View) -> set[str]:
    return {a.get("id") for a in load(view.read_new(APPROVALS)).get("approvals", []) if isinstance(a, dict)}


def test_command_change(view: View) -> list[str]:
    old = load(view.read_old(PROJECT_FILE.as_posix()))
    new = load(view.read_new(PROJECT_FILE.as_posix()))
    if old.get("test_command") == new.get("test_command"):
        return []
    command = new.get("test_command")
    if not (isinstance(command, list) and command and "{test_file}" in command):
        return ["project.json test_command must be a list containing \"{test_file}\""]
    problem = approval_ok(view, str(new.get("test_command_approval", "")), "test_command")
    return [f"project.json test_command changed; its approval {problem}"] if problem else []


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
    old_ids = {c.get("id") for c in load(view.read_old(CHECKS)).get("checks", []) if isinstance(c, dict)}
    reasons = []
    for check in load(view.read_new(CHECKS)).get("checks", []):
        if isinstance(check, dict) and check.get("id") not in old_ids:
            ref = str((check.get("approval") or {}).get("ref", ""))
            problem = approval_ok(view, ref, str(check.get("id", "")))
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
    reasons = []
    for change in changes:
        if not change.path.startswith("docs/slices/") or change.status == "D":
            continue
        new = slice_fields((view.read_new(change.path) or b"").decode("utf-8", "replace"))
        if new[0] not in ("Approved", "In progress", "Done"):
            continue
        found_id = RECORD_ID.search(Path(change.path).name)
        slice_id = found_id.group(1) if found_id else None
        old_text = (view.read_old(change.old_path or change.path) or b"").decode("utf-8", "replace")
        old = slice_fields(old_text) if old_text else ("", "", "")
        if old[0] in ("Approved", "In progress", "Done") and old[1] == new[1] and old[2] == new[2]:
            continue  # same scope and approval: a status step inside approved work needs nothing new
        problem = approval_ok(view, new[2], slice_id) if new[2] else "cites no approval from your messages"
        if problem:
            reasons.append(f"{change.path} is {new[0]} but {problem}")
            continue
        if old[0] and old[1] != new[1] and old[2] == new[2]:
            reasons.append(f"{change.path}: Scope changed without a new approval")
    return reasons


def ledger_approvals(view: View) -> list[str]:
    """Ledger lines added in this change that claim an approval must cite a valid one."""
    added = Counter(view.added_lines().get("docs/_memlog.md", []))
    lines = (view.read_new("docs/_memlog.md") or b"").decode("utf-8", "replace").splitlines()
    reasons = []
    summary = ""
    for line in lines:
        if line.startswith("### ["):
            summary = ""
        found = re.match(tiers.FIELD % "Summary", line, re.I)
        if found:
            summary = found.group(1).strip()
        match = APPROVAL_FIELD.match(line)
        if match and added[line]:
            added[line] -= 1
            expected = f"decision:{' '.join(summary.split()).casefold()}" if summary else None
            problem = approval_ok(view, match.group(1).strip().strip("`"), expected)
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


def is_bootstrap(view: View) -> bool:
    """True for the first commit that introduces CGSpec project state in this history."""
    if view.read_old(PROJECT_FILE.as_posix()) is not None or view.read_new(PROJECT_FILE.as_posix()) is None:
        return False
    from .gitview import git
    seen = bool(view.old and git(view.root, "log", "-1", "--format=%H", view.old,
                                 "--", PROJECT_FILE.as_posix()).stdout.strip())
    return not seen


def canonical_adapter_refresh(view: View, rel: str) -> bool:
    """True when an existing Claude or Antigravity adapter file changed only by the exact
    canonical `adapters.refresh` transformation."""
    if rel not in {".claude/settings.json", ".agents/hooks.json"}:
        return False
    old_raw, new_raw = view.read_old(rel), view.read_new(rel)
    if not old_raw or not new_raw:
        return False
    try:
        expected = json.loads(old_raw.decode("utf-8"))
        actual = json.loads(new_raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return False
    if not isinstance(expected, dict) or not isinstance(actual, dict):
        return False
    from . import adapters
    if rel == ".claude/settings.json":
        hooks = expected.get("hooks", {})
        if not isinstance(hooks, dict):
            return False
        for event in list(hooks):
            if isinstance(hooks.get(event), list):
                hooks[event] = [e for e in hooks[event] if adapters.MARK not in json.dumps(e)]
                if not hooks[event]:
                    del hooks[event]
        adapters._claude(expected)
    else:
        if "cgspec" not in expected:
            return False
        adapters._antigravity(expected)
    return actual == expected


def governance_change(view: View) -> bool:
    """True when the change touches the fixed governance floor or the trusted plugin source."""
    from .governance_paths import governance_path
    if is_bootstrap(view):
        return False
    for change in view.changes():
        if any(governance_path(rel) and not canonical_adapter_refresh(view, rel)
               for rel in (change.path, change.old_path) if rel):
            return True
    old = load(view.read_old(PROJECT_FILE.as_posix()))
    new = load(view.read_new(PROJECT_FILE.as_posix()))
    return bool(old) and bool(new) and old.get("plugin_source") != new.get("plugin_source")


def governance_authorized(view: View) -> bool:
    """A governance change needs the user's `Approved-by:` trailer on a commit signed by a key the
    parent already trusted. A staged change has no message yet: when the parent has trusted
    approver keys, commit-msg demands the trailer and CI verifies the signature."""
    message = commit_message(view)
    if message is None:
        return bool(load(view.read_old(PROJECT_FILE.as_posix())).get("approver_keys"))
    return bool(TRAILER.search(message)) and trusted_signature(view)


def commit_msg_problem(root: Path, text: str) -> str | None:
    """Why the message file cannot be committed with the staged change, or None."""
    view = View.staged(root)
    if TRAILER.search(text):
        return None
    if staged_trailer_refs(view):
        return "CGSpec: this commit cites the 'trailer' approval; add 'Approved-by: <you>' to the message yourself"
    if governance_change(view):
        return ("CGSpec: this commit changes governance files (hooks, workflows, ownership, plugin source); "
                "add 'Approved-by: <you>' yourself and sign the commit with a trusted approver key")
    return None
