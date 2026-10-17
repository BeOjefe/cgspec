---
name: cgspec-init
description: Initialize or migrate a monorepo, polyrepo, or existing legacy codebase into CGSpec (AGENTS.md, 1-line CLAUDE.md, docs/.memlog.md, docs/00..05 spines, doctor hook, and Brownfield Ingestion).
---

# cgspec-init

## Execution Modes & Philosophy

CGSpec accommodates both **Greenfield projects** (starting from scratch) and **Brownfield codebases** (existing systems, legacy repos, or monorepos needing structured specification).

Universal Invariants:
- **Law 3 (Experience Precedes Architecture):** Human Experience, UI/UX, and interactive prototypes strictly precede physical database tables, SQL schemas, and backend frameworks.
- **Topological Neutrality:** Never dogmatically impose a repository structure. Inspect the workspace and support Monorepos, Multi-Service Polyrepos, and Standalone Microservices neutrally.
- **Zero Decorative Emojis:** Strictly clean engineering typography across all generated docs and communications.

---

## Execution Steps

### 1. Topology & Ingestion Mode Detection
Determine whether the project is Greenfield or Brownfield:
- **Greenfield Setup:** Empty or new repository. Proceed to Step 2.
- **Brownfield Ingestion (`cgspec ingest`):** Existing codebase with pre-existing code, routes, or database schemas.
  1. **Deterministic AST Extraction:** Run `python3 {skill-dir}/scripts/ingest.py {project-root}` (optionally `--subsystem <path>` for bounded context scoping or `--live-schema <path>` for live SQL dumps).
  2. **Manifest Generation:** Produces `{project-root}/docs/.working/brownfield-manifest.json` conforming to `docs/.working/brownfield-manifest.schema.json`.
  3. **OOUX Distillation:** High-level domain nouns automatically populated into `02-NOUNS-AND-FLOWS.md` without raw physical SQL.
  4. **Baseline Lock (`ADR-000`):** Creates `docs/adr/ADR-000-legacy-baseline-adoption.md` codifying existing architectural decisions as the baseline freeze.

### 2. Workspace Topology Configuration
Detect or ask (via `ask_question`) the project structure:
- **Mode A (Monorepo):** Single repository containing docs, specs, backend services, frontend, and workers.
- **Mode B (Multi-Service Polyrepo Hub):** Central blueprint holding shared PRD, cross-cutting nouns, and mounting microservices or frontend repos.
- **Mode C (Service Satellite Repo):** A single microservice repo with its own code and migrations, consuming shared contracts from the central blueprint or MCP gateway.

### 3. Root Constitution
1. Write `{project-root}/AGENTS.md` containing the 7 Immutable Laws, the clean 1-line compass, the `scripts/doctor.py` hook, and the verification rules.
2. Write `{project-root}/CLAUDE.md` as a 1-line DRY pointer:
   `Read and strictly follow all instructions in [./AGENTS.md](./AGENTS.md).`

### 4. Directory & Spine Initialization
1. Create directories:
   `{project-root}/docs/.working/`, `{project-root}/docs/archive/`, `{project-root}/docs/adr/`, `{project-root}/docs/slices/`, `{project-root}/scripts/`.
2. Install `{project-root}/scripts/doctor.py` from `{skill-dir}/scripts/doctor.py`.
3. Move any legacy or scattered markdown files into `docs/archive/` or `docs/.working/` (never delete history).
4. Initialize `{project-root}/docs/.memlog.md`:
   ```bash
   uv run {skill-dir}/scripts/memlog.py add {project-root}/docs/.memlog.md \
     --tags "lock,init" \
     --summary "Initialized CGSpec vault"
   ```
5. Generate the 6 core spine files in `{project-root}/docs/`:
   - `00-INDEX.md`: Phase state, spine matrix, and slice registry table.
   - `00-INBOX.md`: Parked future sparks and scope buffer.
   - `01-PRD.md`: Problem statement, glossary, user profiles, and Day-in-the-Life journey.
   - `02-NOUNS-AND-FLOWS.md`: OOUX domain mental models (`erDiagram`), Owner + 6 permissions (`read|invoke|propose_edit|write|share|admin`), core business flows. (Zero physical SQL/DDL).
   - `03-ARCHITECTURE.md`: Modular boundaries, physical DDL, API contracts, Ports & Adapters, crypto/MCP envelopes.
   - `04-DESIGN.md`: Typography scale, layout grid, aesthetic archetype, visual tokens.
   - `05-EXPERIENCE.md`: Named protagonists, complete screen inventory, and the 7-State Component Matrix (`Populated`, `Loading Skeleton`, `Empty`, `Error`, `Denied 403`, `Offline`, `Partial`).

### 5. Pre-Flight Integrity Verification
Run the CGSpec Doctor to ensure all spines and memory logs are 100% compliant:
```bash
python3 scripts/doctor.py .
```
Verify zero errors before proceeding to Stage 1.
