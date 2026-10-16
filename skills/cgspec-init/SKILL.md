---
name: cgspec-init
description: Initialize or migrate a monorepo/polyrepo into CGSpec (AGENTS.md, 1-line CLAUDE.md, docs/.memlog.md, docs/00..05 spines, docs/.working/).
---

# cgspec-init

## Execution Steps

1. **Topology Detection:**
   - Determine if `{project-root}` is **Mode A (Monorepo)** or **Mode B (Polyrepo Hub `<project>-blueprint`)**. Ask a 1-click question only if ambiguous.

2. **Root Constitution:**
   - Write `{project-root}/AGENTS.md` with Autopilot Coach rules (non-linear `.memlog.md` spine derivation, mid-stream spark parking into `00-INBOX.md`, explicit `Owner` + `read|invoke|propose_edit|write|share|admin` permissions, Ports & Adapters modularity, browser visual QA).
   - Write `{project-root}/CLAUDE.md` as a 1-line DRY pointer:
     `Read and strictly follow all instructions in [./AGENTS.md](./AGENTS.md).`

3. **Directory & Spine Initialization:**
   - Create `{project-root}/docs/.working/`, `{project-root}/docs/archive/`, `{project-root}/docs/adr/`, `{project-root}/docs/slices/`.
   - Move any legacy/scattered markdown or prototypes into `docs/archive/` or `docs/.working/` (never delete history).
   - Initialize `{project-root}/docs/.memlog.md`:
     ```bash
     uv run {skill-dir}/scripts/memlog.py add {project-root}/docs/.memlog.md \
       --tags "lock,init" \
       --summary "Initialized CGSpec vault"
     ```
   - Generate terse spine files in `{project-root}/docs/`:
     - `00-INDEX.md` (Phase state, spine matrix, slice table)
     - `00-INBOX.md` (`v0.2+` parked sparks)
     - `01-PRD.md` (Problem, glossary, `v0.1` wedge)
     - `02-NOUNS-AND-FLOWS.md` (`erDiagram`, `Owner` + 6 granular permissions, core flows)
     - `03-ARCHITECTURE.md` (Modular boundaries, DB/crypto/MCP contracts)
     - `04-DESIGN.md` (Google Labs `design.md` visual tokens & layout grid)
     - `05-EXPERIENCE.md` (Named protagonists, `v0.1` screen inventory with 7 states, WCAG 2.2 AA)
