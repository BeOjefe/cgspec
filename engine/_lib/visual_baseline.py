"""Approved visual baseline recording and loading (spec 7 layer 2).

Baselines are stored in docs/prototypes/_baselines/<screen>-<viewport>.png,
made read-only, and recorded in docs/_cgspec/07-state/frozen.json with kind 'baseline'.
Write gate, commit gate, and doctor protect frozen baselines against silent overwrite.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
from pathlib import Path

from .common import STATE_DIR, CgspecError, utc_now, write_json


def baseline_dir(root: Path) -> Path:
    return root / "docs/prototypes/_baselines"


def find_baselines(root: Path, label: str) -> tuple[dict[str, str], dict[str, bool]]:
    """(baselines_map for driver, has_baselines boolean map)."""
    base = baseline_dir(root)
    driver_map = {}
    has_map = {}
    for vp in ("desktop", "mobile"):
        b_path = base / f"{label}-{vp}.png"
        exists = b_path.is_file()
        has_map[vp] = exists
        if exists:
            driver_map[vp] = str(b_path.resolve())
    return driver_map, has_map


def approve_baseline(root: Path, screen: str, reason: str = "") -> list[Path]:
    base = root / "docs/prototypes"
    screen_dir = base / screen
    page_path = root / screen
    if not screen_dir.is_dir() and not page_path.is_file():
        raise CgspecError(f"no prototype screen or page named {screen!r}")

    shots = root / ".cgspec-scratch/visual"
    desktop_shot = shots / f"{screen}-desktop.png"
    mobile_shot = shots / f"{screen}-mobile.png"
    if not (desktop_shot.is_file() and mobile_shot.is_file()):
        from visual_audit import audit
        audit(root, [screen], write=False)
    if not (desktop_shot.is_file() and mobile_shot.is_file()):
        raise CgspecError(f"could not capture screenshots for {screen!r} in .cgspec-scratch/visual/")

    b_dir = baseline_dir(root)
    b_dir.mkdir(parents=True, exist_ok=True)

    frozen_path = root / STATE_DIR / "frozen.json"
    try:
        frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        frozen = {"schema": 1, "entries": []}

    frozen_paths = {e.get("path") for e in frozen.get("entries", [])}
    desktop_rel = f"docs/prototypes/_baselines/{screen}-desktop.png"
    mobile_rel = f"docs/prototypes/_baselines/{screen}-mobile.png"

    if desktop_rel in frozen_paths or mobile_rel in frozen_paths:
        raise CgspecError(f"baseline for {screen!r} is already frozen in 07-state/frozen.json; frozen baselines cannot be overwritten")

    saved = []
    for vp, shot, rel in (("desktop", desktop_shot, desktop_rel), ("mobile", mobile_shot, mobile_rel)):
        dest = root / rel
        shutil.copyfile(shot, dest)
        os.chmod(dest, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        digest = hashlib.sha256(dest.read_bytes()).hexdigest()
        frozen.setdefault("entries", []).append({
            "path": rel,
            "sha256": digest,
            "kind": "baseline",
            "added": utc_now(),
            "reason": reason or f"approved visual baseline for {screen} ({vp})"
        })
        saved.append(dest)

    write_json(frozen_path, frozen)
    try:
        import memlog
        memlog.main(["--root", str(root), "add", "--summary", f"Visual baseline approved for {screen}",
                     "--tags", "visual,baseline", "--details", f"{desktop_rel}, {mobile_rel}"])
    except Exception:
        pass
    print(f"approved baseline for {screen} in docs/prototypes/_baselines/ and recorded in 07-state/frozen.json")
    return saved
