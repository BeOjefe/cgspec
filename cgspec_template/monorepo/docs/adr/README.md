# Architecture Decision Records (`docs/adr/`)

This directory contains the permanent, immutable **Architecture Decision Records (ADRs)** for the project, following the Markdown Architectural Decision Records (MADR) and Michael Nygard standards.

---

## 1. What is an ADR?
An ADR captures a single significant architectural or design decision along with its context, considered options, trade-offs, and consequences. Once accepted, an ADR is an immutable historical record. If a decision changes later, a new superseding ADR is drafted (referencing the original via `Supersedes: ADR-XXX`).

---

## 2. Naming & Format Convention
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

## 3. Two-Tier ADR Governance (Polyrepo / Distributed Systems)
- **Tier 1 (Global System ADRs):** Cross-cutting mandates that bind all subsystems (e.g. authentication schemes, event schemas, port protocols).
- **Tier 2 (Service-Local ADRs):** Technical decisions strictly internal to an individual subsystem or service repository (e.g. internal caching libraries, database drivers).
