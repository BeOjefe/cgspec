"""Semantic Versioning release governance (issue #42).

Every versioned CGSpec project declares its release policy in
docs/_cgspec/project.json; each T1+ slice records its compatibility impact
in a `Release:` field; `release check --target VERSION` computes the maximum
required bump across the declared impacts and rejects an undersized target.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from .common import CgspecError, EXIT_BLOCK, EXIT_OK, PROJECT_FILE, read_json

# Strict SemVer 2.0.0 core (no build/pre-release handling beyond parsing).
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)

IMPACTS = ("none", "patch", "minor", "major")
IMPACT_ORDER = {"none": 0, "patch": 1, "minor": 2, "major": 3}
PRE_1_0_CHOICES = ("0.major.0", "0.minor.0", "0.patch.0")
DEFAULT_PRE_1_0 = "0.minor.0"
DEPRECATION_HINTS = ("deprecat",)

# Same field style the tier gate reads for Status/Scope/Approval.
SLICE_FIELD = r"^\s*[-*]?\s*\*{0,2}%s:?\*{0,2}:?\s*(.+?)\s*$"
RELEASE_FIELD = r"^\s*[-*]?\s*\*{0,2}Release:?\*{0,2}:?\s*([A-Za-z]+)\b(.*)$"
SLICE_STATUSES = {"Approved", "In progress", "Done"}


def parse_version(text: str) -> tuple[int, int, int] | None:
    """Strict semver parse; returns (major, minor, patch) or None."""
    if not isinstance(text, str):
        return None
    match = SEMVER_RE.match(text.strip())
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def compare_versions(a: str, b: str) -> int:
    """-1, 0, 1 ordering for valid semver strings; raises on invalid input."""
    pa, pb = parse_version(a), parse_version(b)
    if pa is None or pb is None:
        raise CgspecError(f"invalid semantic version: {a!r} vs {b!r}")
    return (pa > pb) - (pa < pb)


def policy_data(root: Path) -> dict | None:
    """The project's declared release block, or None when not declared."""
    pj = root / PROJECT_FILE
    if not pj.is_file():
        return None
    data = read_json(pj)
    if not isinstance(data, dict):
        return None
    block = data.get("release")
    return block if isinstance(block, dict) else None


def policy_errors(block: dict | None) -> list[str]:
    """Validation of the declared release policy; empty means usable."""
    if block is None:
        return ["project declares no release policy; set release.enabled (or enabled=false to opt out) — "
                "the engine never guesses a version policy"]
    if not isinstance(block.get("enabled"), bool):
        return ["release.enabled must be true or false"]
    errors = []
    if block.get("enabled") is True:
        current = block.get("current_version")
        if not isinstance(current, str) or parse_version(current) is None:
            errors.append("release.current_version must be a valid semver string when release is enabled")
        pre = block.get("pre_1_0", DEFAULT_PRE_1_0)
        if pre not in PRE_1_0_CHOICES:
            errors.append(f"release.pre_1_0 must be one of {', '.join(PRE_1_0_CHOICES)}")
    return errors


def slice_status(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(SLICE_FIELD % "Status", text, re.M | re.I)
    return match.group(1).strip("* ") if match else ""


def slice_release(path: Path) -> dict | None:
    """Parse the `Release:` field of a slice document; None when absent."""
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(RELEASE_FIELD, text, re.M | re.I)
    if not match:
        return None
    return {"impact": match.group(1).strip().lower(), "detail": match.group(2).strip()}


def declared_impacts(root: Path, slice_ids: list[str] | None = None) -> list[dict]:
    """Every included slice's declared Release field as {slice_id, path, status, release}."""
    wanted = {s.split(":")[-1] for s in (slice_ids or [])}
    result = []
    slices_dir = root / "docs/slices"
    if not slices_dir.is_dir():
        return result
    for path in sorted(slices_dir.glob("SLICE-*.md")):
        slice_id = "-".join(path.name.split("-")[:2])
        if wanted and slice_id not in wanted:
            continue
        status = slice_status(path)
        if status not in SLICE_STATUSES:
            continue  # drafts and blocked slices are not part of a release
        result.append({"slice_id": slice_id, "path": path.as_posix(), "status": status,
                       "release": slice_release(path)})
    return result


def classification_errors(root: Path, slice_ids: list[str] | None = None) -> list[str]:
    """Missing or malformed Release fields on included slices."""
    errors = []
    for item in declared_impacts(root, slice_ids):
        release = item["release"]
        if release is None:
            errors.append(f"{item['slice_id']} ({item['status']}) has no Release field; "
                          "record none|patch|minor|major with the affected surface and rationale")
            continue
        if release["impact"] not in IMPACTS:
            errors.append(f"{item['slice_id']} Release impact {release['impact']!r} is not one of {', '.join(IMPACTS)}")
        if release["impact"] != "none" and not release["detail"]:
            errors.append(f"{item['slice_id']} Release needs the affected public surface and rationale after the impact")
    return errors


def effective_impact(impact: str, detail: str) -> str:
    """Backward-compatible deprecations must advance at least a minor even when declared patch."""
    if impact == "patch" and any(hint in detail.lower() for hint in DEPRECATION_HINTS):
        return "minor"
    return impact


def required_bump(root: Path, slice_ids: list[str] | None = None) -> tuple[str, list[str]]:
    """(max effective impact, slice ids causing it) across the declared impacts."""
    causes: list[str] = []
    highest = "none"
    for item in declared_impacts(root, slice_ids):
        release = item["release"]
        if not release or release["impact"] == "none":
            continue
        impact = effective_impact(release["impact"], release["detail"])
        if IMPACT_ORDER[impact] > IMPACT_ORDER[highest]:
            highest, causes = impact, [item["slice_id"]]
        elif IMPACT_ORDER[impact] == IMPACT_ORDER[highest]:
            causes.append(item["slice_id"])
    return highest, causes


def bump(current: str, impact: str, pre_1_0: str = DEFAULT_PRE_1_0) -> str:
    """The minimum version that satisfies `impact` applied to `current`."""
    if impact not in IMPACT_ORDER:
        raise CgspecError(f"unknown release impact {impact!r}")
    parsed = parse_version(current)
    if parsed is None:
        raise CgspecError(f"invalid current version {current!r}")
    major, minor, patch = parsed
    if impact == "minor":
        return f"{major}.{minor + 1}.0"
    if impact == "major":
        if major == 0:
            if pre_1_0 == "0.major.0":
                return f"{major + 1}.0.0"
            if pre_1_0 == "0.minor.0":
                return f"{major}.{minor + 1}.0"
            if pre_1_0 == "0.patch.0":
                return f"{major}.{minor}.{patch + 1}"
            raise CgspecError(f"unknown pre-1.0 policy {pre_1_0!r}")
        return f"{major + 1}.0.0"
    # none or patch: a backward-compatible fix advances the patch segment
    return f"{major}.{minor}.{patch + 1}"


def check(root: Path, target: str | None, slice_ids: list[str] | None = None) -> list[str]:
    """Release problems for a candidate target version; empty means acceptable."""
    block = policy_data(root)
    errors = list(policy_errors(block))
    if errors:
        return errors
    assert block is not None
    if block.get("enabled") is not True:
        return []  # explicit opt-out; the CLI prints a note, nothing is enforced
    if target is None:
        return ["release check needs --target VERSION"]
    if parse_version(target) is None:
        return [f"invalid target version {target!r}; use X.Y.Z semantic versions"]
    errors += classification_errors(root, slice_ids)
    if errors:
        return errors
    impact, causes = required_bump(root, slice_ids)
    if impact == "none":
        return []
    minimum = bump(str(block["current_version"]), impact, block.get("pre_1_0", DEFAULT_PRE_1_0))
    if compare_versions(target, minimum) < 0:
        return [f"target {target} is below the required {minimum} for a {impact} release "
                f"(caused by {', '.join(causes)})"]
    return []


def plan(root: Path, slice_ids: list[str] | None = None) -> dict:
    """Machine-readable release plan: policy, classified slices, required bump."""
    block = policy_data(root)
    declared = declared_impacts(root, slice_ids)
    impact, causes = required_bump(root, slice_ids)
    policy_problems = policy_errors(block)
    return {
        "schema": 1,
        "policy_problems": policy_problems,
        "policy": block,
        "slices": [{**item, "effective_impact": effective_impact(item["release"]["impact"], item["release"]["detail"])
                    if item["release"] else None} for item in declared] if block else [],
        "required_bump": impact,
        "causes": causes,
    }


def cli(root: Path, args) -> int:
    action = args.rest[0] if args.rest else ""
    slice_ids = [s.strip() for s in (args.slices or "").split(",") if s.strip()] or None
    if action == "policy":
        block = policy_data(root)
        print(json.dumps({"policy": block, "problems": policy_errors(block)}, indent=2))
        return EXIT_OK
    if action == "plan":
        print(json.dumps(plan(root, slice_ids), indent=2))
        return EXIT_OK
    if action == "check":
        problems = check(root, args.target, slice_ids)
        if not problems:
            block = policy_data(root) or {}
            note = ("release policy opt-out; no version governance enforced"
                    if block.get("enabled") is not True
                    else "target version satisfies the required release bump")
            print(note)
            return EXIT_OK
        for problem in problems:
            print(problem, file=sys.stderr)
        return EXIT_BLOCK
    raise CgspecError("usage: cgspec_hook.py release policy|plan|check --target VERSION [--slices SLICE-...]")
