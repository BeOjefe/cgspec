# CGSpec Project Templates (Reformed CGSpec v0.2)

This directory provides three production-ready starter template archetypes for bootstrapping or governing any software project using the **Reformed CGSpec v0.2 Specification-Driven SDLC Methodology**:

```
cgspec_template/
├── README.md               # This architectural guide
├── monorepo/               # Standard Monorepo (single-file spines 01-INTENT.md..05-DELIVERY.md)
├── monorepo_big/           # Enterprise Monorepo (sprouted directory spines 01-INTENT/..05-DELIVERY/)
└── polyrepo/               # Federated Polyrepo Ecosystem (Central Governance + Decoupled Services)
```

---

## 1. Choosing Your Template Flavor

| Template Flavor | Best For | Spine Topology | ADR & Slice Isolation |
| :--- | :--- | :--- | :--- |
| **[`monorepo/`](./monorepo/)** | Greenfield startups, SaaS MVPs, single-team applications (`< 500` spec lines per spine). | Single-file living spines (`docs/01-INTENT.md` through `docs/05-DELIVERY.md`). | Central `04-adr/` and `06-slice/` inside `docs/.cgspec/`. |
| **[`monorepo_big/`](./monorepo_big/)** | Enterprise platforms, complex systems (`> 500` spec lines or multi-squad development). | Sprouted directory spines (`docs/01-INTENT/` through `docs/05-DELIVERY/` with `INDEX.md`). | Modular sub-documents per noun, schema, and milestone. |
| **[`polyrepo/`](./polyrepo/)** | Distributed multi-repo ecosystems (e.g. Next.js web + FastAPI backend + Airflow pipelines in separate Git repos). | Central governance repo + local service `docs/` and local ADRs. | Two-tier ADRs (Global vs Service-Local) + Consumer-Driven Contracts. |

---

## 2. Quickstart Instructions

### Option A: Standard Monorepo
```bash
cp -r cgspec_template/monorepo/AGENTS.md /path/to/your-project/
cp -r cgspec_template/monorepo/docs /path/to/your-project/
cd /path/to/your-project/
python3 docs/.cgspec/01-script/doctor.py --repo . --strict-emojis
```

### Option B: Enterprise Monorepo (Sprouted Spines)
```bash
cp -r cgspec_template/monorepo_big/AGENTS.md /path/to/enterprise-project/
cp -r cgspec_template/monorepo_big/docs /path/to/enterprise-project/
cd /path/to/enterprise-project/
python3 docs/.cgspec/01-script/doctor.py --repo . --strict-emojis
```

### Option C: Federated Polyrepo
```bash
# 1. Place central-governance in your blueprint or management repository
cp -r cgspec_template/polyrepo/central-governance/AGENTS.md /path/to/management-repo/
cp -r cgspec_template/polyrepo/central-governance/docs /path/to/management-repo/

# 2. Ingest existing physical polyrepos into the central manifest
python3 docs/.cgspec/01-script/ingest.py /path/to/frontend-repo --subsystem frontend
python3 docs/.cgspec/01-script/ingest.py /path/to/backend-repo  --subsystem backend
python3 docs/.cgspec/01-script/ingest.py /path/to/data-repo     --subsystem data-pipelines

# 3. Verify cross-service health
python3 docs/.cgspec/01-script/doctor.py --repo /path/to/management-repo --strict-emojis
```
