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
  - **UI Deliverables (`docs/03-EXPERIENCE.md` & `.cgspec/prototypes/`):** Declarative spatial wireframes, versioned HTML wireframes (`wireframe-v1.html..vN.html`), design tokens, state matrix, and milestone prototype (`prototype-v0.1.html`).

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

### 2.2 Stage 2 Execution Invariants (5-Tier Insulated Swarm)
1. **Main Agent Insulation (`cgspec-inspector` Only):**
   - **Never spawn multiple builders directly from the Main Agent** (which leaks raw subagent completions into the user's primary chat window) and **never spawn `type="research"` for builders or auditors**.
   - The Main Agent registers and invokes **ONLY ONE** child subagent: [`cgspec-inspector`](../../agents/cgspec-inspector.md) (`enable_write_tools=True`, `enable_subagent_tools=True`), passing cold factual paths (`01-INTENT.md`, `02-OOUX.md`, `03-EXPERIENCE.md`, `quality-rubric.md`).
2. **Tier 2 Peer-to-Peer Builders (`cgspec-builder` $\times K$) + Output Token Limit Guard + Phase A Self-Verification:**
   - `cgspec-inspector` spawns $K$ [`cgspec-builder`](../../agents/cgspec-builder.md) agents (1 per screen or surface) and distributes a **Builder Peer Directory** via `send_message` so builders coordinate shared header chrome, CSS tokens, and cross-screen navigation links laterally.
   - **Output Token Limit Guard (`< 600` Lines per `write_to_file`):** Never emit a 1,500–2,500 line monolithic HTML file in a single `write_to_file` call (which hits the LLM output token limit). Either write modular per-screen files (`scr-01-<slug>.html`, `< 600` lines each) or, when incrementing `v(N-1) -> vN`, run `cp wireframe-v(N-1).html wireframe-vN.html` via `run_command` and apply surgical `replace_file_content` edits (`< 300` lines per call).
   - Builders write strictly to disk (never dumping raw HTML into chat messages) and execute **Phase A Exhaustive Self-Verification** (`visual_audit.py` exit `0` + `view_file` inspection of `1440x900`, `1180x800`, and `375x812` PNGs + `01-INTENT`/`02-OOUX` check) before notifying `cgspec-inspector`.
3. **Tier 3 Peer-to-Peer Unit Adversaries (`cgspec-unit-adversary` $\times K$) — Inner `while (unit_verdict_i != PASS)` Loop:**
   - `cgspec-inspector` pairs each `Builder_i` with a dedicated [`cgspec-unit-adversary`](../../agents/cgspec-unit-adversary.md) given **cold facts only** (file path, screenshot paths, `01..03` spines, `quality-rubric.md`) and an **Adversary Peer Directory** (`send_message`) to verify cross-screen parity.
   - Each `(Builder_i, Unit Adversary_i)` pair loops (`Fix -> Phase A Self-Verify -> Re-Audit`) **while `unit_verdict_i != PASS`**.
4. **Tier 4 Chief Global Adversarial Gatekeeper (`cgspec-chief-adversary` $\times 1$) — Outer `while (global_verdict != PASS)` Loop:**
   - Only when **all $K$ Unit Adversaries** report `PASS (0 defects)` does `cgspec-inspector` invoke [`cgspec-chief-adversary`](../../agents/cgspec-chief-adversary.md) to audit the integrated multi-screen build, end-to-end user journeys, and version non-destruction (`v1..vN`). If `GLOBAL_VERDICT == FAIL`, `cgspec-inspector` routes defects back to the swarm until `GLOBAL_VERDICT: PASS (0 defects)`.
5. **Tier 5 Human Validation & Deep Root-Cause Interview (`If User Says No`):**
   - Only after `GLOBAL_VERDICT: PASS` does `cgspec-inspector` return to the Main Agent to present the verified build (`UserFacing: true` in `<appDataDir>/brain/<conversation-id>/wireframe-vN.html` + `.cgspec/prototypes/wireframe-vN.html`).
   - **If the user says "No" or rejects any aspect:** The Main Agent **MUST NOT** immediately re-run `cgspec-inspector`. It must first interview the user to deeply understand *why*, record the root cause in `docs/.memlog.md`, update `01-INTENT.md` / `02-OOUX.md` / `03-EXPERIENCE.md`, confirm the updated spine with the user, and only then re-invoke `cgspec-inspector`.

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
2. **Inner & Outer Adversarial Loops:** All $K$ [`cgspec-unit-adversary`](../../agents/cgspec-unit-adversary.md) agents returned `UNIT_VERDICT: PASS (0 defects)` AND [`cgspec-chief-adversary`](../../agents/cgspec-chief-adversary.md) returned `GLOBAL_VERDICT: PASS (0 defects)`.
3. **Human Lock:** Explicit user approval recorded in `docs/.memlog.md`.
```bash
python3 .cgspec/scripts/visual_audit.py --html .cgspec/prototypes/prototype-v0.1.html --screenshot-dir /tmp/cgspec-shots
python3 .cgspec/scripts/doctor.py --repo . --strict-emojis
```
