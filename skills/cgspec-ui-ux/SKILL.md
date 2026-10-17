---
name: cgspec-ui-ux
description: Stage 2 Dual-Spine UI & UX Compilation Engine. Use when designing screens, wireframes, UX flows, tactile ergonomics, design tokens, state matrices, or interactive HTML prototypes (03-EXPERIENCE.md) for websites, mobile apps (iOS/Android), web workspaces, or CLIs.
---

# cgspec-ui-ux

## 1. Contract (Inputs -> Outputs)
- **Stage:** `2. Design & Experience` (Inherits all global laws from [`AGENTS.md`](../../AGENTS.md)).
- **Requires:** Approved `docs/01-INTENT.md` and `docs/02-OOUX.md`.
- **Produces:**
  - **UX Deliverables (`docs/design/`):** Task brief (`brief.md`), mechanism reference analysis (`references.md`), tactile interaction decisions (`decisions/UXD-NNN.md`).
  - **UI Deliverables (`docs/03-EXPERIENCE.md` & `docs/.cgspec/prototypes/`):** Declarative spatial wireframes, versioned HTML wireframes (`wireframe-v1.html..vN.html`), design tokens, state matrix, and milestone prototype (`prototype-v0.1.html`).

---

## 2. Stage-Specific Rules

### 2.1 Adaptive Surface Profile Matrix
Calibrate geometry, input ergonomics, and required states to the project's **Target Surface Profile**:

| Surface Profile | Spatial Zoning Geometry | Ergonomics & Input | Required State Matrix | Executable Prototype |
| :--- | :--- | :--- | :--- | :--- |
| **Profile A: Simple Website** *(Landing, portfolio, docs)* | **Vertical Scroll Storyboard:** Sticky Header -> Hero + Proof -> Contrast Strip -> Bento Showcase -> FAQ & Footer. *(No 3-pane sidebars!)* | Reading rhythm, above-the-fold clarity, responsive mobile stacking. | **4 States:** `Desktop Wide`, `Mobile Compact`, `Hover/Expanded`, `Form Validation`. | Full-bleed responsive HTML with Desktop/Mobile switcher. |
| **Profile B: Mobile App (iOS / Android)** *(SwiftUI, Kotlin, Flutter, RN)* | **Thumb-Zone Vertical Stack:** Top Bar -> Scrollable Canvas -> Draggable Bottom Sheet (`Peek/Half/Full` detents) -> Bottom Tab Bar. | `44x44pt` / `48x48dp` targets, one-handed thumb arc, swipe actions, **Virtual Keyboard Avoidance**. | **7 States:** `Populated`, `Skeleton`, `Empty`, `Error`, `OS Permission`, `Offline`, `Keyboard Up (40% occluded)`. | `390x844` (iOS) / `412x915` (Android) frame with sheet & keyboard switcher. |
| **Profile C: Web Workspace** *(SaaS, dashboard, IDE)* | **Multi-Pane Viewport:** Header -> Left Multi-Root Explorer Rail -> Center Canvas -> Right Drawer. | `Cmd+K` bar, draggable `col-resize` splitters, click-to-fold rail, `32-40px` dense rows. | **7 States:** `Populated`, `Skeleton`, `Empty`, `Error`, `Denied 403`, `Offline`, `Filtered Zero`. | Full-viewport (`100vh`) workspace with state & role switcher. |
| **Profile D: CLI / TUI** *(Terminal tool, daemon, SDK)* | **Command & Stream Topology:** Subcommand tree, flag matrix, split TUI panes, `stdout` vs `stderr`. | Pipeability, `--json` flag, TTY spinner vs quiet mode, exit codes. | **5 States:** `Success (0)`, `Help`, `Validation Error (1)`, `Auth/Net Error`, `Pipe Mode`. | Interactive terminal transcript / TUI simulator in HTML. |

### 2.2 Stage 2 Execution Invariants
1. **One Focal Screen at a Time (Phase Fidelity Ceiling):** Prototype strictly **1 focal screen** (`SCR-01`) until locked; keep other navigation items as inactive placeholders (`[Scheduled for SCR-02]`). In Phase 2 (Macro Layout), render only zone boundaries, resizable splitters, and navigation trees—never invent uninterviewed micro-buttons.
2. **Visual-First Choice & Dual-Target Versioning (`v1 -> v2 -> v3`):** Render the interactive HTML wireframe Artifact (`UserFacing: true` in `<appDataDir>/brain/<conversation-id>/wireframe-vN.html` for side-pane preview—never inline `<agent-embed>` for desktop layouts) AND archive to `docs/.cgspec/prototypes/wireframe-vN.html` **before** calling `ask_question` on layout choices. Never overwrite prior iterations.
3. **2-Phase Verification & Independent Adversarial Critic Loop (`while verdict != PASS`):**
   - **Phase A (Exhaustive Self-Verification First):** Run `visual_audit.py`, open the HTML in headless Chrome across `1440x900` and `1180x800`, click through every interactive state (`Preview`, `Edit Mode`, `Diff + Toggle Back`, `Folder View`, `Full Repo Code View`, `Drawer Closed`), inspect every screenshot via `view_file`, and fix all violations of the 8 Structural UI Coherence Laws in [`references/quality-rubric.md`](references/quality-rubric.md).
   - **Phase B (Facts-Only Adversarial Critic Subagent Loop):** Before showing or claiming work done to the user, spawn an independent `Adversarial UX & Spec Critic` subagent (`invoke_subagent`, `TypeName: "self"`) using the **Facts-Only Prompt** in [`references/quality-rubric.md`](references/quality-rubric.md#part-3-phase-b-facts-only-adversarial-critic-subagent-loop-while-verdict--pass). Loop (`Fix defects -> Re-run Phase A -> send_message to Critic`) **while `verdict != PASS`**. Never present to the user until the Critic returns `VERDICT: PASS (0 defects)`.
4. **Design Stash Protocol (Mid-Design Scope Pivots):** If a user spark requires reopening Stage 1 (`01-INTENT`/`02-OOUX`), snapshot active prototypes to `docs/.cgspec/prototypes/stash/<timestamp>-<name>/`, log the pause in `.memlog.md`, re-lock Stage 1, and perform a Design Delta Assessment upon returning.

---

## 3. Workflow (Progressive Playbooks)
Load only the playbook and references for the active step:
1. **Step 1 — Brief & Focal Screen Selection:** [`playbooks/01-discovery.md`](playbooks/01-discovery.md) + [`templates/design-brief.md`](templates/design-brief.md)
2. **Step 2 — References & Zero-Color Wireframe (`wireframe-v1.html`):** [`playbooks/02-layout-and-interaction.md`](playbooks/02-layout-and-interaction.md) + [`templates/reference-analysis.md`](templates/reference-analysis.md)
3. **Step 3 — Tactile Ergonomics (`wireframe-v2.html`):** [`references/interaction-patterns.md`](references/interaction-patterns.md) + [`templates/decision-record.md`](templates/decision-record.md)
4. **Step 4 — Visual Direction & Positive Tokens:** [`playbooks/03-visual-direction.md`](playbooks/03-visual-direction.md) + [`references/anti-slop-codex.md`](references/anti-slop-codex.md)
5. **Step 5 — State Matrix & Milestone Prototype (`prototype-v0.1.html`):** [`playbooks/04-prototyping-and-testing.md`](playbooks/04-prototyping-and-testing.md) + [`references/quality-rubric.md`](references/quality-rubric.md) + [`references/accessibility-checklist.md`](references/accessibility-checklist.md)
- *Post-Build Audit:* [`playbooks/05-implementation-review.md`](playbooks/05-implementation-review.md)

---

## 4. Exit Gate
Before presenting any wireframe/prototype or entering Stage 3 (`04-ARCHITECTURE.md`), confirm:
1. **Phase A Self-Verification:** `visual_audit.py` + `doctor.py --strict-emojis` (`0 errors`) + multi-state screenshots inspected via `view_file`.
2. **Phase B Adversarial Critic Loop:** Independent `Adversarial UX & Spec Critic` subagent returned `VERDICT: PASS (0 defects)`.
3. **Human Lock:** Explicit user approval recorded in `docs/.memlog.md`.
```bash
python3 docs/.cgspec/scripts/visual_audit.py docs/.cgspec/prototypes/prototype-v0.1.html --screenshot-dir /tmp/cgspec-shots
python3 docs/.cgspec/scripts/doctor.py --repo . --strict-emojis
```
