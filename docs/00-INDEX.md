# docs/00-INDEX.md — CGSpec (`cgspec`) Live State & Control Center

> **Single Source of Truth:** This file tracks the live engineering state of **CGSpec (`cgspec`)** — the AI-agnostic Spec-Driven SDLC Engine & CortexGate Bridge under the **Reformed CGSpec v0.2** topology.

---

## 1. Current System Phase
- **Active Phase:** `PHASE 2: ARCHITECTURE & SKILL SPECIFICATION LOCKED`
- **Active Milestone:** `v0.1 — Core Portable Skill Suite & Non-Linear _memlog.md Engine`
- **Memory Log:** [20 entries (Latest: M-020)](file:///home/ojefe/Documents/Project/cgspec/docs/_memlog.md)
- **Current Focus:** Standardizing the Model 1 (`docs/spines/`) topology, visible first-class ADRs (`docs/adr/`), slice contracts (`docs/slices/`), and underscore engine space (`docs/_cgspec/`).

---

## 2. Canonical Living Spines (`docs/spines/`)

The core specification is organized into 5 living spines strictly following **Law 3 Purity (Intent -> Domain -> Experience -> Architecture -> Delivery)**:

| Pillar Document | Status | Last ADR | Purpose |
| :--- | :--- | :--- | :--- |
| [`00-INBOX.md`](file:///home/ojefe/Documents/Project/cgspec/docs/00-INBOX.md) | `[Active]` | — | Idea Parking Lot & future sparks |
| [`01-INTENT.md`](file:///home/ojefe/Documents/Project/cgspec/docs/spines/01-INTENT.md) | `[Locked]` | [`ADR-001`](file:///home/ojefe/Documents/Project/cgspec/docs/adr/ADR-001-first-principles-spec-driven-sdlc-architecture.md) | Problem Statement, Mission, Glossary & Day-in-the-Life Journey |
| [`02-OOUX.md`](file:///home/ojefe/Documents/Project/cgspec/docs/spines/02-OOUX.md) | `[Locked]` | [`ADR-002`](file:///home/ojefe/Documents/Project/cgspec/docs/adr/ADR-002-monorepo-vs-polyrepo-and-db-migrations.md) | Domain Mental Models, 6 Permissions & Non-Linear Lifecycle Flows |
| [`03-EXPERIENCE.md`](file:///home/ojefe/Documents/Project/cgspec/docs/spines/03-EXPERIENCE.md) | `[Locked]` | [`ADR-004`](file:///home/ojefe/Documents/Project/cgspec/docs/adr/ADR-004-arbitrary-multi-service-topologies-and-virtual-mounting.md) | Spatial Zoning, Visual Tokens, Functional Protagonists & 7-State Matrix |
| [`04-ARCHITECTURE.md`](file:///home/ojefe/Documents/Project/cgspec/docs/spines/04-ARCHITECTURE.md) | `[Locked]` | [`ADR-003`](file:///home/ojefe/Documents/Project/cgspec/docs/adr/ADR-003-supervised-peer-council-architecture.md) | Hexagonal Ports & Adapters, Council Architecture & MCP Bridge |
| [`05-DELIVERY.md`](file:///home/ojefe/Documents/Project/cgspec/docs/spines/05-DELIVERY.md) | `[Locked]` | [`ADR-005`](file:///home/ojefe/Documents/Project/cgspec/docs/adr/ADR-005-hierarchical-adrs-and-documentation-scaling.md) | Bounded Slices, Verification Criteria, Doctor Gates & AST Ingestion |

---

## 3. Active & Upcoming Vertical Slices (`docs/slices/`)

| Slice ID | Slice Name | Spec Status | Build Status | Verification |
| :--- | :--- | :--- | :--- | :--- |
| **Slice 001** | **CGSpec Blueprint & Architecture Docs (`/Project/cgspec/docs/`)** | `[Locked]` | `[Built]` | `[User Review]` |
| **Slice 002** | **Portable `cgspec` Skills (`skills/cgspec-*/SKILL.md` + `memlog.py`)** | `[Locked in 03]` | `[Queued Next]` | `[Pending]` |
| **Slice 003** | **Real-Project Validation on `CortexGate` (`/Project/cortexgate/`)** | `[Queued]` | `[Pending]` | `[Pending]` |

---

## 4. Accepted Architecture Decision Records (`docs/adr/`)

| ADR | Title & Invariant | Status |
| :--- | :--- | :--- |
| **[`ADR-001`](file:///home/ojefe/Documents/Project/cgspec/docs/adr/ADR-001-first-principles-spec-driven-sdlc-architecture.md)** | **First-Principles Architecture of the CGSpec Specification Engine** | `[Accepted]` |
| **[`ADR-002`](file:///home/ojefe/Documents/Project/cgspec/docs/adr/ADR-002-monorepo-vs-polyrepo-and-db-migrations.md)** | **Adaptive Monorepo vs. Multi-Repo (Polyrepo) & Database Migration Architecture** | `[Accepted]` |
| **[`ADR-003`](file:///home/ojefe/Documents/Project/cgspec/docs/adr/ADR-003-supervised-peer-council-architecture.md)** | **Supervised 3-Agent Peer Debate Council Architecture** | `[Accepted]` |
| **[`ADR-004`](file:///home/ojefe/Documents/Project/cgspec/docs/adr/ADR-004-arbitrary-multi-service-topologies-and-virtual-mounting.md)** | **Arbitrary Multi-Service Topologies, Virtual Mounting & Contract-First Interface Decoupling** | `[Accepted]` |
| **[`ADR-005`](file:///home/ojefe/Documents/Project/cgspec/docs/adr/ADR-005-hierarchical-adrs-and-documentation-scaling.md)** | **Hierarchical ADRs, Documentation Scaling & Multi-Tenant Scoping** | `[Accepted]` |

---

## 5. Technical Spikes & Research Compendiums (`docs/_cgspec/02-research/`)

| Spike ID | Title & Investigation Focus | Status | Target Spine / Scope |
| :--- | :--- | :--- | :--- |
| **[`RES-001`](file:///home/ojefe/Documents/Project/cgspec/docs/_cgspec/02-research/RES-001-ui-design-systems-and-surface-profiles-benchmark.md)** | **UI Frameworks, Design Systems & Adaptive Surface Profiles Benchmark** | `[Concluded]` | [`03-EXPERIENCE.md`](file:///home/ojefe/Documents/Project/cgspec/docs/spines/03-EXPERIENCE.md) (Profiles A, B, C, D) |
| **[`RES-002`](file:///home/ojefe/Documents/Project/cgspec/docs/_cgspec/02-research/RES-002-anti-slop-constrained-ui-and-deterministic-gates.md)** | **Anti-AI-Slop Architecture, Constrained Generative UI & Deterministic Quality Gates** | `[Concluded]` | [`03-EXPERIENCE.md`](file:///home/ojefe/Documents/Project/cgspec/docs/spines/03-EXPERIENCE.md), `visual_audit.py` |
| **[`RES-003`](file:///home/ojefe/Documents/Project/cgspec/docs/_cgspec/02-research/RES-003-agentic-design-skills-and-anti-slop-frontier.md)** | **Frontier Agentic Design Skills & Anti-Slop Ecosystem Benchmark** | `[Concluded]` | [`03-EXPERIENCE.md`](file:///home/ojefe/Documents/Project/cgspec/docs/spines/03-EXPERIENCE.md), `cgspec-ui-ux` |
| **[`RES-004`](file:///home/ojefe/Documents/Project/cgspec/docs/_cgspec/02-research/RES-004-vibecoded-design-tells-and-high-craft-ergonomics.md)** | **Empirical Vibe-Coded Design Tells, Anti-Slop Scanners & High-Craft Interaction Ergonomics** | `[Concluded]` | [`03-EXPERIENCE.md`](file:///home/ojefe/Documents/Project/cgspec/docs/spines/03-EXPERIENCE.md), `visual_audit.py` |
