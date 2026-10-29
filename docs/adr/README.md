# Architecture Decision Records (`docs/adr/`)
Created: unknown · Last edited: 2026-10-20T17:54:17Z

This directory contains the permanent, immutable **Architecture Decision Records (ADRs)** for the project, following the Markdown Architectural Decision Records (MADR) and Michael Nygard standards.

For current work, [METHOD.md](../METHOD.md) defines the consumer layout and rules. ADR-001 through ADR-005 retain v0.1 history; their Accepted labels do not override current paths or establish generic tenant/MCP guarantees. [ADR-006](ADR-006-main-branch-governance.md) records the current governance choice for this plugin repository, including its unfinished credential boundary. Preserve older records rather than silently rewriting their decisions.

---

## 1. Historical v0.1 ADR conventions
An ADR captures a single significant architectural or design decision along with its context, considered options, trade-offs, and consequences. Once accepted, an ADR is an immutable historical record. If a decision changes later, a new superseding ADR is drafted (referencing the original via `Supersedes: ADR-XXX`).

---

## 2. Historical v0.1 naming and format
- **File Naming:** `ADR-NNN-<slug>.md` (e.g. `ADR-001-first-principles-spec-driven-sdlc-architecture.md`).
- **Required Metadata Headers:**
  - `- **Status:** [Proposed | Accepted | Superseded | Deprecated]`
  - `- **Date:** YYYY-MM-DD`
  - `- **Deciders:** List of deciders or agent roles`
  - `- **Consulted / Debated:** Reference to Council session if contested`
- **Sections:**
  1. Context and Problem Statement
  2. Considered Options & Trade-Off Analysis
  3. Decision & Invariants
  4. Positive & Negative Consequences
  5. Affected Spines & Code Boundaries

---

## 3. Historical v0.1 two-tier governance
- **Tier 1 (Global System ADRs):** Cross-cutting mandates that bind all subsystems (e.g. authentication schemes, event schemas, port protocols).
- **Tier 2 (Service-Local ADRs):** Technical decisions strictly internal to an individual subsystem or service repository (e.g. internal caching libraries, database drivers).
