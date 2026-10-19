"""Quality measurements from a rendered page (spec 7 layer 2): contrast, focus, type scale, spacing grid
and accent hues. Contrast and focus are errors; the rest are warnings judged against the project's
token sheet when one exists (layer 5b), otherwise against plain limits."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

SKIP = {".git", "node_modules", ".cgspec-scratch", "dist", "build", ".next"}
MAX_SIZES = 6
GRID_SHARE = 0.8
MAX_HUES = 3


def find_tokens(root: Path) -> dict:
    """{'sizes': [px...], 'unit': px} from the first DTCG token sheet found, or {}."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP]
        for name in filenames:
            if re.fullmatch(r"(design-)?tokens(\.[\w-]+)?\.json", name) and "template" not in name:
                try:
                    data = json.loads((Path(dirpath) / name).read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                sizes = _px_values(((data.get("font") or {}).get("size")) or {})
                unit = _px(((data.get("space") or {}).get("unit") or {}).get("$value"))
                if sizes or unit:
                    return {"sizes": sizes, "unit": unit, "path": str((Path(dirpath) / name).relative_to(root))}
    return {}


def _px(value) -> float | None:
    if isinstance(value, dict):  # DTCG 2025 dimension object
        value = f"{value.get('value')}{value.get('unit', 'px')}"
    match = re.fullmatch(r"\s*([\d.]+)\s*(px|rem)?\s*", str(value or ""))
    if not match:
        return None
    return float(match.group(1)) * (16 if match.group(2) == "rem" else 1)


def _px_values(group: dict) -> list[float]:
    out = []
    for key, item in group.items():
        if not key.startswith("$") and isinstance(item, dict) and _px(item.get("$value")) is not None:
            out.append(_px(item["$value"]))
    return sorted(set(out))


def analyse(viewport: dict, tokens: dict) -> tuple[list[str], list[str]]:
    q, name = viewport.get("quality") or {}, viewport["viewport"]
    errors, warnings = [], []
    if q.get("contrastFailCount"):
        worst = ", ".join(f"'{f['text']}' {f['ratio']}:1 (needs {f['need']})" for f in q["contrastFails"][:4])
        errors.append(f"E-CONTRAST ({name}): {q['contrastFailCount']} text elements below WCAG AA: {worst}")
    focus = q.get("focus") or {}
    if focus.get("missing"):
        errors.append(f"E-FOCUS ({name}): no visible focus style on {', '.join(focus['missing'])}")
    sizes = sorted(float(s) for s in (q.get("sizes") or {}))
    if tokens.get("sizes"):
        off = [s for s in sizes if not any(abs(s - t) < 0.6 for t in tokens["sizes"])]
        if off:
            warnings.append(f"W-TYPE-SCALE ({name}): sizes {off} are not in the token scale {tokens['sizes']}")
    elif len(sizes) > MAX_SIZES:
        warnings.append(f"W-TYPE-SCALE ({name}): {len(sizes)} different font sizes {sizes}; a scale needs about {MAX_SIZES}")
    spacing = {int(k): v for k, v in (q.get("spacing") or {}).items()}
    unit = tokens.get("unit") or 4
    total = sum(spacing.values())
    on_grid = sum(v for k, v in spacing.items() if k % unit == 0 or k <= 1)
    if total >= 10 and on_grid / total < GRID_SHARE:
        strays = sorted(k for k in spacing if k % unit and k > 1)[:8]
        warnings.append(f"W-SPACING ({name}): {round(100 * on_grid / total)}% of spacing on the {unit:g}px grid; "
                        f"strays {strays}")
    hues = q.get("hues") or {}
    if len(hues) > MAX_HUES:
        warnings.append(f"W-ACCENTS ({name}): {len(hues)} saturated hue families in use (bins {sorted(int(h) for h in hues)}); "
                        "one accent plus status colours is the target")
    return errors, warnings


def deliberate(root: Path) -> set[str]:
    """Generic-look tells the register records as deliberate choices."""
    path = root / "docs/spines/03-EXPERIENCE.md"
    try:
        text = path.read_text(encoding="utf-8").lower()
    except OSError:
        return set()
    match = re.search(r"deliberate choices\s*:\s*(.+)", text)
    if not match or re.match(r"\s*(none|-|n/a)\b", match.group(1)):
        return set()
    line = match.group(1)
    keys = {"purple": "purple", "violet": "purple", "indigo": "purple", "gradient text": "gradient-text",
            "glow": "glow", "hero": "hero-cards", "three cards": "hero-cards", "cream": "cream-serif", "serif": "cream-serif"}
    return {tell for word, tell in keys.items() if word in line}
