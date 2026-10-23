#!/usr/bin/env python3
"""visual_audit.py: audit prototype screens and built pages (spec 6, 7 layer 2).

Static checks always run: controls that do nothing, references to IDs that do not exist,
duplicate IDs, images without alt text, controls without an accessible name, emojis, missing
viewport, controls without a test ID, and the generic-look tells (RES-004) as warnings.
Rendered checks run when the project's Playwright can start Chromium: page errors, horizontal
overflow on mobile, text contrast (WCAG AA) and visible keyboard focus as errors; small touch targets,
font sizes outside the token scale, spacing off the base grid and too many accent hues as warnings;
desktop/mobile screenshots in .cgspec-scratch/visual/ for the critique rubric.
Exit 0 PASS, 1 FAIL, 2 PARTIAL (static checks passed, no browser for rendered checks), 3 internal.
A tell is accepted only when the locked experience register lists its exact ID and reason.
"""

from __future__ import annotations

import argparse
import colorsys
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import browser, evidence, visual_quality  # noqa: E402
from _lib.visual_baseline import approve_baseline, find_baselines  # noqa: E402
from _lib.common import EXIT_FAIL, EXIT_INTERNAL, EXIT_OK, PROJECT_FILE, STATE_DIR, CgspecError, resolve_root, utc_now, write_json
import hashlib
import shutil
import os
import stat  # noqa: E402
from _lib.gates import EMOJI  # noqa: E402
from _lib.layout import GUI_PROFILES  # noqa: E402

EXIT_PARTIAL = 2
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
REF_ATTRS = ("for", "list", "form", "aria-controls", "aria-labelledby", "aria-describedby", "aria-owns")
HANDLER_ATTRS = ("onclick", "onmousedown", "onpointerdown", "ontouchstart", "onkeydown", "onchange", "oninput")
COLOR = re.compile(r"#([0-9a-f]{6}|[0-9a-f]{3})\b|rgba?\(\s*(\d+)[\s,]+(\d+)[\s,]+(\d+)|hsla?\(\s*(\d+)", re.I)


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.elements: list[dict] = []
        self.stack: list[int] = []
        self.scripts: list[str] = []
        self.styles: list[str] = []
        self.links: list[tuple[str, str]] = []  # (kind, local ref)
        self._raw: str | None = None

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        el = {"tag": tag, "attrs": a, "text": "", "parent": self.stack[-1] if self.stack else None, "cards": 0,
              "form": any(self.elements[i]["tag"] == "form" for i in self.stack)}
        if el["parent"] is not None and "card" in a.get("class", "").lower():
            self.elements[el["parent"]]["cards"] += 1
        self.elements.append(el)
        if tag == "script" and a.get("src"):
            self.links.append(("script", a["src"]))
        if tag == "link" and "stylesheet" in a.get("rel", "").lower() and a.get("href"):
            self.links.append(("style", a["href"]))
        if "style" in a:
            self.styles.append(a["style"])
        if tag in ("script", "style") and not a.get("src"):
            self._raw = tag
            self._buf = []
        if tag not in VOID:
            self.stack.append(len(self.elements) - 1)

    def handle_endtag(self, tag):
        if self._raw == tag:
            (self.scripts if tag == "script" else self.styles).append("".join(self._buf))
            self._raw = None
        for depth in range(len(self.stack) - 1, -1, -1):
            if self.elements[self.stack[depth]]["tag"] == tag:
                del self.stack[depth:]
                break

    def handle_data(self, data):
        if self._raw:
            self._buf.append(data)
            return
        for i in self.stack:
            self.elements[i]["text"] += data


def _local_text(here: Path, refs: list[str]) -> str:
    out = []
    for ref in refs:
        if re.match(r"^(?:[a-z][a-z0-9+.-]*:|//)", ref, re.I):
            continue
        path = here / ref.split("?", 1)[0].split("#", 1)[0]
        if path.is_file():
            out.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(out)


def _label(el: dict) -> str:
    a = el["attrs"]
    name = " ".join(el["text"].split())[:40] or a.get("aria-label") or a.get("title") or a.get("data-testid") or ""
    return f"<{el['tag']}{' ' + repr(name) if name else ''}>"


def _wired(el: dict, script: str) -> bool:
    a = el["attrs"]
    if any(a.get(h) for h in HANDLER_ATTRS) or "disabled" in a:
        return True
    if el["tag"] == "a":
        href = a.get("href", "").strip()
        return bool(href) and href != "#" and not href.lower().startswith("javascript:")
    if el["tag"] == "button" and el["form"] and a.get("type", "submit").lower() in ("submit", "reset"):
        return True
    if a.get("data-action") and re.search(r"data-action|dataset\.action", script):
        return True
    keys = [a.get("id"), a.get("data-testid"), a.get("data-action"), a.get("name")]
    keys += [c for c in a.get("class", "").split() if len(c) > 2]
    return any(k and re.search(rf"""["'`#.\[=]{re.escape(k)}["'`\]\s)]""", script) for k in keys)


def _hsl(match) -> tuple[float, float, float] | None:
    if match.group(1):
        h = match.group(1)
        h = "".join(c * 2 for c in h) if len(h) == 3 else h
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    elif match.group(2):
        r, g, b = (min(int(match.group(i)), 255) / 255 for i in (2, 3, 4))
    else:
        return None  # hsl() hue alone is enough for purple only; skip to avoid guessing
    hue, light, sat = colorsys.rgb_to_hls(r, g, b)
    return hue * 360, sat, light


def tells(css: str, page: Page, accepted: set[str] | None = None) -> list[str]:
    allowed = accepted or set()
    found = []
    colors = [c for c in (_hsl(m) for m in COLOR.finditer(css)) if c]
    if "purple" not in allowed and any(255 <= h <= 295 and s >= 0.35 and 0.2 <= l <= 0.8 for h, s, l in colors):
        found.append("W-LOOK-PURPLE: purple accent; a common AI default unless the brand asked for it")
    if "gradient-text" not in allowed and re.search(r"background-clip\s*:\s*text", css, re.I) and "gradient(" in css:
        found.append("W-LOOK-GRADIENT-TEXT: gradient-filled text")
    if "glow" not in allowed and any(int(n) >= 15 for n in re.findall(
            r"(?:box|text)-shadow\s*:[^;]*?\b0(?:px)?\s+0(?:px)?\s+(\d+)px", css, re.I)):
        found.append("W-LOOK-GLOW: neon glow shadows")
    hero = any("hero" in (el["attrs"].get("class", "") + el["attrs"].get("id", "")).lower() for el in page.elements)
    if "hero-cards" not in allowed and hero and any(el["cards"] == 3 for el in page.elements):
        found.append("W-LOOK-HERO-CARDS: centered hero followed by three cards")
    cream = any(25 <= h <= 60 and s >= 0.2 and l >= 0.88 for h, s, l in colors)
    serif = re.search(r"font-family\s*:[^;]*\bserif\b", re.sub(r"sans-serif", "", css, flags=re.I), re.I)
    if "cream-serif" not in allowed and cream and serif:
        found.append("W-LOOK-CREAM-SERIF: cream background with serif type, the 'tasteful default'")
    return found


def static_audit(path: Path, profile: str, accepted: set[str] | None = None) -> tuple[list[str], list[str]]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    page = Page()
    page.feed(raw)
    page.close()
    here = path.parent
    script = "\n".join(page.scripts) + "\n" + _local_text(here, [r for k, r in page.links if k == "script"])
    css = "\n".join(page.styles) + "\n" + _local_text(here, [r for k, r in page.links if k == "style"])
    errors, warnings = [], []
    ids = [el["attrs"]["id"] for el in page.elements if el["attrs"].get("id")]
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        errors.append(f"E-DUP-ID: id {dup!r} is used more than once")
    made = re.findall(r"""\.id\s*=\s*["'`]([\w-]+)|\bid=\\?["']([\w-]+)""", script)
    known = set(ids) | {x for pair in made for x in pair if x}
    refs = []
    for el in page.elements:
        a = el["attrs"]
        if el["tag"] == "a" and a.get("href", "").startswith("#") and len(a["href"]) > 1:
            refs.append((a["href"][1:], _label(el)))
        refs += [(r, f"{attr} on {_label(el)}") for attr in REF_ATTRS for r in a.get(attr, "").split()]
    refs += [(m, "script") for m in re.findall(r"""getElementById\(\s*["'`]([\w-]+)["'`]""", script)]
    refs += [(m, "script") for m in re.findall(r"""querySelector(?:All)?\(\s*["'`]#([\w-]+)["'`]""", script)]
    for ref, where in refs:
        if ref not in known:
            errors.append(f"E-PHANTOM-ID: {where} points to id {ref!r}, which does not exist")
    for el in page.elements:
        a, tag = el["attrs"], el["tag"]
        control = tag in ("button", "a") or a.get("role") == "button"
        if control and not _wired(el, script):
            errors.append(f"E-HANDLER: {_label(el)} does nothing (no handler, link, form submit or script reference)")
        if control and not (" ".join(el["text"].split()) or a.get("aria-label") or a.get("aria-labelledby") or a.get("title")):
            errors.append(f"E-NO-NAME: {_label(el)} has no accessible name")
        if tag == "img" and "alt" not in a:
            errors.append(f"E-IMG-ALT: <img src={a.get('src', '')[:40]!r}> has no alt text")
        if (control or tag in ("input", "select", "textarea")) and not a.get("data-testid") and a.get("type") != "hidden":
            warnings.append(f"W-TESTID: {_label(el)} has no data-testid; journeys address controls by test ID")
    for el in page.elements:
        ref = el["attrs"].get("src") or (el["attrs"].get("href") if el["tag"] == "link" else "")
        if ref and not re.match(r"^(?:[a-z][a-z0-9+.-]*:|//|#)", ref, re.I) \
                and not (here / ref.split("?", 1)[0].split("#", 1)[0]).is_file():
            errors.append(f"E-MISSING-FILE: <{el['tag']}> loads {ref!r}, which does not exist")
    for line_no, line in enumerate(raw.splitlines(), 1):
        if EMOJI.search(line):
            errors.append(f"E-EMOJI: line {line_no} uses an emoji; use an inline SVG icon")
    viewport = any(el["tag"] == "meta" and el["attrs"].get("name", "").lower() == "viewport" for el in page.elements)
    if not viewport:
        (errors if profile == "mobile" else warnings).append("viewport meta tag missing; the page will not fit phones")
    if not any(el["tag"] == "html" and el["attrs"].get("lang") for el in page.elements):
        warnings.append("W-LANG: <html> has no lang attribute")
    return errors, warnings + tells(css, page, accepted)


def rendered(item: dict, tokens: dict | None = None, drift_threshold: float = 0.5,
             has_baselines: dict[str, bool] | None = None) -> tuple[list[str], list[str], list[str]]:
    errors, warnings, infos = [], [], []
    has_baselines = has_baselines if has_baselines is not None else {}
    for vp in item.get("viewports", []):
        vp_name = vp.get("viewport", "desktop")
        quality_errors, quality_warnings = visual_quality.analyse(vp, tokens or {})
        errors += quality_errors
        warnings += quality_warnings
        errors += [f"E-RUNTIME ({vp_name}): {e}" for e in vp.get("errors", [])[:5]]
        if vp_name == "mobile" and vp.get("overflow"):
            errors.append(f"E-OVERFLOW: page is {vp['scrollWidth']}px wide on a {vp['width']}px phone screen")
        if vp.get("smallCount"):
            warnings.append(f"W-TOUCH-TARGET: {vp['smallCount']} controls under 44px on mobile: {', '.join(vp['small'])}")

        # Dark mode checks
        if vp.get("darkTheme") is False:
            infos.append("page has no dark theme")
        elif vp.get("darkTheme") is True or vp.get("darkQuality"):
            dark_q = vp.get("darkQuality") or {}
            dark_errors, dark_warns = visual_quality.analyse({"viewport": vp_name, "quality": dark_q}, tokens or {})
            errors += [e.replace(f"({vp_name})", f"({vp_name}) (dark)") for e in dark_errors]
            warnings += [w.replace(f"({vp_name})", f"({vp_name}) (dark)") for w in dark_warns]

        # Drift checks
        baseline_exists = has_baselines.get(vp_name, vp.get("drift") is not None)
        drift = vp.get("drift")
        if baseline_exists and drift:
            if drift.get("differentDimensions"):
                errors.append(f"E-DRIFT ({vp_name}): 100% changed: layout height changed ({drift.get('w1')}x{drift.get('h1')} vs {drift.get('w2')}x{drift.get('h2')})")
            else:
                pct = drift.get("changedPercent", 0.0)
                regions = drift.get("regions", [])
                reg_str = f"in {len(regions)} region{'s' if len(regions) != 1 else ''}: {regions}" if regions else ""
                if pct > drift_threshold:
                    errors.append(f"E-DRIFT ({vp_name}): {pct:.2f}% pixels changed (threshold {drift_threshold}%) {reg_str}".strip())
                elif pct > 0:
                    warnings.append(f"W-DRIFT ({vp_name}): {pct:.2f}% pixels changed {reg_str}".strip())
                else:
                    infos.append(f"({vp_name}): 0% visual drift against baseline")
            if drift.get("diffFile"):
                infos.append(f"diff image in .cgspec-scratch/visual/{drift['diffFile']}")
        elif not baseline_exists:
            infos.append(f"({vp_name}): no approved baseline")

    return errors, warnings, infos


def targets_of(root: Path, raw: list[str]) -> list[tuple[str, Path, list[str]]]:
    """(label, html file, covers)."""
    base = root / "docs/prototypes"
    if not raw:
        raw = [p.name for p in sorted(base.iterdir()) if p.is_dir() and not p.name.startswith("_")] if base.is_dir() else []
    out = []
    for item in raw:
        if evidence.unsafe_name(item):
            raise CgspecError(f"screen or page name {item!r} contains newlines or control characters")
        path = root / item
        if path.is_file():
            out.append((evidence.slug(item), path, [item]))
        elif (base / item / "index.html").is_file():
            out.append((item, base / item / "index.html", [f"docs/prototypes/{item}/**"]))
        else:
            raise CgspecError(f"no page or prototype screen named {item}")
    if not out:
        raise CgspecError("nothing to audit: no prototype screens and no pages given")
    return out


def _prepare_runs(root: Path, items: list[tuple[str, Path, list[str]]], video: bool) -> tuple[list[dict], dict[str, dict[str, bool]]]:
    has_baselines = {}
    runs = []
    for label, path, _ in items:
        b_driver, has_map = find_baselines(root, label)
        has_baselines[label] = has_map
        runs.append({"kind": "audit", "label": label, "url": path.resolve().as_uri(),
                     "video": video, "baselines": b_driver})
    return runs, has_baselines


def audit(root: Path, raw: list[str], write: bool = True, video: bool = False,
          records: list[dict] | None = None) -> tuple[int, list[str]]:
    """(exit code, printed lines). `records` collects one structured {item, verdict, detail} per screen."""
    records = records if records is not None else []
    try:
        project = json.loads((root / PROJECT_FILE).read_text(encoding="utf-8"))
        profile = project.get("profile", "")
    except (OSError, ValueError):
        project, profile = {}, ""
    if profile and profile not in GUI_PROFILES:
        return EXIT_OK, [f"NOT_APPLICABLE: profile {profile} has no user interface"]
    items = targets_of(root, raw)
    accepted = visual_quality.deliberate(root)
    tokens = visual_quality.find_tokens(root, project)
    drift_threshold = float(project.get("visual_drift_threshold", 0.5))
    runs, has_baselines = _prepare_runs(root, items, video)
    results = {label: (*static_audit(path, profile, accepted), []) for label, path, _ in items}
    if tokens.get("issue"):
        for errors, warnings, _ in results.values():
            warnings.append(tokens["issue"])
    shots = root / ".cgspec-scratch/visual"
    shown = browser.run(root, runs, shots, video=video)
    blocked, reported = shown.get("blocked"), browser.results_by_label(shown)
    for run_item in runs if not blocked else []:
        item = reported.get(run_item["label"])
        problems = browser.proof_problems(run_item, item, shots)
        results[run_item["label"]][0].extend(f"E-PROOF: {p}" for p in problems)
        if problems:
            continue
        errs, warns, infos = rendered(item, tokens, drift_threshold, has_baselines.get(run_item["label"], {}))
        results[run_item["label"]][0].extend(errs)
        results[run_item["label"]][1].extend(warns)
        results[run_item["label"]][2].extend(infos)
    rank, lines, seen = {"PASS": EXIT_OK, "PARTIAL": EXIT_PARTIAL, "FAIL": EXIT_FAIL}, [], set()
    for label, path, covers in items:
        errors, warnings, infos = results[label]
        verdict = "FAIL" if errors else ("PARTIAL" if blocked else "PASS")
        seen.add(verdict)
        detail = errors + warnings + infos + ([f"rendered checks not run: {blocked}"] if blocked else
                                      [f"screenshots in .cgspec-scratch/visual/{label}-desktop.png and -mobile.png"])
        lines.append(f"{verdict} {path.relative_to(root).as_posix()}" + "".join("\n  " + d for d in detail))
        records.append({"item": path.relative_to(root).as_posix(), "verdict": verdict, "detail": "\n".join(detail)})
        if write:
            evidence.write(root, "visual", label, f"visual-audit:{label}", verdict, covers, "\n".join(detail),
                           "visual_audit.py")
    worst = next((rank[v] for v in ("FAIL", "PARTIAL", "PASS") if v in seen), EXIT_OK)
    return worst, lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("targets", nargs="*", help="screen names or HTML files (default: every prototype screen)")
    parser.add_argument("--no-evidence", action="store_true")
    parser.add_argument("--video", action="store_true", help="record WebM browser video where rendered audit runs")
    parser.add_argument("--json-out", help="write structured results (one record per screen) to this file")
    parser.add_argument("--approve-baseline", metavar="SCREEN", help="approve current screenshots of SCREEN as baseline")
    parser.add_argument("--reason", default="", help="reason for approved baseline")
    parser.add_argument("--root")
    args = parser.parse_args(argv)
    if args.approve_baseline:
        try:
            approve_baseline(resolve_root(args.root), args.approve_baseline, args.reason)
            return EXIT_OK
        except CgspecError as exc:
            print(f"visual_audit: {exc}", file=sys.stderr)
            return EXIT_FAIL
    records: list[dict] = []
    try:
        code, lines = audit(resolve_root(args.root), args.targets, not args.no_evidence, args.video, records)
        if args.json_out:
            Path(args.json_out).write_text(json.dumps({"schema": 1, "tool": "visual_audit", "records": records},
                                                      indent=2) + "\n", encoding="utf-8")
    except CgspecError as exc:
        print(f"visual_audit: {exc}", file=sys.stderr)
        return EXIT_FAIL
    except Exception as exc:  # report, never crash silently
        print(f"visual_audit: internal error: {exc}", file=sys.stderr)
        return EXIT_INTERNAL
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
