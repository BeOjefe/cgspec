# ADR-001: First-Principles Architecture of the CGSpec Specification Engine
Created: unknown · Last edited: 2026-10-20T17:54:17Z

> Historical v0.1 record; not current v0.2 rules or approval. See [the ADR index](README.md) and [the current method](../METHOD.md).

- **Status:** Accepted
- **Date:** 2026-10-16

---

## 1. Context & Problem

Software engineering with autonomous AI coding agents (Claude, Gemini, Codex, Hermes) suffers from fundamental structural failure modes when managed through unstructured chat:

1. **Context Collapse:** As conversations grow, agents lose track of earlier architectural decisions and user intent, causing hallucinated rewrites and regression bugs.
2. **Premature Coding Reflex:** AI models instinctively jump to writing code, database schemas, and API routes before user intent, mental models (OOUX), spatial zoning, and interface ergonomics are defined and verified.
3. **Unbounded Agent Authority:** Agents operate without explicit boundary gates, modifying protected files and making unilateral architectural shifts without explicit human consensus.
4. **Tool and Vendor Fragmentation:** Frameworks tied to specific IDE plugins or proprietary folder formats break portability when teams work across heterogeneous agent platforms.

---

## 2. Decision & Architectural Invariants

We establish **CGSpec (`cgspec`)** as an autonomous, vendor-neutral, spec-driven software engineering engine governed by seven immutable architectural invariants:

1. **Experience-First Sequencing (Law 3):** Human Experience, UI/UX, spatial zoning, and interactive single-file prototypes strictly precede physical database tables, SQL schemas, and backend implementation.
2. **Append-Only Event Ledger (`.memlog.md`):** All requirements, architectural decisions, and scope changes are recorded as immutable chronological entries in `docs/.memlog.md`. Spines (`01` through `05`) are continuously derived from this ledger, eliminating merge drift and sequence rigidity.
3. **Supervised Peer Debate Councils:** Major architectural disputes and critical technical choices are resolved through a 3-agent peer debate orchestrated by a single `Council Supervisor & Inspector`. Debaters argue across orthogonal lenses (Systems, Security, Pragmatic DX) in background workspaces, insulating the primary human chat from turn clutter.
4. **Zero Decorative Emojis:** Agent communication and specification files enforce strict, distraction-free engineering typography. Decorative status emojis are banned in favor of structured Markdown tags (`[Done]`, `[Active]`, `[Proposed]`, `[Accepted]`).
5. **Contract-First Modularity (Ports & Adapters):** Domain cores remain decoupled from external infrastructure, third-party SDKs, and databases via explicit interface ports and interchangeable adapters.
6. **Automated Specification Linter (`doctor.py`):** An AST-based integrity hook validates core spine completeness, memory log continuity, and ADR registrations before vertical slices can be scaffolded.
7. **Atomic ADR Locking Gate:** Decisions only become architectural invariants (`Status: Accepted`) upon explicit human confirmation, recorded synchronously in both `docs/.memlog.md` and `docs/00-INDEX.md`.

---

## 3. Consequences

- **Clarity over Speed:** Eliminates frantic, broken vibe-coding in favor of verified vertical slices that work on the first try.
- **Portability:** The entire specification suite lives in plain Markdown under `docs/` and standard Python scripts under `scripts/`, runnable identically in Antigravity, Claude Code, OpenAI Codex, or CLI pipelines.
- **Human Autonomy Preserved:** The developer maintains ultimate steering authority over system intent and taste, while AI agents handle exhaustive exploration and verified implementation.
