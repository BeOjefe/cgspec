"""Approved success definitions and executable, outcome-scoped readiness."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from . import tiers
from .common import CgspecError, EXIT_BLOCK, EXIT_OK, read_json, sha256_file, utc_now, write_json
from .inbox import approval_record, contains_secret
from .schema import validate_named

DEFINITION_KEYS = ("goal", "outcomes", "exclusions", "constraints", "design", "prerequisites")


def start_path(root: Path, slice_id: str) -> Path:
    found = tiers.find_slice(root, slice_id)
    if not found:
        raise CgspecError(f"slice not found: {slice_id}")
    return found[0].with_suffix(".start.json")


def empty_readiness() -> dict:
    return {"definition_hash": "", "mocks_allowed": False, "ran_at": None, "checks": []}


def definition_hash(data: dict) -> str:
    definition = {key: data.get(key) for key in DEFINITION_KEYS}
    raw = json.dumps(definition, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def approval_is_fresh(approval: dict, data: dict) -> bool:
    if "captured_ns" in approval:
        return approval["captured_ns"] > data["drafted_ns"]
    # Legacy records only resolve seconds; equality cannot establish ordering.
    return approval.get("at", "") > data["drafted_at"]


def mocks_enabled() -> bool:
    return os.environ.get("CGSPEC_ALLOW_MOCKS", "0") == "1"


def outcome(data: dict, outcome_id: str) -> dict | None:
    return next((item for item in data.get("outcomes", []) if item.get("id") == outcome_id), None)


def validate_record(data: dict) -> list[str]:
    errors = validate_named(data, "start")
    if errors:
        return errors
    outcomes = data["outcomes"]
    outcome_ids = [item["id"] for item in outcomes]
    requirement_ids = [item["id"] for item in data["prerequisites"]]
    if len(set(outcome_ids)) != len(outcome_ids):
        errors.append("outcome IDs must be unique")
    if len(set(requirement_ids)) != len(requirement_ids):
        errors.append("prerequisite IDs must be unique")
    known = set(outcome_ids)
    for item in outcomes:
        evaluation = item["evaluation"]
        if evaluation["requires_real"] and evaluation["data_source"] != "real_backend":
            errors.append(f"{item['id']}: real evaluation requires real-backend data")
    for item in data["prerequisites"]:
        missing = set(item["outcomes"]) - known
        if missing:
            errors.append(f"{item['id']}: unknown outcomes {sorted(missing)}")
        if item.get("capability") and item["check"] is not None:
            errors.append(f"{item['id']}: a capability-backed prerequisite takes its check from "
                          "docs/_cgspec/capabilities.json; set check to null")
    if data["design"]["required"] and not (data["design"]["target"] and data["design"]["states"]):
        errors.append("design.target and design.states are required before implementation")
    missing_active = set(data["active_outcomes"]) - known
    if missing_active:
        errors.append(f"active outcomes are unknown: {sorted(missing_active)}")
    if data["status"] != "Draft" and not data["approval"]:
        errors.append("success and evaluation need explicit approval")
    if data["approval"] and data["approval"]["definition_hash"] != definition_hash(data):
        errors.append("approval is stale for this definition")
    if data["status"] in ("Ready", "In progress"):
        if data["readiness"]["definition_hash"] != definition_hash(data):
            errors.append("readiness is missing or stale for this definition")
        if not data["readiness"]["ran_at"]:
            errors.append("implementation readiness needs an execution timestamp")
        expected = {r["id"] for r in data["prerequisites"] if r["when"] == "before_start"}
        actual = {r["id"] for r in data["readiness"]["checks"]}
        unknown = actual - expected
        if not expected.issubset(actual) or any(not item.startswith("REQ-PREFLIGHT-") for item in unknown):
            errors.append(f"readiness results must cover local prerequisites {sorted(expected)} and only known global preflight checks")
    if data["status"] == "In progress" and not data["active_outcomes"]:
        errors.append("In progress needs at least one active outcome")
    known_requirements = set(requirement_ids)
    for result in data["readiness"]["checks"]:
        if result["id"] not in known_requirements and not result["id"].startswith("REQ-PREFLIGHT-"):
            errors.append(f"readiness names unknown prerequisite {result['id']}")
    return errors


def load(root: Path, slice_id: str) -> tuple[Path, dict]:
    path = start_path(root, slice_id)
    if not path.is_file():
        raise CgspecError(f"{slice_id} has no success agreement; run start set first")
    data = read_json(path)
    errors = validate_record(data)
    from .project_policy import read_project, record_errors
    errors += record_errors(read_project(root), data)
    if errors:
        raise CgspecError(f"invalid success agreement {path.name}: " + "; ".join(errors))
    return path, data


def readiness_input_errors(data: dict, outcome_id: str, reader, requirements=None) -> list[str]:
    results = {r.get("id"): r for r in data["readiness"].get("checks", [])}
    reasons = []
    for req in requirements or data["prerequisites"]:
        if req["when"] != "before_start" or outcome_id not in req["outcomes"]:
            continue
        result = results.get(req["id"], {})
        for rel, expected in result.get("input_hashes", {}).items():
            raw = reader(rel)
            if raw is None or hashlib.sha256(raw).hexdigest() != expected:
                reasons.append(f"{outcome_id}: readiness input {rel} changed or is missing; rerun start ready")
    return reasons


def root_reader(root: Path):
    def read(rel: str) -> bytes | None:
        try:
            return (root / rel).read_bytes()
        except OSError:
            return None
    return read


def eligibility_errors(data: dict, outcome_id: str, allow_mocks: bool, reader=None, requirements=None) -> list[str]:
    item = outcome(data, outcome_id)
    if not item:
        return [f"unknown outcome {outcome_id}"]
    if not data.get("approval") or data.get("status") == "Draft":
        return [f"{outcome_id}: goal and evaluation are not explicitly approved"]
    if data["readiness"].get("definition_hash") != definition_hash(data):
        return [f"{outcome_id}: readiness is missing or stale; run start ready"]
    reasons = []
    development = item["development"]
    if development["uses_mocks"] and not allow_mocks:
        reasons.append(f"{outcome_id}: CGSPEC_ALLOW_MOCKS=0 disables mock-based development substitution")
    results = {r.get("id"): r for r in data["readiness"].get("checks", [])}
    for req in requirements or data["prerequisites"]:
        if req["when"] != "before_start" or outcome_id not in req["outcomes"]:
            continue
        result = results.get(req["id"])
        if not result or result.get("status") != "PASS":
            detail = result.get("detail") if result else req["need"]
            reasons.append(f"{outcome_id}: {detail} Owner: {req['owner']}. Next: {req['assistance']}")
    if reader:
        reasons += readiness_input_errors(data, outcome_id, reader, requirements)
    return reasons


def save(path: Path, data: dict) -> None:
    serialized = json.dumps(data, ensure_ascii=False, indent=2)
    if (kind := next((kind for line in serialized.splitlines() if (kind := contains_secret(line))), None)):
        raise CgspecError(f"success agreement contains a possible {kind}; use environment variable names only")
    errors = validate_record(data)
    if errors:
        raise CgspecError("invalid success agreement: " + "; ".join(errors))
    data["updated"] = utc_now()
    write_json(path, data)


def set_definition(root: Path, slice_id: str, source: Path) -> None:
    draft = read_json(source)
    if not isinstance(draft, dict) or set(draft) - set(DEFINITION_KEYS):
        raise CgspecError("start draft contains unknown fields; provide only the success definition")
    path = start_path(root, slice_id)
    previous = read_json(path) if path.is_file() else {}
    prior = list(previous.get("prior_approvals", []))
    if previous.get("approval") and previous["approval"].get("ref"):
        prior.append(previous["approval"]["ref"])
    record = {
        "schema": 1, "slice": slice_id, "version": previous.get("version", 0) + 1,
        "status": "Draft", **{key: copy.deepcopy(draft.get(key)) for key in DEFINITION_KEYS},
        "approval": None, "prior_approvals": list(dict.fromkeys(prior)),
        "readiness": empty_readiness(), "active_outcomes": [], "drafted_at": utc_now(),
        "drafted_ns": time.time_ns(), "updated": utc_now(),
    }
    save(path, record)
    print(f"success agreement drafted: {slice_id} version {record['version']}")


def verify_trailer_draft(root: Path, path: Path, slice_id: str) -> str:
    """Return the signed HEAD approving this exact Draft."""
    from . import commit_trust as trust
    from .gitview import View, git
    rel = path.relative_to(root).as_posix()
    head = git(root, "rev-parse", "HEAD").stdout.strip()
    view = View.commit(root, head)
    if view.read_new(rel) != path.read_bytes():
        raise CgspecError("trailer approval needs the exact Draft committed and signed in HEAD first")
    problem = trust.approval_ok(view, "trailer", slice_id.split(":")[-1])
    if problem:
        raise CgspecError(f"start draft {problem}")
    return head


def agree(root: Path, slice_id: str, ref: str) -> None:
    path, data = load(root, slice_id)
    if data["status"] != "Draft":
        raise CgspecError("only a Draft definition can be approved")
    bare = slice_id.split(":")[-1]
    commit = None
    if ref == "trailer":
        commit = verify_trailer_draft(root, path, slice_id)
    else:
        approval = approval_record(root, ref, bare)
        if not approval:
            raise CgspecError(f"approval must come from your message naming {bare}")
        if not approval_is_fresh(approval, data):
            raise CgspecError("approval predates this Draft; review and approve the current definition")
        slice_text = tiers.find_slice(root, slice_id)[0].read_text(encoding="utf-8", errors="replace")
        import re
        match = re.search(tiers.FIELD % "Approval", slice_text, re.M | re.I)
        slice_ref = match.group(1).strip("* `") if match else ""
        if ref == slice_ref or ref in data["prior_approvals"]:
            raise CgspecError("success and evaluation need a new approval, not an earlier slice/agreement approval")
    data["approval"] = {"ref": ref, "at": utc_now(), "definition_hash": definition_hash(data), "commit": commit}
    data["status"] = "Agreed"
    save(path, data)
    print(f"success and evaluation approved: {slice_id} version {data['version']}")


def probe_input_hashes(root: Path, check: dict) -> dict[str, str]:
    candidates = set(check["inputs"])
    for arg in check["argv"]:
        path = (root / arg).resolve()
        try:
            rel = path.relative_to(root.resolve()).as_posix()
        except ValueError:
            continue
        if path.is_file():
            candidates.add(rel)
    hashes = {}
    for rel in sorted(candidates):
        path = (root / rel).resolve()
        try:
            contained = path.relative_to(root.resolve()).as_posix()
        except ValueError:
            raise CgspecError(f"readiness input escapes the project: {rel}") from None
        if not path.is_file():
            raise CgspecError(f"readiness input is missing: {rel}") from None
        hashes[contained] = sha256_file(path)
    return hashes


def probe_result(req: dict, status: str, detail: str, now: str, hashes: dict[str, str]) -> dict:
    return {"id": req["id"], "status": status, "detail": detail, "ran_at": now, "input_hashes": hashes}


def run_probe(root: Path, req: dict) -> dict:
    now = utc_now()
    check = req["check"]
    if check is None:
        detail = f"{req['need']}. Owner: {req['owner']}. Next: {req['assistance']}"
        return probe_result(req, "BLOCKED", detail, now, {})
    try:
        hashes = probe_input_hashes(root, check)
    except CgspecError as exc:
        return probe_result(req, "BLOCKED", f"{exc}. Next: {req['assistance']}", now, {})
    cwd = (root / check["cwd"]).resolve()
    try:
        cwd.relative_to(root.resolve())
    except ValueError:
        detail = f"probe working directory escapes the project. Next: {req['assistance']}"
        return probe_result(req, "BLOCKED", detail, now, hashes)
    try:
        result = subprocess.run(check["argv"], cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                timeout=check["timeout_seconds"], check=False)
        if result.returncode == 0:
            return probe_result(req, "PASS", f"Probe passed: {req['need']}", now, hashes)
        detail = f"{req['need']} (probe exit {result.returncode}). Next: {req['assistance']}"
    except (OSError, subprocess.TimeoutExpired) as exc:
        detail = f"{req['need']} (probe could not run: {type(exc).__name__}). Next: {req['assistance']}"
    return probe_result(req, "BLOCKED", detail, now, hashes)


def probe_requirement(root: Path, req: dict) -> dict:
    if req.get("capability"):
        from .capabilities import probe_prerequisite
        return probe_prerequisite(root, req)
    return run_probe(root, req)


def ready(root: Path, slice_id: str) -> int:
    path, data = load(root, slice_id)
    if data["status"] not in ("Agreed", "Ready", "In progress"):
        raise CgspecError("approve the success definition before readiness")
    allow_mocks = mocks_enabled()
    from .project_policy import PROJECT_REL, bind_project, effective_requirements
    requirements = effective_requirements(root, data)
    project_raw = (root / PROJECT_REL).read_bytes()
    checks = [probe_requirement(root, req) for req in requirements if req["when"] == "before_start"]
    checks = [bind_project(result, project_raw) if result["id"].startswith("REQ-PREFLIGHT-") else result
              for result in checks]
    data["readiness"] = {"definition_hash": definition_hash(data), "mocks_allowed": allow_mocks,
                         "ran_at": utc_now(), "checks": checks}
    eligible = [o["id"] for o in data["outcomes"] if not eligibility_errors(data, o["id"], allow_mocks, root_reader(root), requirements)]
    data["active_outcomes"] = [oid for oid in data["active_outcomes"] if oid in eligible]
    data["status"] = "In progress" if data["active_outcomes"] else ("Ready" if eligible else "Agreed")
    save(path, data)
    blocked = {o["id"]: eligibility_errors(data, o["id"], allow_mocks, root_reader(root), requirements) for o in data["outcomes"] if o["id"] not in eligible}
    for outcome_id, reasons in blocked.items():
        print(f"{outcome_id}: " + " | ".join(reasons), file=sys.stderr)
    print(f"readiness: {len(eligible)} eligible, {len(blocked)} blocked; mocks_allowed={str(allow_mocks).lower()}")
    return EXIT_OK if eligible else EXIT_BLOCK


def begin(root: Path, slice_id: str, raw_ids: str) -> None:
    path, data = load(root, slice_id)
    if data["status"] not in ("Ready", "In progress"):
        raise CgspecError("run start ready before beginning implementation")
    ids = [item.strip() for item in raw_ids.split(",") if item.strip()]
    if not ids:
        raise CgspecError("begin needs --outcome OUT-ID[,OUT-ID]")
    from .project_policy import effective_requirements
    requirements = effective_requirements(root, data)
    reasons = [reason for oid in ids for reason in eligibility_errors(data, oid, mocks_enabled(), root_reader(root), requirements)]
    if reasons:
        raise CgspecError("; ".join(reasons))
    data["active_outcomes"] = list(dict.fromkeys(data["active_outcomes"] + ids))
    data["status"] = "In progress"
    save(path, data)
    print(f"implementation started: {', '.join(ids)}")


def cli(root: Path, args) -> int:
    action = args.rest[0] if args.rest else ""
    if not args.slice:
        raise CgspecError("start needs --slice SLICE-NNN")
    if action == "set":
        if not args.file:
            raise CgspecError("start set needs --file <draft.json>")
        set_definition(root, args.slice, Path(args.file))
    elif action == "agree":
        if not args.approval:
            raise CgspecError("start agree needs --approval A-...")
        agree(root, args.slice, args.approval)
    elif action == "ready":
        return ready(root, args.slice)
    elif action == "begin":
        begin(root, args.slice, args.outcome or "")
    elif action == "show":
        _, data = load(root, args.slice)
        from .project_policy import effective_requirements
        requirements = effective_requirements(root, data)
        result = copy.deepcopy(data)
        result["eligible_outcomes"] = [o["id"] for o in data["outcomes"] if not eligibility_errors(data, o["id"], mocks_enabled(), root_reader(root), requirements)]
        result["blockers"] = {o["id"]: eligibility_errors(data, o["id"], mocks_enabled(), root_reader(root), requirements) for o in data["outcomes"]
                              if eligibility_errors(data, o["id"], mocks_enabled(), root_reader(root), requirements)}
        print(json.dumps(result, indent=2))
    else:
        raise CgspecError("usage: cgspec_hook.py start set|agree|ready|begin|show --slice SLICE-NNN")
    return EXIT_OK
