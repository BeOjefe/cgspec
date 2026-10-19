"""Write one evidence record (FORMATS: 06-evidence/<scope>/<name>.json)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .common import EVIDENCE_DIR, utc_now, write_json


def revision(root: Path) -> str:
    out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root, capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else "working-tree"


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "unnamed"


def write(root: Path, scope: str, name: str, check: str, verdict: str, covers: list[str], details: str,
          ran_by: str) -> Path:
    path = root / EVIDENCE_DIR / scope / f"{name}.json"
    write_json(path, {"schema": 1, "check": check, "revision": revision(root), "verdict": verdict, "state": "Fresh",
                      "covers": covers, "details": details[:4000], "ran_at": utc_now(), "ran_by": ran_by})
    return path
