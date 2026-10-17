# docs/00-INDEX.md — CGSpec (`cgspec`) Live State & Control Center

> **Single Source of Truth:** This file tracks the live engineering state of **CGSpec (`cgspec`)** — the AI-agnostic Spec-Driven SDLC Engine & CortexGate Bridge.

---

## 1. Current System Phase
- **Active Phase:** `PHASE 2: ARCHITECTURE & SKILL SPECIFICATION LOCKED`
- **Active Milestone:** `v0.1 — Core Portable Skill Suite & Non-Linear .memlog.md Engine`
- **Current Focus:** Reviewing the vendor-neutral `cgspec` documentation in `/home/ojefe/Documents/Project/cgspec/docs/` (compatible with Hermes, Claude Code, Codex, Cursor, and Antigravity) before generating the portable `skills/cgspec-*/SKILL.md` files and `.cgspec/scripts/memlog.py`.

---

## 2. Canonical Document Status Matrix (Reformed CGSpec v2)

| Pillar Document | Status | Last ADR | Purpose |
| :--- | :--- | :--- | :--- |
| [`00-INBOX.md`](file:///home/ojefe/Documents/Project/cgspec/docs/00-INBOX.md) | `[Active]` | — | Idea Parking Lot & future sparks |
| [`01-INTENT.md`](file:///home/ojefe/Documents/Project/cgspec/docs/01-INTENT.md) | `[Locked]` | [`ADR-001`](file:///home/ojefe/Documents/Project/cgspec/docs/adr/ADR-001-first-principles-spec-driven-sdlc-architecture.md) | Problem Statement, Mission, Glossary & Day-in-the-Life Journey |
| [`02-OOUX.md`](file:///home/ojefe/Documents/Project/cgspec/docs/02-OOUX.md) | `[Locked]` | [`ADR-002`](file:///home/ojefe/Documents/Project/cgspec/docs/adr/ADR-002-monorepo-vs-polyrepo-and-db-migrations.md) | Domain Mental Models, 6 Permissions & Non-Linear Lifecycle Flows |
| [`03-EXPERIENCE.md`](file:///home/ojefe/Documents/Project/cgspec/docs/03-EXPERIENCE.md) | `[Locked]` | [`ADR-004`](file:///home/ojefe/Documents/Project/cgspec/docs/adr/ADR-004-arbitrary-multi-service-topologies-and-virtual-mounting.md) | Spatial Zoning, Visual Tokens, Functional Protagonists & 7-State Matrix |
| [`04-ARCHITECTURE.md`](file:///home/ojefe/Documents/Project/cgspec/docs/04-ARCHITECTURE.md) | `[Locked]` | [`ADR-003`](file:///home/ojefe/Documents/Project/cgspec/docs/adr/ADR-003-supervised-peer-council-architecture.md) | Hexagonal Ports & Adapters, Council Architecture & MCP Bridge |
| [`05-DELIVERY.md`](file:///home/ojefe/Documents/Project/cgspec/docs/05-DELIVERY.md) | `[Locked]` | [`ADR-005`](file:///home/ojefe/Documents/Project/cgspec/docs/adr/ADR-005-hierarchical-adrs-and-documentation-scaling.md) | Bounded Slices, Verification Criteria, Doctor Gates & AST Ingestion |

---

## 3. Active & Upcoming Vertical Slices (`v0.1`)

| Slice ID | Slice Name | Spec Status | Build Status | Verification |
| :--- | :--- | :--- | :--- | :--- |
| **Slice 001** | **CGSpec Blueprint & Architecture Docs (`/Project/cgspec/docs/`)** | `[Locked]` | `[Built]` | `[User Review]` |
| **Slice 002** | **Portable `cgspec` Skills (`skills/cgspec-*/SKILL.md` + `.cgspec/scripts/memlog.py`)** | `[Locked in 03]` | `[Queued Next]` | `[Pending]` |
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

