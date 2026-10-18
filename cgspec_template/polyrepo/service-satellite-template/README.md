# Service Satellite Template (ADR-004 Topology-Neutral Service Repository)

This template is the generic, topology-neutral starter kit for **ANY independent service repository** in an $N$-tier polyrepo ecosystem (e.g. `service-auth`, `service-billing`, `worker-indexing`, `app-web-checkout`, `app-mobile-ios`, or `pipeline-analytics`).

---

## 1. How to Instantiate a New Service Repository

Whenever you create or onboard a new service repository in your polyrepo architecture:

1. **Copy this directory into your service repository root:**
   ```bash
   cp -r service-satellite-template/* /path/to/my-new-service/
   ```
2. **Update `docs/00-INDEX.md`** with the service's name and its connection to the Central Governance Blueprint.
3. **Register this service in the Central Blueprint's `docs/00-INDEX.md`** under the **Arbitrary Virtual Mounting Table (ADR-004)**.
4. **Verify baseline health:**
   ```bash
   python3 docs/.cgspec/01-script/doctor.py --repo . --strict-emojis
   ```

---

## 2. Directory Structure

```
my-service-repo/
├── AGENTS.md               # Local Service Agent Instructions (inheriting Global Laws)
├── docs/
│   ├── 00-INDEX.md         # Local Service Compass & Central Blueprint Pointer
│   ├── .memlog.md          # Local Service Release & Milestone Log
│   └── .cgspec/            # Local Engine Room
│       ├── 01-script/      # doctor.py (local verification)
│       ├── 04-adr/         # Service-Local ADRs (e.g. choice of ORM, local cache)
│       ├── 06-slice/       # Service-Local Slice Implementation Contracts
│       └── .archive/       # Stashed local prototypes and specs
└── src/ or app/            # Service Production Code (100% owned by this repository)
```
