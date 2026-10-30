"""Project-wide gates that every implementation slice must inherit."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .common import read_json

PROJECT_REL = "docs/_cgspec/project.json"
GLOBAL_PREFIX = "REQ-PREFLIGHT-"


def read_project(root: Path) -> dict:
    try:
        data = read_json(root / PROJECT_REL)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def project_from_reader(reader) -> tuple[dict, bytes | None]:
    raw = reader(PROJECT_REL)
    try:
        data = json.loads(raw.decode("utf-8")) if raw else {}
    except (UnicodeDecodeError, ValueError):
        data = {}
    return (data if isinstance(data, dict) else {}), raw


def check_id(capability_id: str) -> str:
    return GLOBAL_PREFIX + re.sub(r"[^A-Za-z0-9-]", "-", capability_id)


def global_requirements(project: dict, data: dict) -> list[dict]:
    outcomes = [item["id"] for item in data.get("outcomes", [])]
    return [{
        "id": check_id(cap_id), "need": f"Project implementation capability {cap_id} is operational",
        "owner": "user", "assistance": "Restore the capability and rerun start ready",
        "when": "before_start", "outcomes": outcomes, "check": None, "capability": cap_id,
    } for cap_id in project.get("implementation_capabilities", [])]


def effective_requirements(root: Path, data: dict) -> list[dict]:
    return list(data["prerequisites"]) + global_requirements(read_project(root), data)


def effective_from_reader(reader, data: dict) -> tuple[list[dict], bytes | None]:
    project, raw = project_from_reader(reader)
    return list(data["prerequisites"]) + global_requirements(project, data), raw


def record_errors(project: dict, data: dict) -> list[str]:
    if data.get("status") not in ("Ready", "In progress"):
        return []
    expected = {req["id"] for req in global_requirements(project, data)}
    actual = {result.get("id") for result in data.get("readiness", {}).get("checks", [])
              if str(result.get("id", "")).startswith(GLOBAL_PREFIX)}
    return [] if actual == expected else [
        f"global implementation preflight must cover exactly {sorted(expected)}; rerun start ready"
    ]


def bind_project(result: dict, raw: bytes | None) -> dict:
    if raw is not None:
        result["input_hashes"][PROJECT_REL] = hashlib.sha256(raw).hexdigest()
    return result


def protected_branches(project: dict) -> set[str]:
    return set(project.get("protected_branches", []))


def plan_errors(project: dict, plan: dict) -> list[str]:
    protected = protected_branches(project)
    branches = [repo.get("branch", "") for repo in plan.get("repositories", [])]
    branches += [item.get("branch", "") for item in plan.get("branch_policy", {}).get("stacked_branches", [])]
    return [f"implementation branch {branch} is a protected branch; use a dedicated feature branch"
            for branch in dict.fromkeys(branches) if branch in protected]


def doctor_findings(root: Path):
    from .doctor_checks import Finding, load_json
    project = read_project(root)
    for path in sorted((root / "docs/slices").glob("*.start.json")):
        data, findings = load_json(path, root, "start")
        if not findings and isinstance(data, dict):
            for error in record_errors(project, data):
                yield Finding("E-PREFLIGHT", path.relative_to(root).as_posix(), error)
    for path in sorted((root / "docs/slices").glob("*.git-plan.json")):
        data, findings = load_json(path, root, "git-plan")
        if not findings and isinstance(data, dict):
            for error in plan_errors(project, data):
                yield Finding("E-PROTECTED-BRANCH", path.relative_to(root).as_posix(), error)
