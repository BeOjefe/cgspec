# Ergonomic Interaction Patterns

This reference catalogues high-craft tactile patterns for AI-native software experiences:

---

## 1. In-Place Fluid Editing (The Living Document Pattern)
- **Concept:** Reading view is clean, formatted, and editorial. Editing happens immediately where the cursor lands without switching modes or opening a modal dialog.
- **Physical Mechanics:**
  - When the cursor clicks or tabs into a paragraph/heading, markdown syntax markers quietly appear around the active word or line.
  - When the cursor moves away, formatting settles smoothly back into rendered typographic styling.
  - No vertical layout shifts: line height and block spacing remain identical between active editing and static reading.

---

## 2. Shallow Jump-List Triad (Anti-4-Box Navigation)
- **Concept:** Replaces generic, passive metric cards with actionable, high-velocity navigation jumps.
- **Physical Mechanics:**
  - Instead of 4 static boxes showing numbers, provide a horizontal triad of shallow jump cards:
    `[ Virtual Keys (12 Active) > ]`  `[ Upstream MCP Servers (4 Running) > ]`  `[ Audit Trail (3 Anomalies) > ]`
  - Clicking any card immediately filters the main table or jumps directly to that operational context with zero nested page-load lag.

---

## 3. Sliding Inspection Drawer (Context Without Context-Switching)
- **Concept:** Inspect deep details or linked references without navigating away from the primary canvas.
- **Physical Mechanics:**
  - Selecting an item or pressing hotkey (e.g. `Alt+B` for backlinks) slides a 300px panel from the right edge.
  - The drawer compresses the main canvas slightly rather than obscuring it, preserving full read access.
  - Dismissable via `Escape` key or backdrop click.

---

## 4. Hardware Keycap Buttons
- **Concept:** Accelerates human muscle memory by displaying keyboard shortcuts directly inside action buttons.
- **Physical Mechanics:**
  - Button text includes embedded keycap styling: `New Document [N]`, `Run Analysis [R]`, `Search [⌘K]`.
  - Pressing the hotkey gives an immediate tactile active press animation on the button itself.

---

## 5. Non-Blocking Status Toast vs Persistent Hairline Banner
- **Concept:** Transient successes should not interrupt; persistent degradations must not disappear.
- **Physical Mechanics:**
  - Transient operations (e.g. "Synced to disk") pulse quietly in the status bar or small bottom toast for 2.5 seconds, then fade.
  - Critical states (e.g. "Offline - Local cache only", "Index degraded") stay pinned as a quiet 1px hairline banner below the header until resolved.

---

## 6. Seamless Nested Tree with Guide Lines & View Switcher (KDE Dolphin Pattern)
- **Concept:** Users navigating multi-mount repositories or deep folder hierarchies need immediate tactile perception of nesting depth without visual clutter.
- **Physical Mechanics:**
  - **Zero Artificial Number Prefixes:** Never prefix mounts or navigation items with numbers (`1. CG-Core` or `01`). Display clean folder/mount icons and editable aliases (`CG-Core`, `services/auth`).
  - **Continuous Connector Lines:** Render unbroken vertical (`border-left: 1px solid`) and horizontal (`::before` `11px` connector) guide lines connecting parent folders directly to their children. Never place multi-line description blocks *between* a folder row and its children (which severs the tree line); place descriptions as a subtle eyebrow *above* the mount or inside a hover tooltip.
  - **TradingView Row Drag + Inline Sync:** Allow direct row drag-and-drop to rank mounts (instead of ugly `⋮⋮` dots or up/down arrows) and place a compact inline Git Fetch/Sync icon + badge (`↑1`) right on each mount row.
  - **View Mode Switcher & Interactive Breadcrumb:** Pair the top path breadcrumb (`Scope > Mount > Folder > File` — where clicking any parent folder opens a Folder Overview) with a compact View Switcher (`Split Tree + Editor`, `Details Tree Table`, `Compact Columns`, plus `Show Dotfiles Ctrl+H`).

---

## 7. Draggable Split-Pane Resizers & Click-to-Fold Rail (VS Code / IDE Reflex)
- **Concept:** Fixed-width sidebars inevitably truncate long paths (`services/orders`) and frustrate human spatial reflexes.
- **Physical Mechanics:**
  - Place a `4px` interactive vertical splitter (`cursor: col-resize`) between `Left Tree <-> Center Canvas` and `Center Canvas <-> Right Inspector` so the user can drag to widen or narrow any pane smoothly.
  - Clicking the currently active icon in the Left Navigation Rail (or double-clicking the splitter) immediately collapses or restores the secondary tree panel.

---

## 8. One Control Per Action & Context-Scoped Chrome (Zero Duplicate UI)
- **Concept:** Every action or mode transition must have exactly one predictable home; controls irrelevant to the active screen must disappear.
- **Physical Mechanics:**
  - **Single Adaptive Document Header:** When switching from reading a document to `Side-by-Side Diff` (triggered from the `History` tab), transform the existing document header in-place to show `<- Back to Document` and the compared revisions—never stack two headers on top of each other, and never put a standalone `[Diff]` button in the toolbar when `History` owns revision comparison.
  - **Single Inspector Trigger:** Use one consistent top-right toggle icon (plus `Alt+I`) to open/close the Right Inspector—never render both a top-bar button and a floating side-edge tab simultaneously.
  - **Context-Scoped Top Bar:** File-specific controls (`View Mode`, file breadcrumbs, `Doc Zone | Code Zone` switch, `Right File Inspector`) are visible **only** when the `Files` workspace is active, keeping `Home / Overview`, `Resources`, and `Settings` clean.
  - **Compact Clickable Access Pill:** Consolidate ownership and effective role into a single subtle pill (`Access: Editor (Inherited) · Shared (6)`) that opens the Inspector's `Access & Keys` tab when clicked.

