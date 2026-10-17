# CGSpec Experience Quality Rubric & 8 Structural UI Coherence Laws

This file is the **single canonical source of truth** for visual and structural verification (`docs/.cgspec/scripts/visual_audit.py` + headless browser screenshot inspection via `view_file`).

---

## Part 1: The 8 Structural UI Coherence Laws (Pre-Presentation Gate)

Every wireframe (`wireframe-v1.html`) and prototype (`prototype-v0.1.html`) must pass all 8 laws before being shown to the user:

### 1. Zero Dead Viewport Void (Full-Bleed Root)
```css
/* BROKEN — styling only body or using fixed height leaves a 30-40% empty void in iframes */
body { min-height: 600px; }

/* CORRECT — full-bleed root flex container filling 100vh x 100vw */
html, body { height: 100%; min-height: 100vh; margin: 0; overflow: hidden; display: flex; flex-direction: column; }
```

### 2. One Control Per Action (Zero Duplicate Triggers or Stacked Headers)
- **Single Action Trigger:** Every state transition (`toggleDrawer()`, `enterDiffMode()`, `syncRepo()`) must have **one** canonical button. Never wire two visible buttons in the same view to the same action.
- **Single Transforming Header:** When entering a comparison, diff, or sub-inspection view, transform the existing header bar in place (`<- Back to View`). Never stack two header bars with two `Back` buttons on top of each other.
- **Unified History & Proposals:** Keep version history and change proposals in a single unified timeline/queue rather than splitting them across disconnected screens and drawers.

### 3. Context-Scoped Top & Side Chrome
- Controls that belong to a specific workspace view (e.g. file-tree view switchers, path breadcrumbs, document mode toggles, contextual file inspectors) must **hide automatically** when the user switches to global views (`Home`, `Hub`, `Settings`).
- Place tree-filtering switches (e.g. `Docs Only | Full Tree`) directly inside the tree header they filter, never in the global top bar.

### 4. Direct Spatial Manipulation (Resizable Panes & Multi-Root Explorer)
- **Draggable Splitters:** Multi-column desktop layouts must include `4px` interactive splitters (`cursor: col-resize`) between panes so truncated labels can be widened with the mouse.
- **Click-to-Fold Rail:** Clicking the active icon in the primary navigation rail (or double-clicking a splitter) collapses/restores the adjacent panel.
- **Multi-Root Workspace Explorer:** Prefer collapsible workspace roots with inline hover actions and a `...` visibility/pin menu (VS Code / Antigravity Explorer pattern) over clunky top-bar scope dropdowns.

### 5. Unbroken Tree Hierarchy (Continuous Guide Lines)
- Render continuous vertical (`border-left: 1px solid`) and horizontal (`::before`) connector lines from parent folders to children (KDE Dolphin pattern).
- Never prefix tree nodes with artificial numbers (`1. Folder`) and never place multi-line subtitle blocks *between* a parent folder and its child tree (place optional descriptions as a compact eyebrow *above* the folder or in a hover tooltip).
- Support direct row drag-and-drop for ordering instead of noisy `⋮⋮` handles or up/down arrows.

### 6. Unified Domain Taxonomy
- Group sibling domain entities of the same archetype (e.g. extensions, templates, skills, connectors, pins) into a single unified filterable hub rather than scattering them across 5 separate top-level navigation tabs.

### 7. Zero Schema Identifier Leakage in Human UI
```html
<!-- BROKEN — leaking raw snake_case schema fields, PascalCase models, or UPPER_SNAKE_CASE enums -->
<h3>Configure Mount (ProjectRepoMount)</h3>
<label>Branch (git_branch)</label>
<span>GIT_PLAINTEXT</span>
<div>BASE SHA VERIFIED base_revision_sha: fd2782d matches current_head_sha</div>

<!-- CORRECT — natural human labels and quiet state presentation -->
<h3>Repository Settings</h3>
<label>Branch</label>
<span>Plaintext Git</span>
<!-- Clean diffs show zero noisy verification banners; only conflicts show a warning -->
```

### 8. Capability-Driven UI Hiding (Never Show Conflicting Role Buttons or Debug Access Badges)
```html
<!-- BROKEN — showing a debug access badge AND both Edit + Propose Edit buttons simultaneously -->
<span>Your Access: Editor (write | admin)</span>
<button>Edit</button>
<button>Propose Edit</button>

<!-- CORRECT — hide controls the current role cannot touch (Dokploy / Linear pattern) -->
<!-- If role has 'write': show [Edit]. If 'propose_edit': show [Propose Change]. If 'read': show neither. -->
<button>Edit</button>
```

---

## Part 2: 5-Dimension Experience Scoring Rubric

1. **Spatial Hierarchy & Chrome Coherence (25%):** Full-bleed viewport (`100vh`), context-scoped chrome, one control per action, zero stacked headers.
2. **Tactile Ergonomics & Direct Manipulation (25%):** Draggable `col-resize` splitters, unbroken tree guide lines, multi-root workspace pinning, zero modal friction.
3. **Human Language & Typographic Craft (20%):** Zero `snake_case` / `UPPER_SNAKE_CASE` schema leakage, capability-driven control hiding, max 3 font families, `tabular-nums` monospace for metrics/hashes, 1 surgical brand anchor.
4. **Proportional State Completeness (15%):** All surface-required lifecycle states modeled cleanly (4 states for Simple Websites; 7 mobile states for iOS/Android; 7 operational states for Web Workspaces; 5 states for CLI).
5. **Keyboard Flow & Closed-Loop Visual QA (15%):** Full keyboard reachability, WCAG AA contrast (`>= 4.5:1`), verified via `visual_audit.py` + `view_file` screenshot inspection across `Default`, `Secondary Tab`, and `Diff/Modal` states.
