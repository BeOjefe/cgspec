"""Quality measurements from a rendered page (spec 7 layer 2): contrast, focus, type scale, spacing grid
and accent hues. Contrast and focus are errors; the rest are warnings judged against the project's
token sheet when one exists (layer 5b), otherwise against plain limits."""

from __future__ import annotations

import json
import re
import colorsys
from pathlib import Path

MAX_SIZES = 5
GRID_SHARE = 0.8
MAX_HUES = 3


def find_tokens(root: Path, project: dict | None = None) -> dict:
    """Read only the project's declared DTCG sheet; never infer a path by walking files."""
    project = project or {}
    declared = project.get("design_tokens") or (project.get("design_system") or {}).get("tokens")
    if not declared:
        return {"issue": "W-TOKENS-UNDECLARED: no project design token sheet declared"}
    rel = Path(str(declared))
    if rel.is_absolute() or ".." in rel.parts:
        return {"issue": f"W-TOKENS-INVALID: unsafe token path {declared!r}"}
    path = root / rel
    try:
        if not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError("path missing or outside the project")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("sheet is not a JSON object")
    except (OSError, ValueError) as exc:
        return {"issue": f"W-TOKENS-INVALID: {declared}: {exc}"}
    sizes = _px_values(((data.get("font") or {}).get("size")) or {})
    unit = _px(((data.get("space") or {}).get("unit") or {}).get("$value"))
    colors = data.get("color") or {}
    hues, unparsed = _color_hues(colors)
    result = {"sizes": sizes, "unit": unit, "path": rel.as_posix()}
    if unparsed:
        result["issue"] = f"W-TOKEN-COLOR-UNPARSED: {len(unparsed)} colour token values cannot be compared to rendered hues"
    elif colors:
        result["hues"] = hues
    return result


def _color_hues(group: dict) -> tuple[set[int], list[str]]:
    bins: set[int] = set()
    unparsed: list[str] = []
    for key, value in group.items():
        if not isinstance(value, dict):
            continue
        if "$value" not in value:
            nested, unknown = _color_hues(value)
            bins.update(nested)
            unparsed.extend(unknown)
            continue
        color = str(value["$value"])
        if re.fullmatch(r"#[0-9a-fA-F]{3}", color):
            color = "#" + "".join(c * 2 for c in color[1:])
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            unparsed.append(key)
            continue
        red, green, blue = (int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
        hue, light, saturation = colorsys.rgb_to_hls(red, green, blue)
        if saturation >= 0.35 and 0.15 <= light <= 0.9:
            bins.add(round(round(hue * 360) / 30) * 30 % 360)
    return bins, unparsed


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
        warnings.append(f"W-TYPE-SCALE ({name}): {len(sizes)} different font sizes {sizes}; use no more than about {MAX_SIZES} on one screen")
    spacing = {int(k): v for k, v in (q.get("spacing") or {}).items()}
    unit = tokens.get("unit") or 4
    total = sum(spacing.values())
    on_grid = sum(v for k, v in spacing.items() if k % unit == 0 or k <= 1)
    if total >= 10 and on_grid / total < GRID_SHARE:
        strays = sorted(k for k in spacing if k % unit and k > 1)[:8]
        warnings.append(f"W-SPACING ({name}): {round(100 * on_grid / total)}% of spacing on the {unit:g}px grid; "
                        f"strays {strays}")
    hues = q.get("hues") or {}
    extra = set(map(int, hues)) - tokens["hues"] if "hues" in tokens else set()
    if extra:
        warnings.append(f"W-ACCENTS ({name}): rendered hue bins {sorted(extra)} are outside the declared token sheet")
    elif "hues" not in tokens and "path" not in tokens and len(hues) > MAX_HUES:
        warnings.append(f"W-ACCENTS ({name}): {len(hues)} saturated hue families in use (bins {sorted(int(h) for h in hues)}); "
                        "one accent plus status colours is the target")
    return errors, warnings


def deliberate(root: Path) -> set[str]:
    """Generic-look tells the register records as deliberate choices."""
    path = root / "docs/spines/03-EXPERIENCE.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return set()
    section = re.search(r"^## Register\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S | re.I)
    if not section or not re.search(r"^Status:\s*Locked(?:\s*\([^\n]*\))?\s*$", section.group(1), re.M | re.I):
        return set()
    match = re.search(r"^\s*- Deliberate choices:\s*([^\n]+)$", section.group(1), re.M | re.I)
    if not match:
        return set()
    items = [item.strip().lower() for item in match.group(1).split(",")]
    allowed = {"purple", "cream-serif", "gradient-text", "glow", "hero-cards"}
    if not items or not all(item in allowed for item in items):
        return set()
    section_text = section.group(1)
    for item in items:
        reason = re.search(rf"^\s*- Deliberate reason {re.escape(item)}:\s*(\S[^\n]*)$",
                           section_text, re.M | re.I)
        if not reason:
            return set()
    return set(items)
