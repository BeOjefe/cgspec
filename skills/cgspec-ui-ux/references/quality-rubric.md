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

### 2. One Control Per Action, Single Header Ownership & Cross-Pane DRY Metadata
- **Single Action Trigger & Reversible Toggles:** Every state transition (`toggleDrawer()`, `enterDiffMode()`, `syncRepo()`) must have **one** canonical button, and clicking an active diff/compare button again (or clicking a clear `<- Exit Diff` button at the left of the canvas header) must return to the document.
- **Single Breadcrumb / Path Header (Docs & Code):** Never render two competing file-path headers (e.g. a top-bar breadcrumb AND a second center-pane or dark code-viewer path header below it, and never duplicate path segments like `src / src/file.ts`).
- **Zero Cross-Pane Metadata Duplication (DRY Across Visible Panes):** When the Right Inspector is open and displays a file's commit hash, supersession provenance, and open PRs, do not repeat the same commit/supersession subheader bar and PR pills across the Top Header, Left Tree, and Center Document Canvas simultaneously. If a file can have multiple open PRs, show a compact count (`2 PRs`) rather than hardcoding a single PR title pill in the tree/header.
- **Stationary Icon-Only Panel Toggle:** Place the right-drawer/inspector toggle as a clean `16x16` `<svg>` icon button with a `title` tooltip at the far right of the Top Header Bar (without confusing unexplained colored dots).

### 3. Context-Scoped Top & Side Chrome
- Controls that belong to a specific workspace view (e.g. file-tree view switchers, path breadcrumbs, document mode toggles, contextual file inspectors) must **hide automatically** when the user switches to global views (`Home`, `Hub`, `Settings`).
- Place tree-filtering switches (e.g. `Docs Only | Full Tree` or a filter icon button) directly inside the Explorer header they filter, never in the global top bar.

### 4. Direct Spatial Manipulation (Resizable Panes & Multi-Root Explorer)
- **Draggable Splitters (Zero Permanent Coaching Text):** Multi-column desktop layouts must include `4px` interactive splitters (`cursor: col-resize`) between panes. Never render permanent instructional text boxes like `"Drag the left border of this panel to resize it anytime"` inside the UI.
- **Click-to-Fold Rail:** Clicking the active icon in the primary navigation rail (or double-clicking a splitter) collapses/restores the adjacent panel.
- **Multi-Root Workspace Explorer:** Prefer collapsible workspace roots with inline hover actions and a filter/pin icon menu (VS Code / Antigravity Explorer pattern) over clunky top-bar scope dropdowns.

### 5. Unbroken Tree Hierarchy (Continuous Guide Lines)
- Render continuous vertical (`border-left: 1px solid`) and horizontal (`::before`) connector lines from parent folders to children (KDE Dolphin pattern).
- Never prefix tree nodes with artificial numbers (`1. Folder`) and never place multi-line subtitle blocks *between* a parent folder and its child tree (place optional descriptions as a compact eyebrow *above* the folder or in a hover tooltip).
- Support direct row drag-and-drop for ordering instead of noisy `⋮⋮` handles or up/down arrows.

### 6. Unified Domain Taxonomy
- Group sibling domain entities of the same archetype (e.g. extensions, templates, skills, connectors, pins) into a single unified filterable hub rather than scattering them across 5 separate top-level navigation tabs.

### 7. Zero Schema Leakage, Zero Emojis, Zero Meta-Tutorial Text & Clean Preview vs Edit Mode
- **Pure Inline `<svg>` Icons Only:** Never use Unicode emojis or pictographs (`📌`, `🔒`, `📄`, `👁️`, `⚙`, `↻`) in HTML wireframes or prototypes. Every icon must be a clean inline `<svg>`.
- **Zero Self-Referential Wireframe Commentary:** Never place meta-tutorial boxes inside a wireframe explaining what changed in `v6` (`"1. Fixed Top Header..."`, `"2. Every File & Folder is Live"`). Populate wireframes strictly with realistic domain content.
- **Rendered Preview vs Interactive Edit Mode:** In Document Preview mode, render clean typography (never show raw `# ` hashes or `**` asterisks in headings/paragraphs). Clicking `Edit` on a `.md` document must switch to an actual interactive editor (`<textarea>` with `Save / Propose Change` and `Cancel`).
```html
<!-- BROKEN — leaking raw snake_case schema fields, raw '# ' Markdown in <h1>, or meta-coaching text -->
<h1># docs/01-INTENT.md</h1>
<label>Branch (git_branch)</label>
<div>Drag the left border of this panel to resize it anytime.</div>

<!-- CORRECT — clean rendered heading in Preview mode and natural human labels -->
<h1>CortexGate Problem, Mission & Day-in-the-Life</h1>
<label>Branch</label>
```

### 8. Capability-Driven & Content-Type-Driven UI Hiding
- Hide actions the current actor role OR active file type cannot support:
  - When viewing a **read-only Code file** (`.ts`, `.rs`, `.py` in Full Repo mode) or a **Folder Overview**, hide the document `Edit` / `Propose Edit` button automatically (only `.md` documentation files in the Doc Zone are editable).
  - Never show a `Your Access: Editor` debug badge or both `Edit` and `Propose Edit` simultaneously.

---

## Part 2: Phase A — Builder Exhaustive Self-Verification (Mandatory First Gate)

Before spawning the Adversarial Critic subagent, the Builder (Main Agent) must do **everything possible** to verify its own work:
1. **Static & DOM Gate:** Run `python3 docs/.cgspec/scripts/visual_audit.py <file.html> --screenshot-dir <dir>` and `python3 docs/.cgspec/scripts/doctor.py --repo . --strict-emojis` until `0 errors`.
2. **Multi-Viewport & Interactive Manipulation:** Capture headless Chrome screenshots across Desktop (`1440x900`), Laptop (`1180x800` — checking that header buttons like `Edit` and panel toggles never clip or overflow when sidebars are open), and Compact (`375x812`), plus every interactive state (`Default Preview`, `Markdown Edit Mode`, `Diff Mode + Toggle Back`, `Folder Overview`, `Full Repo Read-Only Code View`, `Drawer Closed`).
3. **Self-Inspection Against Skills & Good Practices:** View every captured PNG via `view_file` and verify all 8 Structural UI Coherence Laws above.

---

## Part 3: Phase B — Facts-Only Adversarial Critic Subagent Loop (`while verdict != PASS`)

Author confirmation bias causes an agent to overlook flaws in HTML it just wrote. Therefore, **after Phase A passes and BEFORE showing or claiming work done to the user**, the Main Agent must execute a closed-loop audit with an independent **`Adversarial UX & Spec Critic`** subagent:

### 1. Facts-Only Input Rule (Zero Bias or Self-Praise)
Invoke `invoke_subagent` (`TypeName: "self"`, `Role: "Adversarial UX & Spec Critic"`, `Workspace: "inherit"`) and provide **ONLY cold facts**:
```text
You are an independent, uncompromising Adversarial UX & Spec Critic.
Inspect the candidate deliverable and return a strict factual verdict (VERDICT: PASS or VERDICT: FAIL).

Factual Inputs:
- Candidate HTML: <absolute/path/to/wireframe-vN.html>
- Captured State Screenshots: <absolute/paths/to/screenshots/*.png>
- Locked Domain Spines: docs/01-INTENT.md, docs/02-OOUX.md, docs/03-EXPERIENCE.md
- Quality Rubric & Auditor: skills/cgspec-ui-ux/references/quality-rubric.md, docs/.cgspec/scripts/visual_audit.py

Audit Checklist (Test & View Every State):
1. Run visual_audit.py and view every screenshot via view_file (and capture additional states/widths such as 1180x800 if needed).
2. Check Cross-Pane DRY Metadata: Is any commit hash, supersession string, file path, or PR badge duplicated simultaneously across the Top Header, Tree, Center Canvas, and Right Drawer?
3. Check Control Reachability & Reversibility: Are the Edit and Right-Panel Toggle buttons clipped at 1180px-1440px when the drawer is open? Does clicking 'Edit' on a .md file actually open an editor (and hide on read-only code files/folders)? Does clicking 'Review Diff' / 'Compare' toggle back when clicked again, with an accessible 'Exit Diff' button?
4. Check Multi-Item Scaling & Zero Meta-Coaching: What happens when a file has 2+ open PRs (and when 1 PR is merged, do remaining PRs re-evaluate for conflicts)? Are there any self-referential tutorial/coaching boxes ('Drag border to resize...', 'Every file is live') or raw Markdown '# ' / '**' syntax in Preview mode?

Output Format:
- Status: VERDICT: PASS (only if 0 defects) or VERDICT: FAIL
- Numbered list of exact factual defects (file/line/screenshot evidence and required fix).
```

### 2. The `while (verdict != PASS)` Loop (`Boucle Tant Que`)
- **If `VERDICT: FAIL`:** Do **not** message the user or claim completion. Fix every numbered defect in the HTML, re-run Phase A (`visual_audit.py` + updated screenshots), and send the updated file/screenshot paths back to the SAME Critic subagent via `send_message` for Round $k+1$.
- **Exit Condition:** Repeat the loop until the Adversarial Critic returns **`VERDICT: PASS (0 defects)`**, then terminate the critic subagent (`manage_subagents` `kill`) and present the verified work to the user.

