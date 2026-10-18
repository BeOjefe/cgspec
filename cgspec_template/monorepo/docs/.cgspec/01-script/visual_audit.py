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
import hashlib
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

    # 1. Check versioned filename invariant & sibling version SHA-256 clobbering
    name = html_path.name
    if not re.search(r"([-_]v\d+(\.\d+)?|ADR-\d+)\.html$", name) and name != "prototype.html":
        warnings.append(
            f"Filename '{name}' does not carry an explicit version suffix (e.g. wireframe-v1.html, wireframe-v2.html, prototype-v0.1.html). Never overwrite iterations in place."
        )

    raw_bytes = html_path.read_bytes()
    target_sha = hashlib.sha256(raw_bytes).hexdigest()
    clobbered_siblings = []
    for sib in sorted(html_path.parent.glob("*.html")):
        if sib != html_path and re.search(r"[-_]v\d+(\.\d+)?\.html$", sib.name):
            if hashlib.sha256(sib.read_bytes()).hexdigest() == target_sha:
                clobbered_siblings.append(sib.name)
    if clobbered_siblings and ".gemini" not in str(html_path):
        errors.append(
            f"Version History Clobber Violation (Law 6): '{name}' has identical SHA-256 content to sibling version file(s) {clobbered_siblings}. Never copy a newer version over prior v1/v2/v3/v4/v5 files in the repository."
        )

    content = raw_bytes.decode("utf-8", errors="replace")

    # 2. Check HTML Unicode Emoji & Pictograph Ban (Zero decorative emojis; require inline <svg>)
    emoji_pattern = re.compile(
        "["
        "\U0001F300-\U0001F5FF"
        "\U0001F600-\U0001F64F"
        "\U0001F680-\U0001F6FF"
        "\U0001F700-\U0001F77F"
        "\U0001F780-\U0001F7FF"
        "\U0001F800-\U0001F8FF"
        "\U0001F900-\U0001F9FF"
        "\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF"
        "\u2600-\u26FF"
        "\u2700-\u27BF"
        "]"
    )
    found_emojis = sorted(set(emoji_pattern.findall(content)))
    if found_emojis:
        errors.append(
            f"Unicode Emoji Ban Violation: Found {len(found_emojis)} decorative emoji/pictograph character(s) in HTML {found_emojis[:10]}. Use crisp inline Lucide/Feather <svg> icons only."
        )

    # 3. Check full-bleed viewport CSS (prevent 40% bottom white void in Artifact iframe & browser)
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

    # Check for narrow fixed max-width containers that leave dead margins in multi-column desktop layouts
    if ("aside" in content or "left-rail" in content or "<nav" in content):
        narrow_matches = re.findall(r"\bmax-w-(?:[234]xl|md|lg)\b", content)
        if narrow_matches and ("main" in content or "center" in content or "gh-file-box" in content):
            warnings.append(
                f"Found narrow container max-width {set(narrow_matches)}. Fluid Canvas Invariant: primary reading/editing/analytical work surfaces should use fluid/broad containers (e.g. 'w-full flex-1 max-w-7xl') to prevent excessive dead gutters on desktop viewports."
            )

    # 4. Check for draggable split resizers in multi-column desktop wireframes
    if ("aside" in content or "left-rail" in content or "right-inspector" in content) and "col-resize" not in content:
        errors.append(
            "Multi-column layout detected without draggable split-pane resizers ('cursor: col-resize' / 'cursor-col-resize'). Static sidebars truncate labels and block human resize reflexes."
        )

    # 5. Check for duplicate buttons / stacked action headers / text-heavy moving drawer toggles
    parser = ControlExtractor()
    parser.feed(content)
    normalized_labels = []
    for btn in parser.buttons:
        norm = re.sub(r"\s*\([^)]*\)", "", btn).replace("←", "").replace("<-", "").strip().lower()
        if len(norm) >= 4:
            normalized_labels.append((norm, btn))

    counts = Counter(norm for norm, _ in normalized_labels)
    for norm, count in counts.items():
        if count > 1 and norm in ("edit", "back to document", "inspector", "propose edit", "propose pr", "git sync"):
            raw_examples = [orig for n, orig in normalized_labels if n == norm]
            errors.append(
                f"Duplicate control label (Law of One Control Per Action): '{norm}' appears {count} times ({raw_examples}). Consolidate into a single control."
            )

    # Check for bulky text-based drawer toggle buttons ("History & Info") that shift position when clicked
    for norm, orig in normalized_labels:
        if norm in ("history & info", "history and info", "toggle inspector", "open inspector"):
            errors.append(
                f"Moving / Text-Heavy Panel Toggle Violation (Law 2 & Law 4): Found text button '{orig}' for panel toggling. Use a stationary 16x16 <svg> panel-right icon button with a tooltip anchored in the fixed top-right header so the button never shifts under the user's cursor."
            )

    onclick_counts = Counter(fn for fn, _ in parser.onclicks if "(" in fn and not fn.startswith(("select", "switch", "set", "openMount")))
    for fn, count in onclick_counts.items():
        if count > 1 and any(k in fn.lower() for k in ("drawer", "diff", "inspector", "back")):
            labels = [lbl for f, lbl in parser.onclicks if f == fn]
            errors.append(
                f"Duplicate action handler (Law of One Control Per Action): onclick='{fn}' is wired to {count} separate buttons {labels}. Keep only one canonical trigger."
            )

    # 6. Check for Schema Identifier Leakage (Law 7: snake_case / UPPER_SNAKE_CASE in UI labels & headings)
    leaked_identifiers = []
    for tag, text in parser.labels_and_headings:
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

    # 7. Check for Capability-Driven UI Hiding violations (Law 8: simultaneous Edit + Propose Edit or 'Your Access:' debug badge)
    vis_lower = [re.sub(r"[^a-z ]", "", b.lower()).strip() for b in parser.visible_buttons]
    if "edit" in vis_lower and ("propose edit" in vis_lower or "propose change" in vis_lower):
        errors.append(
            "Capability-Driven UI Violation (Law 8): Both 'Edit' and 'Propose Edit' buttons are visible simultaneously. Show only the single action matching the active user's role (hide controls the user cannot use)."
        )
    if "your access:" in content.lower():
        errors.append(
            "Capability-Driven UI Violation (Law 8): Found noisy 'Your Access: ...' debug badge in the UI. Instead of telling the user their role in a badge, simply hide actions they lack permission to touch (Dokploy / Linear pattern)."
        )

    # 8. Check for Split-Brain Dual Breadcrumb / Path Headers (Law 2: Single Header Ownership)
    if "bc-leaf" in content and ("doc-path-header" in content or "code-path-label" in content):
        errors.append(
            "Split-Brain Dual Path Header Violation (Law 2): Found both a top-bar breadcrumb ('bc-leaf') AND a second center-pane path header ('doc-path-header' / 'code-path-label'). Maintain a single canonical breadcrumb header above Center+Right."
        )

    # 9. Check for Meta-Wireframe Coaching / Self-Referential Tutorial Text in UI
    meta_coaching_phrases = [
        "drag the left border of this panel",
        "resize it anytime",
        "every file & folder is live",
        "every file &amp; folder is live",
        "fixed top header & icon-only",
        "fixed top header &amp; icon-only",
    ]
    found_meta = [p for p in meta_coaching_phrases if p in content.lower()]
    if found_meta:
        errors.append(
            f"Meta-Wireframe Coaching Text Violation: Found self-referential wireframe tutorial text in the UI {found_meta}. Never render permanent instructional hints ('Drag border to resize...') or meta-commentary inside the product canvas."
        )

    # 10. Check for Raw Markdown Syntax Leaking in Rendered Preview Headings (static <h1>..<h4> or JS title: '# ...')
    raw_md_headings = []
    for tag, text in parser.labels_and_headings:
        if tag in ("h1", "h2", "h3", "h4") and (text.startswith("# ") or "**" in text):
            raw_md_headings.append(f"<{tag}>{text[:50]}</{tag}>")
    js_md_titles = re.findall(r"title\s*:\s*['\"]#\s+[^'\"]{1,60}['\"]", content)
    for m in js_md_titles:
        raw_md_headings.append(f"JS {m}")
    if raw_md_headings:
        errors.append(
            f"Raw Markdown Syntax in Preview Violation: Found literal '# ' or '**' inside rendered heading(s) {raw_md_headings[:4]}. Preview mode must render clean typography; show raw Markdown syntax only inside the active Edit mode <textarea>."
        )

    # 11. Inline <script> JavaScript Syntax Check (via node --check)
    node_bin = shutil.which("node")
    if node_bin:
        import tempfile
        scripts = re.findall(r"<script(?![^>]*src=)[^>]*>(.*?)</script>", content, re.S | re.I)
        for idx, js_code in enumerate(scripts, 1):
            if not js_code.strip():
                continue
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=True, encoding="utf-8") as tf:
                tf.write(js_code)
                tf.flush()
                res = subprocess.run([node_bin, "--check", tf.name], capture_output=True, text=True, timeout=10)
                if res.returncode != 0:
                    err_snip = " | ".join(res.stderr.strip().splitlines()[:3])
                    errors.append(f"Inline <script> #{idx} JavaScript Syntax Error (node --check): {err_snip}")

    # 12. Check for Naked Cryptographic / Engineering Acronyms in User UI (Law 6: Plain English First, Jargon Second)
    # Flags raw DEK, KEK, MEK, OOUX, DDL displayed in badges, buttons, tooltips, or headings without plain English explanation
    naked_jargon_found = []
    for m in re.finditer(r">\s*(?:DEK|KEK|MEK|OOUX|DDL)\s*<", content):
        naked_jargon_found.append(m.group(0))
    for m in re.finditer(r"<button[^>]*>[^<]*\b(?:DEK|KEK)\b[^<]*</button>", content):
        naked_jargon_found.append(m.group(0).strip())
    if naked_jargon_found:
        errors.append(
            f"Naked Cryptographic Acronym in User UI (Law 6 Violation): Found bare internal key-management jargon in user-facing UI: {naked_jargon_found[:4]}. Use plain human language ('Encrypted Note', 'Private Key', 'Shred Note & Key') instead of unexplained engineering acronyms."
        )

    # 13. Hierarchical Nesting Indentation Check (Law 5: Progressive Container Indentation)
    # Applies ONLY when hierarchical tree structures or nested groups (role="tree", .tree-children, .nested-group) are present
    has_tree = any(k in content for k in ('role="tree"', 'class="tree', 'tree-children', 'dolphin-children', 'nested-group', 'nested-children'))
    if has_tree:
        unindented_trees = re.findall(r'<div[^>]*class="[^"]*(?:tree-children|dolphin-children|nested-children)[^"]*"[^>]*>', content)
        for tag in unindented_trees:
            if not any(k in tag for k in ("pl-", "ml-", "border-l", "padding-left", "margin-left")):
                warnings.append(
                    "Flat Tree Hierarchy (Law 5): Detected nested tree container without visible progressive indentation ('pl-', 'ml-', or 'border-l'). Nested children will appear flush with parent nodes."
                )
                break

    # 14. Check for Phantom DOM Element References in Inline JavaScript (Law of Interactive Integrity)
    # Extracts document.getElementById('...') calls and flags IDs that do not exist anywhere in the HTML DOM
    dom_ids = set(re.findall(r'\bid=["\']([^"\']+)["\']', content))
    phantom_ids = set()
    for sb in re.findall(r"<script(?![^>]*src=)[^>]*>(.*?)</script>", content, re.S | re.I):
        for match in re.finditer(r"document\.getElementById\(\s*['\"]([^'\"]+)['\"]\s*\)", sb):
            target_id = match.group(1)
            # Skip dynamically computed prefix patterns
            if any(target_id.startswith(p) for p in ("label-", "desc-", "file-item-", "status-", "mount-")):
                continue
            if target_id not in dom_ids:
                phantom_ids.add(target_id)
    if phantom_ids:
        errors.append(
            f"Phantom DOM Element Reference Violation (Nielsen H5: Error Prevention): Found document.getElementById() calls for IDs not present in the HTML DOM: {sorted(list(phantom_ids))[:8]}. This causes catastrophic runtime TypeErrors ('Cannot read properties of null') when users interact with the UI. Ensure every referenced ID exists in the HTML or prune dead script logic."
        )

    # 15. Check for AI Slop Gradient Clichés (Anti-Slop Invariant — RES-002 & Hallmark Gate #12)
    # Detects generic AI purple-to-indigo/violet gradients that indicate lazy uncurated prompt defaults
    purple_grad_matches = re.findall(
        r"\bfrom-(?:purple|indigo|violet|fuchsia)-(?:500|600|700)\s+to-(?:indigo|purple|violet|pink|fuchsia)-(?:500|600|700)\b",
        content,
    )
    if purple_grad_matches:
        errors.append(
            f"AI UI Slop Violation (RES-002 / Hallmark Gate #12): Detected generic AI purple/indigo hero gradient {set(purple_grad_matches)}. Use intentional brand color anchors, tonal surface elevation (#09090b -> #121316), or high-trust monochrome styling instead of default AI purple gradients."
        )

    # 16. Check for Disembodied Dark-Mode Box Shadows (Hallmark Gate #18 & Tactile Hairline Invariant)
    # In dark mode, pure CSS drop shadows are muddy or invisible; cards require 1px hairline borders (border-white/10 or border-zinc-800)
    shadow_divs = re.findall(r'<div[^>]*class="([^"]*shadow-(?:2xl|xl)[^"]*)"', content)
    disembodied_cards = []
    for c in shadow_divs:
        # Check if card is dark-themed or inside dark canvas
        is_dark = any(k in c for k in ("bg-zinc-9", "bg-neutral-9", "bg-slate-9", "bg-black", "bg-[#0", "dark:bg-"))
        has_border = any(k in c for k in ("border", "ring-1", "ring-2", "outline"))
        if is_dark and not has_border:
            disembodied_cards.append(c[:60])
    if disembodied_cards:
        warnings.append(
            f"Disembodied Dark Shadow Slop (RES-002 / Hallmark Gate #18): Found {len(disembodied_cards)} dark card(s) using shadow-xl/2xl without a 1px hairline border: {disembodied_cards[:2]}. In dark mode, pure CSS shadows appear muddy; pair with 'border border-white/10' or 'border border-zinc-800' for crisp tactile elevation."
        )

    # 17. Check for Multi-State Architecture Support (Puck Constrained Generative UI Invariant)
    # Production-ready UI cannot be a happy-path-only static mockup; must support state branching (empty, skeleton/loading, error)
    has_state_architecture = any(
        k in content
        for k in (
            "st ===",
            "state ===",
            "data-state",
            "?state=",
            "switchState",
            "setState",
            "state-switcher",
            "state-selector",
            "skeleton",
            "empty-state",
        )
    )
    if not has_state_architecture:
        warnings.append(
            "Monolithic Happy-Path Viewport (RES-002 / Puck Model): No interactive state branching detected (missing '?state=', 'data-state', skeleton, or empty state). Production interfaces must handle loading skeletons, empty collections, and error states deterministically."
        )

    # 18. Check for Typographic Alignment on Critical Metrics (Tactile Monospace / Tabular Numerals)
    # Metrics with latencies (ms, kb, tokens) should use tabular numerals or monospace to prevent jitter
    has_metrics = bool(re.search(r">\s*\d+(?:\.\d+)?\s*(?:ms|tokens|kb|mb|req/s|%)\s*<", content, re.I))
    has_tabular = "tabular-nums" in content or "font-mono" in content
    if has_metrics and not has_tabular:
        warnings.append(
            "Jittering Technical Metrics (RES-002 / Nielsen H8): Found latency or token metric values without 'tabular-nums' or 'font-mono'. Numerical readouts should use tabular lining figures to prevent layout jittering during updates."
        )

    # 19. Check for Gradient-Filled Heading Text (Vibe-Coded Tell #3 - RES-004 & JCarterJohnson/devibe_scan)
    # Detects bg-clip-text text-transparent used on headings, which online users flag as an immediate AI slop tell
    gradient_text_matches = re.findall(
        r"(?:bg-clip-text\s+[^\"'`]*text-transparent|text-transparent\s+[^\"'`]*bg-clip-text|-webkit-background-clip:\s*text)",
        content,
        re.I,
    )
    if gradient_text_matches and "unslop-ignore" not in content:
        errors.append(
            f"Gradient Text Slop Violation (RES-004 / Vibe-Coded Tell #3): Detected gradient-filled text ({len(gradient_text_matches)} occurrences). Headings and body copy must use solid, high-contrast typography. Gradient body/heading text is a top cited aesthetic tell for low-effort AI prototypes."
        )

    # 20. Check for Unprompted Neon Glow Box Shadows (Vibe-Coded Tell #4 & DesignCode Invariant - RES-004)
    # Detects high-radius uncalibrated neon glow box shadows (shadow-[0_0_... or box-shadow: 0 0 50px)
    neon_glow_matches = re.findall(
        r"(?:shadow-\[0_0_\d+px|drop-shadow-\[0_0_\d+px|box-shadow:\s*0\s+0\s+\d{2,}px)",
        content,
        re.I,
    )
    if neon_glow_matches and "unslop-ignore" not in content:
        warnings.append(
            f"Unprompted Neon Glow Slop (RES-004 / Vibe-Coded Tell #4): Detected disembodied neon glow shadow ({len(neon_glow_matches)} matches). Elevate surfaces using tonal background steps (#09090b -> #121316) and 1px tactile specular hairlines (border-white/10) rather than muddy neon drops."
        )

    # 21. Check for Untouched Stock shadcn Card Signature (Vibe-Coded Tell #1 - RES-004)
    # Detects repeated instances of the verbatim default shadcn Card class string
    stock_shadcn_card = "rounded-lg border bg-card text-card-foreground shadow-sm"
    shadcn_count = content.count(stock_shadcn_card)
    if shadcn_count >= 3 and "unslop-ignore" not in content:
        warnings.append(
            f"Stock shadcn Default Card Signature (RES-004 / Vibe-Coded Tell #1): Detected {shadcn_count} occurrences of untouched stock shadcn Card classes ('{stock_shadcn_card}'). Customize corner radii, neutral palette ramps, and border contrast to the specific project surface profile."
        )

    # 22. Check for 2026 'Tasteful Default' Convergence Trap (Vibe-Coded Tell #0 - RES-004)
    # Flags the co-occurrence of cream backgrounds with serif display fonts, which users now flag as the Claude/Anthropic default
    has_cream_bg = bool(re.search(r"#(?:faf8f5|f5f1e8|f3eee3|fdfbf7|f7f3ec|faf6ef)\b|\bbg-(?:stone|amber|orange)-(?:50|100)\b", content, re.I))
    has_serif_head = bool(re.search(r"\b(?:Instrument\s*Serif|Fraunces|Playfair\s*Display|Cormorant|Spectral|DM\s*Serif)\b", content, re.I))
    if has_cream_bg and has_serif_head and "unslop-ignore" not in content:
        warnings.append(
            "The 2026 'Tasteful Default' Convergence Trap (RES-004 / Vibe-Coded Tell #0): Detected co-occurrence of cream background with serif display heading. Trading 2024 purple gradients for 2026 Anthropic cream-serif-sage is replacing old slop with new slop unless this is an explicit, curated brand decision. Add '<!-- unslop-ignore -->' if this is an intentional project brand anchor."
        )

    return errors, warnings


def capture_screenshot(html_path: pathlib.Path, out_dir: pathlib.Path, extra_states: str | None = None) -> list[pathlib.Path]:
    import concurrent.futures

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

    base_url = f"file://{html_path.resolve()}"
    jobs: list[tuple[str, str, pathlib.Path]] = []
    for label, size in [("desktop-1440x900", "1440,900"), ("laptop-1180x800", "1180,800"), ("compact-375x812", "375,812")]:
        jobs.append((base_url, size, out_dir / f"{html_path.stem}-{label}.png"))

    # Auto-discover ?state=<name> branches in HTML or use --states
    state_names: list[str] = []
    if extra_states:
        state_names = [s.strip() for s in extra_states.split(",") if s.strip()]
    else:
        try:
            html_text = html_path.read_text(encoding="utf-8", errors="ignore")
            found = re.findall(r"\b(?:st|state)\s*===\s*['\"]([a-zA-Z0-9_-]{2,32})['\"]", html_text)
            for s in found:
                if s not in state_names:
                    state_names.append(s)
        except Exception:
            pass

    for st in state_names[:12]:
        jobs.append((f"{base_url}?state={st}", "1440,900", out_dir / f"{html_path.stem}-state-{st}.png"))

    def _run_job(job: tuple[str, str, pathlib.Path]) -> pathlib.Path | None:
        url, size, out_png = job
        cmd = [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--virtual-time-budget=2000",
            f"--window-size={size}",
            f"--screenshot={out_png}",
            url,
        ]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
            if res.returncode == 0 and out_png.exists():
                return out_png
        except subprocess.TimeoutExpired:
            pass
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for res_path in pool.map(_run_job, jobs):
            if res_path is not None:
                captured.append(res_path)
    return captured


def main() -> int:
    ap = argparse.ArgumentParser(description="CGSpec Visual & Structural Wireframe Auditor")
    ap.add_argument("html_file", nargs="?", default=None, help="Path to the HTML wireframe or prototype file")
    ap.add_argument("--html", dest="html_flag", default=None, help="Explicit path to the HTML wireframe or prototype file")
    ap.add_argument("--screenshot-dir", help="Optional directory to save headless browser screenshots", default=None)
    ap.add_argument("--states", help="Optional comma-separated ?state= query values to screenshot (auto-discovered by default)", default=None)
    ap.add_argument("--mode", help="Optional audit mode (wireframe | prototype)", default="wireframe")
    ap.add_argument("--strict-emojis", action="store_true", help="Enforce strict HTML Unicode emoji ban (enabled by default)")
    args = ap.parse_args()

    html_target = args.html_flag or args.html_file
    if not html_target:
        ap.error("You must provide an HTML file path either positionally or via --html <file>.")
    target = pathlib.Path(html_target).resolve()
    print(f"CGSpec Visual Auditor: Inspecting {target}")
    print("-" * 60)

    errors, warnings = audit_html(target)

    for w in warnings:
        print(f"  [WARN] {w}")
    for e in errors:
        print(f"  [FAIL] {e}")

    if not errors and not warnings:
        print("  [PASS] Static DOM & Viewport Invariants: 0 duplicate controls, 0 emojis, full-bleed viewport, versioned filename.")

    if args.screenshot_dir:
        shots = capture_screenshot(target, pathlib.Path(args.screenshot_dir), extra_states=args.states)
        for s in shots:
            print(f"  [SHOT] Captured screenshot: {s} (Inspect via view_file!)")

    print("-" * 60)
    # Auto-register .metadata.json if target is located inside an Antigravity brain artifact directory
    if "/brain/" in str(target) and not target.with_suffix(".html.metadata.json").exists():
        import json, datetime
        meta_file = target.with_name(f"{target.name}.metadata.json")
        if not meta_file.exists():
            meta_data = {
                "summary": f"CGSpec Verified HTML Prototype: {target.stem}",
                "updatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "userFacing": True,
            }
            meta_file.write_text(json.dumps(meta_data, indent=2), encoding="utf-8")
            print(f"  [META] Auto-registered Antigravity artifact metadata -> {meta_file.name}")

    if errors:
        print(f"FAILED: {len(errors)} structural UI error(s) detected. Fix before running Phase B Adversarial Critic.")
        return 1
    print("PHASE A PASSED: Static DOM checks clean.")
    print("MANDATORY NEXT STEP (Phase B — Independent Adversarial Critic Loop):")
    print("  1. Inspect all interactive state screenshots yourself via view_file (Preview, Edit, Diff+Back, Folder, Code, Drawer Closed).")
    print("  2. Spawn the 'Adversarial UX & Spec Critic' subagent (invoke_subagent) with FACTS ONLY (file paths + rubric path).")
    print("  3. Loop (Fix -> Re-verify -> send_message to Critic) WHILE Critic verdict != PASS. Never present to user before Critic PASS!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
