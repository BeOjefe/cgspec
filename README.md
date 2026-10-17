# CGSpec (`cgspec`) — The AI-Native Software Engineering Methodology

CGSpec is a first-principles specification engine and governance constitution designed specifically for the era of AI-native software development.

Where traditional agile assumes human engineering squads and ad-hoc vibe-coding assumes single-prompt magic, **CGSpec establishes the engineering invariants, architectural spines, and phased design funnels that transform autonomous AI agents into disciplined, high-craft software engineering partners.**

---

## The Core Philosophy: Invariants Over Vibes

AI models do not fail because they lack intelligence; they fail because they lack **bounded context, deterministic constraints, and sequential discipline**. Left to unstructured prompting, AI coding produces:
- Premature backend implementation before human user experience is understood.
- Visual convergence toward generic, soulless "AI slop" (purple gradients, bouncy cards, zero edge-case handling).
- Disconnected database schemas that drift from real-world user workflows.
- Hallucinated consensus and silent architectural debt.

CGSpec solves this through a non-linear, dual-spine architecture governed by strict engineering laws:

```
  Human Director / Architect
              │
              ▼
   Stage 1: Intent & Brainstorming (docs/01-INTENT.md, docs/02-OOUX.md)
              │
              ▼
   Stage 2: Design & Experience Discovery (docs/03-EXPERIENCE.md, docs/design/)
              │
              ▼
   Stage 3: Physical Architecture & System Contracts (docs/04-ARCHITECTURE.md, docs/adr/)
              │
              ▼
   Stage 4: Milestone Slices & Delivery Roadmap (docs/05-DELIVERY.md, docs/00-INDEX.md)
              │
              ▼
   Stage 5: Modular Coding & Implementation (src/domain, src/adapters)
              │
              ▼
   Stage 6: Testing & Verification Gates (tests/, python3 docs/.cgspec/scripts/doctor.py)
              │
              ▼
   Stage 7: CI/CD & Automated Delivery (.github/workflows/, containerization)
              │
              ▼
   Stage 8: Follow-up, Rollout & Backlog Evolution (docs/.memlog.md, docs/00-INBOX.md)
```

---

## Key Pillars of CGSpec

### 1. Human Experience Precedes Architecture & Backend (Law 3)
Software begins with human intent, mental models, and daily ergonomics. Technical implementation ("how": SQL tables, foreign keys, programming languages, ORMs, and servers) is strictly forbidden until the Day-in-the-Life walkthrough, spatial zoning, and interactive prototype are validated and approved.

### 2. The 5-Stage Phased Design Locking Funnel (Law 10)
High-craft user experience cannot be generated in a single prompt. Every screen advances through 5 locked, versioned stages:
1. **Macro Spatial Zoning & Zero-Color Wireframe:** Low-fidelity partitioning across screen zones (Vertical Scroll Storyboard for Simple Websites, Thumb-Zone Stack for iOS/Android Mobile Apps, or Multi-Pane Viewport for Web Apps) with clean declarative diagram subgraphs (Mermaid `flowchart TB`, D2, PlantUML) in an Artifact. The human must see and approve where things live on screen before discussing micro-interactions. Zero colors, zero themes yet.
2. **Tactile Ergonomics & Direct Manipulation:** Defining how hands navigate between zones and how editing/gestures operate inside the primary workspace (e.g. inline editing, bottom sheet detents, keyboard shortcuts).
3. **Design Tokens & Aesthetic Direction:** Establishing typography hierarchy, atmospheric canvas texture, and a surgical signature brand anchor.
4. **Proportional Component State Matrix:** Engineering for the full operational lifecycle (4 narrative/viewport states for Simple Websites, 7 mobile/touch states including `Keyboard Up` for iOS/Android, or 7 operational states for Web Workspaces).
5. **Interactive Milestone Baseline Prototype:** Single-file, zero-build executable HTML (`docs/.cgspec/prototypes/prototype-v0.1.html`) with live state switching.

### 3. Hierarchical Peer Debate Council (`cgspec-council`)
To prevent single-model sycophancy and blind spots, cross-cutting architectural and security choices are pressure-tested by a 3-agent peer council:
- **Systems & Modularity Lens:** Enforcing clean boundaries, Ports & Adapters, and loose coupling.
- **Adversarial Security & Edge Cases Lens:** Stress-testing race conditions, permission bypasses, memory limits, and fail-safe defaults.
- **Pragmatic DX & Ship Speed Lens:** Fiercely eliminating speculative over-engineering and onboarding friction.
The Council Supervisor coordinates the debate in an isolated side pane, keeping the human's primary chat 100% clean and free of debater spam.

### 4. Atomic Architecture Decision Records (Law 7)
Every significant technical choice must produce a formal ADR under `docs/adr/ADR-NNN-<slug>.md` and be registered in `docs/00-INDEX.md`. An agent is strictly forbidden from advancing a phase with "memlog-only" shortcuts.

### 5. Automated Spec Integrity Hook (`cgspec doctor`)
Specification drift is eliminated deterministically. The built-in doctor utility (`python3 docs/.cgspec/scripts/doctor.py`) validates that all 6 spines exist, memory log entries maintain strict hash continuity (`M-001` .. `M-NNN`), all accepted ADRs are registered, and zero orphan concepts exist before any milestone is closed.

### 6. Disk-First Immediate Capture (Law 11)
Chat context is ephemeral and lost across compacting or session boundaries; disk is permanent truth. Whenever an idea, spark, decision, consensus, or user preference emerges during a turn, the agent must commit it to disk (`docs/00-INBOX.md`, `docs/.memlog.md`, or the active spine) in the exact same turn before concluding its execution. The human architect must never bear the burden of asking "did you write that down?".

---

## Universal Modularity: 3 Macro Milestone Tiers, 4 Surface Profiles & Any-Stage Entry Gate

CGSpec is designed to be fully modular and adaptable to **any project size, target platform (Simple Website, Mobile iOS/Android, Web App, CLI), and lifecycle entry point**:

```
+----------------------------------------------------------------------------------------------------------------+
| TIER 1: BRAINSTORMED & LOCKED v0.1 INTENT (docs/01-INTENT.md, docs/02-OOUX.md)                                 |
| - Active Thinking & Brainstorming: Is it interesting? Problem statement, mission, glossary, anti-goals.       |
| - Day-in-the-Life Walkthrough: Realistic end-to-end human scenario from trigger to resolution.                 |
| - Domain Mental Model: Sophia Prater OOUX nouns, object relationships, and explicit granular permissions.      |
+----------------------------------------------------------------------------------------------------------------+
| TIER 2: VALIDATED v0.1 DESIGN & EXPERIENCE (docs/03-EXPERIENCE.md, docs/.cgspec/prototypes/)                   |
| - Adaptive Surface Profile: Simple Website (Scroll Storyboard), Mobile iOS/Android (Thumb-Zone Stack),         |
|   Web/Desktop Workspace (Multi-Pane), or CLI/TUI (Command Grammar).                                            |
| - Zero-Color Macro Layout Wireframe (Mermaid / D2 / PlantUML subgraphs) -> Tactile Ergonomics & Tokens.        |
| - Proportional State Matrix -> Interactive Executable Prototype (docs/.cgspec/prototypes/prototype-v0.1.html). |
+----------------------------------------------------------------------------------------------------------------+
| TIER 3: ENGINEERED v0.1 FOUNDATION & DELIVERY (docs/04-ARCHITECTURE.md, docs/05-DELIVERY.md, docs/adr/)       |
| - Physical Architecture: Hexagonal Ports & Adapters, physical DDL schemas, foreign keys, contracts, ADRs       |
|   (or lightweight static content/asset spec for Simple Websites).                                              |
| - Code Conventions & Preferences: Explicit human code preferences, selected libraries, formatting rules.       |
| - Delivery Slices: Bounded vertical slices (SLICE-001..N), definition of done, AST ingestion gates.           |
| - Code Management & CI/CD: Git templates (issues/PRs), pre-commit doctor hook, automated testing, docker.      |
| - Follow-up & Backlog Evolution: Ship v0.1 -> roll over to Future Backlog (v0.2+) in docs/00-INBOX.md.          |
+----------------------------------------------------------------------------------------------------------------+
```

### The 4 Any-Stage Entry Modes:
1. **Mode A — Greenfield Creation (Simple Website, Mobile iOS/Android, or Web SaaS):** Traverse Tier 1 (Brainstorming) -> Tier 2 (Surface-Adapted UI/UX) -> Tier 3 (Architecture, CI/CD, Delivery).
2. **Mode B — Headless / Backend / CLI (No GUI):** Execute Tier 1 (Intent & Nouns) -> skip GUI to define TUI/CLI command syntax & ergonomics -> execute Tier 3 (Architecture, Code, CI/CD).
3. **Mode C — Brownfield Legacy Adoption (Existing Codebase):** Run `python3 docs/.cgspec/scripts/ingest.py` (deterministic AST route & model parser) to generate `docs/.cgspec/brownfield-manifest.json` -> reverse-derive `docs/02-OOUX.md` -> activate `doctor.py` integrity gate -> build bounded vertical slices (`cgspec-slice`) with zero disruption to legacy code.
4. **Mode D — Mid-Flight Course Correction (Pivot / Migration):** Trigger `cgspec-pivot` to evaluate impact across Tier 1 (Adapter Swap), Tier 2 (Additive Scope Expansion), or Tier 3 (Total Soul Extraction).

---

## Repository Structure (Zero Root Workspace Pollution)

All internal CGSpec tooling, scripts, prototypes, and council logs are centralized inside the hidden `docs/.cgspec/` engine directory, keeping the project root 100% focused on the user's product:

```
.
├── AGENTS.md                  # Universal Autopilot Constitution (Applies across all AI agents)
├── CLAUDE.md                  # DRY 1-line pointer to AGENTS.md
├── CHANGELOG.md               # Versioned methodology evolutions
├── skills/
│   ├── cgspec-init/           # Monorepo/polyrepo setup, .cgspec vault, and brownfield ingestion
│   ├── cgspec-forge/          # Stage 1 active thinking, intent & ORCA object map compiler
│   ├── cgspec-ui-ux/          # Stage 2 dual-spine UI & UX compiler (Simple Site, iOS/Android, Web, CLI)
│   ├── cgspec-council/        # Supervised 3-agent hierarchical debate council
│   ├── cgspec-slice/          # Bounded vertical slice builder (Ports & Adapters)
│   └── cgspec-pivot/          # 3-tier course-correction and migration engine
└── docs/                      # The 5 Canonical Spines + Centralized .cgspec Engine Vault
    ├── 00-INDEX.md            # Live project state, ADR registry, and slice roadmap
    ├── 00-INBOX.md            # Spark parking lot for out-of-scope ideas (v0.2+)
    ├── 01-INTENT.md           # Problem definition, intent, scope, and day-in-the-life
    ├── 02-OOUX.md             # Sophia Prater domain mental model, nouns, and 6 permissions
    ├── 03-EXPERIENCE.md       # Adaptive zoning, design tokens, state matrix, prototype links
    ├── 04-ARCHITECTURE.md     # Ports & adapters, system topologies, physical DDL schemas
    ├── 05-DELIVERY.md         # Bounded vertical slices, verification gates, AST ingestion
    ├── .memlog.md             # Append-only chronological decision ledger
    ├── adr/                   # Formal Architecture Decision Records (ADR-NNN)
    └── .cgspec/               # Hidden centralized CGSpec engine (zero root clutter)
        ├── scripts/           # memlog.py, doctor.py, ingest.py
        ├── prototypes/        # prototype-v0.1.html & stash/
        └── council/           # Isolated multi-agent debate workspaces
```

---

## Universal Multi-Agent Compatibility

CGSpec is 100% vendor-agnostic. It works identically across:
- **Anthropic Claude Code**
- **OpenAI Codex & ChatGPT**
- **Cursor & Windsurf**
- **Google Antigravity & Gemini CLI**
- **Hermes / Open-Source Local Agents**

Zero proprietary lock-in. All instructions, constraints, and skills live directly inside your Git repository as clean, portable Markdown and Python scripts.
