"""Approved, immutable mappings between old and replacement run lifecycles."""

from __future__ import annotations

import json
from pathlib import Path

from .common import CgspecError, RUNS_DIR, utc_now, write_json


def _refs(data: dict, kind: str) -> list[str] | None:
    if kind == "outcomes":
        values = data.get(kind)
        return list(values) if isinstance(values, list) and all(isinstance(v, str) for v in values) else None
    values = data.get(kind)
    return ([item.get("path") for item in values]
            if isinstance(values, list) and all(isinstance(item, dict) and isinstance(item.get("path"), str)
                                                for item in values) else None)


def errors(old: dict, new: dict) -> list[str]:
    """Validate a complete old/new replacement map without reading mutable working state."""
    metadata = new.get("supersession")
    if not isinstance(metadata, dict):
        return ["replacement run has no frozen supersession links"]
    reasons = []
    if old.get("run_id") == new.get("run_id") or not old.get("frozen_at") or not new.get("frozen_at"):
        reasons.append("supersession needs distinct frozen old and replacement runs")
    if metadata.get("replaces") != old.get("run_id"):
        reasons.append("replacement run does not point back to the old run")
    if not isinstance(metadata.get("reason"), str) or len(metadata["reason"].strip()) < 3:
        reasons.append("replacement reason is missing")
    if not isinstance(metadata.get("approval"), dict):
        reasons.append("replacement links have no explicit approval")
    links = metadata.get("links")
    if not isinstance(links, dict):
        return reasons + ["replacement links are missing"]
    for label, field in (("agreements", "criteria"), ("outcomes", "outcomes"),
                         ("tests", "tests"), ("proofs", "proofs")):
        old_refs, new_refs = _refs(old, field), _refs(new, field)
        if old_refs is None or new_refs is None:
            reasons.append(f"{field} inventory is unknown; supersession fails closed")
            continue
        mappings = links.get(label)
        if not isinstance(mappings, list) or any(not isinstance(link, dict) for link in mappings):
            reasons.append(f"{label} links must be an array")
            continue
        if any(not isinstance(link.get("old"), str) or not isinstance(link.get("new"), str) for link in mappings):
            reasons.append(f"{label} links need string old and new references")
            continue
        linked_old = [link["old"] for link in mappings]
        if len(linked_old) != len(set(linked_old)):
            reasons.append(f"{label} links contain duplicate old references")
        missing, extra = sorted(set(old_refs) - set(linked_old)), sorted(set(linked_old) - set(old_refs))
        if missing:
            reasons.append(f"{label} links retire still-required references: {', '.join(missing)}")
        if extra:
            reasons.append(f"{label} links name unknown old references: {', '.join(extra)}")
        unknown_new = sorted(set(link["new"] for link in mappings) - set(new_refs))
        if unknown_new:
            reasons.append(f"{label} links name unknown replacement references: {', '.join(unknown_new)}")
    return reasons


def _data(view, path: str) -> dict | None:
    raw = view.read_new(path)
    if raw is None:
        return None
    try:
        data = json.loads(raw.decode("utf-8", "replace"))
    except (ValueError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def immutable_proof_errors(view) -> list[str]:
    old_proofs = view.files_old("docs/_cgspec/06-evidence/tests")
    return [f"{rel} is immutable historical failing-test proof; add a replacement record and supersession link"
            for rel in old_proofs if rel.endswith(".json") and view.read_new(rel) != view.read_old(rel)]


def approval_refs(view) -> list[str]:
    refs = []
    for rel in view.files_new("docs/_cgspec/05-runs"):
        data = _data(view, rel) if rel.endswith("/run.json") else None
        supersession = data.get("supersession") if isinstance(data, dict) else None
        approval = supersession.get("approval") if isinstance(supersession, dict) else None
        if isinstance(approval, dict) and approval.get("ref"):
            refs.append(str(approval["ref"]))
    return refs


def commit_errors(view, old_runs: set[str], new_runs: set[str]) -> list[str]:
    """Validate every active-to-superseded transition in the candidate Git view."""
    reasons = []
    by_id = {data.get("run_id"): data for path in new_runs if (data := _data(view, path))}
    for path in sorted(old_runs):
        old_raw, new_data = view.read_old(path), _data(view, path)
        try:
            old_data = json.loads(old_raw.decode("utf-8", "replace")) if old_raw else {}
        except (ValueError, TypeError):
            old_data = {}
        if not (isinstance(old_data, dict) and isinstance(new_data, dict) and
                old_data.get("status", "completed") == "active" and new_data.get("status") == "superseded"):
            continue
        replacement = by_id.get(new_data.get("superseded_by"))
        if not replacement:
            reasons.append(f"{path}: superseded_by does not identify a preserved replacement run")
            continue
        validation = errors(old_data, replacement)
        validation += proof_link_errors(old_data, replacement, view.read_new)
        validation += outcome_errors(old_data, view.read_old, view.files_old("docs/slices"))
        validation += outcome_errors(replacement, view.read_new, view.files_new("docs/slices"))
        reasons += [f"{path}: {problem}" for problem in validation]
        metadata = replacement.get("supersession") if isinstance(replacement.get("supersession"), dict) else {}
        approval = metadata.get("approval")
        from .commit_trust import approval_ok
        target = f"supersession:{old_data.get('run_id')}:{replacement.get('run_id')}"
        problem = approval_ok(view, str(approval.get("ref", "")) if isinstance(approval, dict) else "", target)
        if problem:
            reasons.append(f"{path}: supersession approval {problem}")
    return reasons


def prepare(root: Path, data: dict, specification: object, resolve_approval, load_run_file) -> None:
    """Freeze validated replacement metadata into a not-yet-written new run."""
    if not isinstance(specification, dict):
        raise CgspecError("supersession must be an object")
    old_id, approval = specification.get("replaces"), resolve_approval(root, specification.get("approval_ref"))
    if not approval:
        raise CgspecError("supersession needs explicit approval")
    if approval.get("source") == "message-hook":
        from .inbox import approval_target
        approvals_path = root / "docs/_cgspec/07-state/approvals.json"
        try:
            approvals = json.loads(approvals_path.read_text(encoding="utf-8")).get("approvals", [])
        except (OSError, ValueError, AttributeError) as exc:
            raise CgspecError(f"cannot validate supersession approval: {exc}") from exc
        entry = next((item for item in approvals if isinstance(item, dict) and
                      item.get("id") == approval.get("ref")), {})
        expected = f"supersession:{old_id}:{data.get('run_id')}"
        if approval_target(str(entry.get("excerpt", ""))) != expected:
            raise CgspecError(f"supersession approval must explicitly name {expected}")
    old_path = root / RUNS_DIR / str(old_id) / "run.json"
    old, problems = load_run_file(old_path, root) if old_path.is_file() else (None, ["old run not found"])
    if problems or not old:
        raise CgspecError(f"cannot replace {old_id}: {'; '.join(problems)}")
    data["supersession"] = {"replaces": old_id, "reason": specification.get("reason"),
                            "approval": approval, "links": specification.get("links"), "frozen_at": utc_now()}
    problems = errors(old, data) + proof_link_errors(old, data, lambda p: (root / p).read_bytes() if (root / p).is_file() else None)
    paths = [p.relative_to(root).as_posix() for p in (root / "docs/slices").glob("*.start.json")]
    problems += outcome_errors(old, lambda p: (root / p).read_bytes(), paths)
    problems += outcome_errors(data, lambda p: (root / p).read_bytes(), paths)
    if problems:
        raise CgspecError("invalid supersession: " + "; ".join(problems))


def transition(root: Path, run_id: str, replacement_id: str, load_run_file) -> dict:
    """Move an active old run to its terminal superseded state."""
    target = root / RUNS_DIR / run_id / "run.json"
    if not target.is_file():
        raise CgspecError(f"run {run_id} not found")
    data, problems = load_run_file(target, root)
    if problems or not data:
        raise CgspecError(f"cannot supersede malformed run {run_id}: {'; '.join(problems)}")
    if data.get("status") != "active":
        raise CgspecError(f"cannot supersede {data.get('status')} run {run_id}")
    replacement_path = root / RUNS_DIR / replacement_id / "run.json"
    replacement, replacement_problems = (load_run_file(replacement_path, root)
                                         if replacement_path.is_file() else (None, ["replacement run not found"]))
    if replacement_problems or not replacement:
        raise CgspecError(f"cannot supersede with {replacement_id}: {'; '.join(replacement_problems)}")
    if replacement.get("status") == "superseded":
        raise CgspecError(f"replacement run {replacement_id} is already superseded")
    reader = lambda path: (root / path).read_bytes() if (root / path).is_file() else None
    start_paths = [path.relative_to(root).as_posix()
                   for path in (root / "docs/slices").glob("*.start.json")]
    problems = errors(data, replacement)
    problems += proof_link_errors(data, replacement, reader)
    problems += outcome_errors(data, reader, start_paths)
    problems += outcome_errors(replacement, reader, start_paths)
    if problems:
        raise CgspecError("invalid supersession: " + "; ".join(problems))
    data.update(status="superseded", superseded_by=replacement_id, superseded_at=utc_now())
    write_json(target, data)
    print(f"superseded run {run_id} by {replacement_id}")
    return data


def outcome_errors(data: dict, reader, paths) -> list[str]:
    """Bind explicit outcome inventories to the slice's versioned start agreement."""
    if not data.get("slice"):
        return []
    prefix = data["slice"].split(":")[-1] + "-"
    matches = [p for p in paths if Path(p).name.startswith(prefix) and p.endswith(".start.json")]
    if len(matches) != 1:
        return ["slice outcome inventory needs exactly one start record"]
    try:
        start = json.loads(reader(matches[0]))
        required = {item["id"] for item in start["outcomes"]}
    except (TypeError, ValueError, KeyError):
        return ["slice start outcome inventory is malformed"]
    inventory = _refs(data, "outcomes")
    if inventory is None or len(inventory) != len(set(inventory)) or set(inventory) != required:
        return ["run outcomes must explicitly inventory every required slice start outcome"]
    return []


def proof_link_errors(old: dict, new: dict, reader) -> list[str]:
    """Proof replacements are distinct, schema-valid pairs bound to the replacement run."""
    from .schema import validate_named
    problems = []
    metadata = new.get("supersession")
    links = metadata.get("links") if isinstance(metadata, dict) else None
    links = links.get("proofs") if isinstance(links, dict) else None
    if not isinstance(links, list) or any(not isinstance(link, dict) for link in links):
        return ["proofs links must be an array of objects"]
    tests = set(_refs(new, "tests") or [])
    old_proofs = set(_refs(old, "proofs") or [])
    old_tests = set(_refs(old, "tests") or [])
    test_links = metadata.get("links", {}).get("tests", [])
    test_links = test_links if isinstance(test_links, list) else []
    for link in links:
        target = link.get("new")
        if isinstance(target, str) and target in old_proofs:
            problems.append("replacement proof must be distinct from every retired proof")
        if not isinstance(target, str) or not target.startswith("docs/_cgspec/06-evidence/tests/") or not target.endswith(".json"):
            problems.append("replacement proof must name a test-pair record")
            continue
        try:
            pair = json.loads(reader(target))
        except (TypeError, ValueError):
            pair = None
        if not isinstance(pair, dict) or validate_named(pair, "test-pair"):
            problems.append(f"{target}: replacement proof is not a valid test-pair")
        elif not pair.get("runner_id") or not pair.get("test_semantics"):
            problems.append(f"{target}: replacement requires fresh semantic proof with a complete dependency closure")
        elif pair.get("test_file") not in tests or pair.get("slice") != new.get("slice"):
            problems.append(f"{target}: replacement test-pair must match the replacement run tests and slice")
        else:
            source = link.get("old")
            try:
                original = json.loads(reader(source)) if isinstance(source, str) else None
            except (TypeError, ValueError):
                original = None
            if (not isinstance(original, dict) or validate_named(original, "test-pair") or
                    original.get("test_file") not in old_tests or original.get("slice") != old.get("slice")):
                problems.append(f"{source}: retired test-pair must match the old run tests and slice")
            elif not any(isinstance(mapping, dict) and mapping.get("old") == original["test_file"] and
                         mapping.get("new") == pair["test_file"] for mapping in test_links):
                problems.append(f"{target}: proof replacement must follow the frozen old/new test mapping")
    return problems


def retired_proofs(view) -> set[str]:
    """Structurally approved retirements; CI still independently replays replacement proof."""
    from .runs import check_run_commit, FROZEN_FIELDS
    result = set()
    for path in view.files_new("docs/_cgspec/05-runs"):
        if not path.endswith("/run.json"):
            continue
        old = _data(view, path)
        if not old or old.get("status") != "superseded":
            continue
        history = [view]
        if view.old:
            from .gitview import View, git
            history += [View.commit(view.root, rev) for rev in git(
                view.root, "log", "--format=%H", view.old, "--", path).stdout.splitlines()]
        for transition in history:
            try:
                before = json.loads(transition.read_old(path) or b"{}")
                after = json.loads(transition.read_new(path) or b"{}")
            except (ValueError, TypeError):
                continue
            if (isinstance(before, dict) and before.get("status") == "active" and after == old
                    and not check_run_commit(transition)):
                replacement_path = f"docs/_cgspec/05-runs/{old.get('superseded_by')}/run.json"
                replacement = _data(view, replacement_path)
                frozen_replacement = _data(transition, replacement_path)
                preserved = (replacement and frozen_replacement and all(
                    replacement.get(field) == frozen_replacement.get(field) for field in FROZEN_FIELDS))
                import hashlib
                proofs = (old.get("proofs", []) + replacement.get("proofs", [])) if preserved else []
                intact = preserved and all(view.read_new(item["path"]) is not None and
                    hashlib.sha256(view.read_new(item["path"])).hexdigest() == item["sha256"] for item in proofs)
                if intact and not errors(old, replacement) and not proof_link_errors(old, replacement, view.read_new):
                    result.update(_refs(old, "proofs") or [])
                break
    return result
