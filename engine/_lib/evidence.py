"""Write one evidence record (FORMATS: 06-evidence/<scope>/<name>.json)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .common import EVIDENCE_DIR, utc_now, write_json


def revision(root: Path) -> str:
    out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root, capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else "working-tree"


# C0/C1 controls (newline included) and Unicode line/paragraph separators. Names reported by journeys and
# audits are printed and rendered into summaries, so a name containing one could forge extra records.
CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f\u2028\u2029]")


def unsafe_name(text: object) -> bool:
    """True when `text` cannot be used as a reported identifier (not a string, empty or has controls)."""
    return not isinstance(text, str) or not text.strip() or bool(CONTROL.search(text))


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "unnamed"


def write(root: Path, scope: str, name: str, check: str, verdict: str, covers: list[str], details: str,
          ran_by: str) -> Path:
    path = root / EVIDENCE_DIR / scope / f"{name}.json"
    write_json(path, {"schema": 1, "check": check, "revision": revision(root), "verdict": verdict, "state": "Fresh",
                      "covers": covers, "details": details[:4000], "ran_at": utc_now(), "ran_by": ran_by})
    return path
