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
