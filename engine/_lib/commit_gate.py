"""Commit-level rules (spec 8, commit hook and CI columns), evaluated on a git View."""

from __future__ import annotations

import hashlib
from pathlib import Path

from . import git_protocol, proof_seals, tiers
from .common import ENGINE_DIR, PROJECT_FILE, STATE_DIR
from . import commit_trust as trust
from .gates import EMOJI, HOST_PATH, Context, _is_script_name, _script_allowed
from .gitview import View, git
from .document_dates import managed_doc, validate_change
from .inbox import contains_secret
from .path_policy import live_prototype_source, needs_tier, prototype_journey
from .globs import match_any
from . import runs
from .governance_paths import governance_path


def _preserved_prototype(view: View, change) -> bool:
    if not change.path.startswith(("docs/prototypes/_archive/", "docs/prototypes/_snapshots/")):
        return False
    content = view.read_new(change.path)
    if content is None:
        return False
    if (change.status == "R" and change.old_path
            and (live_prototype_source(change.old_path) or prototype_journey(change.old_path))
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
        if rel.endswith(".md") and Path(rel).name.startswith(bare + "-"):
            status, scope, approval = trust.slice_fields((view.read_new(rel) or b"").decode("utf-8", "replace"))
            return status, [g.strip().strip("`") for g in scope.split(",") if g.strip()], approval
    return None


def _tier_rules(view: View, code_changes, tier: dict | None, classes: dict) -> list[str]:
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
        from . import start_gate
        reasons += start_gate.commit_implementation(view, tier, set())
        return reasons
    found = _slice(view, tier.get("slice", ""))
    if not found or found[0] not in tiers.WORKING_SLICE:
        return [f"slice {tier.get('slice')} is missing or not Approved/In progress"]
    if found[2] != trust.TRAILER_REF and found[2] not in trust.approval_ids(view):
        return [f"slice {tier.get('slice')} cites no approval from your messages"]
    reasons = [f"{p} is outside the scope of {tier.get('slice')}" for p in sorted(paths) if not match_any(p, found[1])]
    if tier.get("tier") == "T1" and lines > tiers.T1_MAX_LINES:
        reasons.append(f"T1 allows {tiers.T1_MAX_LINES} changed lines, this commit changes {lines}")
    from . import start_gate
    implementation_paths = {p for p in paths if start_gate.is_implementation(p, classes)}
    reasons += start_gate.commit_implementation(view, tier, implementation_paths)
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
    records = [(p, trust.load(view.read_new(p))) for p in paths]
    from .run_supersession import retired_proofs
    retired = retired_proofs(view)
    records = [(p, r) for p, r in records if r.get("slice") == tier.get("slice") and p not in retired]
    head = "HEAD" if view.new == ":" else view.new
    reasons = []
    from . import runner_contracts
    for rel, record in records:
        rev, test_file = record.get("failed_at", ""), record.get("test_file", "")
        if not (view.commit_exists(rev) and view.is_ancestor(rev, head)):
            from .proof_seals import historical_pair_error
            if problem := historical_pair_error(view, rel, record):
                reasons.append(f"test-pair {record.get('test_id')}: {problem}")
        if (not test_file or not (prototype_journey(test_file) or match_any(test_file, classes.get("tests", [])))
                or view.read_new(test_file) is None):
            reasons.append(f"test-pair {record.get('test_id')}: test_file {test_file!r} must be an existing file in the tests path class")
        if any(field in record for field in ("runner_id", "runner_hash", "selector")):
            reasons += [f"{rel}: {reason}" for reason in runner_contracts.pair_errors(project, record, view.read_new)]
        elif project.get("test_runners") and (code or view.read_new(rel) != view.read_old(rel)):
            reasons.append(f"{rel}: proof after migration needs an approved named runner and configuration hash")
        elif not isinstance(command, list) or not command:
            reasons.append("no project test_command in project.json; set one (with your approval) so failing tests can be proven")
        elif record.get("command") != [test_file if part == "{test_file}" else part for part in command]:
            reasons.append(f"test-pair {record.get('test_id')}: command must be the project test_command run on its test_file")
    covered = {p for _, r in records for p in r.get("covers", [])}
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


def _evidence_rules(view: View, changes) -> list[str]:
    """New passing evidence names what it proves and which data it exercised.

    This is a claim-consistency check, not proof that an agent labelled its source
    honestly. Project checks and independently run integration tests supply that proof.
    """
    prefix = "docs/_cgspec/06-evidence/"
    project = trust.load(view.read_new(PROJECT_FILE.as_posix()))
    reasons = []
    for change in changes:
        if change.status == "D" or not change.path.startswith(prefix) or not change.path.endswith(".json"):
            continue
        if change.path.startswith(prefix + "tests/"):
            continue  # failing-test pairs use a different schema
        record = trust.load(view.read_new(change.path))
        if record.get("verdict") != "PASS":
            continue
        claim, source = record.get("claim"), record.get("data_source")
        if not claim or not source:
            reasons.append(f"{change.path}: passing evidence needs claim and data_source; "
                           "state whether it used fixtures, a real backend, static checks or an unknown source")
        elif claim == "integration" and source != "real_backend":
            reasons.append(f"{change.path}: {source} cannot prove integration with a real backend")
        fields = ("runner_id", "runner_hash", "selector", "test_id")
        test_backed = (any(field in record for field in fields) or
                       (project.get("test_runners") and claim in ("integration", "ui_behavior")))
        if test_backed:
            if not all(record.get(field) for field in fields):
                reasons.append(f"{change.path}: runner completion needs runner_id, runner_hash, selector and test_id")
                continue
            pairs = [trust.load(view.read_new(path)) for path in view.files_new(prefix + "tests")
                     if path.endswith(".json")]
            if not any(all(pair.get(field) == record[field] for field in fields) for pair in pairs):
                reasons.append(f"{change.path}: runner completion does not match a bound test-pair")
    return reasons


def _governance_reasons(root: Path, view: View, changes) -> list[str]:
    """A candidate project configuration cannot narrow the fixed governance floor. Initial
    installation is a bootstrap; later changes need the user's signed `Approved-by:` trailer,
    which ordinary inbox citations cannot provide."""
    reasons: list[str] = []
    project_path = PROJECT_FILE.as_posix()
    old_project = view.read_old(project_path)
    new_project = view.read_new(project_path)
    prior_project_history = bool(view.old and git(root, "log", "-1", "--format=%H", view.old,
                                                   "--", project_path).stdout.strip())
    bootstrap = old_project is None and new_project is not None and not prior_project_history
    if old_project is not None and new_project is None:
        reasons.append(f"{project_path}: established CGSpec project state cannot be deleted or renamed away")
    if old_project is None and new_project is not None and prior_project_history:
        reasons.append(f"{project_path}: restoring prior project state is not a new installation")
    authorized = trust.governance_authorized(view)
    if old_project is not None and new_project is not None and not authorized:
        if trust.load(old_project).get("plugin_source") != trust.load(new_project).get("plugin_source"):
            reasons.append(f"{project_path}: APPROVAL_REQUIRED for plugin_source change; "
                           "it selects the engine trusted by later CI runs")
    for change in changes:
        for rel in filter(None, (change.path, change.old_path)):
            if governance_path(rel) and not bootstrap and not authorized and not trust.canonical_adapter_refresh(view, rel):
                reasons.append(f"{rel}: APPROVAL_REQUIRED for governance change ({change.status}); "
                               "needs an 'Approved-by:' trailer on a commit signed by a trusted approver key; "
                               "ordinary project approvals do not authorize guard changes")
    return reasons


def evaluate(root: Path, view: View, release_dir: Path | None = None, strict: bool = False) -> list[str]:
    changes = view.changes()
    project = trust.load(view.read_new(PROJECT_FILE.as_posix()))
    classes = project.get("path_classes", {}) if isinstance(project.get("path_classes"), dict) else {}
    tier = trust.load(view.read_new((STATE_DIR / "tier.json").as_posix())).get("active")
    ctx = Context.load(root)
    ctx.project = project  # the view may see a staged project.json the disk copy doesn't have yet
    exempt = trust.install_exempt(view)
    reasons = trust.append_only(view) + trust.frozen_touched(view, changes) + proof_seals.record_errors(view, changes)
    reasons += runs.check_run_commit(view)
    from . import capabilities, start_gate
    reasons += start_gate.commit_records(view, changes) + capabilities.commit_records(view, changes)
    from . import parity_manifest
    reasons += parity_manifest.gate(view, [c for c in changes if c.path not in exempt
                               and not c.path.startswith(trust.ENGINE)], project)
    reasons += _governance_reasons(root, view, changes)
    reasons += trust.engine_changes(view, changes, release_dir, strict)
    reasons += trust.approvals_have_inbox_lines(view) + trust.check_approvals(view)
    reasons += trust.slice_approvals(view, changes) + trust.ledger_approvals(view)
    from . import runner_trust
    reasons += trust.test_command_change(view) + runner_trust.check(view)
    reasons += trust.approver_key_change(view) + proof_seals.signer_policy_errors(view) + trust.single_use(view)
    reasons += [f"{c.path}: cache files may not be committed (__pycache__/.pyc)" for c in changes
                if c.status != "D" and ("__pycache__/" in c.path or c.path.endswith(".pyc"))]
    code_changes = [c for c in changes if (needs_tier(c.path) or (c.old_path and needs_tier(c.old_path)))
                    and c.path not in exempt
                    and not trust.engine_file(c.path) and not c.path.startswith(trust.ENGINE)
                    and c.path != parity_manifest.MANIFEST]
    reasons += _tier_rules(view, code_changes, tier, classes)
    reasons += git_protocol.commit_plan_reasons(view, tier)
    reasons += _test_pairs(view, code_changes, tier, classes, project)
    reasons += _evidence_rules(view, changes)
    reasons += parity_manifest.gate(view, changes, project)
    reasons += _document_dates(view, changes)
    for change in changes:
        if change.path.startswith(trust.ENGINE) or change.path in exempt:
            continue  # engine files are checked above; install-owned files (e.g. copied skills) come from the plugin
        raw_bytes = view.read_new(change.path) if change.status != "D" else None
        if raw_bytes and b"\x00" not in raw_bytes:
            content = raw_bytes.decode("utf-8", "replace")
            if change.path not in ctx.legacy and match_any(change.path, classes.get("code", [])):
                lines_cnt = len(content.splitlines())
                if lines_cnt > 400:
                    reasons.append(f"{change.path}: {lines_cnt} lines exceeds the 400 lines per file limit (spec 7b)")
            if b"\r\n" in raw_bytes:
                reasons.append(f"{change.path}: contains CRLF line endings; convert to LF before committing")
            if change.status in "AC" and _is_script_name(change.path, None) and not _script_allowed(ctx, change.path, content):
                reasons.append(f"new script {change.path} is not allowed here (spec 8)")
    for path, lines in view.added_lines().items():
        if path.startswith(trust.ENGINE):
            continue
        if any(EMOJI.search(line) for line in lines):
            reasons.append(f"decorative emoji added in {path} (spec 1)")
        if match_any(path, classes.get("code", [])) and any(HOST_PATH.search(line) for line in lines):
            reasons.append(f"{path}: added content contains a hardcoded host path; use project-relative paths or environment variables")
        kind = next((k for line in lines if (k := contains_secret(line))), None)
        if kind:
            reasons.append(f"{path}: added content looks like a {kind} (spec 1: no secrets committed; "
                           "use environment variables, and reference them by name only)")
    return list(dict.fromkeys(reasons))
