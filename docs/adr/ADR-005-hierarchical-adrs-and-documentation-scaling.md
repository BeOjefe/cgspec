# ADR-005: Hierarchical ADRs, Documentation Scaling & Multi-Tenant Scoping

- **Status:** Accepted
- **Date:** 2026-10-16
- **Context:** As systems grow from initial `v0.1` prototypes to complex multi-team enterprise platforms, managing Architecture Decision Records (ADRs) and specifications requires answering three critical questions:
  1. Do backend-specific ADRs mix with global architecture ADRs?
  2. How do single spine files scale as documentation expands?
  3. How are ADRs and specs isolated in multi-tenant environments?
- **Decision:**
  1. **Two-Tier Hierarchical ADRs (Never Mixed):**
     - **Global / System ADRs (in `CG-Core` / `blueprint/docs/adr/`):** Decisions affecting the whole product, cross-service communication, global auth schemas, and data conventions (e.g. `JWT format`, `PostgreSQL as primary DB`, `Kafka event bus`).
     - **Local / Service ADRs (in `<service-repo>/docs/adr/`):** Decisions strictly internal to that service (e.g. `Use SQLAlchemy 2.0 with asyncpg in meoce-api`, `Airflow CeleryExecutor configuration in meoce-airflow`). Frontend and other teams are not burdened with internal backend ADRs.
  2. **File-to-Folder Sprouting (Cell Division):**
     - In `v0.1`, keeping core spines as single files (`01-PRD.md`, `02-NOUNS-AND-FLOWS.md`, `03-ARCHITECTURE.md`) provides maximum readability and agent context efficiency.
     - When a domain grows beyond $\sim 300-500$ lines, the file sprouts into a directory of the same name (e.g. `docs/01-PRD.md` $\rightarrow$ `docs/prd/` with `overview.md`, `features/`, `actors.md`). `docs/00-INDEX.md` remains the central compass.
  3. **Multi-Tenant & Role Isolation:**
     - **Organization Boundary:** Hard cryptographic and database isolation. Tenant A cannot search, read, or discover Tenant B's ADRs or specs.
     - **Project Boundary:** Studio groups ADRs cleanly by provenance (`Global / System` vs. `Service-Specific`).
     - **Scoped MCP Context:** An AI agent with a key scoped to `Backend API` retrieves only `Global ADRs` + `Backend ADRs`. It never receives unrelated service ADRs or personal vault records.
- **Consequences:**
  - Clear architectural boundaries: engineers read only relevant decisions.
  - Zero context pollution for AI agents querying MCP.
  - Linear scaling from day 1 prototype to multi-organization enterprise.
