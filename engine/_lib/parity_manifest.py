"""Built-app parity manifest validation against the actual UI diff."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .common import CgspecError
from .globs import match_any
from .layout import GUI_PROFILES

MANIFEST = "docs/prototypes/parity.json"
UI_SUFFIXES = {".html", ".htm", ".css", ".scss", ".sass", ".js", ".jsx", ".ts", ".tsx", ".vue",
               ".svelte", ".svg", ".png", ".jpg", ".jpeg", ".webp", ".woff", ".woff2"}
EXCLUDED = ("docs/_cgspec/", "docs/prototypes/", "tests/", ".cgspec-scratch/", "engine/", ".agents/",
            ".claude/", ".cursor/", ".github/")
HASH = re.compile(r"[0-9a-f]{64}")


def digest(data) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":"),
                                 ensure_ascii=False).encode()).hexdigest()


def ui_paths(paths, project):
    profile = project.get("profile", "")
    if profile and profile not in GUI_PROFILES:
        return []
    return sorted(p for p in paths if not p.startswith(EXCLUDED) and
                  (Path(p).suffix.lower() in UI_SUFFIXES or p == "package.json"))


def _binding(entry: dict, where: str) -> None:
    required = ("approval", "approval_sha256", "reviewer", "approved_at", "revision")
    if not isinstance(entry, dict) or any(not entry.get(key) for key in required):
        raise CgspecError(f"{where} needs exact approval, reviewer, timestamp and revision binding")
    if not HASH.fullmatch(str(entry.get("approval_sha256", ""))) or not re.fullmatch(
            r"[0-9a-f]{40}", str(entry.get("revision", ""))):
        raise CgspecError(f"{where} has an invalid approval hash or revision")


def validate(data, changed):
    if not isinstance(data, dict) or data.get("schema") != 1:
        raise CgspecError("UI changes require docs/prototypes/parity.json schema 1")
    covers = data.get("covers")
    if not isinstance(covers, list) or not covers or not all(isinstance(x, str) and x for x in covers):
        raise CgspecError("parity covers must be non-empty globs matching the actual UI diff")
    missing = [path for path in changed if not match_any(path, covers)]
    unused = [glob for glob in covers if not any(match_any(path, [glob]) for path in changed)] if changed else []
    if missing or unused:
        raise CgspecError(f"parity covers mismatch: uncovered {missing}; nonmatching {unused}")
    for field in ("build_mode", "data_source", "authentication_method", "mock_switch_state"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            raise CgspecError(f"parity requires {field} on every proof artifact")
    allowed = {"build_mode": {"production", "development", "test"},
               "data_source": {"real-backend", "fixtures", "injected", "unknown"},
               "authentication_method": {"two-real-accounts", "real-account", "test-identity", "dev-switch", "none", "unknown"},
               "mock_switch_state": {"absent", "disabled", "enabled"}}
    if any(data[field] not in values for field, values in allowed.items()):
        raise CgspecError("parity environment labels contain unsupported values")
    if data.get("two_account_claim"):
        if (data["build_mode"], data["data_source"], data["authentication_method"], data["mock_switch_state"]) != (
                "production", "real-backend", "two-real-accounts", "absent"):
            raise CgspecError("real two-account closure requires production, real backend, two real accounts, and no mock switch")
        if not isinstance(data.get("authorization"), dict):
            raise CgspecError("real two-account closure requires executed authorization configuration")
    app = data.get("app")
    if not isinstance(app, dict) or not all(app.get(key) for key in ("build", "serve", "ready_url")):
        raise CgspecError("parity requires built-app build, serve and readiness setup")
    states = data.get("states")
    if not isinstance(states, list) or not states:
        raise CgspecError("parity requires named states")
    names, signatures = set(), set()
    for state in states:
        if not isinstance(state, dict) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", state.get("name", "")):
            raise CgspecError("invalid parity state name")
        signature = tuple(state.get(key) for key in ("route", "name", "data_set"))
        if state["name"] in names or signature in signatures or not all(isinstance(x, str) and x for x in signature):
            raise CgspecError("parity states need unique route/state/data-set mappings")
        names.add(state["name"]); signatures.add(signature)
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", state.get("screen", "")):
            raise CgspecError(f"{state['name']}: screen mapping is required")
        if not isinstance(state.get("journey"), str) or not isinstance(state.get("baselines"), dict):
            raise CgspecError(f"{state['name']}: journey and named state baselines required")
        for viewport in ("desktop", "mobile"):
            for theme in ("light", "dark"):
                key, entry = f"{viewport}-{theme}", state["baselines"].get(f"{viewport}-{theme}", {})
                if not isinstance(entry, dict) or not entry.get("file") or not HASH.fullmatch(entry.get("sha256", "")):
                    raise CgspecError(f"{state['name']}: missing hash-bound {key} baseline")
                _binding(entry, f"{state['name']} {key} baseline")
    review = data.get("review")
    _binding(review, "independent visual review")
    for key in ("base_revision", "functional_revision", "visual_revision", "content_sha256", "diff_sha256"):
        if not review.get(key):
            raise CgspecError(f"independent visual review requires {key}")
    if review["functional_revision"] != review["visual_revision"] or review["revision"] != review["visual_revision"]:
        raise CgspecError("visual and functional review must bind the same exact revision")
    return data


def gate(view, changes, project):
    changed = ui_paths({p for change in changes for p in (change.path, change.old_path) if p}, project)
    if not changed:
        return []
    try:
        validate(json.loads((view.read_new(MANIFEST) or b"null").decode()), changed)
        return []
    except (UnicodeDecodeError, ValueError, CgspecError) as exc:
        return [f"built-app parity: {exc}"]
