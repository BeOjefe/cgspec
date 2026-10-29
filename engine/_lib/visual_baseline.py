"""Approved visual baseline recording and loading (spec 7 layer 2).

Baselines are stored in docs/prototypes/_baselines/<screen>-v<N>-<viewport>.png,
made read-only, and recorded in docs/_cgspec/07-state/frozen.json with kind 'baseline'.
Write gate, commit gate, and doctor protect frozen baselines against silent overwrite.
Active baselines are tracked in docs/prototypes/_baselines/active.json.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import struct
import subprocess
from pathlib import Path

from . import browser
from .common import STATE_DIR, CgspecError, utc_now, write_json


def baseline_dir(root: Path) -> Path:
    return root / "docs/prototypes/_baselines"


def _check_no_symlinks(root: Path, path: Path) -> None:
    cur = path
    root_res = root.resolve()
    while True:
        if cur.is_symlink():
            raise CgspecError(f"path or ancestor {cur} is a symlink")
        if cur == root or cur.resolve() == root_res or cur == cur.parent:
            break
        cur = cur.parent


def validate_png(path: Path, expected_min_width: int = 1, expected_min_height: int = 1) -> tuple[int, int]:
    if path.is_symlink():
        raise CgspecError(f"{path.name} is a symlink")
    if not path.is_file():
        raise CgspecError(f"{path.name} is missing or not a regular file")
    data = path.read_bytes()
    if len(data) < 33 or not data.startswith(bytes([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])):
        raise CgspecError(f"{path.name} is not a valid PNG (bad signature)")
    if data[12:16] != b"IHDR":
        raise CgspecError(f"{path.name} is not a valid PNG (missing IHDR chunk)")
    width, height = struct.unpack(">II", data[16:24])
    if width < expected_min_width or height < expected_min_height:
        raise CgspecError(f"{path.name} has invalid dimensions ({width}x{height})")
    if b"IEND" not in data[-12:]:
        raise CgspecError(f"{path.name} is truncated or corrupt (missing IEND chunk)")
    return width, height


def resolve_canonical_target(root: Path, screen: str) -> tuple[str, Path]:
    if not screen or not isinstance(screen, str):
        raise CgspecError(f"invalid screen identifier {screen!r}")
    if (screen.startswith("./") or screen.startswith("../") or screen.startswith("/") or
            Path(screen).is_absolute() or ".." in Path(screen).parts or screen.endswith("/")):
        raise CgspecError(f"invalid screen identifier {screen!r}: aliases, absolute paths, and traversal are rejected")
    from visual_audit import targets_of
    items = targets_of(root, [screen])
    if not items:
        raise CgspecError(f"no prototype screen or page named {screen!r}")
    label, path, _ = items[0]
    return label, path


def resolve_canonical_label(root: Path, screen: str) -> str:
    label, _ = resolve_canonical_target(root, screen)
    return label


def next_baseline_version(root: Path, label: str, state: str = "default") -> int:
    base = baseline_dir(root)
    prefix = label if state == "default" else f"{label}-{state}"
    versions = []
    if base.is_dir():
        for p in base.glob(f"{prefix}-v*-*.png"):
            m = re.fullmatch(rf"{re.escape(prefix)}-v(\d+)-(desktop|mobile)(?:-dark)?\.png", p.name)
            if m:
                versions.append(int(m.group(1)))
    frozen_path = root / STATE_DIR / "frozen.json"
    if frozen_path.is_file():
        try:
            frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
            for entry in frozen.get("entries", []):
                p = entry.get("path", "")
                m = re.search(rf"{re.escape(prefix)}-v(\d+)-(desktop|mobile)(?:-dark)?\.png$", p)
                if m:
                    versions.append(int(m.group(1)))
        except (OSError, ValueError):
            pass
    return max(versions, default=0) + 1


def load_active(root: Path) -> dict:
    active_path = baseline_dir(root) / "active.json"
    if not active_path.is_file():
        return {"schema": 1, "screens": {}}
    if active_path.is_symlink():
        raise CgspecError(f"active baselines file {active_path} is a symlink")
    try:
        data = json.loads(active_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"schema": 1, "screens": {}}
        return data
    except (OSError, ValueError):
        return {"schema": 1, "screens": {}}


def find_baselines(root: Path, label: str, state: str = "default") -> tuple[dict[str, str], dict[str, bool]]:
    """(baselines_map for driver, has_baselines boolean map)."""
    active = load_active(root)
    screens = active.get("screens", {}) if isinstance(active, dict) else {}
    if label in screens and isinstance(screens[label], dict):
        entry = screens[label]
        states = entry.get("states") if isinstance(entry.get("states"), dict) else {}
        if state in states and isinstance(states[state], dict):
            entry = {vp: states[state].get(f"{vp}-light") for vp in ("desktop", "mobile")}
        driver_map = {}
        has_map = {}
        for vp in ("desktop", "mobile"):
            vp_info = entry.get(vp)
            file_rel = vp_info.get("file") if isinstance(vp_info, dict) else vp_info
            if isinstance(file_rel, str) and file_rel:
                b_path = root / file_rel
                exists = b_path.is_file() and not b_path.is_symlink()
                has_map[vp] = exists
                if exists:
                    driver_map[vp] = str(b_path.resolve())
            else:
                has_map[vp] = False
        return driver_map, has_map

    base = baseline_dir(root)
    driver_map = {}
    has_map = {}
    for vp in ("desktop", "mobile"):
        # Check highest version first: label-v{N}-{vp}.png
        pattern = f"{label}-v*-{vp}.png"
        candidates = sorted(base.glob(pattern), key=lambda p: [int(c) if c.isdigit() else c for c in re.split(r"(\d+)", p.name)]) if base.is_dir() else []
        b_path = candidates[-1] if candidates else base / f"{label}-{vp}.png"
        exists = b_path.is_file() and not b_path.is_symlink()
        has_map[vp] = exists
        if exists:
            driver_map[vp] = str(b_path.resolve())
    return driver_map, has_map


def _revision(root: Path) -> str:
    out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else "no-git"


def _resolve_approval(root: Path, approval: str | None) -> dict:
    approvals_path = root / STATE_DIR / "approvals.json"
    if not approvals_path.is_file():
        raise CgspecError("no approvals.json; approving a baseline requires validated user approval")
    if approvals_path.is_symlink():
        raise CgspecError("approvals.json is a symlink")
    try:
        approvals_data = json.loads(approvals_path.read_text(encoding="utf-8"))
        if not isinstance(approvals_data, dict):
            raise CgspecError("approvals.json is malformed")
    except (OSError, ValueError) as exc:
        raise CgspecError(f"approvals.json is malformed or unreadable: {exc}")
    approvals_list = approvals_data.get("approvals", [])
    if not approvals_list or not isinstance(approvals_list, list):
        raise CgspecError("no approvals found in approvals.json")
    if approval:
        entry = next((a for a in approvals_list if isinstance(a, dict) and a.get("id") == approval), None)
        if not entry:
            raise CgspecError(f"approval {approval} is not in 07-state/approvals.json")
        return entry
    entry = approvals_list[-1]
    chosen = entry.get("id") if isinstance(entry, dict) else None
    if not chosen:
        raise CgspecError("latest approval in approvals.json has no id")
    return entry


def _load_and_validate_frozen(root: Path) -> tuple[Path, dict]:
    frozen_path = root / STATE_DIR / "frozen.json"
    if not frozen_path.is_file():
        return frozen_path, {"schema": 1, "entries": []}
    if frozen_path.is_symlink():
        raise CgspecError("frozen.json is a symlink")
    try:
        frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CgspecError(f"existing 07-state/frozen.json is malformed: {exc}")
    if not isinstance(frozen, dict) or frozen.get("schema") != 1 or not isinstance(frozen.get("entries"), list):
        raise CgspecError("existing 07-state/frozen.json is schema-invalid")
    for e in frozen["entries"]:
        if not isinstance(e, dict) or not all(k in e for k in ("path", "sha256", "kind", "added", "reason")):
            raise CgspecError("existing 07-state/frozen.json has schema-invalid entry")
    return frozen_path, frozen


def _capture_fresh_screenshots(root: Path, label: str, page_path: Path, screen: str, b_dir: Path,
                               steps: list[dict] | None = None) -> dict[str, Path]:
    shots = root / ".cgspec-scratch/visual"
    shots.mkdir(parents=True, exist_ok=True)
    _check_no_symlinks(root, shots)
    _check_no_symlinks(root, b_dir)
    for existing in b_dir.glob("*.png"):
        if existing.is_symlink():
            raise CgspecError(f"baseline storage contains a symlink: {existing.name}")
    b_dir_res = b_dir.resolve()
    state_res = (root / STATE_DIR).resolve()
    if shots.resolve() in (b_dir_res, state_res) or shots.resolve().is_relative_to(b_dir_res) or shots.resolve().is_relative_to(state_res):
        raise CgspecError("scratch directory resolves into baseline storage or state")
    for vp in ("desktop", "mobile"):
        for suffix in (".png", "-dark.png", "-diff.png"):
            p = shots / f"{label}-{vp}{suffix}"
            if p.is_symlink():
                raise CgspecError(f"scratch screenshot is a symlink: {p.name}")
            if p.is_file():
                if suffix == ".png":
                    validate_png(p)
                p.unlink()
    from visual_audit import _prepare_runs
    runs, _ = _prepare_runs(root, [(label, page_path, [screen])], video=False)
    runs[0]["steps"] = steps or []
    driver_out = browser.run(root, runs, shots, video=False)
    if not isinstance(driver_out, dict):
        raise CgspecError("browser driver gave no result object")
    if driver_out.get("blocked"):
        raise CgspecError(f"browser unavailable at approval time: {driver_out['blocked']}")
    reported = browser.results_by_label(driver_out)
    problems = browser.proof_problems(runs[0], reported.get(label), shots)
    if problems:
        raise CgspecError(f"browser capture proof failed for {label}: {'; '.join(problems)}")
    captured = {f"{vp}-{theme}": shots / f"{label}-{vp}{'-dark' if theme == 'dark' else ''}.png"
                for vp in ("desktop", "mobile") for theme in ("light", "dark")}
    for shot in captured.values():
        if shot.is_symlink() or shot.resolve() in (b_dir_res, state_res) or shot.resolve().is_relative_to(b_dir_res) or shot.resolve().is_relative_to(state_res):
            raise CgspecError(f"screenshot {shot} is a symlink or resolves into baseline storage")
        validate_png(shot)
    return captured


def _write_baseline_files(root: Path, label: str, state: str, version: int, shots: dict[str, Path],
                           b_dir: Path, reason: str, rev: str, approval: dict, reviewer: str, frozen: dict):
    b_dir_res = b_dir.resolve()
    saved, hashes, rels = [], {}, {}
    prefix = label if state == "default" else f"{label}-{state}"
    approved_at = utc_now()
    chosen = approval["id"]
    for key, shot in shots.items():
        vp, theme = key.split("-", 1)
        rel = f"docs/prototypes/_baselines/{prefix}-v{version}-{vp}{'-dark' if theme == 'dark' else ''}.png"
        rels[key] = rel
        dest = root / rel
        if dest.is_symlink() or (dest.resolve().parent != b_dir_res and not dest.resolve().is_relative_to(b_dir_res)):
            raise CgspecError(f"destination {dest} is a symlink or resolves outside baseline directory")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(dest, flags, 0o444)
        except OSError as exc:
            raise CgspecError(f"failed to create baseline file {dest}: {exc}")
        data = shot.read_bytes()
        try:
            os.write(fd, data)
        finally:
            os.close(fd)
        os.chmod(dest, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        digest = hashlib.sha256(data).hexdigest()
        hashes[key] = digest
        frozen.setdefault("entries", []).append({
            "path": rel, "sha256": digest, "kind": "baseline", "added": utc_now(),
            "reason": reason or f"approved visual baseline for {label} state {state} v{version} ({vp}/{theme}); rev {rev}; approval {chosen}"
        })
        saved.append(dest)
    binding = {"approval": chosen, "approval_sha256": approval["sha256"], "reviewer": reviewer,
               "approved_at": approved_at, "revision": rev, "state": state}
    return saved, hashes, rels, binding


def _state_steps(root: Path, journey: str | None, screenshot: str | None) -> list[dict]:
    if not journey:
        return []
    path = (root / journey).resolve()
    if root.resolve() not in path.parents or path.is_symlink() or not path.is_file():
        raise CgspecError("baseline journey must be a regular project file")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CgspecError(f"baseline journey is invalid: {exc}") from exc
    steps = data.get("steps") if isinstance(data, dict) else None
    if not isinstance(steps, list) or not steps:
        raise CgspecError("baseline journey has no steps")
    if not screenshot:
        return steps
    for index, step in enumerate(steps):
        if isinstance(step, dict) and step.get("screenshot") == screenshot:
            return steps[:index + 1]
    raise CgspecError(f"baseline journey has no screenshot {screenshot!r}")


def approve_baseline(root: Path, screen: str, reason: str = "", approval: str | None = None,
                     state: str = "default", reviewer: str = "user", journey: str | None = None,
                     screenshot: str | None = None) -> list[Path]:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", state):
        raise CgspecError("baseline state must be a safe identifier")
    if not reviewer.strip():
        raise CgspecError("baseline approval requires reviewer identity")
    label, page_path = resolve_canonical_target(root, screen)
    chosen = _resolve_approval(root, approval)
    frozen_path, frozen = _load_and_validate_frozen(root)
    b_dir = baseline_dir(root)
    b_dir.mkdir(parents=True, exist_ok=True)
    shots = _capture_fresh_screenshots(root, label, page_path, screen, b_dir,
                                       _state_steps(root, journey, screenshot))
    version = next_baseline_version(root, label, state)
    rev = _revision(root)
    saved, hashes, rels, binding = _write_baseline_files(
        root, label, state, version, shots, b_dir, reason, rev, chosen, reviewer, frozen)
    write_json(frozen_path, frozen)
    active = load_active(root)
    screen_entry = active.setdefault("screens", {}).setdefault(label, {})
    state_entry = {"version": version}
    for key in rels:
        state_entry[key] = {"file": rels[key], "sha256": hashes[key], **binding}
    screen_entry.setdefault("states", {})[state] = state_entry
    if state == "default":
        screen_entry.update({"version": version, "approval": binding["approval"], "revision": rev,
                             "desktop": state_entry["desktop-light"], "mobile": state_entry["mobile-light"],
                             "approved_at": binding["approved_at"]})
    write_json(b_dir / "active.json", active)
    try:
        import memlog
        memlog.main(["--root", str(root), "add", "--summary", f"Visual baseline approved for {label} {state} v{version}",
                     "--tags", "visual,baseline", "--details", f"{', '.join(rels.values())}; approval {chosen['id']}"])
    except Exception:
        pass
    print(f"approved baseline for {label} state {state} v{version} in docs/prototypes/_baselines/ and recorded in 07-state/frozen.json")
    return saved
