#!/usr/bin/env python3
"""
CGSpec Visual & Structural Wireframe Auditor (visual_audit.py)
Enforces the gstack / BMAD Closed-Loop Visual Self-Critique invariants on HTML wireframes and prototypes:
1. Non-destructive versioning check (must be versioned: *-v1.html, *-v2.html, prototype-v0.1.html).
2. Full-bleed viewport utilization check (100vh / 100% flex root, zero artificial max-height voids).
3. Duplicate control / button label detector (prevents stacked 'Back to Document' headers or duplicate 'Inspector' toggles).
4. Optional headless browser screenshot capture (--screenshot) at desktop (1440x900) and mobile (375x812) viewports.
"""
import argparse
import html.parser
import pathlib
import re
import shutil
import subprocess
import sys
from collections import Counter


class ControlExtractor(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.active_tag = None
        self.current_text = []
        self.current_onclick = None
        self.current_class = ""
        self.buttons = []
        self.visible_buttons = []
        self.labels_and_headings = []
        self.onclicks = []

    def handle_starttag(self, tag, attrs):
        if tag in ("button", "a", "label", "h1", "h2", "h3", "h4", "th"):
            self.active_tag = tag
            self.current_text = []
            attr_dict = dict(attrs)
            self.current_onclick = attr_dict.get("onclick")
            self.current_class = attr_dict.get("class", "")

    def handle_endtag(self, tag):
        if tag == self.active_tag:
            text = " ".join("".join(self.current_text).split()).strip()
            if tag in ("button", "a"):
                if text:
                    self.buttons.append(text)
                    if "hidden" not in self.current_class.split():
                        self.visible_buttons.append(text)
                if self.current_onclick:
                    self.onclicks.append((self.current_onclick.strip(), text or "<icon-button>"))
            elif tag in ("label", "h1", "h2", "h3", "h4", "th") and text:
                self.labels_and_headings.append((tag, text))
            self.active_tag = None
            self.current_onclick = None
            self.current_class = ""

    def handle_data(self, data):
        if self.active_tag:
            self.current_text.append(data)


def audit_html(html_path: pathlib.Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not html_path.exists():
        return [f"File not found: {html_path}"], []

    # 1. Check versioned filename invariant
    name = html_path.name
    if not re.search(r"(-v\d+(\.\d+)?|ADR-\d+)\.html$", name) and name != "prototype.html":
        warnings.append(
            f"Filename '{name}' does not carry an explicit hyphenated version suffix (e.g. wireframe-v1.html, wireframe-v2.html, prototype-v0.1.html). Never overwrite iterations in place."
        )

    content = html_path.read_text(encoding="utf-8", errors="replace")

    # 2. Check full-bleed viewport CSS (prevent 40% bottom white void in Artifact iframe & browser)
    has_full_height = ("100vh" in content or "h-screen" in content)
    has_html_height = bool(re.search(r"html\s*,\s*body\s*\{[^}]*height:\s*100%", content)) or "h-full" in content
    if not has_full_height or not has_html_height:
        errors.append(
            "Missing full-bleed root CSS ('html, body { height: 100%; min-height: 100vh; }'). In Artifact iframes, styling only 'body' leaves a 40% white void at the bottom."
        )

    # Check for fixed short container heights that trap desktop layouts inside a small box
    short_height_matches = re.findall(r"\bh-\[(?:[3456]\d\d)px\]", content)
    if short_height_matches:
        warnings.append(
            f"Found fixed pixel height class(es) {set(short_height_matches)}. Ensure the root workspace uses 'flex-1 min-h-0' instead of fixed short heights that leave dead space."
        )

    # 3. Check for draggable split resizers in multi-column desktop wireframes
    if ("aside" in content or "left-rail" in content or "right-inspector" in content) and "col-resize" not in content:
        errors.append(
            "Multi-column layout detected without draggable split-pane resizers ('cursor: col-resize' / 'cursor-col-resize'). Static sidebars truncate labels and block human resize reflexes."
        )

    # 4. Check for duplicate buttons / stacked action headers / duplicate onclick triggers
    parser = ControlExtractor()
    parser.feed(content)
    normalized_labels = []
    for btn in parser.buttons:
        norm = re.sub(r"\s*\([^)]*\)", "", btn).replace("←", "").replace("<-", "").strip().lower()
        if len(norm) >= 4:
            normalized_labels.append((norm, btn))

    counts = Counter(norm for norm, _ in normalized_labels)
    for norm, count in counts.items():
        if count > 1 and norm in ("back to document", "inspector", "propose edit", "propose pr", "git sync"):
            raw_examples = [orig for n, orig in normalized_labels if n == norm]
            errors.append(
                f"Duplicate control label (Law of One Control Per Action): '{norm}' appears {count} times ({raw_examples}). Consolidate into a single control."
            )

    onclick_counts = Counter(fn for fn, _ in parser.onclicks if "(" in fn and not fn.startswith(("select", "switch", "set", "openMount")))
    for fn, count in onclick_counts.items():
        if count > 1 and any(k in fn.lower() for k in ("drawer", "diff", "inspector", "back")):
            labels = [lbl for f, lbl in parser.onclicks if f == fn]
            errors.append(
                f"Duplicate action handler (Law of One Control Per Action): onclick='{fn}' is wired to {count} separate buttons {labels}. Keep only one canonical trigger."
            )

    # 5. Check for Schema Identifier Leakage (Law 7: snake_case / UPPER_SNAKE_CASE in UI labels & headings)
    leaked_identifiers = []
    for tag, text in parser.labels_and_headings:
        # Look for snake_case or UPPER_SNAKE_CASE tokens inside form labels and headings
        matches = re.findall(r"\b(?:[a-z]{2,}_[a-z0-9_]+|[A-Z]{2,}_[A-Z0-9_]+)\b", text)
        for m in matches:
            leaked_identifiers.append(f"<{tag}> '{text}' -> '{m}'")
    upper_enum_matches = re.findall(r">\s*([A-Z]{3,}_[A-Z0-9_]+)\s*<", content)
    for m in set(upper_enum_matches):
        leaked_identifiers.append(f"enum badge '{m}'")
    if leaked_identifiers:
        errors.append(
            f"Schema Identifier Leakage in Human UI (Law 7): Found raw snake_case / UPPER_SNAKE_CASE database identifiers in user-facing labels or badges: {leaked_identifiers[:6]}. Use natural human language ('Branch' instead of 'git_branch', 'Pending Merge' instead of 'APPROVED_PENDING_GIT')."
        )

    # 6. Check for Capability-Driven UI Hiding violations (Law 8: simultaneous Edit + Propose Edit or 'Your Access:' debug badge)
    vis_lower = [re.sub(r"[^a-z ]", "", b.lower()).strip() for b in parser.visible_buttons]
    if "edit" in vis_lower and ("propose edit" in vis_lower or "propose change" in vis_lower):
        errors.append(
            "Capability-Driven UI Violation (Law 8): Both 'Edit' and 'Propose Edit' buttons are visible simultaneously. Show only the single action matching the active user's role (hide controls the user cannot use)."
        )
    if "your access:" in content.lower():
        errors.append(
            "Capability-Driven UI Violation (Law 8): Found noisy 'Your Access: ...' debug badge in the UI. Instead of telling the user their role in a badge, simply hide actions they lack permission to touch (Dokploy / Linear pattern)."
        )

    return errors, warnings


def capture_screenshot(html_path: pathlib.Path, out_dir: pathlib.Path) -> list[pathlib.Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    captured: list[pathlib.Path] = []
    browser = (
        shutil.which("chromium")
        or shutil.which("chromium-browser")
        or shutil.which("google-chrome")
        or shutil.which("google-chrome-stable")
    )
    if not browser:
        print("  [INFO] No local headless Chromium binary found on PATH; use chrome-devtools-mcp for live capture.")
        return captured

    url = f"file://{html_path.resolve()}"
    for label, size in [("desktop-1440x900", "1440,900"), ("compact-375x812", "375,812")]:
        out_png = out_dir / f"{html_path.stem}-{label}.png"
        cmd = [
            browser,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            f"--window-size={size}",
            f"--screenshot={out_png}",
            url,
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20)
        if res.returncode == 0 and out_png.exists():
            captured.append(out_png)
    return captured


def main() -> int:
    ap = argparse.ArgumentParser(description="CGSpec Visual & Structural Wireframe Auditor")
    ap.add_argument("html_file", help="Path to the HTML wireframe or prototype file")
    ap.add_argument("--screenshot-dir", help="Optional directory to save headless browser screenshots", default=None)
    args = ap.parse_args()

    target = pathlib.Path(args.html_file).resolve()
    print(f"CGSpec Visual Auditor: Inspecting {target}")
    print("-" * 60)

    errors, warnings = audit_html(target)

    for w in warnings:
        print(f"  [WARN] {w}")
    for e in errors:
        print(f"  [FAIL] {e}")

    if not errors and not warnings:
        print("  [PASS] Static DOM & Viewport Invariants: 0 duplicate controls, full-bleed viewport, versioned filename.")

    if args.screenshot_dir:
        shots = capture_screenshot(target, pathlib.Path(args.screenshot_dir))
        for s in shots:
            print(f"  [SHOT] Captured screenshot: {s} (Inspect via view_file before showing user!)")

    print("-" * 60)
    if errors:
        print(f"FAILED: {len(errors)} structural UI error(s) detected. Fix before presenting to the user.")
        return 1
    print("SUCCESS: Wireframe passed static structural checks. Remember to inspect screenshots via view_file.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
