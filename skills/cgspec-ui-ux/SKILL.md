---
name: cgspec-ui-ux
description: Dual-Spine UI & UX Compilation Engine. Ingests locked Stage 1 ORCA object maps (01-INTENT & 02-OOUX) and compiles them into zero-color spatial layouts (Mermaid/D2/PlantUML), tactile ergonomics, positive design tokens, 7-state matrices, and executable prototypes (03-EXPERIENCE.md).
---

# cgspec-ui-ux

## The Dual-Spine Architecture: UI vs. UX Responsibilities

`cgspec-ui-ux` is the unified engine for Stage 2, tightly binding the two inseparable halves of digital product creation:

| Domain | Core Focus | What It Solves | Deliverables in Stage 2 |
| :--- | :--- | :--- | :--- |
| **UX (User Experience)** | Ergonomics, Navigation & Behavior | *How it works & how hands move:* Direct manipulation mechanics (in-place vs modal), focal screen selection, keyboard/touch gestures, cognitive pacing, error recovery. | Journey slice contract, tactile interaction specifications, accessibility navigation flow. |
| **UI (User Interface)** | Spatial Layout, Presentation & Craft | *Where things live & how it looks:* Macro spatial zoning (Sections, Thumb-Zones, or Panels), declarative wireframes (Mermaid/D2/PlantUML), typography scale (`tabular-nums`), tonal surface elevation (1px hairlines), 1 surgical brand anchor. | Macro spatial wireframe, design tokens, proportional state matrix, single-file HTML prototype (`prototype-v0.1.html`). |

---

## Adaptive Surface Profile Gate (Never Impose Desktop SaaS on Mobile or Simple Sites)

Before drawing layouts or modeling states, identify the project's **Target Surface Profile** from `01-INTENT.md` and calibrate spatial zoning, ergonomics, and required states accordingly:

| Surface Profile | Spatial Zoning Geometry | Ergonomics & Physical Input | Proportional State Matrix | Executable Prototype (`prototype-v0.1.html`) |
| :--- | :--- | :--- | :--- | :--- |
| **Profile A: Simple / Narrative Website** *(Landing page, portfolio, blog, marketing site)* | **Vertical Scroll Storyboard:** Sticky Header -> Hero Hook + Live Proof -> Problem/Solution Contrast -> Bento/Comparison -> FAQ & CTA Footer. *(No 3-pane sidebars!)* | Visual pacing, reading rhythm, above-the-fold clarity, responsive mobile stacking. | **4 Narrative States:** `Desktop Wide`, `Mobile Compact`, `Interactive Hover/Expanded`, `Form Validation/Submitted`. | Full-bleed responsive HTML page with Desktop/Mobile viewport toggle. |
| **Profile B: Mobile App (iOS / Android)** *(SwiftUI, Kotlin, Flutter, React Native)* | **Thumb-Zone Vertical Stack:** Top Status/App Bar -> Scrollable Feed/Canvas -> Draggable Bottom Sheet (Peek/Half/Full detents) -> Bottom Tab Bar. *(No wide side rails!)* | **Touch & Gestures:** 44x44pt (iOS HIG) / 48x48dp (Android M3) hit targets, one-handed thumb arc, swipe actions, pull-to-refresh, **Virtual Keyboard Avoidance**. | **7 Mobile States:** `Populated`, `Loading Skeleton`, `Empty`, `Error/Retry`, `OS Permission Prompt`, `Offline/Cached`, `Keyboard Up (40% occluded)`. | Interactive `390x844` (iOS) / `412x915` (Android) device frame with sheet/gesture & keyboard switcher. |
| **Profile C: Web / Desktop Workspace** *(SaaS, dashboard, IDE, data tool)* | **Multi-Pane Viewport:** Top Header Bar -> Left Nav Rail -> Center Workhorse Canvas -> Right Contextual Drawer. | **Mouse + Keyboard-First:** `Cmd+K` command bar, `<kbd>` hotkeys, in-place fluid editing, 32-40px dense rows. | **7 Operational States:** `Populated`, `Loading Skeleton`, `Empty`, `Error`, `Denied 403`, `Offline`, `Filtered Zero`. | Full-viewport multi-pane workspace with 7-state switcher bar. |
| **Profile D: CLI / TUI / Headless** *(Terminal tool, daemon, SDK)* | **Command & Stream Topology:** Subcommand tree, flag matrix, split TUI panes, `stdout` data vs `stderr` diagnostics. | **TTY Ergonomics:** Pipeability, `--json` flag, interactive spinner vs non-TTY quiet mode, exit codes. | **5 CLI States:** `Success (Exit 0)`, `Usage/Help`, `Validation Error (Exit 1)`, `Auth/Network Error`, `Non-TTY Pipe Mode`. | Interactive terminal transcript / TUI simulator in HTML or CLI contract spec. |

---

## Operating Contract (Read Before Every Turn)

1. **Ingest Locked Intent (Do Not Re-Interview from Ground Zero):**
   - Stage 1 (`cgspec-forge`) has already established the user persona, core problem statement, Day-in-the-Life walkthrough (`01-INTENT.md`), and the ORCA domain nouns & relationships (`02-OOUX.md`).
   - `cgspec-ui-ux` ingests this locked foundation. It never forces the human to repeat themselves.
   - Its design task is strictly: **Which journey slice or focal screen from `01-INTENT.md` are we mapping first, which Surface Profile (Simple Site, Mobile iOS/Android, Web App, or CLI) applies, and how do hands physically manipulate those nouns?**
2. **Maintain State & Visibility:** Maintain an active screen, active phase, and explicit list of unresolved questions.
3. **Separate Categories:** Distinctly separate verified facts, human preferences, working assumptions, and approved decisions.
4. **Small Question Batches:** Ask small batches of consequential questions. Never overwhelm the user with long questionnaires.
5. **Plain Language Before Jargon:** Explain physical interactions in plain, everyday English before introducing technical design terms.
6. **Analyze Specific Mechanisms:** Use references to analyze specific mechanisms (e.g. navigation trees, syntax collapsing, drawers); never drop naked product names.
7. **Meaningful Alternatives:** Explore structural alternatives only when they test genuinely different propositions (e.g. persistent rail vs focused fullscreen canvas).
8. **Test Rough Interactions Early:** Build lightweight prototypes to validate how an interaction feels before investing in visual styling or design tokens.
9. **Provisional Approvals:** Treat layout and design approvals as provisional hypotheses that can be reopened if subsequent interaction testing reveals flaws.
10. **Systematic Accessibility:** Apply accessibility (keyboard traversal, focus states, contrast, touch targets) throughout discovery, design, and verification.
11. **Truthful Inspection Claims:** Never claim to have inspected screenshots, files, videos, or browser behaviors unless available tools actually executed that inspection.
12. **Graceful Capability Degradation:** If a capability is unavailable in the environment, state the limitation and provide an executable manual verification procedure.
13. **Strict Gate Before Scaffolding:** Do not scaffold production backend or frontend code before the relevant user experience is approved.
14. **Purposeful Decoration:** Never add decorative elements (gradients, drop shadows, textures) without a clear hierarchy, task, or identity rationale.
15. **Visual-First Choice Invariant (Never Ask Layout Questions Blind):** Never call `ask_question` on layout hypotheses in plain text before rendering an interactive visual wireframe Artifact (`UserFacing: true`) so the human can see and click both options first.
16. **Non-Destructive Iteration Versioning (`v1 -> v2 -> v3`):** Never overwrite previous wireframes or prototypes in place. Every iteration must be saved both to `<appDataDir>/brain/<conversation-id>/wireframe-vN.html` (`UserFacing: true` for live side-pane preview—never inline `<agent-embed>` for desktop layouts) AND archived to `docs/.cgspec/prototypes/wireframe-vN.html`.
17. **Mandatory Closed-Loop Visual Self-Critique (`gstack / BMAD` Pattern — Inspect Your Own Pixels Before Speaking):**
    - Before presenting ANY wireframe or prototype HTML to the user, the agent MUST open it in a headless browser (`visual_audit.py` or `chrome-devtools-mcp`), capture screenshots across states (`Default`, `Home/Secondary Tab`, `Diff/Modal/Drawer`), inspect those screenshots via `view_file`, and auto-fix any violation of the **6 Structural UI Coherence Laws**:
      1. *Zero Dead Viewport Void:* `100vh x 100vw` flex container (`flex: 1; min-height: 0`) with zero empty bottom/side whitespace gaps.
      2. *One Control Per Action:* Zero duplicate buttons or stacked headers (never two `Back` bars in Diff mode, never two `Inspector` toggles, never 4 separate `Git` buttons).
      3. *Context-Scoped Top Chrome:* File-specific controls (`Split Tree`, file breadcrumbs, `Doc/Code` switch, `File Inspector`) appear ONLY on the `Files` screen—never on `Home` or `Settings`.
      4. *Direct Spatial Manipulation:* Multi-column layouts include draggable split-pane resizers (`col-resize`) to prevent unresolvable truncation (`services/o...`), and clicking the active rail icon collapses/expands the secondary tree panel.
      5. *Unbroken Tree Hierarchy:* Nested trees (KDE Dolphin style) maintain continuous vertical/horizontal guide lines (`│`, `├─`, `└─`) without bulky boxes or mid-tree subtitle blocks severing parent-to-child lines.
      6. *Unified Resource Taxonomy & Compact Access Pills:* Domain nouns of the same archetype (`MCP`, `Prompts`, `Skills`, `Agents`, `Pins`) group into a unified hub; ownership and role metadata consolidate into a single clickable pill (`Access: Editor · Shared`).
18. **Phase Fidelity Ceiling & One-Screen-at-a-Time Discipline:**
    - Never build 6 screens (`Home`, `Files`, `PRs`, `Prompts`, `MCP`, `Settings`) simultaneously inside one giant wireframe. Scope active prototyping strictly to the **single active focal screen** (`SCR-01`), rendering other navigation destinations as clean inactive placeholders (`[Scheduled for SCR-02]`) until `SCR-01` is locked.
    - During **Phase 2 (Macro Spatial Layout)**, never populate uninterviewed zones with invented micro-buttons (`[Edit] [Diff] [Propose PR] [Owned by]`); use clean zone placeholders until Phase 3 (Tactile Interactions) so premature micro-controls do not derail macro layout review.
19. **3-Bucket Triage Gate (Capture 100% of User Input Without Derailing the Current Step):**
    - When the user mentions ideas or requirements for *other screens*, *later UX phases*, or *backend schemas* during a layout review, immediately persist them to disk in their proper bucket (`Bucket A`: apply to active screen now; `Bucket B`: log other-screen requirements to `docs/03-EXPERIENCE.md` & `.memlog.md`; `Bucket C`: log backend/future items to `02-OOUX.md`, `04-ARCHITECTURE.md`, or `00-INBOX.md`) and explicitly confirm to the user what was saved on disk vs what is being tested in the current step.
20. **Consistent Turn Wrap-Up:** Conclude each turn by running `visual_audit.py` and `doctor.py`, synchronizing all diagrams and tables in `docs/03-EXPERIENCE.md`, logging approved decisions to `.memlog.md`, and stating the next concrete action.

---

## Handling Mid-Design Sparks & Scope Pivots (The Design Stash Protocol)

Design can only operate cleanly on a **locked scope milestone** (e.g. `v0.1` intent and domain nouns). When a new idea, feature, or fundamental realization emerges during active design:

1. **Evaluate & Advise 1-on-1 (The Scope Firewall):**
   - The AI pauses design exploration and discusses the spark with the user directly.
   - Give an honest technical and ergonomic assessment: explain whether adding it to `v0.1` risks diluting the core loop, or whether parking it in `docs/00-INBOX.md` under `Future Backlog (v0.2+)` preserves focus.
   - Ask the user: *"Do you want to park this for v0.2+, or is this essential enough to pause design and return to brainstorming to reshape v0.1?"*

2. **If Parking for v0.2+:**
   - Immediately capture the idea to `docs/00-INBOX.md` under `## 2. Future Backlog (v0.2+)` (Law 11).
   - Resume the active design phase with zero disruption to active prototypes.

3. **If Expanding v0.1 (Returning to Brainstorming):**
   - **Never delete or discard mid-work design:** Any sketches, wireframes, or prototypes represent valuable cognitive labor.
   - **Stash the Mid-Work:** Snapshot current design assets into `docs/.cgspec/prototypes/stash/<timestamp>-<name>/`.
   - **Log the Pause:** Append a record to `docs/.memlog.md` (e.g. `### [M-NNN] Paused Stage 2 Design: Reopening Stage 1 Intent for <New Concept>`).
   - **Re-lock Intent (Stage 1):** Return to `docs/01-INTENT.md` and `docs/02-OOUX.md` to define the new noun, relationships, and user journey. Confirm user approval.
   - **Design Delta Assessment:** Upon returning to Stage 2, inspect the stashed mid-work:
     - *Additive:* Keep the existing layout wireframe as the foundation; graft the new zone or control into the canvas.
     - *Cosmetic / Behavioral:* Restore the stashed prototype directly and calibrate behavior.
     - *Paradigm Shift:* If spatial zoning must change completely, extract the typography scale, surface elevation, and color tokens into the new layout so aesthetic craft is never wasted.

---

## The Repeatable 5-Phase Experience Cycle

### Phase 1: Establish the Design Brief & Map the Journey
- **Understand the Job:** Define the primary user, the main task, usage context, existing frustrations, and strict anti-goals (what is out of scope).
- **Map the Scenario:** Walk through a real day-in-the-life scenario from entry point to completion feedback and error recovery.
- **Select Focal Screen:** Pick the screen with the highest combination of frequency, user value, and uncertainty (not automatically the dashboard).

### Phase 2: Scout References & Explore Spatial Layouts
- **Mechanism-Driven References:** Share 2-3 real-world exemplars, identifying what specific interaction mechanism is worth borrowing and what should NOT be copied.
- **Zero-Color Layout Hypotheses + Interactive Wireframe Artifact (`wireframe-v1.html`):** Generate two meaningfully different structural proposals using declarative diagram subgraphs (Mermaid `flowchart TB`, D2, PlantUML) AND a full-bleed interactive zero-color wireframe HTML Artifact (`UserFacing: true`).
- **Closed-Loop Self-Critique Before Asking:** Render the wireframe in a headless browser, capture & inspect screenshots via `view_file`, auto-fix any layout/chrome defects, and ONLY THEN ask the user to approve where zones live.

### Phase 3: Test Tactile Interactions in a Rough Prototype
- **Interaction Contract:** Specify triggers, visible results, keyboard shortcuts, focus targets, save behaviors, and recovery mechanics in plain English.
- **Rough Prototyping (`wireframe-v2.html`, `wireframe-v3.html`):** Build only enough interactive behavior to test uncertain mechanics (draggable splitters, tree expansion, inline editing vs split diff) without premature styling, preserving every version (`v1`, `v2`, `v3`) in `docs/.cgspec/prototypes/`.

### Phase 4: Develop Visual Direction & Positive Quality Rules
- **Translate Human Reactions:** Convert desired pacing (e.g. "quiet editorial notebook") into information density, typographic scale, surface rhythm, and 1 dominant brand anchor.
- **Positive Design Standards:** Replace negative bans with positive design rules (legibility, language coverage, clear hierarchy, labeled fixtures).
- **Comparative Styling:** Create two visual directions using the exact same layout and content to ensure fair comparison.

### Phase 5: Model States & Build Evaluated Milestone Prototype
- **Coexisting State Matrix:** Model states at both screen and component level (`Loading`, `Empty`, `Recoverable Error`, `Offline`, `Filtered`, `Conflict`).
- **Milestone Baseline Prototype:** Deliver single-file, self-contained HTML (`docs/.cgspec/prototypes/prototype-v0.1.html`) with an interactive state switcher.
- **Browser Verification Gate:** Capture desktop and compact viewports, verify keyboard-only completion, and record results in `docs/03-EXPERIENCE.md`.

---

## Supporting Architecture & Sub-Modules

### Playbooks (`playbooks/`)
- [`playbooks/01-discovery.md`](playbooks/01-discovery.md): Task brief, persona, journey mapping, focal screen selection.
- [`playbooks/02-layout-and-interaction.md`](playbooks/02-layout-and-interaction.md): Reference scouting, zero-color declarative wireframes (Mermaid/D2/PlantUML), spatial zoning.
- [`playbooks/03-visual-direction.md`](playbooks/03-visual-direction.md): Tactile density, typography pairings, surgical brand anchor, positive standards.
- [`playbooks/04-prototyping-and-testing.md`](playbooks/04-prototyping-and-testing.md): Coexisting state matrix, zero-build single-file HTML prototype (`prototype-v0.1.html`).
- [`playbooks/05-implementation-review.md`](playbooks/05-implementation-review.md): Production fidelity audit and deviation logging.

### Templates (`templates/`)
- [`templates/design-brief.md`](templates/design-brief.md): Initial user discovery and scope boundaries.
- [`templates/screen-spec.md`](templates/screen-spec.md): Detailed screen inventory, wireframe, and state matrix.
- [`templates/reference-analysis.md`](templates/reference-analysis.md): Deconstruction of real-world patterns.
- [`templates/decision-record.md`](templates/decision-record.md): UX decision record with explicit reopening conditions.
- [`templates/usability-test.md`](templates/usability-test.md): Usability test observation record.

### References (`references/`)
- [`references/anti-slop-codex.md`](references/anti-slop-codex.md): Prohibitions against generic AI artifacts and disembodied styling.
- [`references/quality-rubric.md`](references/quality-rubric.md): 5-dimension scoring rubric (Hierarchy, Ergonomics, Typography, States, Keyboard).
- [`references/accessibility-checklist.md`](references/accessibility-checklist.md): WCAG AA and power-user accessibility criteria.
- [`references/interaction-patterns.md`](references/interaction-patterns.md): Concrete mechanical recipes (In-place editing, Jump-lists, Drawers, Keycaps).

