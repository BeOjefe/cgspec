"""Commit-level rules (spec 8, commit hook and CI columns), evaluated on a git View."""

from __future__ import annotations

import hashlib
from pathlib import Path

from . import tiers
from .common import ENGINE_DIR, PROJECT_FILE, STATE_DIR
from . import commit_trust as trust
from .gates import EMOJI, Context, _is_script_name, _script_allowed
from .gitview import View
from .document_dates import managed_doc, validate_change
from .path_policy import live_prototype_source, needs_tier, prototype_journey
from .globs import match_any


def _preserved_prototype(view: View, change) -> bool:
    if not change.path.startswith(("docs/prototypes/_archive/", "docs/prototypes/_snapshots/")):
        return False
    content = view.read_new(change.path)
    if content is None:
        return False
    if (change.status == "R" and change.old_path and live_prototype_source(change.old_path)
            and Path(change.old_path).suffix == Path(change.path).suffix
            and change.path.startswith("docs/prototypes/_archive/")):
        return content == view.read_old(change.old_path)
    if (change.status == "A" and change.path.startswith("docs/prototypes/_snapshots/")
            and change.path.count("/") == 3 and change.path.endswith(".html")):
        entries = trust.load(view.read_new(trust.FROZEN)).get("entries", [])
        return any(isinstance(e, dict) and e.get("path") == change.path and e.get("kind") == "snapshot"
                   and e.get("sha256") == hashlib.sha256(content).hexdigest() for e in entries)
    return False


def _slice(view: View, slice_id: str) -> tuple[str, list[str], str] | None:
    """(status, scope globs, approval id) of SLICE-NNN in the new tree."""
    bare = slice_id.split(":")[-1]
    for rel in view.files_new("docs/slices"):
        if Path(rel).name.startswith(bare + "-"):
            status, scope, approval = trust.slice_fields((view.read_new(rel) or b"").decode("utf-8", "replace"))
            return status, [g.strip().strip("`") for g in scope.split(",") if g.strip()], approval
    return None


def _tier_rules(view: View, code_changes, tier: dict | None) -> list[str]:
    if not code_changes:
        return []
    paths = {c.path for c in code_changes}
    paths |= {c.old_path for c in code_changes if c.old_path and needs_tier(c.old_path)}
    if not tier:
        return [f"no change tier declared for {sorted(paths)} (07-state/tier.json)"]
    lines = view.changed_line_count(paths | {c.old_path for c in code_changes if c.old_path})
    if tier.get("tier") == "T0":
        reasons = [f"T0 cannot create files ({c.path})" for c in code_changes if c.status in "AC"]
        reasons += [f"{p} is not in the T0 file list" for p in sorted(paths) if p not in tier.get("files", [])]
        if len(paths) > tiers.T0_MAX_FILES:
            reasons.append(f"T0 allows {tiers.T0_MAX_FILES} files, this commit changes {len(paths)}")
        if lines > tiers.T0_MAX_LINES:
            reasons.append(f"T0 allows {tiers.T0_MAX_LINES} changed lines, this commit changes {lines}")
        return reasons
    found = _slice(view, tier.get("slice", ""))
    if not found or found[0] not in tiers.WORKING_SLICE:
        return [f"slice {tier.get('slice')} is missing or not Approved/In progress"]
    if found[2] != trust.TRAILER_REF and found[2] not in trust.approval_ids(view):
        return [f"slice {tier.get('slice')} cites no approval from your messages"]
    reasons = [f"{p} is outside the scope of {tier.get('slice')}" for p in sorted(paths) if not match_any(p, found[1])]
    if tier.get("tier") == "T1" and lines > tiers.T1_MAX_LINES:
        reasons.append(f"T1 allows {tiers.T1_MAX_LINES} changed lines, this commit changes {lines}")
    return reasons


def _test_pairs(view: View, code_changes, tier: dict | None, classes: dict, project: dict) -> list[str]:
    if not tier or tier.get("tier") == "T0":
        return []
    command = project.get("test_command")
    code = [c.path for c in code_changes if c.status != "D"
            and (live_prototype_source(c.path) or match_any(c.path, classes.get("code", [])))
            and not (prototype_journey(c.path) or match_any(c.path, classes.get("tests", [])))
            and not _preserved_prototype(view, c)]
    paths = [p for p in view.files_new("docs/_cgspec/06-evidence/tests") if p.endswith(".json")]
    records = [r for r in (trust.load(view.read_new(p)) for p in paths) if r.get("slice") == tier.get("slice")]
    head = "HEAD" if view.new == ":" else view.new
    reasons = []
    for record in records:
        rev, test_file = record.get("failed_at", ""), record.get("test_file", "")
        if not (view.commit_exists(rev) and view.is_ancestor(rev, head)):
            reasons.append(f"test-pair {record.get('test_id')}: failed_at {rev!r} is not a commit in this history")
        if (not test_file or not (prototype_journey(test_file) or match_any(test_file, classes.get("tests", [])))
                or view.read_new(test_file) is None):
            reasons.append(f"test-pair {record.get('test_id')}: test_file {test_file!r} must be an existing file in the tests path class")
        if not isinstance(command, list) or not command:
            reasons.append("no project test_command in project.json; set one (with your approval) so failing tests can be proven")
        elif record.get("command") != [test_file if part == "{test_file}" else part for part in command]:
            reasons.append(f"test-pair {record.get('test_id')}: command must be the project test_command run on its test_file")
    covered = {p for r in records for p in r.get("covers", [])}
    reasons += [f"{p} changed without a failing-test record for {tier.get('slice')} in 06-evidence/tests (spec 7)"
                for p in code if p not in covered]
    return reasons


def _document_dates(view: View, changes) -> list[str]:
    """Spec 2: visible Created / Last edited dates, checked against the checker's own clock."""
    from datetime import datetime, timezone
    from .document_dates import created_of, rename_key
    now = datetime.now(timezone.utc)
    floor = trust.load(view.read_new(trust.ENGINE + "owned-files.json")).get("installed_at")
    install = trust.is_install_commit(view)
    text = lambda raw: raw.decode("utf-8", "replace") if raw is not None else None
    deleted = {}
    for change in changes:
        if change.status == "D" and managed_doc(change.path):
            old = text(view.read_old(change.path))
            if rename_key(change.path, old):
                deleted[rename_key(change.path, old)] = created_of(old)
    reasons = []
    for change in changes:
        if change.status == "D" or not managed_doc(change.path):
            continue
        new, old = text(view.read_new(change.path)), text(view.read_old(change.old_path or change.path))
        if new is None:
            continue
        renamed = deleted.get(rename_key(change.path, new)) if old is None else None
        reasons += [f"{change.path}: {issue}" for issue in validate_change(
            old, new, now=now, floor=floor, allow_unknown=install, renamed_from_created=renamed)]
    return reasons


def evaluate(root: Path, view: View, release_dir: Path | None = None, strict: bool = False) -> list[str]:
    changes = view.changes()
    project = trust.load(view.read_new(PROJECT_FILE.as_posix()))
    classes = project.get("path_classes", {}) if isinstance(project.get("path_classes"), dict) else {}
    tier = trust.load(view.read_new((STATE_DIR / "tier.json").as_posix())).get("active")
    ctx = Context(root, project)
    exempt = trust.install_exempt(view)
    reasons = trust.append_only(view) + trust.frozen_touched(view, changes)
    reasons += trust.engine_changes(view, changes, release_dir, strict)
    reasons += trust.approvals_have_inbox_lines(view) + trust.check_approvals(view)
    reasons += trust.slice_approvals(view, changes) + trust.ledger_approvals(view)
    reasons += trust.test_command_change(view) + trust.approver_key_change(view) + trust.single_use(view)
    reasons += [f"{c.path}: cache files may not be committed (__pycache__/.pyc)" for c in changes
                if c.status != "D" and ("__pycache__/" in c.path or c.path.endswith(".pyc"))]
    code_changes = [c for c in changes if (needs_tier(c.path) or (c.old_path and needs_tier(c.old_path)))
                    and c.path not in exempt
                    and not trust.engine_file(c.path) and not c.path.startswith(trust.ENGINE)]
    reasons += _tier_rules(view, code_changes, tier)
    reasons += _test_pairs(view, code_changes, tier, classes, project)
    reasons += _document_dates(view, changes)
    for change in changes:
        if change.path.startswith(trust.ENGINE) or change.path in exempt:
            continue  # engine files are checked above; install-owned files (e.g. copied skills) come from the plugin
        if change.status in "AC" and _is_script_name(change.path, None):
            content = (view.read_new(change.path) or b"").decode("utf-8", "replace")
            if not _script_allowed(ctx, change.path, content):
                reasons.append(f"new script {change.path} is not allowed here (spec 8)")
    for path, lines in view.added_lines().items():
        if not path.startswith(trust.ENGINE) and any(EMOJI.search(line) for line in lines):
            reasons.append(f"decorative emoji added in {path} (spec 1)")
    return list(dict.fromkeys(reasons))
