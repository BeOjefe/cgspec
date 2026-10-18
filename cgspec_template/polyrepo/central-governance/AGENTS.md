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
   Keep spines as single files in `docs/spines/` in `v0.1`. Sprout into a numbered folder (`docs/spines/02-OOUX/`) only when a spine exceeds 500 lines or reaches multi-squad `v0.2+`.
9. **Law 9 — Main Agent Chat Insulation (`cgspec-inspector` & `cgspec-council-debater`):**
   Nobody talks to the human user except the Main Agent. Whenever spawning multi-agent councils (`/cgspec-council`) or multi-screen UI/slice swarms (`/cgspec-ui-ux`, `/cgspec-slice`), the Main Agent spawns **ONLY ONE** child subagent ([`cgspec-inspector`](./agents/cgspec-inspector.md) or Council Supervisor). Never spawn multiple workers directly from the Main Agent (prevents subagent turn-completion spam in user chat), and never spawn `type="research"` for builders or auditors.
10. **Law 10 — Proactive Discovery & 5-Tier Insulated Swarm (`/cgspec-ui-ux` & `/cgspec-slice`):**
    The human user is an executive curator, NOT a UI draftsman or bug hunter. The AI already has the domain nouns and flows (`docs/spines/02-OOUX.md`). Adapt Stage 2 to the project's **Surface Profile** (`Profile A: Simple Website`, `Profile B: Mobile iOS/Android`, `Profile C: Web Workspace`, `Profile D: CLI/TUI`), automatically increment monotonic versioned files (`scr<NN>-wireframe-v<N+1>.html` where $v(N+1) = \max(\text{existing}) + 1$, never waiting for human naming), and execute the **Proactive Discovery + 5-Tier Swarm**:
    - **Tier 0 (Proactive Scouting & Multi-Archetype Presentation):** Before writing code, the AI must autonomously scout 2–3 real-world gold-standard products matching the OOUX domain (e.g. GitHub, Linear, Cloudflare, Supabase) via web search or DevTools MCP, extract design DNA, and present 2–3 distinct structural/aesthetic archetypes with side-by-side trade-offs. The user's role is editorial selection, not manual drafting.
    - **Tier 1 (`cgspec-inspector`):** Receives cold facts only (`spines/01..05` + `quality-rubric.md`), spawns $K$ [`cgspec-builder`](./agents/cgspec-builder.md) agents (1 per screen/module), and sends them a **Builder Peer Directory** via `send_message` so they coordinate shared headers, tokens, and route contracts laterally.
    - **Tier 2 (`cgspec-builder` $\times K$ — Phase A Self-Verification):** Each builder writes strictly to disk in `docs/prototypes/` (never dumping raw HTML/code into chat messages), runs `docs/_cgspec/01-script/visual_audit.py` (`0 errors`), inspects `1440x900`, `1180x800`, and `375x812` screenshots via `view_file`, and verifies `01-INTENT`/`02-OOUX` completeness before reporting to `cgspec-inspector`.
    - **Tier 3 (`cgspec-unit-adversary` $\times K$ — Inner `while unit_verdict_i != PASS` Loop):** Each builder is audited by a dedicated, cold-facts-only [`cgspec-unit-adversary`](./agents/cgspec-unit-adversary.md) (wired with an **Adversary Peer Directory** via `send_message` to check cross-screen parity). Each pair loops (`Fix -> Phase A Self-Verify -> Re-Audit`) **while `unit_verdict_i != PASS`**.
    - **Tier 4 (`cgspec-chief-adversary` $\times 1$ — Outer `while global_verdict != PASS` Loop):** Once all $K$ Unit Adversaries return `PASS`, [`cgspec-chief-adversary`](./agents/cgspec-chief-adversary.md) audits the integrated multi-screen build across all spines. If `GLOBAL_VERDICT == FAIL`, defects route back to the swarm until `GLOBAL_VERDICT: PASS (0 defects)`.
    - **Tier 5 (Human Validation & Deep Root-Cause Interview):** Only after `GLOBAL_VERDICT: PASS` does the Main Agent present to the user. **If the user says "No":** the Main Agent never immediately re-runs `cgspec-inspector`; it first interviews the user to deeply understand *why*, updates `docs/_memlog.md` and spines (`01..03`), confirms with the user, and only then re-dispatches `cgspec-inspector`.

11. **Law 11 — Disk-First Immediate Capture & 4-Bucket Triage:**
    Chat is ephemeral; disk is permanent truth. Before replying to multi-topic user feedback, triage and persist 100% of user input to disk **without derailing the active step**:
    - **Bucket A (Active Screen / Current Step):** Apply immediately to the active artifact/spine.
    - **Bucket B (Other Screens / Later UX Phases):** Record immediately in `docs/spines/03-EXPERIENCE.md`, `docs/prototypes/`, and `docs/_memlog.md` (do not code all screens at once).
    - **Bucket C (Backend / Future `v0.2+` Scope):** Record immediately in `docs/spines/02-OOUX.md`, `docs/spines/04-ARCHITECTURE.md`, or `docs/00-INBOX.md` (`Future Backlog v0.2+`).
    - **Bucket D (Technical Spikes, Benchmarks & Framework Evaluations):** Record immediately in `docs/_cgspec/02-research/RES-NNN-<slug>.md` and register in `docs/00-INDEX.md` (Section 5). Never lose technical discussions or let them clutter raw feature inboxes.
    Always synchronize top diagrams and bottom tables within any modified spine, then run `python3 docs/_cgspec/01-script/doctor.py --repo .` before concluding the turn.

---

## 2. Universal Hygiene & Engineering Standards
- **Zero Decorative Emojis:** No Unicode emojis or pictographs in chat or specs. Use clean Markdown headings and `-` bullets.
- **Specification Hub & Visible Engine Architecture (`docs/`):** Keep the project root and `docs/` clean, structured, and visible to developers, search tools (`ripgrep`), and file managers:
  - `docs/00-INDEX.md` (master compass and live status matrix)
  - `docs/spines/` (`01-INTENT.md` through `05-DELIVERY.md`)
  - `docs/adr/` (`ADR-001-...`, permanent architecture decision records)
  - `docs/slices/` (`SLICE-001-...`, bounded vertical slice contracts)
  - `docs/prototypes/` (`wireframe-v1.html..vN.html`, `prototype-v0.1.html`)
  - `docs/_memlog.md` (append-only chronological milestone and lock ledger)
  - `docs/_cgspec/` (visible engine room using underscore prefix for ripgrep indexing):
    - `docs/_cgspec/01-script/` (doctor.py, memlog.py, ingest.py, visual_audit.py)
    - `docs/_cgspec/02-research/` (RES-001-..., technical spikes, benchmarks)
    - `docs/_cgspec/03-council/` (COUNCIL-001-..., debate logs, transcripts)
    - `docs/_cgspec/_archive/` (superseded spines, drafts, legacy v1 artifacts)
- **Explicit Functional Actors & Capability-Driven UI:** Never use fictional persona names (`Sam`, `Maya`) or abstract tier codes (`L1/L2`). Use functional roles (`Organization Owner`, `Project Lead`, `Developer`, `Auditor`) and explicit permissions (`Owner` + `read | invoke | propose_edit | write | share | admin`). In UIs, hide actions the current role cannot perform instead of rendering disabled/conflicting buttons or debug role badges, and never leak `snake_case` schema identifiers into user-facing labels.
- **Topological Neutrality & Ports/Adapters:** Support Monorepo and Polyrepo equally (inspect workspace first or ask via `ask_question`; never force polyrepo overhead). Enforce strict Ports & Adapters isolation (`uv` for Python, `bun`/`pnpm` for TypeScript/JS).
- **Universal Multi-AI Lifecycle Hooks (`cgspec_hook.py`):** Enforces Law 3 (slice contract precedes code), Law 10 (strict zero emojis), and Law 11 (disk capture & zero drift) deterministically across all AI coding assistants (Antigravity via `.agents/hooks.json`, Claude Code via `CLAUDE.md`, Cursor via `.cursorrules`, and native Git via `.githooks/pre-commit`). Run `python3 docs/_cgspec/01-script/cgspec_hook.py install` to activate.

---

## 3. Progressive Skill Routing & 4 Entry Modes

| Lifecycle Stage / Entry Mode | Canonical Spine(s) | On-Demand Skill to Activate |
| :--- | :--- | :--- |
| **0. Init / Brownfield AST Ingestion** | `AGENTS.md`, `00-INDEX.md`, `docs/.cgspec/` | [`cgspec-init`](./skills/cgspec-init/SKILL.md) (`ingest.py` for existing repos) |
| **1. Brainstorming & OOUX Nouns** | `01-INTENT.md`, `02-OOUX.md`, `00-INBOX.md` | [`cgspec-forge`](./skills/cgspec-forge/SKILL.md) |
| **2. UI/UX, Wireframes & Prototypes** | `03-EXPERIENCE.md`, `docs/.cgspec/05-prototype/` | [`cgspec-ui-ux`](./skills/cgspec-ui-ux/SKILL.md) (`visual_audit.py` gate) |
| **3. Architecture & Trade-Off Debates** | `04-ARCHITECTURE.md`, `docs/.cgspec/04-adr/` | [`cgspec-council`](./skills/cgspec-council/SKILL.md) |
| **4–7. Vertical Slices, Testing & CI/CD** | `05-DELIVERY.md`, `docs/.cgspec/06-slice/` | [`cgspec-slice`](./skills/cgspec-slice/SKILL.md) (`doctor.py` gate) |
| **8. Mid-Flight Pivots & Migrations** | Affected spines + `docs/.cgspec/05-prototype/stash/` | [`cgspec-pivot`](./skills/cgspec-pivot/SKILL.md) |
