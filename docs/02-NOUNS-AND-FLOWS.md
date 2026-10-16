# docs/02-NOUNS-AND-FLOWS.md — CGSpec (`cgspec`) Domain Model, Non-Linear Flow & Multi-Repo Topology

> **Pillar 2: Core Objects, Non-Linear `.memlog.md` Loop, 3-Tier Pivot Engine, and Monorepo vs. Polyrepo Layout**

---

## 1. Core Domain Objects ("The Nouns of CGSpec")

Every artifact managed by `cgspec` (both in local Git files today and via **CortexGate MCP** tomorrow) maps to 7 explicit nouns with built-in **Ownership & Granular Permissions**:

```mermaid
erDiagram
    PROJECT_BLUEPRINT ||--|| MEMLOG : "records chronological truth in"
    PROJECT_BLUEPRINT ||--|{ DERIVED_SPINE : "projects terse contracts into"
    PROJECT_BLUEPRINT ||--o{ INBOX_SPARK : "parks future ideas in"
    PROJECT_BLUEPRINT ||--|{ ADR_RECORD : "locks major decisions in"
    PROJECT_BLUEPRINT ||--|{ VERTICAL_SLICE : "executes work via"
    DERIVED_SPINE ||--o{ WORKING_ARTIFACT : "explores options in .working/"

    MEMLOG {
        string entry_id PK "e.g., M-042"
        string tag "decision | assumption | crack | kill | direction:parked | lock"
        string owner_id "User or Team ID (CortexGate MCP compatible)"
        string permissions "read | invoke | propose_edit | write | share | admin"
    }
    DERIVED_SPINE {
        string doc_id PK "00-INDEX | 01-PRD | 02-NOUNS | 03-ARCH | 04-DESIGN | 05-EXPERIENCE"
        string status "DRAFT | LOCKED | PIVOTING"
        string derived_from_memlog_id "Latest M-NNN"
    }
    WORKING_ARTIFACT {
        string path PK "docs/.working/* (Excalidraw, HTML theme/direction mocks)"
        boolean ephemeral "True (never loaded into build context)"
    }
    VERTICAL_SLICE {
        string slice_id PK "e.g., 001-auth-slice"
        string target_repos "Monorepo path or Polyrepo list"
        string status "SPEC_LOCKED | BUILDING | VERIFIED"
    }
```

---

## 2. Dynamic Non-Linear Flow & 3-Tier Pivot Engine

By combining **BMAD v7's `.memlog.md` non-linear derivation** + **`bmad-correct-course`'s 6-step impact audit** + **CGSpec's 3-Tier Migration Engine**, you can change direction at **any moment** without losing structure:

```mermaid
flowchart TD
    IDEA["💡 New Idea, Critique, or Pivot Arrives<br/>(Anytime: Discovery, UX, or Mid-Coding)"] --> GATE{"Autopilot Triage Gate<br/>(AGENTS.md)"}

    GATE -->|"Off-scope for current v0.1 task"| PARK["📥 Park in docs/00-INBOX.md<br/>+ memlog.py --tags direction:parked<br/>(Zero interruption to active slice)"]

    GATE -->|"Refines PRD / UX / Arch in current scope"| NONLINEAR["🔄 Non-Linear Spine Update<br/>1. Log lock to docs/.memlog.md<br/>2. Re-derive affected Spine (01..05)<br/>3. Update 00-INDEX.md"]

    GATE -->|"Changes existing built code or architecture"| TIER{"6-Step Course-Correction Audit<br/>(cgspec-pivot)"}

    TIER -->|"Tier 1: Module Swap<br/>(e.g., SQLite -> Postgres)"| T1["🟢 Tier 1: Adapter Swap<br/>1. Write ADR-NNN<br/>2. Update 03-ARCHITECTURE.md<br/>3. Swap src/adapters/<module> only"]
    TIER -->|"Tier 2: Scope Expansion<br/>(e.g., Solo -> Team RBAC)"| T2["🟡 Tier 2: Additive Slice<br/>1. Write ADR-NNN<br/>2. Update 02-NOUNS & 03-ARCH<br/>3. Create additive DB migration & Slice"]
    TIER -->|"Tier 3: Total Architecture Switch<br/>(v1 -> v2)"| T3["🔴 Tier 3: Soul Extraction<br/>1. Freeze v1-legacy branch<br/>2. Keep 01-PRD & 02-NOUNS<br/>3. Rewrite 03-ARCH & scaffold v2"]
```

---

## 3. Monorepo vs. Multi-Repo (Polyrepo) + Database Migrations

Adopted and enhanced from [`BMAD-METHOD`'s Polyrepo & Worktrees pattern](file:///home/ojefe/.gemini/antigravity/brain/fe188afb-593e-4644-85a6-ef222a1f5bc4/scratch/BMAD-METHOD/skills/bmod-method/help/monorepo-and-polyrepo.md):

- **Mode A: Monorepo (Default for Single-Repo Projects):**
  - `docs/` (including `docs/.memlog.md` and `docs/.working/`) lives at the repo root alongside `AGENTS.md`, `CLAUDE.md`, `db/migrations/`, and `src/`.
- **Mode B: Multi-Repo / Polyrepo Workspace (For Multi-Team Companies & CortexGate):**
  - A central **`<project>-blueprint/` Git repository** at the workspace root holds `AGENTS.md`, `docs/.memlog.md`, `docs/00..05-*.md`, `docs/adr/`, and cross-repo slice specs.
  - **Where Database Docs & Migrations Live:**
    - The **Global Entity-Relationship Contract** lives in the Blueprint Hub (`docs/02-NOUNS-AND-FLOWS.md` & `docs/03-ARCHITECTURE.md`).
    - The **Executable SQL/ORM Migration Files** (`db/migrations/001_init.sql`) live **inside the specific service repo that owns that database** (e.g., `cortexgate-core/db/migrations/`), linked by Slice ID!
    - When **CortexGate MCP** is connected, editing a spec in the CortexGate UI or any AI agent creates a governed branch/PR against `<project>-blueprint` automatically.
