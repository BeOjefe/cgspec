"""Commit-level rules (spec 8, commit hook and CI columns), evaluated on a git View."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from . import tiers
from .common import ENGINE_DIR, PROJECT_FILE, STATE_DIR
from .gates import EMOJI, Context, _is_script_name, _script_allowed
from .gitview import View
from .globs import match_any

FROZEN = (STATE_DIR / "frozen.json").as_posix()
CHECKS = "docs/_cgspec/04-checks/manifest.json"
NO_TIER = ("docs/", ".cgspec-scratch/")


def _json(raw: bytes | None) -> dict:
    try:
        data = json.loads(raw.decode("utf-8")) if raw else {}
        return data if isinstance(data, dict) else {}
    except (UnicodeDecodeError, ValueError):
        return {}


def _append_only(view: View, rel: str, key: str, ident: str) -> list[str]:
    old = {e.get(ident): e for e in _json(view.read_old(rel)).get(key, []) if isinstance(e, dict)}
    new = {e.get(ident): e for e in _json(view.read_new(rel)).get(key, []) if isinstance(e, dict)}
    return [f"{rel} is append-only: existing entry {k} was changed or removed"
            for k, entry in old.items() if new.get(k) != entry]


def _frozen_and_engine(view: View, changes) -> list[str]:
    reasons = _append_only(view, FROZEN, "entries", "path") + _append_only(view, CHECKS, "checks", "id")
    frozen_old = {e.get("path") for e in _json(view.read_old(FROZEN)).get("entries", [])}
    engine_prefix = ENGINE_DIR.as_posix() + "/"
    engine_touched = False
    for change in changes:
        for rel in filter(None, (change.path, change.old_path)):
            if rel in frozen_old:
                reasons.append(f"{rel} is frozen and was changed ({change.status})")
            if rel.startswith(engine_prefix):
                engine_touched = True
    if engine_touched:
        manifest = _json(view.read_new(engine_prefix + "manifest.json")).get("files", {})
        for rel in view.files_new(ENGINE_DIR.as_posix()):
            name = rel[len(engine_prefix):]
            if name in ("manifest.json", "owned-files.json"):
                continue
            data = view.read_new(rel) or b""
            if manifest.get(name) != hashlib.sha256(data).hexdigest():
                reasons.append(f"engine file {name} does not match the engine manifest; only install.py upgrade changes the engine")
    return reasons


def _slice(view: View, slice_id: str) -> tuple[str, list[str]] | None:
    bare = slice_id.split(":")[-1]
    for rel in view.files_new("docs/slices"):
        if Path(rel).name.startswith(bare + "-"):
            text = (view.read_new(rel) or b"").decode("utf-8", "replace")
            status = re.search(tiers.FIELD % "Status", text, re.M | re.I)
            scope = re.search(tiers.FIELD % "Scope", text, re.M | re.I)
            globs = [g.strip().strip("`") for g in scope.group(1).split(",")] if scope else []
            return (status.group(1).strip("* ") if status else ""), [g for g in globs if g]
    return None


def _tier_rules(view: View, code_changes, tier: dict | None) -> list[str]:
    if not code_changes:
        return []
    paths = {c.path for c in code_changes}
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
    reasons = [f"{p} is outside the scope of {tier.get('slice')}" for p in sorted(paths) if not match_any(p, found[1])]
    if tier.get("tier") == "T1" and lines > tiers.T1_MAX_LINES:
        reasons.append(f"T1 allows {tiers.T1_MAX_LINES} changed lines, this commit changes {lines}")
    return reasons


def _test_pairs(view: View, code_changes, tier: dict | None, classes: dict) -> list[str]:
    if not tier or tier.get("tier") == "T0":
        return []
    code = [c.path for c in code_changes if c.status != "D" and match_any(c.path, classes.get("code", []))
            and not match_any(c.path, classes.get("tests", []))]
    records = [_json(view.read_new(p)) for p in view.files_new("docs/_cgspec/06-evidence/tests") if p.endswith(".json")]
    head = "HEAD" if view.new == ":" else view.new
    reasons = []
    for record in records:
        rev = record.get("failed_at", "")
        if not (view.commit_exists(rev) and view.is_ancestor(rev, head)):
            reasons.append(f"test-pair {record.get('test_id')}: failed_at {rev!r} is not a commit in this history")
    covered = {p for r in records for p in r.get("covers", [])}
    reasons += [f"{p} changed without a failing-test record in 06-evidence/tests (spec 7)" for p in code if p not in covered]
    return reasons


def _is_install_commit(view: View) -> bool:
    """A commit that adds the version marker or changes its version, with a manifest-consistent
    engine (checked separately), is install.py at work: install-owned files need no tier."""
    old = _json(view.read_old(PROJECT_FILE.as_posix())).get("cgspec_version")
    new = _json(view.read_new(PROJECT_FILE.as_posix())).get("cgspec_version")
    engine_version = (view.read_new(ENGINE_DIR.as_posix() + "/VERSION") or b"").decode().strip()
    return bool(new) and new != old and new == engine_version


def _install_owned(view: View) -> set[str]:
    owned = _json(view.read_new(ENGINE_DIR.as_posix() + "/owned-files.json"))
    paths = set(owned.get("created", {})) | set(owned.get("replaced", {})) | {".gitignore"}
    for value in owned.get("adapters", {}).values():
        if isinstance(value, dict):
            paths.add(value.get("path", ""))
        elif isinstance(value, list):
            paths.update(value)
        elif isinstance(value, str):
            paths.add(value)
    return paths


def evaluate(root: Path, view: View) -> list[str]:
    changes = view.changes()
    engine_prefix = ENGINE_DIR.as_posix() + "/"
    install_owned = _install_owned(view) if _is_install_commit(view) else set()
    project = _json(view.read_new(PROJECT_FILE.as_posix()))
    classes = project.get("path_classes", {}) if isinstance(project.get("path_classes"), dict) else {}
    tier = _json(view.read_new((STATE_DIR / "tier.json").as_posix())).get("active")
    ctx = Context(root, project)
    reasons = _frozen_and_engine(view, changes)
    code_changes = [c for c in changes if not c.path.startswith(NO_TIER) and c.path not in install_owned]
    reasons += _tier_rules(view, code_changes, tier)
    reasons += _test_pairs(view, code_changes, tier, classes)
    for change in changes:
        if change.path.startswith(engine_prefix):
            continue  # engine files are verified against the engine manifest above
        if change.status in "AC" and _is_script_name(change.path, None):
            content = (view.read_new(change.path) or b"").decode("utf-8", "replace")
            if not _script_allowed(ctx, change.path, content):
                reasons.append(f"new script {change.path} is not allowed here (spec 8)")
    for path, lines in view.added_lines().items():
        if not path.startswith(engine_prefix) and any(EMOJI.search(line) for line in lines):
            reasons.append(f"decorative emoji added in {path} (spec 1)")
    return list(dict.fromkeys(reasons))
