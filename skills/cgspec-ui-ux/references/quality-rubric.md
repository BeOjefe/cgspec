# CGSpec Experience Quality Rubric

This rubric evaluates user experience and interface design across 5 uncompromising craft dimensions:

---

## 1. Spatial Hierarchy, Viewport Fill & Chrome Coherence (Weight: 25%)
- **Score 5 (Exemplary):** Full-bleed viewport utilization (`100vh x 100vw` flex layout with zero dead bottom/side voids). Context-scoped top bar (workspace-specific controls hide on `Home`/`Settings`). Strictly one control per action (zero duplicate Inspector buttons, zero stacked `Back` headers in Diff mode, unified Resource navigation).
- **Score 3 (Acceptable):** Screen has clear zones, but minor redundant toolbar buttons or fixed-width columns that truncate long paths.
- **Score 1 (Failing):** AI Slop or uninspected blind HTML: giant 40% empty viewport voids at the bottom, two `Back` headers stacked on top of each other, two Inspector buttons visible at once, or file controls leaking onto `Home`.

---

## 2. Tactile Ergonomics, Direct Manipulation & Tree Continuity (Weight: 25%)
- **Score 5 (Exemplary):** Zero modal friction. Multi-column layouts include working draggable splitters (`col-resize`) and click-to-collapse rails. Nested trees (KDE Dolphin style) have continuous, unbroken vertical/horizontal guide lines (`│`, `├─`, `└─`), zero artificial number prefixes, direct row drag-and-drop ranking, and eyebrow/tooltip descriptions that never sever parent-to-child tree lines.
- **Score 3 (Acceptable):** Functional editing and navigation, but static non-resizable columns or clunky up/down reorder buttons.
- **Score 1 (Failing):** Disconnected bulky boxes around tree folders, subtitle text breaking tree connector lines, unindented flat lists pretending to be trees, or rigid modal dialogs interrupting flow.

---

## 3. Typographic Discipline & Token Craft (Weight: 20%)
- **Score 5 (Exemplary):** Coherent typographic scale (max 3 font families). Monospace paired with `tabular-nums` for all metrics, codes, hashes, and timestamps. Exactly 1 surgical brand anchor color. Tonal elevation with 1px hairlines. Compact clickable status pills (`Access: Editor · Shared`) instead of noisy multi-box metadata headers.
- **Score 3 (Acceptable):** Legible typography, but occasional inconsistent font weights or verbose button labels where compact SVG icons + tooltips belong.
- **Score 1 (Failing):** Unstyled default browser fonts, generic purple-indigo gradients, emojis used as interface icons, uncalibrated high-saturation rainbows.

---

## 4. Operational State Completeness (Weight: 15%)
- **Score 5 (Exemplary):** All surface-required lifecycle states modeled cleanly at both screen and component level (4 states for Simple Websites; 7 mobile states for iOS/Android; 7 operational states for Web Workspaces). Loading skeletons prevent layout shift. Empty states provide clear next actions.
- **Score 3 (Acceptable):** Populated and loading states well-handled, but empty or error states look like generic placeholders.
- **Score 1 (Failing):** Happy-path only, or forcing irrelevant desktop states (`Denied 403`) onto a static marketing landing page.

---

## 5. Keyboard Flow, Accessibility & Closed-Loop Visual QA (Weight: 15%)
- **Score 5 (Exemplary):** Complete end-to-end task execution reachable via keyboard. Visible focus rings, WCAG AA contrast (`>= 4.5:1`), `Cmd/Ctrl+K` command search. Verified via **Closed-Loop Browser Self-Critique** (`visual_audit.py` / `chrome-devtools-mcp` screenshots inspected via `view_file` across `Default`, `Home`, and `Diff/Drawer` states before user presentation).
- **Score 3 (Acceptable):** Tab navigation works, but minor visual alignment flaws were not caught before showing the user.
- **Score 1 (Failing):** HTML presented blindly without browser screenshot inspection, resulting in broken layout containers or keyboard traps.

