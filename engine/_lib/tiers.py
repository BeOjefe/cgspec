"""Tier declarations (spec 3) and slice lookup."""

from __future__ import annotations

import re
from pathlib import Path

from .common import STATE_DIR, CgspecError, new_id, read_json, utc_now, write_json
from .globs import match_any

TIER_FILE = STATE_DIR / "tier.json"
T0_MAX_FILES = 3
T0_MAX_LINES = 40
T1_MAX_LINES = 400
T0_FORBIDDEN_CLASSES = ("schema", "api", "auth", "deps")
WORKING_SLICE = ("Approved", "In progress")
FIELD = r"^\s*[-*]?\s*\*{0,2}%s:?\*{0,2}:?\s*(.+?)\s*$"


def active(root: Path) -> dict | None:
    path = root / TIER_FILE
    if not path.is_file():
        return None
    data = read_json(path)
    return data.get("active") if isinstance(data, dict) else None


def find_slice(root: Path, slice_id: str) -> tuple[Path, str, list[str]] | None:
    """(path, status, scope globs) for SLICE-NNN, or None."""
    bare = slice_id.split(":")[-1]
    for path in sorted((root / "docs/slices").glob(f"{bare}-*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        status = re.search(FIELD % "Status", text, re.M | re.I)
        scope = re.search(FIELD % "Scope", text, re.M | re.I)
        globs = [g.strip().strip("`") for g in scope.group(1).split(",")] if scope else []
        return path, (status.group(1).strip("* ") if status else ""), [g for g in globs if g]
    return None


def classes_of(rel: str, path_classes: dict) -> list[str]:
    return [name for name, globs in path_classes.items() if match_any(rel, globs)]


def set_tier(root: Path, tier: str, reason: str, files: list[str], slice_id: str | None,
             path_classes: dict, protected, verification: str | None = None) -> dict:
    entry = {"id": new_id("T"), "tier": tier, "reason": reason.strip(), "created": utc_now()}
    if len(entry["reason"]) < 3:
        raise CgspecError("--reason must say why (at least 3 characters)")
    if tier == "T0":
        if not verification or not verification.strip():
            raise CgspecError("T0 needs --verify describing how the outcome will be checked")
        entry["verification"] = verification.strip()
        if not 1 <= len(files) <= T0_MAX_FILES:
            raise CgspecError(f"T0 lists 1 to {T0_MAX_FILES} files; this change is bigger, use T1 with a slice")
        for rel in files:
            if not (root / rel).is_file():
                raise CgspecError(f"T0 cannot create files ({rel} does not exist); use T1 with a slice")
            bad = [c for c in classes_of(rel, path_classes) if c in T0_FORBIDDEN_CLASSES]
            if bad:
                raise CgspecError(f"T0 cannot touch {rel} (path class: {', '.join(bad)}); use T1 or higher")
            if protected(rel):
                raise CgspecError(f"{rel} is protected and cannot be edited at any tier")
        entry["files"] = files
    else:
        if not slice_id:
            raise CgspecError(f"{tier} needs --slice with an approved slice (spec 3)")
        found = find_slice(root, slice_id)
        if not found:
            raise CgspecError(f"slice not found: {slice_id}")
        if found[1] not in WORKING_SLICE:
            raise CgspecError(f"{slice_id} has status '{found[1]}'; it must be Approved or In progress")
        if not found[2]:
            raise CgspecError(f"{slice_id} has no Scope line listing the files it may change")
        approval = re.search(FIELD % "Approval", found[0].read_text(encoding="utf-8", errors="replace"), re.M | re.I)
        from .inbox import approval_exists
        ref = approval.group(1).strip("* `") if approval else ""
        if ref != "trailer" and not approval_exists(root, ref):
            raise CgspecError(f"{slice_id} needs an Approval line citing your approval (A-... from 07-state/approvals.json)")
        entry["slice"] = slice_id
    write_json(root / TIER_FILE, {"schema": 1, "active": entry})
    return entry


def clear(root: Path) -> None:
    write_json(root / TIER_FILE, {"schema": 1, "active": None})
