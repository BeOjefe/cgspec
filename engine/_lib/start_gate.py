"""Editor and Git-candidate enforcement for success/readiness agreements."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import commit_trust as trust
from . import start
from .common import CgspecError
from .globs import match_any
from .path_policy import needs_tier, prototype_source

IMPLEMENTATION_CLASSES = ("schema", "api", "auth", "deps", "code")


def is_implementation(rel: str, classes: dict) -> bool:
    if match_any(rel, classes.get("tests", [])) or rel.startswith("tests/") or \
            Path(rel).name.startswith("test_") or Path(rel).stem.endswith((".test", ".spec")):
        return False
    if prototype_source(rel) or rel.startswith("docs/") or not needs_tier(rel):
        return False
    return any(match_any(rel, classes.get(name, [])) for name in IMPLEMENTATION_CLASSES) or \
        Path(rel).suffix in {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".rb", ".sh",
                             ".c", ".cc", ".cpp", ".h", ".hpp", ".kt", ".swift", ".cs"}


def _matching(data: dict, rel: str) -> list[dict]:
    return [item for item in data.get("outcomes", []) if match_any(rel, item.get("covers", []))]


def editor_reason(root: Path, tier: dict, rel: str, classes: dict) -> str | None:
    if not is_implementation(rel, classes):
        return None
    if tier.get("tier") == "T0":
        return None if tier.get("verification") else "T0 needs an explicit verification; redeclare it with --verify"
    slice_id = tier.get("slice", "")
    try:
        _, data = start.load(root, slice_id)
    except CgspecError as exc:
        return str(exc)
    if data["status"] != "In progress":
        return f"{slice_id} is {data['status']}; approve, run readiness, and begin its outcomes before implementation"
    from . import git_protocol
    plan_problem = git_protocol.check_plan_declared(root, slice_id)
    if plan_problem:
        return plan_problem
    loaded = git_protocol.load_if_exists(root, slice_id)
    worker_problem = git_protocol.check_worker_context(root, loaded[1], rel) if loaded else None
    if worker_problem:
        return worker_problem
    matched = _matching(data, rel)
    if not matched:
        return f"{rel} has no agreed outcome coverage in {slice_id}"
    planned = {oid for repo in loaded[1]["repositories"] for oid in repo["outcomes"]} if loaded else set()
    if missing := {item["id"] for item in matched} - planned:
        return f"{rel} covers outcomes absent from the git execution plan: {', '.join(sorted(missing))}"
    reasons = []
    from .project_policy import effective_requirements
    requirements = effective_requirements(root, data)
    for item in matched:
        oid = item["id"]
        if oid not in data["active_outcomes"]:
            reasons.append(f"{oid} is not active; run start begin --outcome {oid}")
        reasons += start.eligibility_errors(data, oid, start.mocks_enabled(), start.root_reader(root), requirements)
    return "; ".join(dict.fromkeys(reasons)) or None


def _candidate(view, slice_id: str) -> tuple[str, dict] | tuple[None, None]:
    bare = slice_id.split(":")[-1]
    for rel in view.files_new("docs/slices"):
        if rel.endswith(".start.json") and Path(rel).name.startswith(bare + "-"):
            raw = view.read_new(rel)
            try:
                data = json.loads(raw.decode("utf-8")) if raw else {}
            except (UnicodeDecodeError, ValueError):
                data = {}
            return rel, data if isinstance(data, dict) else {}
    return None, None


def staged_trailer_refs(view) -> bool:
    for change in view.changes():
        if change.status == "D" or not (change.path.startswith("docs/slices/") and change.path.endswith(".start.json")):
            continue
        new = trust.load(view.read_new(change.path)).get("approval")
        old = trust.load(view.read_old(change.path)).get("approval")
        if isinstance(new, dict) and new.get("ref") == trust.TRAILER_REF and not \
                (isinstance(old, dict) and old.get("ref") == trust.TRAILER_REF) and \
                _approval_reason(view, change.path, trust.load(view.read_new(change.path))):
            return True
    for path, lines in view.added_lines().items():
        if path.startswith("docs/slices/") or path == "docs/_memlog.md":
            if any((m := trust.APPROVAL_FIELD.match(line)) and m.group(1).strip().strip("`") == trust.TRAILER_REF
                   for line in lines):
                return True
    from .capabilities import staged_trailer_ref
    return staged_trailer_ref(view)


def _approval_reason(view, rel: str, data: dict) -> str | None:
    if data.get("status") == "Draft":
        return None
    approval = data.get("approval") or {}
    ref = str(approval.get("ref", ""))
    if not ref:
        return f"{rel}: approved readiness cites no approval"
    slice_id = data.get("slice", "").split(":")[-1]
    if data["approval"].get("definition_hash") != start.definition_hash(data):
        return f"{rel}: approval does not bind this definition"
    if ref == trust.TRAILER_REF:
        commit = data["approval"].get("commit")
        if not commit or not view.commit_exists(commit) or not view.is_ancestor(commit, view.old or "HEAD"):
            return f"{rel}: signed Draft is not an ancestor of the candidate"
        from .gitview import View
        signed = View.commit(view.root, commit)
        original = trust.load(signed.read_new(rel))
        if original.get("status") != "Draft" or start.definition_hash(original) != start.definition_hash(data) \
                or trust.approval_ok(signed, ref, slice_id):
            return f"{rel}: signed Draft does not approve this exact definition"
        return None
    from .inbox import approval_target
    approvals = trust.load(view.read_new("docs/_cgspec/07-state/approvals.json")).get("approvals", [])
    captured = next((a for a in approvals if isinstance(a, dict) and a.get("id") == ref
                     and approval_target(str(a.get("excerpt", ""))) == slice_id), None)
    if captured and not start.approval_is_fresh(captured, data):
        return f"{rel}: approval predates this Draft"
    old_raw = view.read_old(rel)
    old = trust.load(old_raw)
    changed_approval = not old_raw or old.get("status") == "Draft" or \
        start.definition_hash(old) != start.definition_hash(data) or \
        (old.get("approval") or {}).get("ref") != ref
    if changed_approval:
        problem = trust.approval_ok(view, ref, slice_id)
        return f"{rel}: success agreement {problem}" if problem else None
    if ref != trust.TRAILER_REF and ref not in trust.approval_ids(view):
        return f"{rel}: approval {ref} is not in the approval record"
    return None


def commit_records(view, changes) -> list[str]:
    reasons = []
    for change in changes:
        rel = change.path
        if not (rel.startswith("docs/slices/") and rel.endswith(".start.json")):
            continue
        if change.status == "D":
            reasons.append(f"{rel}: success agreements are versioned, not deleted")
            continue
        data = trust.load(view.read_new(rel))
        errors = start.validate_record(data)
        reasons += [f"{rel}: {error}" for error in errors]
        if not errors:
            problem = _approval_reason(view, rel, data)
            if problem:
                reasons.append(problem)
    return reasons


def _candidate_plan(view, slice_id: str) -> dict | None:
    bare = slice_id.split(":")[-1]
    for rel in view.files_new("docs/slices"):
        if rel.endswith(".git-plan.json") and Path(rel).name.startswith(bare + "-"):
            raw = view.read_new(rel)
            try:
                data = json.loads(raw.decode("utf-8")) if raw else {}
            except (UnicodeDecodeError, ValueError):
                data = {}
            from . import git_protocol
            if isinstance(data, dict) and not git_protocol.validate_plan(data):
                return data
    return None


def _probe_binding(view, req: dict, hashes: dict) -> list[str]:
    """Readiness must hash every probe input, and the candidate must hold the checked bytes."""
    reasons, check = [], req["check"]
    if req.get("capability"):
        from .capabilities import REGISTRY_REL, candidate_check
        check = candidate_check(view, req["capability"])
        if REGISTRY_REL not in hashes:
            reasons.append(f"{req['id']}: readiness did not bind the capability registry; rerun start ready")
    if check is None:
        return reasons
    if not set(check["inputs"]).issubset(hashes):
        reasons.append(f"{req['id']}: readiness missing declared probe input hashes")
    for arg in check["argv"]:
        if view.read_new(arg) is not None and arg not in hashes:
            reasons.append(f"{req['id']}: executable probe input {arg} was not bound to readiness")
    for input_path, digest in hashes.items():
        raw = view.read_new(input_path)
        if raw is None or hashlib.sha256(raw).hexdigest() != digest:
            reasons.append(f"{req['id']}: staged readiness input {input_path} differs from checked version")
    return reasons


def commit_implementation(view, tier: dict, paths: set[str]) -> list[str]:
    if tier.get("tier") == "T0":
        return [] if tier.get("verification") else ["T0 needs explicit verification in 07-state/tier.json"]
    if not paths:
        return []  # Design and test definition may be committed before readiness.
    slice_id = tier.get("slice", "")
    plan = _candidate_plan(view, slice_id)
    if not plan:
        return [f"{slice_id} has no git execution plan in the candidate; declare repository, base, branch and outcomes before implementation"]
    rel, data = _candidate(view, slice_id)
    if not rel:
        return [f"{slice_id} has no success agreement in the candidate"]
    errors = start.validate_record(data)
    from .project_policy import effective_from_reader, plan_errors, project_from_reader, record_errors
    project, _ = project_from_reader(view.read_new)
    errors += record_errors(project, data)
    if errors:
        return [f"{rel}: {error}" for error in errors]
    if data.get("slice") != slice_id:
        return [f"{rel}: agreement belongs to {data.get('slice')}, not {slice_id}"]
    if data["status"] != "In progress":
        return [f"{slice_id} is {data['status']}; implementation requires active, ready outcomes"]
    reasons = []
    reasons += plan_errors(project, plan)
    touched_outcomes = {item["id"] for path in paths for item in _matching(data, path)}
    planned_outcomes = {oid for repo in plan["repositories"] for oid in repo["outcomes"]}
    if missing := touched_outcomes - planned_outcomes:
        reasons.append(f"implementation covers outcomes absent from the git execution plan: {', '.join(sorted(missing))}")
    if len(touched_outcomes) > 1:
        reasons.append("commit combines implementation for unrelated outcomes; split it into logical behavior commits")
    results = {result["id"]: result for result in data["readiness"]["checks"]}
    requirements, _ = effective_from_reader(view.read_new, data)
    for req in requirements:
        if req["when"] == "before_start" and touched_outcomes.intersection(req["outcomes"]):
            result = results.get(req["id"])
            if result:
                reasons += _probe_binding(view, req, result["input_hashes"])
    for path in sorted(paths):
        matched = _matching(data, path)
        if not matched:
            reasons.append(f"{path} has no agreed outcome coverage in {slice_id}")
            continue
        for item in matched:
            oid = item["id"]
            if oid not in data["active_outcomes"]:
                reasons.append(f"{path}: {oid} is not active")
            reasons += [f"{path}: {reason}" for reason in
                        start.eligibility_errors(data, oid, start.mocks_enabled(), view.read_new, requirements)]
    problem = _approval_reason(view, rel, data)
    return reasons + ([problem] if problem else [])
