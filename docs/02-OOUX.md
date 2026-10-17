# 02-OOUX: Domain Mental Model, Nouns & Core Flows

> **Stage 1 (Domain Model): Sophia Prater Object-Oriented UX, Granular Permissions & Lifecycle Flows**

---

## 1. Domain Nouns & Object Relationships

Every artifact managed by `cgspec` maps to 6 core domain nouns governed by explicit **Resource Ownership (`Owner`)** and **Granular Permissions (`read | invoke | propose_edit | write | share | admin`)**:

```mermaid
erDiagram
    PROJECT_BLUEPRINT ||--|| MEMLOG : "records chronological truth in"
    PROJECT_BLUEPRINT ||--|{ DERIVED_SPINE : "projects terse contracts into"
    PROJECT_BLUEPRINT ||--o{ INBOX_SPARK : "parks future ideas in"
    PROJECT_BLUEPRINT ||--|{ ADR_RECORD : "locks major decisions in"
    PROJECT_BLUEPRINT ||--|{ VERTICAL_SLICE : "executes work via"
    DERIVED_SPINE ||--o{ WORKING_ARTIFACT : "explores options in .cgspec/"

    MEMLOG {
        string entry_id PK "e.g., M-001"
        string tag "decision | assumption | crack | kill | direction:parked | lock"
        string owner_id "User or Team ID"
        string permissions "read | invoke | propose_edit | write | share | admin"
    }
    DERIVED_SPINE {
        string doc_id PK "00-INDEX | 01-INTENT | 02-OOUX | 03-EXPERIENCE | 04-ARCHITECTURE | 05-DELIVERY"
        string status "Draft | Locked | Pivoting"
        string derived_from_memlog_id "Latest M-NNN"
    }
    WORKING_ARTIFACT {
        string path PK "docs/.cgspec/* (Excalidraw, HTML mocks, manifests)"
        boolean ephemeral "True (never loaded into build context)"
    }
    VERTICAL_SLICE {
        string slice_id PK "e.g., SLICE-001"
        string target_modules "Monorepo packages or Service repos"
        string status "Proposed | In_Progress | Verified"
    }
```

---

## 2. Event-Sourced Spine Derivation & 3-Tier Pivot Engine

CGSpec uses an append-only event ledger (`.memlog.md`) as the single source of truth. Spines are continuously derived from locked ledger entries, ensuring that any idea, challenge, or pivot can be triaged without context drift:

```mermaid
flowchart TD
    IDEA["New Idea, Critique, or Pivot Arrives<br/>(Anytime: Discovery, UX, or Mid-Coding)"] --> GATE{"Autopilot Triage Gate<br/>(AGENTS.md)"}

    GATE -->|"Off-scope for current v0.1 task"| PARK["Park in docs/00-INBOX.md<br/>+ memlog.py --tags direction:parked<br/>(Zero interruption to active slice)"]

    GATE -->|"Refines Intent / UX / Arch in current scope"| NONLINEAR["Non-Linear Spine Update<br/>1. Log lock to docs/.memlog.md<br/>2. Re-derive affected Spine (01..05)<br/>3. Update 00-INDEX.md"]

    GATE -->|"Changes existing built code or architecture"| TIER{"6-Step Course-Correction Audit<br/>(cgspec-pivot)"}

    TIER -->|"Tier 1: Module Swap<br/>(e.g., SQLite -> Postgres)"| T1["Tier 1: Adapter Swap<br/>1. Write ADR-NNN<br/>2. Update 04-ARCHITECTURE.md<br/>3. Swap src/adapters/<module> only"]
    TIER -->|"Tier 2: Scope Expansion<br/>(e.g., Solo -> Team RBAC)"| T2["Tier 2: Additive Slice<br/>1. Write ADR-NNN<br/>2. Update 02-OOUX & 04-ARCH<br/>3. Create additive DB migration & Slice"]
    TIER -->|"Tier 3: Total Architecture Switch<br/>(v1 -> v2)"| T3["Tier 3: Soul Extraction<br/>1. Freeze v1-legacy branch<br/>2. Keep 01-INTENT & 02-OOUX<br/>3. Rewrite 04-ARCH & scaffold v2"]
```

---

## 3. Topology Neutrality

CGSpec operates neutrally across all repository layouts without dogmatically imposing monorepo or polyrepo structures:

- **Mode A (Monorepo):** `docs/` lives at the repo root alongside code packages, services, and workers.
- **Mode B (Multi-Service Blueprint Hub):** A dedicated blueprint repository holds shared intent, OOUX nouns, architecture contracts, and mounts satellite microservice repos.
- **Mode C (Service Satellite Repo):** A standalone service repository containing local code and migrations, consuming shared contracts from an upstream blueprint or MCP gateway.
