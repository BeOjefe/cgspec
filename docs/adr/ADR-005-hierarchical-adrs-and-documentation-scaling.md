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
  2. **File-to-Folder Sprouting ("Cell Division" with Numeric Prefix Preservation):**
     - **Numeric Prefix Invariant:** When a spine sprouts into a directory, it **MUST retain its two-digit numerical prefix** to maintain strict alphabetical/numerical ordering in file trees and terminal `ls` commands:
       - `docs/01-INTENT.md` $\longrightarrow$ `docs/01-INTENT/` (contains `00-INDEX.md`, `mission/`, etc.)
       - `docs/02-OOUX.md` $\longrightarrow$ `docs/02-OOUX/` (contains `00-INDEX.md`, `nouns/`, etc.)
       - `docs/03-EXPERIENCE.md` $\longrightarrow$ `docs/03-EXPERIENCE/` (contains `00-INDEX.md`, `prototypes/`, etc.)
       - `docs/04-ARCHITECTURE.md` $\longrightarrow$ `docs/04-ARCHITECTURE/` (contains `00-INDEX.md`, `contracts/`, etc.)
       - `docs/05-DELIVERY.md` $\longrightarrow$ `docs/05-DELIVERY/` (contains `00-INDEX.md`, `slices/`, etc.)
     - **Deterministic Trigger Criteria (Zero Ambiguity for AI):**
       - **Rule 1 (v0.1 Default):** Spines MUST remain single files (`docs/01-INTENT.md` through `docs/05-DELIVERY.md`) during `v0.1` for maximum reading speed and minimal LLM prompt token consumption.
       - **Rule 2 (Sprout Gate):** An agent is ONLY permitted to convert a spine file into a numbered folder if:
         - **Condition A (Line Limit):** The spine file exceeds **500 lines** on disk (`wc -l > 500`), OR
         - **Condition B (Multi-Squad Gate):** The project phase in `docs/00-INDEX.md` is explicitly set to `v0.2+` with multiple squads editing distinct sub-domains concurrently.
       - If neither condition is met, the file MUST remain a single file.

  3. **Multi-Tenant & Role Isolation:**
     - **Organization Boundary:** Hard cryptographic and database isolation. Tenant A cannot search, read, or discover Tenant B's ADRs or specs.
     - **Project Boundary:** Studio groups ADRs cleanly by provenance (`Global / System` vs. `Service-Specific`).
     - **Scoped MCP Context:** An AI agent with a key scoped to `Backend API` retrieves only `Global ADRs` + `Backend ADRs`. It never receives unrelated service ADRs or personal vault records.
- **Consequences:**
  - Clear architectural boundaries: engineers read only relevant decisions.
  - Zero context pollution for AI agents querying MCP.
  - Linear scaling from day 1 prototype to multi-organization enterprise.
