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
   Stage 1: Intent, User Journey & Conceptual OOUX Nouns (docs/01-INTENT.md, docs/02-OOUX.md)
              │
              ▼
   Stage 2: Adaptive UI/UX & Interactive Prototype (docs/03-EXPERIENCE.md)
              │
              ▼
   Stage 3: Physical Architecture, DDL & System Topology (docs/04-ARCHITECTURE.md)
              │
              ▼
   Stage 4: Delivery Slices, Verification & Ingest Gates (docs/05-DELIVERY.md)
```

---

## Key Pillars of CGSpec

### 1. Human Experience Precedes Architecture & Backend (Law 3)
Software begins with human intent, mental models, and daily ergonomics. Technical implementation ("how": SQL tables, foreign keys, programming languages, ORMs, and servers) is strictly forbidden until the Day-in-the-Life walkthrough, spatial zoning, and interactive prototype are validated and approved.

### 2. The 5-Stage Phased Design Locking Funnel (Law 10)
High-craft user experience cannot be generated in a single prompt. Every screen advances through 5 locked, versioned stages:
1. **Macro Spatial Zoning & Zero-Color Wireframe:** Low-fidelity partitioning across screen zones (Header, Navigation Rail, Main Canvas, Context Drawer) with clean ASCII blockouts or wireframes in an Artifact. The human must see and approve where things live on screen before discussing micro-interactions. Zero colors, zero themes yet.
2. **Tactile Ergonomics & Direct Manipulation:** Defining how hands navigate between zones and how editing operates inside the primary workspace (e.g. inline editing vs split preview, keyboard shortcuts, command palette).
3. **Design Tokens & Aesthetic Direction:** Establishing typography hierarchy, atmospheric canvas texture, and a surgical signature brand anchor.
4. **The 7-State Component Matrix:** Engineering for the full operational lifecycle (`Populated`, `Loading Skeleton`, `Empty`, `Error`, `Denied 403`, `Offline`, `Partial/Filtered`) with adversarial worst-case edge data.
5. **Interactive Milestone Baseline Prototype:** Single-file, zero-build executable HTML (`prototype-v0.1.html`) with live state switching and keyboard shortcuts.

### 3. Hierarchical Peer Debate Council (`cgspec-council`)
To prevent single-model sycophancy and blind spots, cross-cutting architectural and security choices are pressure-tested by a 3-agent peer council:
- **Systems & Modularity Lens:** Enforcing clean boundaries, Ports & Adapters, and loose coupling.
- **Adversarial Security & Edge Cases Lens:** Stress-testing race conditions, permission bypasses, memory limits, and fail-safe defaults.
- **Pragmatic DX & Ship Speed Lens:** Fiercely eliminating speculative over-engineering and onboarding friction.
The Council Supervisor coordinates the debate in an isolated side pane, keeping the human's primary chat 100% clean and free of debater spam.

### 4. Atomic Architecture Decision Records (Law 7)
Every significant technical choice must produce a formal ADR under `docs/adr/ADR-NNN-<slug>.md` and be registered in `docs/00-INDEX.md`. An agent is strictly forbidden from advancing a phase with "memlog-only" shortcuts.

### 5. Automated Spec Integrity Hook (`cgspec doctor`)
Specification drift is eliminated deterministically. The built-in doctor utility (`python3 scripts/doctor.py`) validates that all 6 spines exist, memory log entries maintain strict hash continuity (`M-001` .. `M-NNN`), all accepted ADRs are registered, and zero orphan concepts exist before any milestone is closed.

### 6. Disk-First Immediate Capture (Law 11)
Chat context is ephemeral and lost across compacting or session boundaries; disk is permanent truth. Whenever an idea, spark, decision, consensus, or user preference emerges during a turn, the agent must commit it to disk (`docs/00-INBOX.md`, `docs/.memlog.md`, or the active spine) in the exact same turn before concluding its execution. The human architect must never bear the burden of asking "did you write that down?".

---

## Repository Structure

```
.
├── AGENTS.md                  # Universal Autopilot Constitution (Applies across all AI agents)
├── CLAUDE.md                  # DRY 1-line pointer to AGENTS.md
├── CHANGELOG.md               # Versioned methodology evolutions
├── scripts/
│   ├── memlog.py              # CLI append-only memory logger
│   ├── doctor.py              # Deterministic spec linter & integrity hook
│   └── ingest.py              # Deterministic AST codebase ingestion engine
├── skills/
│   ├── cgspec-init/           # Monorepo/polyrepo setup and initialization
│   ├── cgspec-forge/          # Non-linear problem stress-tester and PRD hub
│   ├── cgspec-ux/             # 4-stage phased design locking engine & anti-slop codex
│   ├── cgspec-council/        # Supervised 3-agent hierarchical debate council
│   ├── cgspec-slice/          # Bounded vertical slice builder (Ports & Adapters)
│   └── cgspec-pivot/          # 3-tier course-correction and migration engine
└── docs/                      # The 5 Canonical Spines (Reformed CGSpec v2)
    ├── 00-INDEX.md            # Live project state, ADR registry, and slice roadmap
    ├── 00-INBOX.md            # Spark parking lot for out-of-scope ideas (v0.2+)
    ├── 01-INTENT.md           # Problem definition, intent, scope, and day-in-the-life
    ├── 02-OOUX.md             # Sophia Prater domain mental model, nouns, and 6 permissions
    ├── 03-EXPERIENCE.md       # Adaptive zoning, design tokens, 7-state matrix, prototype links
    ├── 04-ARCHITECTURE.md     # Ports & adapters, system topologies, physical DDL schemas
    ├── 05-DELIVERY.md         # Bounded vertical slices, verification gates, AST ingestion
    ├── .memlog.md             # Append-only chronological decision ledger
    └── adr/                   # Formal Architecture Decision Records (ADR-NNN)
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
