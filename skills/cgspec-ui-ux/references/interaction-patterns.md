# Ergonomic Interaction Patterns

Canonical catalogue of tactile interaction mechanics for Stage 2 (`cgspec-ui-ux` Phase 3). For structural layout & verification laws, see [`references/quality-rubric.md`](quality-rubric.md).

---

## 1. In-Place Fluid Editing (The Living Document Pattern)
- **Concept:** Reading view is clean and editorial; editing happens where the cursor lands without modal dialogs or layout shift.
- **Mechanics:** Clicking a line reveals syntax markers inline; moving focus away settles back into rendered typography with identical line-height.

---

## 2. Shallow Jump-List Triad (Anti-4-Box Navigation)
- **Concept:** Replaces passive 4-box metric ribbons with high-velocity navigation jumps.
- **Mechanics:** Render 3 actionable summary cards (`[ Active Items (12) > ]`) that filter the main table or jump directly to that operational view in 1 click.

---

## 3. Sliding Inspection Drawer & Unified Timeline
- **Concept:** Inspect revision history, open proposals, or metadata without leaving the main canvas.
- **Mechanics:**
  - Selecting an item or pressing a single top-right toggle (`Alt+I`) slides a resizable (`col-resize`) drawer from the right edge, compressing rather than obscuring the main canvas.
  - Consolidate **Version History & Change Proposals (PRs)** into a single unified timeline tab rather than splitting them across separate pages and drawers.

---

## 4. Hardware Keycap Buttons
- **Concept:** Builds muscle memory by embedding keyboard shortcuts directly inside action buttons (`New Item [N]`, `Search [⌘K]`).

---

## 5. Non-Blocking Status Toast vs Persistent Hairline Banner
- **Concept:** Transient successes pulse quietly for 2.5s; critical degradations (`Offline`, `Merge Conflict`) stay pinned as a 1px hairline banner until resolved. Clean/healthy states show **zero** verification banners.

---

## 6. Multi-Root Workspace Explorer & Continuous Tree Lines (VS Code / KDE Dolphin Pattern)
- **Concept:** Users navigating multi-root workspaces or deep folder hierarchies need immediate visual depth, direct manipulation, and 1-click folder pinning/hiding.
- **Mechanics:**
  - **Multi-Root Explorer Header:** Provide an `EXPLORER` header with a `...` menu to Pin, Hide, or Reorder workspace roots and repositories, plus inline hover icons (`New File`, `Add Folder/Mount`, `Sync/Refresh`, `Collapse All`)—instead of a global top-bar project dropdown.
  - **Continuous Guide Lines:** Render unbroken vertical (`border-left: 1px solid`) and horizontal (`::before`) connectors from parent folders to children. Place optional folder descriptions as a subtle eyebrow *above* the folder or in a hover tooltip so tree lines never break.
  - **Tree-Local View Filtering:** Place tree-filtering controls (`Curated Docs | All Files`, `Show Dotfiles Ctrl+H`) directly in the Explorer header above the tree they control.
