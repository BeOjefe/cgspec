"""Subagent run enforcement, test/criteria immutability management, and run lifecycle."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

from .common import CgspecError, RUNS_DIR, new_id, sha256_file, utc_now, write_json
from .globs import match_any
from .schema import validate_named

RUN_ID_PATTERN = re.compile(r"^R-\d{8}-[0-9a-f]{4}$")
UNIT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
ALLOWED_RUN_STATUSES = {"active", "completed", "superseded"}
ALLOWED_UNIT_STATUSES = {"todo", "in-progress", "PASS", "FAIL", "PARTIAL", "BLOCKED", "NOT_APPLICABLE"}
FROZEN_FIELDS = ("run_id", "tier", "goal", "slice", "criteria", "tests", "proofs", "outcomes", "supersession", "frozen_at", "approval")

def validate_contained_path(root: Path, rel_path: str) -> str:
    """Validate that rel_path is contained within root without symlink escape."""
    if not isinstance(rel_path, str) or not rel_path.strip():
        raise ValueError("path must be a non-empty string")
    p = rel_path.strip().replace("\\", "/")
    if p.startswith("/") or re.match(r"^[A-Za-z]:", p):
        raise ValueError(f"absolute path rejected: {rel_path}")
    parts = Path(p).parts
    if any(part == ".." for part in parts):
        raise ValueError(f"directory traversal ('..') rejected: {rel_path}")
    norm = Path(p).as_posix().lstrip("./") or "."
    root_real = os.path.realpath(root)
    curr = root
    for part in parts:
        curr = curr / part
        if curr.is_symlink() or curr.exists():
            curr_real = os.path.realpath(curr)
            try:
                Path(curr_real).relative_to(root_real)
            except ValueError:
                raise ValueError(f"symlink escape rejected: {rel_path} resolves outside project root ({curr_real})")
    return norm

def load_run_file(path: Path, root: Path | None = None) -> tuple[dict | None, list[str]]:
    """Load and validate a single run.json file against schema and path constraints."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, [f"{path}: malformed run record ({exc})"]
    if not isinstance(data, dict):
        return None, [f"{path}: run record must be a JSON object"]
    schema_errs = validate_named(data, "run")
    if schema_errs:
        return None, [f"{path}: schema error: {', '.join(schema_errs)}"]
    if data.get("run_id") != path.parent.name:
        return None, [f"{path}: run_id '{data.get('run_id')}' does not match folder '{path.parent.name}'"]
    unit_ids, errors = set(), []
    for u in data.get("units", []):
        uid = u.get("id")
        if not uid or not UNIT_ID_PATTERN.match(uid) or uid in unit_ids:
            errors.append(f"{path}: invalid or duplicate unit id '{uid}'")
        unit_ids.add(uid)
    if root:
        for k in ("criteria", "tests"):
            for item in data.get(k, []):
                try: validate_contained_path(root, item.get("path", ""))
                except ValueError as exc: errors.append(f"{path}: {exc}")
        for u in data.get("units", []):
            for ap in u.get("allowed_paths", []):
                try: validate_contained_path(root, ap)
                except ValueError as exc: errors.append(f"{path}: {exc}")
    if "status" not in data:
        data["status"] = "completed"
    return (None, errors) if errors else (data, [])

def load_runs_with_errors(root: Path) -> tuple[list[tuple[str, dict]], list[str]]:
    """Return ([(rel_run_json_path, data)], errors) for all run.json files."""
    runs_dir = root / RUNS_DIR
    if not runs_dir.is_dir():
        return [], []
    runs, errors = [], []
    for path in sorted(runs_dir.glob("*/run.json")):
        data, errs = load_run_file(path, root)
        if errs: errors.extend(errs)
        elif data: runs.append((path.relative_to(root).as_posix(), data))
    return runs, errors

def load_runs(root: Path) -> list[tuple[str, dict]]:
    """Return [(rel_run_json_path, data)] for all valid run.json files."""
    return load_runs_with_errors(root)[0]

def frozen_run_files(root: Path) -> dict[str, str]:
    """Map active frozen run.json, criteria and test paths to their run_id."""
    mapping: dict[str, str] = {}
    for rel_path, data in load_runs_with_errors(root)[0]:
        if not (isinstance(data.get("frozen_at"), str) and data["frozen_at"]):
            continue
        mapping[rel_path] = str(data.get("run_id", ""))
        if data.get("status", "active") == "active":
            for kind in ("criteria", "tests"):
                for item in data.get(kind, []):
                    if isinstance(item, dict) and "path" in item:
                        mapping[str(item["path"])] = str(data.get("run_id", ""))
    return mapping

def _resolve_by_run_id(all_runs: list[tuple[str, dict]], errors: list[str],
                       run_id: str, unit_id: str) -> tuple[dict, dict] | str:
    """Resolve active target run and unit when CGSPEC_RUN is explicitly set."""
    if not RUN_ID_PATTERN.match(run_id):
        return f"invalid CGSPEC_RUN format '{run_id}'; must match R-YYYYMMDD-xxxx"
    if matching_err := [e for e in errors if run_id in e]:
        return f"requested run {run_id} is malformed: {'; '.join(matching_err)}"
    matched = next((d for _, d in all_runs if d.get("run_id") == run_id), None)
    if not matched:
        return f"requested run {run_id} does not exist"
    if matched.get("status") in ("completed", "superseded"):
        return f"requested run {run_id} is {matched.get('status')}; no builder writes permitted"
    if unit_id:
        matched_unit = next((u for u in matched.get("units", []) if u.get("id") == unit_id), None)
        return (matched, matched_unit) if matched_unit else f"unknown CGSPEC_UNIT '{unit_id}' in run {run_id}"
    in_prog = [u for u in matched.get("units", []) if u.get("status") == "in-progress"]
    if len(in_prog) == 0:
        return f"no unit in-progress in run {run_id}; specify CGSPEC_UNIT explicitly"
    if len(in_prog) > 1:
        uids = [u.get("id") for u in in_prog]
        return f"ambiguous active unit in run {run_id}: multiple units are in-progress ({', '.join(uids)}); specify CGSPEC_UNIT explicitly"
    return matched, in_prog[0]

def _resolve_by_unit_id(all_runs: list[tuple[str, dict]], errors: list[str],
                        unit_id: str) -> tuple[dict, dict] | str:
    """Resolve active run and unit across active runs when only CGSPEC_UNIT is set."""
    if errors:
        return f"cannot resolve CGSPEC_UNIT '{unit_id}'; malformed run records exist: {errors[0]}"
    matching = [(d, u) for _, d in all_runs if d.get("status") == "active"
                for u in d.get("units", []) if u.get("id") == unit_id]
    if len(matching) == 0:
        return f"unknown CGSPEC_UNIT '{unit_id}'; no active run contains this unit"
    if len(matching) > 1:
        rids = [r.get("run_id") for r, _ in matching]
        return f"ambiguous CGSPEC_UNIT '{unit_id}'; present in multiple active runs ({', '.join(rids)}); specify CGSPEC_RUN explicitly"
    return matching[0]

def check_unit_scope(root: Path, rel: str) -> str | None:
    """Enforce unit allowed_paths and test/criteria immutability for subagent builders."""
    try: rel = validate_contained_path(root, rel)
    except ValueError as exc: return str(exc)
    frozen = frozen_run_files(root)
    if rel in frozen:
        return f"{rel} is frozen in active run {frozen[rel]}; builders may not edit frozen criteria, tests, or run.json"
    unit_id = os.environ.get("CGSPEC_UNIT", "").strip()
    run_id = os.environ.get("CGSPEC_RUN", "").strip()
    all_runs, errors = load_runs_with_errors(root)
    if run_id:
        res = _resolve_by_run_id(all_runs, errors, run_id, unit_id)
        if isinstance(res, str): return res
        run_data, unit_data = res
    elif unit_id:
        res = _resolve_by_unit_id(all_runs, errors, unit_id)
        if isinstance(res, str): return res
        run_data, unit_data = res
    else:
        if not all_runs and not (root / RUNS_DIR).exists() or rel.startswith("docs/_cgspec/07-state/"):
            return None
        in_prog = [(d, u) for _, d in all_runs if d.get("status") == "active"
                   for u in d.get("units", []) if u.get("status") == "in-progress"]
        if not in_prog: return None
        if len(in_prog) > 1:
            uids = [f"{r.get('run_id')}:{u.get('id')}" for r, u in in_prog]
            return f"ambiguous active unit: multiple units in active runs are in-progress ({', '.join(uids)}); specify CGSPEC_RUN or CGSPEC_UNIT explicitly"
        run_data, unit_data = in_prog[0]
    allowed = unit_data.get("allowed_paths", [])
    if not match_any(rel, allowed):
        return f"{rel} is outside unit {unit_data.get('id')} allowed_paths ({', '.join(allowed)}) in {run_data.get('run_id')}"
    return None

def _files_old(view, prefix: str) -> list[str]:
    """List paths matching prefix in old view."""
    if hasattr(view, "files_old"): return view.files_old(prefix)
    if not getattr(view, "old", None): return []
    from .gitview import git
    out = git(view.root, "ls-tree", "-r", "-z", "--name-only", view.old, "--", prefix).stdout
    return [p for p in out.split("\0") if p]

def _check_old_units(path: str, old_units: list, new_units: list) -> list[str]:
    """Verify that unit definitions (id, owner, allowed_paths) are intact in modified run record."""
    reasons = []
    if len(old_units) != len(new_units) or [u.get("id") for u in old_units] != [u.get("id") for u in new_units]:
        return [f"{path}: frozen unit definitions cannot be added or removed after frozen_at"]
    for old_u, new_u in zip(old_units, new_units):
        uid = old_u.get("id")
        if old_u.get("owner") != new_u.get("owner"):
            reasons.append(f"{path}: unit {uid} owner cannot change after frozen_at")
        if old_u.get("allowed_paths") != new_u.get("allowed_paths"):
            reasons.append(f"{path}: unit {uid} allowed_paths cannot change after frozen_at")
        if new_u.get("status") not in ALLOWED_UNIT_STATUSES:
            reasons.append(f"{path}: unit {uid} has invalid status '{new_u.get('status')}'")
        if new_u.get("review_rounds", 0) < old_u.get("review_rounds", 0):
            reasons.append(f"{path}: unit {uid} review_rounds cannot decrease")
    return reasons

def _check_old_run(view, path: str) -> list[str]:
    """Check if a previously frozen run.json was deleted, tampered, or invalidly transitioned."""
    raw_old = view.read_old(path)
    if not raw_old: return []
    try: old_data = json.loads(raw_old.decode("utf-8", "replace"))
    except (ValueError, TypeError): return []
    if not (isinstance(old_data, dict) and old_data.get("frozen_at")): return []
    raw_new = view.read_new(path)
    if raw_new is None: return [f"{path}: frozen run record may not be deleted"]
    try: new_data = json.loads(raw_new.decode("utf-8", "replace"))
    except (ValueError, TypeError): return [f"{path}: modified run record is not valid JSON"]
    reasons = []
    if any(old_data.get(f) != new_data.get(f) for f in FROZEN_FIELDS):
        reasons.append(f"{path}: frozen run criteria, tests, and metadata cannot change after frozen_at")
    reasons.extend(_check_old_units(path, old_data.get("units", []), new_data.get("units", [])))
    old_status, new_status = old_data.get("status", "completed"), new_data.get("status", "completed")
    if new_status not in ALLOWED_RUN_STATUSES:
        reasons.append(f"{path}: invalid run status '{new_status}'")
    if old_status in ("completed", "superseded") and new_status != old_status:
        reasons.append(f"{path}: run status '{old_status}' is terminal and cannot transition to '{new_status}'")
    if old_status == "superseded" and any(old_data.get(k) != new_data.get(k) for k in ("superseded_by", "superseded_at")):
        reasons.append(f"{path}: terminal supersession links are immutable")
    if new_status == "superseded" and (not new_data.get("superseded_by") or not new_data.get("superseded_at")):
        reasons.append(f"{path}: superseded run must specify superseded_by and superseded_at")
    return reasons

def check_run_commit(view) -> list[str]:
    """Verify that frozen run records, unit definitions, and active hashed files are intact."""
    reasons: list[str] = []
    prefix = RUNS_DIR.as_posix()
    old_files = _files_old(view, prefix)
    old_runs = {p for p in old_files if p.endswith("/run.json") or p == "run.json"}
    for path in sorted(old_runs):
        reasons.extend(_check_old_run(view, path))
    new_files = view.files_new(prefix) if hasattr(view, "files_new") else []
    new_runs = {p for p in new_files if p.endswith("/run.json") or p == "run.json"}
    for path in sorted(new_runs):
        raw = view.read_new(path)
        if not raw: continue
        try: data = json.loads(raw.decode("utf-8", "replace"))
        except (ValueError, TypeError):
            reasons.append(f"{path}: run record is not valid JSON"); continue
        if not isinstance(data, dict):
            reasons.append(f"{path}: run record must be an object")
            continue
        if path not in old_runs and (schema_errs := validate_named(data, "run")):
            reasons.append(f"{path}: schema error: {', '.join(schema_errs)}")
        if path not in old_runs and data.get("status", "completed") != "active":
            reasons.append(f"{path}: newly added runs must start active; terminal state needs a validated transition")
        if data.get("frozen_at"):
            kinds = ("criteria", "tests", "proofs") if data.get("status", "completed") == "active" else ("proofs",)
            for kind in kinds:
                for entry in data.get(kind, []):
                    fpath = entry.get("path")
                    content = view.read_new(fpath)
                    if content is None or hashlib.sha256(content).hexdigest() != entry.get("sha256"):
                        reasons.append(f"run {data.get('run_id')}: frozen {kind} file {fpath} was modified or is missing")
    from .run_supersession import commit_errors
    reasons += commit_errors(view, old_runs, new_runs)
    return reasons

def _clean_units(root: Path, units: list[dict]) -> list[dict]:
    """Validate and normalize unit specifications for freeze_run."""
    clean, seen_uids = [], set()
    for u in units:
        cu = dict(u)
        uid = cu.get("id")
        if not uid or not UNIT_ID_PATTERN.match(uid) or uid in seen_uids:
            raise CgspecError(f"invalid or duplicate unit id '{uid}' in run")
        seen_uids.add(uid)
        cu.setdefault("owner", "builder")
        cu["allowed_paths"] = [validate_contained_path(root, p) for p in cu.get("allowed_paths", [])]
        cu.setdefault("status", "todo")
        clean.append(cu)
    return clean

def _resolve_approval(root: Path, ref: str | None) -> dict | None:
    """Validate and construct approval object for freeze_run."""
    if not ref: return None
    if ref in ("trailer", "commit-trailer"):
        return {"source": "commit-trailer", "ref": "trailer", "at": utc_now()}
    appr_file = root / "docs/_cgspec/07-state/approvals.json"
    if appr_file.is_file():
        try:
            data = json.loads(appr_file.read_text(encoding="utf-8"))
            if ref not in {a.get("id") for a in data.get("approvals", []) if isinstance(a, dict)}:
                raise CgspecError(f"approval ref '{ref}' is not registered in approvals.json")
        except (OSError, ValueError, AttributeError) as exc:
            raise CgspecError(f"cannot validate approval ref '{ref}': {exc}") from exc
    return {"source": "message-hook", "ref": ref, "at": utc_now()}

def freeze_run(root: Path, goal: str, tier: str, criteria_paths: list[str],
               test_paths: list[str], units: list[dict], run_id: str | None = None,
               slice_id: str | None = None, approval_ref: str | None = None,
               outcomes: list[str] | None = None, proof_paths: list[str] | None = None,
               supersession: dict | None = None) -> dict:
    """Freeze a run record with SHA-256 hashes of criteria and tests."""
    run_id = run_id or new_id("R")
    if not RUN_ID_PATTERN.match(run_id):
        raise CgspecError(f"invalid run_id format '{run_id}'; must match R-YYYYMMDD-xxxx")
    target = root / RUNS_DIR / run_id / "run.json"
    if target.exists():
        raise CgspecError(f"run {run_id} already exists; cannot overwrite existing run")
    crit = [{"path": validate_contained_path(root, p), "sha256": sha256_file(root / validate_contained_path(root, p))} for p in criteria_paths]
    tests = [{"path": validate_contained_path(root, p), "sha256": sha256_file(root / validate_contained_path(root, p))} for p in test_paths]
    proofs = [{"path": validate_contained_path(root, p), "sha256": sha256_file(root / validate_contained_path(root, p))} for p in (proof_paths or [])]
    data = {
        "schema": 1, "run_id": run_id, "status": "active", "tier": tier, "goal": goal,
        "criteria": crit, "tests": tests, "proofs": proofs,
        "units": _clean_units(root, units),
        "frozen_at": utc_now(), "approval": _resolve_approval(root, approval_ref),
    }
    if outcomes is not None: data["outcomes"] = list(outcomes)
    if slice_id and (root / "docs/slices").is_dir() and list((root / "docs/slices").glob(f"{slice_id}-*.start.json")): data["closure"] = "required"
    if slice_id: data["slice"] = slice_id
    if supersession is not None:
        from .run_supersession import prepare
        prepare(root, data, supersession, _resolve_approval, load_run_file)
    if errs := validate_named(data, "run"): raise CgspecError(f"invalid run.json: {', '.join(errs)}")
    write_json(target, data)
    print(f"frozen run {run_id} ({len(crit)} criteria, {len(tests)} tests, {len(data['units'])} units)")
    return data

def complete_run(root: Path, run_id: str) -> dict:
    """Transition an active run to completed status."""
    target = root / RUNS_DIR / run_id / "run.json"
    if not target.is_file(): raise CgspecError(f"run {run_id} not found")
    data, errs = load_run_file(target, root)
    if errs or not data: raise CgspecError(f"cannot complete malformed run {run_id}: {'; '.join(errs)}")
    if data.get("status") == "completed": return data
    if data.get("status") == "superseded": raise CgspecError(f"cannot complete superseded run {run_id}")
    if data.get("closure") == "required":
        from .closure import check
        _, blockers = check(root, data["slice"])
        if blockers: raise CgspecError(f"cannot complete run {run_id}: " + "; ".join(blockers))
    data["status"] = "completed"
    data["completed_at"] = utc_now()
    write_json(target, data)
    print(f"completed run {run_id}")
    return data

def supersede_run(root: Path, run_id: str, superseded_by: str) -> dict:
    """Transition a run to superseded status, pointing to the replacing run ID."""
    if not RUN_ID_PATTERN.match(superseded_by):
        raise CgspecError(f"invalid superseded_by run_id '{superseded_by}'")
    from .run_supersession import transition
    return transition(root, run_id, superseded_by, load_run_file)

def update_unit_status(root: Path, run_id: str, unit_id: str, status: str,
                       review_rounds: int | None = None) -> dict:
    """Update status and review_rounds for a specific unit in run.json."""
    if status not in ALLOWED_UNIT_STATUSES: raise CgspecError(f"invalid unit status '{status}'")
    target = root / RUNS_DIR / run_id / "run.json"
    if not target.is_file(): raise CgspecError(f"run {run_id} not found")
    data, errs = load_run_file(target, root)
    if errs or not data: raise CgspecError(f"cannot update unit in malformed run {run_id}: {'; '.join(errs)}")
    matched = next((u for u in data.get("units", []) if u.get("id") == unit_id), None)
    if not matched: raise CgspecError(f"unit {unit_id} not found in run {run_id}")
    matched["status"] = status
    if review_rounds is not None: matched["review_rounds"] = review_rounds
    write_json(target, data)
    return data

def cli(root: Path, args) -> int:
    """CLI dispatcher for run subcommands."""
    from .run_cli import dispatch
    return dispatch(root, args)
