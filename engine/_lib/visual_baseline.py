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


def next_baseline_version(root: Path, label: str) -> int:
    base = baseline_dir(root)
    versions = []
    if base.is_dir():
        for p in base.glob(f"{label}-v*-*.png"):
            m = re.fullmatch(rf"{re.escape(label)}-v(\d+)-(desktop|mobile)\.png", p.name)
            if m:
                versions.append(int(m.group(1)))
    frozen_path = root / STATE_DIR / "frozen.json"
    if frozen_path.is_file():
        try:
            frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
            for entry in frozen.get("entries", []):
                p = entry.get("path", "")
                m = re.search(rf"{re.escape(label)}-v(\d+)-(desktop|mobile)\.png$", p)
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


def find_baselines(root: Path, label: str) -> tuple[dict[str, str], dict[str, bool]]:
    """(baselines_map for driver, has_baselines boolean map)."""
    active = load_active(root)
    screens = active.get("screens", {}) if isinstance(active, dict) else {}
    if label in screens and isinstance(screens[label], dict):
        entry = screens[label]
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
    out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root, capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else "no-git"


def _resolve_approval(root: Path, approval: str | None) -> str:
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
        return approval
    entry = approvals_list[-1]
    chosen = entry.get("id") if isinstance(entry, dict) else None
    if not chosen:
        raise CgspecError("latest approval in approvals.json has no id")
    return chosen


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


def _capture_fresh_screenshots(root: Path, label: str, page_path: Path, screen: str, b_dir: Path) -> tuple[Path, Path]:
    shots = root / ".cgspec-scratch/visual"
    shots.mkdir(parents=True, exist_ok=True)
    _check_no_symlinks(root, b_dir)
    b_dir_res = b_dir.resolve()
    state_res = (root / STATE_DIR).resolve()
    if shots.resolve() in (b_dir_res, state_res) or shots.resolve().is_relative_to(b_dir_res) or shots.resolve().is_relative_to(state_res):
        raise CgspecError("scratch directory resolves into baseline storage or state")
    for vp in ("desktop", "mobile"):
        for suffix in (".png", "-dark.png", "-diff.png"):
            p = shots / f"{label}-{vp}{suffix}"
            if p.is_symlink() or p.is_file():
                p.unlink()
    from visual_audit import _prepare_runs
    runs, _ = _prepare_runs(root, [(label, page_path, [screen])], video=False)
    driver_out = browser.run(root, runs, shots, video=False)
    if not isinstance(driver_out, dict):
        raise CgspecError("browser driver gave no result object")
    if driver_out.get("blocked"):
        raise CgspecError(f"browser unavailable at approval time: {driver_out['blocked']}")
    reported = browser.results_by_label(driver_out)
    problems = browser.proof_problems(runs[0], reported.get(label), shots)
    if problems:
        raise CgspecError(f"browser capture proof failed for {label}: {'; '.join(problems)}")
    desktop_shot, mobile_shot = shots / f"{label}-desktop.png", shots / f"{label}-mobile.png"
    for shot in (desktop_shot, mobile_shot):
        if shot.is_symlink() or shot.resolve() in (b_dir_res, state_res) or shot.resolve().is_relative_to(b_dir_res) or shot.resolve().is_relative_to(state_res):
            raise CgspecError(f"screenshot {shot} is a symlink or resolves into baseline storage")
        validate_png(shot)
    return desktop_shot, mobile_shot


def _write_baseline_files(root: Path, label: str, version: int, shots: tuple[Path, Path],
                          b_dir: Path, reason: str, rev: str, chosen: str, frozen: dict):
    desktop_shot, mobile_shot = shots
    b_dir_res = b_dir.resolve()
    saved, hashes, rels = [], {}, {}
    for vp, shot in (("desktop", desktop_shot), ("mobile", mobile_shot)):
        rel = f"docs/prototypes/_baselines/{label}-v{version}-{vp}.png"
        rels[vp] = rel
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
        hashes[vp] = digest
        frozen.setdefault("entries", []).append({
            "path": rel, "sha256": digest, "kind": "baseline", "added": utc_now(),
            "reason": reason or f"approved visual baseline for {label} v{version} ({vp}); rev {rev}; approval {chosen}"
        })
        saved.append(dest)
    return saved, hashes, rels


def approve_baseline(root: Path, screen: str, reason: str = "", approval: str | None = None) -> list[Path]:
    label, page_path = resolve_canonical_target(root, screen)
    chosen = _resolve_approval(root, approval)
    frozen_path, frozen = _load_and_validate_frozen(root)
    b_dir = baseline_dir(root)
    b_dir.mkdir(parents=True, exist_ok=True)
    shots = _capture_fresh_screenshots(root, label, page_path, screen, b_dir)
    version = next_baseline_version(root, label)
    rev = _revision(root)
    saved, hashes, rels = _write_baseline_files(root, label, version, shots, b_dir, reason, rev, chosen, frozen)
    write_json(frozen_path, frozen)
    active = load_active(root)
    active.setdefault("screens", {})[label] = {
        "version": version, "approval": chosen, "revision": rev,
        "desktop": {"file": rels["desktop"], "sha256": hashes["desktop"]},
        "mobile": {"file": rels["mobile"], "sha256": hashes["mobile"]},
        "approved_at": utc_now(),
    }
    write_json(b_dir / "active.json", active)
    try:
        import memlog
        memlog.main(["--root", str(root), "add", "--summary", f"Visual baseline approved for {label} v{version}",
                     "--tags", "visual,baseline", "--details", f"{rels['desktop']}, {rels['mobile']}; approval {chosen}"])
    except Exception:
        pass
    print(f"approved baseline for {label} v{version} in docs/prototypes/_baselines/ and recorded in 07-state/frozen.json")
    return saved
