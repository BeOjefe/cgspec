# ADR-002: Adaptive Monorepo vs. Multi-Repo (Polyrepo) & Database Migration Architecture

- **Status:** Accepted
- **Date:** 2026-10-16

## Context
Real-world engineering organizations run both single-repository apps (Monorepos) and multi-team, multi-repository systems (Polyrepos). Furthermore, database schemas require both a global architectural contract and executable SQL/ORM migration files.

## Decision
**CGSpec (`cgspec`)** operates in **Adaptive Dual-Mode** (aligned with `BMAD-METHOD` v7's polyrepo pattern + **CortexGate MCP** governance):
1. **Mode A (Monorepo):** `docs/` (including `docs/.memlog.md` and `docs/.working/`), `db/migrations/`, and `src/` live in one repository.
2. **Mode B (Multi-Repo Hub-and-Spoke / Polyrepo):** A central `<project>-blueprint` repository holds the global `docs/` (`.memlog.md`, `00-INDEX.md` .. `05-DELIVERY.md`, `adr/`, and cross-repo slice specs), while each service repository (`*-api`, `*-frontend`, `*-airflow`) holds its own local `AGENTS.md`, `CLAUDE.md`, and executable `db/migrations/` for the services it owns.
3. **CortexGate Virtual Mount Engine:** When connected to **CortexGate**, individual repositories (`BeOjefe/meoce-api`, `mrojefe/meoce-frontend`, `BeOjefe/meoce-airflow`) are mounted into a single virtual Project view in Studio. The AI agent connects via a scoped Virtual Key, reading cross-repo architecture contracts via MCP while strictly committing changes only to the respective repository.

## Consequences
- No forced monorepo migrations: microservices, frontend apps, and data pipelines remain in independent Git repositories.
- Zero cross-repo git pollution: database migrations live strictly inside the backend repository that executes them.
- Centralized human governance: human leads review proposals across repos in CortexGate Studio without juggling git terminal sessions.

