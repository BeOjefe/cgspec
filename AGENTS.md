# AGENTS.md — CGSpec (`cgspec`) Universal AI Autopilot Constitution

> **Universal Multi-Agent Compatibility:** Applies identically across **Hermes, Claude Code, OpenAI Codex, Cursor, Windsurf, and Google Antigravity**. (`CLAUDE.md` is a DRY 1-line pointer to this file.)

## 1. The 11 Core Coach Laws (Read Before Every Turn)

1. **Law 1 — The Draft Document is a Proposal (Never Assume Auto-Approval):**
   - Writing to `docs/01..05` is creating a **draft proposal** for the user to review. It is **never locked** until the user explicitly approves it!
   - Always make it clear: *"I drafted this proposal in `docs/02-...`. Please review it and tell me what you'd like changed."*

2. **Law 2 — Prefer Visual Mermaid Diagrams in Artifacts (No Long Walls of Text):**
   - When presenting data models, user flows, or architecture, **always provide a clean visual Mermaid diagram in an Artifact or fenced code block**.
   - Humans absorb relationships visually much faster than reading 100 lines of plain text in chat.

3. **Law 3 — Experience & Intent Precede Architecture & Code (Zero Premature Tech):**
   - The user defines *why we build* (brainstorming, problem definition, domain nouns) and *what they experience* (macro spatial layout, tactile ergonomics, visual tokens, interactive prototype) **FIRST**.
   - Technical implementation ("how": physical SQL tables, foreign keys, backend frameworks, ORMs, and servers) is **strictly forbidden** until the human has tested and approved the interactive prototype!
   - **The Coherent 8-Stage Lifecycle:**
     `1. Brainstorming & Intent (01-INTENT, 02-OOUX) ──▶ 2. Design & Experience (03-EXPERIENCE) ──▶ 3. Physical Architecture (04-ARCH) ──▶ 4. Milestone Slices (05-DELIVERY) ──▶ 5. Modular Coding (src/) ──▶ 6. Testing & Browser QA (doctor.py) ──▶ 7. CI/CD & Deployment ──▶ 8. Follow-up & Backlog Evolution (00-INBOX)`

4. **Law 4 — 1-Line Plain-English Compass:**
   Start every message with the 1-line progress indicator so the human always knows where we are (clean text, zero emojis):
   `Where we are: 1. Brainstorming [Done] -> [2. Design & Experience] -> 3. Architecture -> 4. Milestones -> 5. Coding -> 6. Testing -> 7. CI/CD -> 8. Follow-up`
   **Never** use internal methodology jargon or cryptic codes (`Spine`, `SLICE-001`, `SCR-05`, `M-008`).

5. **Law 5 — Never Ask Vague Open-Ended "How to Proceed?" Questions:**
   - Always present **concrete, numbered options** (with `(Recommended)` on Option 1) using the interactive `ask_question` tool.

6. **Law 6 — Explain in Plain English First, Ask Second:**
   - If the user asks a question, expresses confusion, or shares an open-ended idea, **answer in clear, natural conversational English first**.

7. **Law 7 — Architectural Choices Produce ADRs (`docs/adr/ADR-NNN-<slug>.md`):**
   - Whenever an architectural choice, trade-off, or cross-cutting protocol is decided (e.g. database tech, auth, crypto, multi-repo mounting, zone separation), the agent **MUST write a formal ADR in `docs/adr/`** and record it in `docs/00-INDEX.md`.
   - **Atomic ADR Gate:** An agent is **strictly forbidden** from declaring a phase complete, asking to move to the next stage, or taking "memlog-only" shortcuts. If a decision touches architecture, security, or protocols, the `docs/adr/ADR-NNN-<slug>.md` file **MUST be written and registered in Git in the exact same turn**.
   - **Pre-Flight ADR Check:** Every AI agent working on architecture or implementation MUST read all existing ADRs in `docs/adr/` to obey established system invariants and avoid re-litigating locked decisions.

8. **Law 8 — Deterministic Sprouting with Numeric Preservation:**
   - **v0.1 Single File Default:** Spine documents remain single files (`docs/01-INTENT.md` .. `docs/05-DELIVERY.md`) for high reading speed and low prompt token usage.
   - **Deterministic Sprout Trigger:** An agent may ONLY sprout a file into a directory if:
     - **Condition A:** The spine file exceeds 500 lines on disk (`wc -l > 500`), OR
     - **Condition B:** The project advances to `v0.2+` with multiple concurrent squads.
   - **Numeric Invariant:** Sprouted directories **MUST retain the two-digit numerical prefix** to maintain strict ordering:
     `docs/01-INTENT.md` $\rightarrow$ `docs/01-INTENT/`, `docs/02-OOUX.md` $\rightarrow$ `docs/02-OOUX/`, `docs/03-EXPERIENCE.md` $\rightarrow$ `docs/03-EXPERIENCE/`, `docs/04-ARCHITECTURE.md` $\rightarrow$ `docs/04-ARCHITECTURE/`.

9. **Law 9 — Strict Council Subagent Tree (Main Agent Spawns ONLY Supervisor):**
   - When executing `/cgspec-council`, the **Main Agent MUST remain in the chat with the user** at all times and provide a high-signal chat briefing (Locked Question, Tension, Stakes, Target Invariant).
   - **Single Subagent Invariant:** The Main Agent calls `invoke_subagent` for **EXACTLY ONE subagent**: `Council Supervisor & Inspector`.
   - **Zero Debater Subagents in Main Agent:** The Main Agent is **strictly forbidden from placing debaters in its subagents array**. When debater subagents are spawned directly by the Main Agent, their turn completions arrive as unwanted message bubbles in the user's primary chat window.
   - The **Supervisor** executes the 3 orthogonal lenses (`Systems`, `Security`, `Pragmatic DX`) in the background council workspace on disk (`debater-1-round-0k.md`, `debater-2-round-0k.md`, `debater-3-round-0k.md`), synthesizes each round (`round-0k.md`), and relays ONLY 3-line status updates back to the Main Agent.
   - **Zero Decorative Emojis:** The Main Agent and Supervisor communicate using calm, clean engineering typography without decorative emojis.

10. **Law 10 — Phased Design Locking Funnel (No Jumping Directly to Code):**
    - High-craft UI/UX cannot be generated in a single prompt. Design is at the absolute center of CGSpec. Every screen must proceed through 5 locked, versioned stages before final scaffolding:
      1. **Stage 1: Macro Spatial Zoning & Zero-Color Wireframe:** Define where parts and zones live on screen (Top Header Bar, Left Navigation Rail, Center Workspace, Right Contextual Drawer) using clean ASCII layout blockouts or visual wireframes in an Artifact. Zero colors, zero themes, zero micro-behaviors yet. The human must see and approve *where things are placed* before discussing how they behave!
      2. **Stage 2: Tactile Ergonomics & Direct Manipulation:** Once zones are placed, define how hands navigate between zones and how editing operates inside the primary workspace (e.g. inline editing vs split preview, keyboard shortcuts, command palette).
      3. **Stage 3: Design Tokens & Visual Direction:** Lock typography pairing (Display vs Sans vs Monospace), canvas atmospheric texture, and signature brand anchor (1 dominant primary). Recorded in `docs/03-EXPERIENCE.md`.
      4. **Stage 4: Component & State Matrix:** Define all 7 lifecycle states (`Populated`, `Loading Skeleton`, `Empty`, `Error`, `Denied 403`, `Offline`, `Partial`) with realistic worst-case edge data. Locked in `docs/03-EXPERIENCE.md`.
      5. **Stage 5: Interactive Prototype Baseline (`prototype-v0.1.html`):** Single-file executable HTML with working state switcher and real keyboard navigation. Never mutate in place; versioned as `prototype-v0.1.html` with ADR experiments as `prototype-ADR-NNN.html`.
    - **One-Question-at-a-Time Interview:** The agent must interview the user on layout, flow, and taste decisions one question at a time (via `ask_question`), locking each decision into `docs/.memlog.md` with tags `lock,ux`.

11. **Law 11 — Disk-First Immediate Capture (Never Leave Truth in Ephemeral Chat):**
    - **Chat is Ephemeral, Disk is Permanent Truth:** Chat context gets compacted, truncated, and lost across sessions. An idea, decision, constraint, spark, or architectural preference mentioned in chat **does not exist until it is written to disk**.
    - **Mandatory Same-Turn Write:** Whenever an idea, spark, decision, consensus, or user preference emerges during a turn, the agent **MUST write it to disk** (`docs/00-INBOX.md`, `docs/.memlog.md`, an active spine `docs/01..05`, or `docs/adr/`) **in the exact same turn before concluding its execution**.
    - **Zero Human Reminder Burden:** The human architect must **NEVER** have to remind the agent to write things down (*"did you save that?"*, *"write that down before speaking"*). If an agent responds about an idea, decision, or spark without first persisting it to disk, it is a catastrophic violation of Law 11.
    - **Immediate Execution Sequence:** When receiving an idea or making an architectural discovery, the sequence is non-negotiable:
      1. Commit to disk (`00-INBOX.md`, `.memlog.md`, or the active spine).
      2. Run `doctor.py` if modifying spines or ADRs.
      3. Respond to the user with the exact file diff or citation.

## 2. Universal Engineering & Communication Rules
- **Language:** English only.
- **Zero Decorative Emoji Spam:** Never decorate chat headers, bullet points, or paragraphs with decorative emojis (📍, ⚖️, 👥, 🏛️, 📦, 🟢, 🔴, ⚠️, 🚀, 💡, ✨). Communicate with clean, calm, professional engineering typography (clean Markdown headings `#`, `##`, `###` and standard `-` bullets).
- **Anti-Jargon & No Naked Product Names:** Never assume the user knows niche apps (*"Typora style"*, *"Bear style"*, *"Linear style"*) or technical design jargon (*"OOUX"*, *"WYSIWYG"*, *"FLIP animation"*). Always explain the physical tactile behavior in clear, everyday English first (*"When you click a line, the raw symbols appear so you can edit; when you move your cursor away, they hide and become formatted text"*), and accompany references with a concrete visual or link in an Artifact.
- **Zero Hallucinated Roadmaps (v0.1 Focus):** Never invent speculative future features in `docs/00-INBOX.md` or spines for `v0.2+` out of thin air. We only know what we need for `v0.1`. Thinking of v0.1, v0.2, and v0.3 all at once creates artificial bloat. The backlog strictly captures sparks explicitly voiced by the user or genuine off-scope items deferred during active slices.
- **No Fictional Names:** Never invent abstract tier codes (`L1/L2/L3`) or made-up human persona names (`Sam`, `Maya`, `Mary`). Always use explicit functional actors (`Organization Owner`, `Project Lead`, `Developer`, `AI Agent`) and explicit permissions (`Owner` + `read | invoke | propose_edit | write | share | admin`).
- **Tooling Defaults:** Use `uv` for Python and `bun`/`pnpm` for TypeScript/JS.
- **Strict Modularity:** Enforce Ports & Adapters. Never allow UI components to import database or crypto clients directly.
- **Visual QA Gate:** Verify all UI changes in a real headless browser across all 7 required states (`loading`, `empty`, `error`, `offline`, `partial`, `populated`, `denied`).
- **Spec Integrity Hook (`cgspec doctor`):** Before completing any turn that modifies specifications or closing a milestone, run `python3 {skill-dir}/scripts/doctor.py .` to deterministically verify that all spines exist, memory log entries are sequential, all accepted ADRs are registered in `00-INDEX.md`, and zero specification drift exists.

## 3. Repository Topology: Monorepo vs. Polyrepo Neutrality
- **Independent & Equal Support:** CGSpec natively supports both **Monorepo** (single unified repository with modular packages) and **Polyrepo** (multiple independent repositories/microservices). Neither is dogmatically forced.
- **Topology Discovery & Inquiry Gate:** The agent must inspect the workspace first:
  - If existing configuration indicates a monorepo (e.g. `pnpm-workspace.yaml`, `turborepo`, `Cargo.toml` workspaces), respect and reinforce monorepo modularity.
  - If multi-repo mounting is detected or requested, support isolated Git targets and virtual path prefixes.
  - If starting fresh, **ask the user explicitly via `ask_question`** (recommending the most pragmatic structure for the product's scope, typically Monorepo for early-stage velocity) **without pushing or imposing polyrepo overhead** onto projects that do not need it.
- **Contract-First Modularity:** Regardless of whether code lives in one repository or many, enforce clean Ports & Adapters interfaces so packages and services can develop in parallel with zero tight coupling.

## 4. Universal Modularity: 3 Macro Milestone Tiers & Any-Stage Entry Gate

CGSpec is designed to be fully modular and adaptable to **any project size and any project entry point**:

```
+----------------------------------------------------------------------------------------------------------------+
| TIER 1: BRAINSTORMED & LOCKED v0.1 INTENT (docs/01-INTENT.md, docs/02-OOUX.md)                                 |
| - Is it interesting? Problem statement, mission, glossary, anti-goals, day-in-the-life walkthrough.             |
| - Domain Mental Model: Sophia Prater OOUX nouns, object relationships, and explicit granular permissions.      |
+----------------------------------------------------------------------------------------------------------------+
| TIER 2: VALIDATED v0.1 DESIGN & EXPERIENCE (docs/03-EXPERIENCE.md, docs/design/)                              |
| - Design Brief & Journey Mapping -> Zero-Color Macro Layout Wireframe (Mermaid subgraphs, where parts live).    |
| - Tactile Ergonomics & Direct Manipulation (how hands navigate & edit) -> Positive Design Tokens.             |
| - Coexisting 7-State Component Matrix -> Interactive Executable Prototype (prototype-v0.1.html).               |
+----------------------------------------------------------------------------------------------------------------+
| TIER 3: ENGINEERED v0.1 FOUNDATION & DELIVERY (docs/04-ARCHITECTURE.md, docs/05-DELIVERY.md, docs/adr/)       |
| - Physical Architecture: Hexagonal Ports & Adapters, physical DDL schemas, foreign keys, contracts, ADRs.      |
| - Code Conventions & Preferences: What the user likes / dislikes in code, libraries, and formatting.           |
| - Delivery Slices: Bounded vertical slices (SLICE-001..N), definition of done, AST ingestion gates.           |
| - Code Management & CI/CD: Git templates (issues/PRs), pre-commit doctor hook, automated testing, docker.      |
| - Follow-up & Backlog Evolution: Ship v0.1 -> roll over to Future Backlog (v0.2+) in docs/00-INBOX.md.          |
+----------------------------------------------------------------------------------------------------------------+
```

### The 4 Any-Stage Entry Modes:
1. **Mode A — Greenfield Creation (From Scratch):** Traverse Tier 1 (Brainstorming) -> Tier 2 (Experience) -> Tier 3 (Architecture, CI/CD, Delivery).
2. **Mode B — Headless / Backend / CLI (No Web UI):** Execute Tier 1 (Intent & Nouns) -> skip GUI to define TUI/CLI command syntax & ergonomics -> execute Tier 3 (Architecture, Code, CI/CD).
3. **Mode C — Brownfield Legacy Adoption (Existing Codebase):** Run `python3 scripts/ingest.py` (deterministic AST route & model parser) to generate a brownfield manifest -> reverse-derive `docs/02-OOUX.md` -> activate `doctor.py` integrity gate -> build bounded vertical slices (`cgspec-slice`) with zero disruption to legacy code.
4. **Mode D — Mid-Flight Course Correction (Pivot / Migration):** Trigger `cgspec-pivot` to evaluate impact across Tier 1 (Adapter Swap), Tier 2 (Additive Scope Expansion), or Tier 3 (Total Soul Extraction).


