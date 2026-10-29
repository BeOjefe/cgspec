"""Declare-once agent-side capabilities with executable checks (issue #53).

A project lists, once, what the agent may use beyond the repository itself: an
authenticated browser or account session, a way to delegate to another model, a
channel to reach the human, or any other tool. Each capability carries the same
executable check shape as a slice prerequisite, and the whole registry needs one
fresh user approval naming "capabilities". A slice prerequisite references a
capability by ID instead of restating its check; `start ready` then runs the
registry's check and binds the registry bytes to readiness. Nothing here is
assumed to work: a missing, invalid, unapproved or failing capability is BLOCKED.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import time
from pathlib import Path

from .common import CGSPEC_DIR, CgspecError, EXIT_BLOCK, EXIT_OK, read_json, utc_now, write_json
from .inbox import approval_record, approval_target, contains_secret
from .schema import validate_named

REGISTRY = CGSPEC_DIR / "capabilities.json"
REGISTRY_REL = REGISTRY.as_posix()
APPROVAL_TARGET = "capabilities"


def registry_hash(data: dict) -> str:
    raw = json.dumps(data.get("capabilities"), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_registry(data) -> list[str]:
    if not isinstance(data, dict):
        return ["capability registry must be a JSON object"]
    errors = validate_named(data, "capabilities")
    if errors:
        return errors
    ids = [item["id"] for item in data["capabilities"]]
    if len(set(ids)) != len(ids):
        errors.append("capability IDs must be unique")
    if data["approval"] and data["approval"]["registry_hash"] != registry_hash(data):
        errors.append("approval is stale for this capability registry")
    return errors


def parse(raw: bytes | None) -> tuple[dict | None, str | None]:
    """(registry, problem) from raw bytes; problem names why it cannot be used."""
    if raw is None:
        return None, f"no capability registry at {REGISTRY_REL}"
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None, f"{REGISTRY_REL} is not valid JSON"
    errors = validate_registry(data)
    if errors:
        return None, f"{REGISTRY_REL} is invalid: " + "; ".join(errors)
    return data, None


def read_bytes(root: Path) -> bytes | None:
    try:
        return (root / REGISTRY).read_bytes()
    except OSError:
        return None


def resolve(data: dict | None, problem: str | None, cap_id: str) -> tuple[dict | None, str | None]:
    """The approved capability named cap_id, or the reason it cannot be relied on."""
    if problem:
        return None, problem
    if not data["approval"]:
        return None, "the capability registry is not approved; ask the user to approve capabilities"
    found = next((item for item in data["capabilities"] if item["id"] == cap_id), None)
    if not found:
        return None, f"{cap_id} is not declared in {REGISTRY_REL}"
    return found, None


def candidate_check(view, cap_id: str) -> dict | None:
    """The check a candidate tree's registry declares for cap_id, or None."""
    capability, _ = resolve(*parse(view.read_new(REGISTRY_REL)), cap_id)
    return capability["check"] if capability else None


def _effective(req: dict, capability: dict) -> dict:
    cap_id = capability["id"]
    return {**req, "check": capability["check"], "need": f"{req['need']} [{cap_id}: {capability['summary']}]",
            "assistance": f"{req['assistance']} ({cap_id}: {capability['assistance']})"}


def probe_prerequisite(root: Path, req: dict) -> dict:
    """Run the registry check behind a capability-backed prerequisite; fail closed."""
    from .start import probe_result, run_probe
    raw = read_bytes(root)
    registry_hashes = {REGISTRY_REL: hashlib.sha256(raw).hexdigest()} if raw is not None else {}
    capability, problem = resolve(*parse(raw), req["capability"])
    if problem:
        detail = f"{req['need']} ({req['capability']}: {problem})."
        return probe_result(req, "BLOCKED", detail, utc_now(), registry_hashes)
    result = run_probe(root, _effective(req, capability))
    result["input_hashes"] = {**result["input_hashes"], **registry_hashes}
    return result


def check_all(root: Path, only: list[str] | None = None) -> list[dict]:
    """Probe declared capabilities now. Results are reported, not cached."""
    from .start import run_probe
    data, problem = parse(read_bytes(root))
    if problem:
        raise CgspecError(problem)
    if not data["approval"]:
        raise CgspecError("the capability registry is not approved; ask the user to approve capabilities")
    known = {item["id"] for item in data["capabilities"]}
    if only and (missing := sorted(set(only) - known)):
        raise CgspecError(f"unknown capabilities: {', '.join(missing)}")
    results = []
    for item in data["capabilities"]:
        if only and item["id"] not in only:
            continue
        req = {"id": item["id"], "need": item["summary"], "owner": item["owner"],
               "assistance": item["assistance"], "check": item["check"]}
        result = run_probe(root, req)
        results.append({"id": item["id"], "kind": item["kind"], "status": result["status"],
                        "detail": result["detail"], "usage": item["usage"], "ran_at": result["ran_at"]})
    return results


def doctor_findings(root: Path):
    """Schema and semantic findings for an optional registry; absence is not a finding."""
    from .doctor_checks import Finding, load_json
    path = root / REGISTRY
    if not path.is_file():
        return
    data, findings = load_json(path, root, "capabilities")
    yield from findings
    if not findings:
        yield from (Finding("E-SCHEMA", REGISTRY_REL, error) for error in validate_registry(data))


def save(root: Path, data: dict) -> None:
    serialized = json.dumps(data, ensure_ascii=False, indent=2)
    if (kind := next((kind for line in serialized.splitlines() if (kind := contains_secret(line))), None)):
        raise CgspecError(f"capability registry contains a possible {kind}; use environment variable names only")
    errors = validate_registry(data)
    if errors:
        raise CgspecError("invalid capability registry: " + "; ".join(errors))
    data["updated"] = utc_now()
    write_json(root / REGISTRY, data)


def load(root: Path) -> dict:
    data, problem = parse(read_bytes(root))
    if problem:
        raise CgspecError(problem)
    return data


def set_registry(root: Path, source: Path) -> None:
    draft = read_json(source)
    if not isinstance(draft, dict) or set(draft) != {"capabilities"}:
        raise CgspecError("capability draft must contain only a 'capabilities' list")
    now = utc_now()
    record = {"schema": 1, "capabilities": copy.deepcopy(draft["capabilities"]), "approval": None,
              "drafted_at": now, "drafted_ns": time.time_ns(), "updated": now}
    save(root, record)
    print(f"capability registry drafted: {len(record['capabilities'])} capabilities; "
          "ask the user to approve capabilities before relying on them")


def _verify_trailer(root: Path) -> str:
    """Return the signed HEAD that committed this exact unapproved registry."""
    from . import commit_trust as trust
    from .gitview import View, git
    head = git(root, "rev-parse", "HEAD").stdout.strip()
    view = View.commit(root, head)
    if view.read_new(REGISTRY_REL) != (root / REGISTRY).read_bytes():
        raise CgspecError("trailer approval needs the exact drafted registry committed and signed in HEAD first")
    problem = trust.approval_ok(view, trust.TRAILER_REF, APPROVAL_TARGET)
    if problem:
        raise CgspecError(f"capability registry {problem}")
    return head


def agree(root: Path, ref: str) -> None:
    data = load(root)
    if data["approval"]:
        raise CgspecError("the capability registry is already approved; draft a change with capability set first")
    commit = None
    if ref == "trailer":
        commit = _verify_trailer(root)
    else:
        approval = approval_record(root, ref, APPROVAL_TARGET)
        if not approval:
            raise CgspecError("approval must come from your message naming capabilities (\"approve capabilities\")")
        if not approval_fresh(approval, data):
            raise CgspecError("approval predates this capability draft; review and approve the current registry")
    data["approval"] = {"ref": ref, "at": utc_now(), "registry_hash": registry_hash(data), "commit": commit}
    save(root, data)
    print(f"capability registry approved: {len(data['capabilities'])} capabilities")


def approval_fresh(approval: dict, data: dict) -> bool:
    if "captured_ns" in approval:
        return approval["captured_ns"] > data["drafted_ns"]
    return approval.get("at", "") > data["drafted_at"]


def approval_reason(view, data: dict) -> str | None:
    """Commit/CI binding for the registry approval; mirrors slice agreement approval."""
    from . import commit_trust as trust
    approval = data.get("approval")
    if not approval:
        return None
    ref = str(approval.get("ref", ""))
    if ref == trust.TRAILER_REF:
        commit = approval.get("commit")
        if not commit or not view.commit_exists(commit) or not view.is_ancestor(commit, view.old or "HEAD"):
            return f"{REGISTRY_REL}: signed draft is not an ancestor of the candidate"
        from .gitview import View
        signed = View.commit(view.root, commit)
        original = trust.load(signed.read_new(REGISTRY_REL))
        if original.get("approval") is not None or registry_hash(original) != registry_hash(data) \
                or trust.approval_ok(signed, ref, APPROVAL_TARGET):
            return f"{REGISTRY_REL}: signed draft does not approve this exact registry"
        return None
    approvals = trust.load(view.read_new("docs/_cgspec/07-state/approvals.json")).get("approvals", [])
    captured = next((a for a in approvals if isinstance(a, dict) and a.get("id") == ref
                     and approval_target(str(a.get("excerpt", ""))) == APPROVAL_TARGET), None)
    if captured and not approval_fresh(captured, data):
        return f"{REGISTRY_REL}: approval predates this capability draft"
    old_raw = view.read_old(REGISTRY_REL)
    old = trust.load(old_raw)
    changed = not old_raw or not old.get("approval") or registry_hash(old) != registry_hash(data) or \
        (old.get("approval") or {}).get("ref") != ref
    if changed:
        problem = trust.approval_ok(view, ref, APPROVAL_TARGET)
        return f"{REGISTRY_REL}: capability approval {problem}" if problem else None
    if ref not in trust.approval_ids(view):
        return f"{REGISTRY_REL}: approval {ref} is not in the approval record"
    return None


def commit_records(view, changes) -> list[str]:
    from . import commit_trust as trust
    if not any(change.path == REGISTRY_REL and change.status != "D" for change in changes):
        return []
    data = trust.load(view.read_new(REGISTRY_REL))
    errors = validate_registry(data)
    if errors:
        return [f"{REGISTRY_REL}: {error}" for error in errors]
    problem = approval_reason(view, data)
    return [problem] if problem else []


def staged_trailer_ref(view) -> bool:
    from . import commit_trust as trust
    new = (trust.load(view.read_new(REGISTRY_REL)).get("approval") or {})
    old = (trust.load(view.read_old(REGISTRY_REL)).get("approval") or {})
    return isinstance(new, dict) and new.get("ref") == trust.TRAILER_REF and \
        not (isinstance(old, dict) and old.get("ref") == trust.TRAILER_REF)


def approval_ref(view) -> str:
    from . import commit_trust as trust
    approval = trust.load(view.read_new(REGISTRY_REL)).get("approval")
    return str(approval.get("ref", "")) if isinstance(approval, dict) else ""


def cli(root: Path, args) -> int:
    action = args.rest[0] if args.rest else ""
    if action == "set":
        if not args.file:
            raise CgspecError("capability set needs --file <draft.json>")
        set_registry(root, Path(args.file))
    elif action == "agree":
        if not args.approval:
            raise CgspecError("capability agree needs --approval A-... (or trailer)")
        agree(root, args.approval)
    elif action == "check":
        only = [item.strip() for item in (getattr(args, "id", None) or "").split(",") if item.strip()] or None
        results = check_all(root, only)
        print(json.dumps(results, indent=2))
        blocked = [r["id"] for r in results if r["status"] != "PASS"]
        for item in blocked:
            print(f"{item}: BLOCKED", file=sys.stderr)
        return EXIT_BLOCK if blocked else EXIT_OK
    elif action == "show":
        data, problem = parse(read_bytes(root))
        print(json.dumps({"registry": data, "problem": problem,
                          "approved": bool(data and data["approval"])}, indent=2))
    else:
        raise CgspecError("usage: cgspec_hook.py capability set|agree|check|show [--file F] [--approval A-...] [--id CAP-...]")
    return EXIT_OK
