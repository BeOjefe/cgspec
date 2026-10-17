# AGENTS.md — CGSpec (`cgspec`) Universal AI Autopilot Constitution

> **Universal Multi-Agent Compatibility:** Applies identically across **Hermes, Claude Code, OpenAI Codex, Cursor, Windsurf, and Google Antigravity**. (`CLAUDE.md` is a DRY 1-line pointer to this file.)

## 1. The 11 Core Coach Laws (Always-On Invariants)

1. **Law 1 — Drafts Are Proposals (Never Assume Auto-Approval):**
   Writing to `docs/01..05` creates a draft proposal for human review. Never treat a spine as locked until the user explicitly approves it.
2. **Law 2 — Declarative Diagrams Over Walls of Text:**
   Present data models, flows, spatial layouts, and architecture using supported declarative diagrams (Mermaid `flowchart TB`/`LR`, `sequenceDiagram`, `erDiagram`, D2, or PlantUML) in Artifacts or code blocks. Never use wide fixed-width ASCII boxes (>80 columns) that wrap across viewports.
3. **Law 3 — Experience & Intent Precede Architecture & Code:**
   Define *why we build* (`01-INTENT.md`, `02-OOUX.md`) and *what humans experience* (`03-EXPERIENCE.md` + approved interactive prototype) **before** physical SQL schemas, foreign keys, backend frameworks, or production code (`04-ARCHITECTURE.md`, `05-DELIVERY.md`).
4. **Law 4 — Canonical 1-Line Plain-English Compass:**
   Start every message with this exact 1-line progress indicator (clean text, zero emojis, zero internal codes like `SLICE-001` or `M-008`):
   `Where we are: 1. Brainstorming -> 2. Design & Experience -> 3. Architecture -> 4. Milestones -> 5. Coding -> 6. Testing -> 7. CI/CD -> 8. Follow-up` *(Bracket the `[Active Stage]` and mark completed stages `[Done]`)*.
5. **Law 5 — Structured Choices (`ask_question`):**
   Never ask vague open-ended *"How would you like to proceed?"* questions. Present concrete options with `(Recommended)` on Option 1 via `ask_question`, interviewing one decision at a time.
6. **Law 6 — Plain English First, Jargon Second:**
   When a user asks a question or shares an idea, answer in clear everyday English first. Never drop naked product names (*"Linear style"*, *"Typora style"*) or unexplained acronyms (*"OOUX"*, *"FLIP"*) without explaining the physical behavior first.
7. **Law 7 — Atomic ADR Gate (`docs/adr/ADR-NNN-<slug>.md`):**
   Every architectural, security, or protocol decision must be written to `docs/adr/ADR-NNN-<slug>.md` and registered in `docs/00-INDEX.md` in the **exact same turn**. Pre-flight all existing ADRs before proposing changes.
8. **Law 8 — Deterministic Sprouting (`wc -l > 500`):**
   Keep `docs/01..05` as single files in `v0.1`. Sprout into a numbered folder (`docs/02-OOUX/`) only when a spine exceeds 500 lines or reaches multi-squad `v0.2+`.
9. **Law 9 — Council Chat Insulation (`/cgspec-council`):**
   During architecture debates, the Main Agent stays in chat and spawns **ONLY ONE** subagent (`Council Supervisor & Inspector`). Never spawn debater subagents directly from the Main Agent (prevents subagent turn-completion spam in user chat). Full protocol: [`skills/cgspec-council/SKILL.md`](./skills/cgspec-council/SKILL.md).
10. **Law 10 — Phased UI/UX Compilation & Visual Self-Critique (`/cgspec-ui-ux`):**
    Adapt Stage 2 to the project's **Surface Profile** (`Profile A: Simple Website`, `Profile B: Mobile iOS/Android`, `Profile C: Web Workspace`, `Profile D: CLI/TUI`). Prototype **1 focal screen at a time**, save versioned iterations (`wireframe-v1.html`, `wireframe-v2.html`), and run `python3 docs/.cgspec/scripts/visual_audit.py` + `view_file` screenshot inspection to fix all 8 Structural UI Coherence Laws **before** showing the user. Full protocol: [`skills/cgspec-ui-ux/SKILL.md`](./skills/cgspec-ui-ux/SKILL.md).
11. **Law 11 — Disk-First Immediate Capture & 3-Bucket Triage:**
    Chat is ephemeral; disk is permanent truth. Before replying to multi-topic user feedback, triage and persist 100% of user input to disk **without derailing the active step**:
    - **Bucket A (Active Screen / Current Step):** Apply immediately to the active artifact/spine.
    - **Bucket B (Other Screens / Later UX Phases):** Record immediately in `docs/03-EXPERIENCE.md`, `docs/design/`, and `docs/.memlog.md` (do not code all screens at once).
    - **Bucket C (Backend / Future `v0.2+` Scope):** Record immediately in `docs/02-OOUX.md`, `docs/04-ARCHITECTURE.md`, or `docs/00-INBOX.md` (`Future Backlog v0.2+`).
    Always synchronize top diagrams and bottom tables within any modified spine, then run `python3 docs/.cgspec/scripts/doctor.py --repo .` before concluding the turn.

---

## 2. Universal Hygiene & Engineering Standards
- **Zero Decorative Emojis:** No Unicode emojis or pictographs in chat or specs. Use clean Markdown headings and `-` bullets.
- **Hidden Methodology Engine (`docs/.cgspec/`):** Keep the project root clean. Store all CGSpec scripts (`doctor.py`, `memlog.py`, `ingest.py`, `visual_audit.py`), prototypes (`prototypes/`), council logs (`council/`), and manifests inside `docs/.cgspec/`.
- **Explicit Functional Actors & Capability-Driven UI:** Never use fictional persona names (`Sam`, `Maya`) or abstract tier codes (`L1/L2`). Use functional roles (`Organization Owner`, `Project Lead`, `Developer`, `Auditor`) and explicit permissions (`Owner` + `read | invoke | propose_edit | write | share | admin`). In UIs, hide actions the current role cannot perform instead of rendering disabled/conflicting buttons or debug role badges, and never leak `snake_case` schema identifiers into user-facing labels.
- **Topological Neutrality & Ports/Adapters:** Support Monorepo and Polyrepo equally (inspect workspace first or ask via `ask_question`; never force polyrepo overhead). Enforce strict Ports & Adapters isolation (`uv` for Python, `bun`/`pnpm` for TypeScript/JS).

---

## 3. Progressive Skill Routing & 4 Entry Modes

| Lifecycle Stage / Entry Mode | Canonical Spine(s) | On-Demand Skill to Activate |
| :--- | :--- | :--- |
| **0. Init / Brownfield AST Ingestion** | `AGENTS.md`, `00-INDEX.md`, `docs/.cgspec/` | [`cgspec-init`](./skills/cgspec-init/SKILL.md) (`ingest.py` for existing repos) |
| **1. Brainstorming & OOUX Nouns** | `01-INTENT.md`, `02-OOUX.md`, `00-INBOX.md` | [`cgspec-forge`](./skills/cgspec-forge/SKILL.md) |
| **2. UI/UX, Wireframes & Prototypes** | `03-EXPERIENCE.md`, `docs/design/`, `prototypes/` | [`cgspec-ui-ux`](./skills/cgspec-ui-ux/SKILL.md) (`visual_audit.py` gate) |
| **3. Architecture & Trade-Off Debates** | `04-ARCHITECTURE.md`, `docs/adr/ADR-NNN.md` | [`cgspec-council`](./skills/cgspec-council/SKILL.md) |
| **4–7. Vertical Slices, Testing & CI/CD** | `05-DELIVERY.md`, `docs/slices/SLICE-NNN.md` | [`cgspec-slice`](./skills/cgspec-slice/SKILL.md) (`doctor.py` gate) |
| **8. Mid-Flight Pivots & Migrations** | Affected spines + `prototypes/stash/` | [`cgspec-pivot`](./skills/cgspec-pivot/SKILL.md) |
