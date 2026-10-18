# CGSpec Polyrepo Template (Federated Multi-Repo Architecture)

This template demonstrates how the **Reformed CGSpec v0.2 Specification-Driven SDLC** governs a multi-repository ecosystem (e.g. separate Git repositories for frontend, backend API, and Airflow data pipelines) while simultaneously guaranteeing **Global Coherence** and **100% Service Independence**.

---

## 1. The Core Polyrepo Problem & The CGSpec Solution

In a polyrepo setup, organizations face a critical tension:
- **Autonomy:** Each team wants their own Git repository, independent deployments, independent CI/CD, and freedom to choose local technologies.
- **Coherence:** The business needs unified authentication, consistent domain nouns, non-conflicting API contracts, and an unbroken user experience.

Without a specification engine, polyrepos degrade into **Silent Integration Drift**: the backend changes an API payload, the frontend breaks in production, and documentation across scattered wikis is perpetually obsolete.

CGSpec solves this through three codified architectural mechanisms:

```mermaid
flowchart TD
    subgraph CentralGovernance["central-governance/ (Global Source of Truth)"]
        direction TB
        G_INDEX["docs/00-INDEX.md (Virtual Mounting Table across all repos)"]
        G_SPINES["docs/spines/ (01-INTENT, 02-OOUX, 03-EXPERIENCE, 04-ARCH, 05-DELIVERY)"]
        G_ADR["docs/adr/ (Global Tier 1 ADRs: JWT standard, crypto, event bus)"]
        G_MEM["docs/_memlog.md (System-Wide Milestone Ledger)"]
    end

    subgraph ServiceRepos["Independent Polyrepos (Decentralized Authoring & Deployments)"]
        direction TB
        subgraph RepoSatellite["service-satellite-template/ (Instantiated per Service)"]
            S_DOCS["Local docs/00-INDEX.md & docs/_memlog.md"]
            S_SPINES["Local docs/spines/ (Bounded Service Context & Flows)"]
            S_ADR["Local docs/adr/ (Tier 2 Service ADRs: tech choices)"]
            S_SLC["Local docs/slices/ (Bounded Service Delivery Contracts)"]
        end
    end

    CentralGovernance -->|"ADR-004 Virtual Mounting"| ServiceRepos
```

---

## 2. The 3 Architectural Mechanisms

### Mechanism 1: Two-Tier Hierarchical ADRs (ADR-005)
- **Tier 1 (Global System ADRs in `central-governance/docs/adr/`):** Decisions that bind all repositories (e.g. `ADR-001: Ed25519 Token Signing`, `ADR-002: PostgreSQL 16 Baseline`, `ADR-003: Hexagonal Port Boundary Standard`).
- **Tier 2 (Service-Local ADRs in `services/<repo>/docs/adr/`):** Decisions strictly internal to that service (e.g. `ADR-001: Use TanStack Query in frontend-web`, `ADR-001: Use Celery in data-pipelines`). Backend and data teams are not burdened with frontend styling decisions.

### Mechanism 2: Consumer-Driven Contracts via Hexagonal Ports (ADR-004)
Services never depend on each other's live infrastructure during development or unit testing:
1. `services/frontend-web` defines the **Consumer Port Interface** (`UserAccountPort`) and an in-memory mock.
2. `services/frontend-web` tests and deploys **100% independently**.
3. `services/backend-api` implements the matching **Provider Adapter**.
4. In CI/CD, contract compatibility tests verify parity before deployment.

### Mechanism 3: Virtual Mounting & Federated Ingestion (`ingest.py`)
The central orchestrator runs deterministic AST scanning across all physical repositories without merging them into a monorepo:

```bash
# Ingest all repositories into the central governance manifest
python3 docs/_cgspec/01-script/ingest.py ../services/frontend-web  --subsystem frontend
python3 docs/_cgspec/01-script/ingest.py ../services/backend-api   --subsystem backend
python3 docs/_cgspec/01-script/ingest.py ../services/data-pipelines --subsystem data-pipelines
```

---

## 3. Directory Layout

```
polyrepo/
├── README.md
├── central-governance/           # Central Management / Blueprint Repository
│   ├── AGENTS.md                 # Global Constitutional Laws 1-11
│   └── docs/
│       ├── 00-INDEX.md           # Master Compass & Virtual Mounting Table
│       ├── README.md             # Docs Hub Overview
│       ├── _memlog.md            # System-Wide Milestone Ledger
│       ├── spines/               # Global Spines (01-INTENT .. 05-DELIVERY)
│       ├── adr/                  # Global Tier 1 ADRs
│       ├── slices/               # Cross-Service Milestone Delivery Contracts
│       └── _cgspec/              # Central Tooling, Research & Councils
│
└── service-satellite-template/   # Generic Blueprint for Any Satellite Service (1..N)
    ├── AGENTS.md                 # Service-Local Autopilot Guidelines
    └── docs/
        ├── 00-INDEX.md           # Service Local Compass
        ├── README.md             # Local Docs Hub Overview
        ├── _memlog.md            # Local Milestone Ledger
        ├── spines/               # Bounded Service Domain Spines (01..05)
        ├── adr/                  # Service-Local Tier 2 ADRs
        ├── slices/               # Service-Local Slice Contracts
        └── _cgspec/              # Local Doctor & Memlog Scripts
```
