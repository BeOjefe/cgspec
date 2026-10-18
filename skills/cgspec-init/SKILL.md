---
name: cgspec-init
description: Stage 0 Workspace Initializer & Brownfield AST Ingestor. Use when starting a new CGSpec project, initializing AGENTS.md and docs/00..05 spines, or onboarding an existing legacy codebase/monorepo via ingest.py.
---

# cgspec-init

## 1. Contract (Inputs -> Outputs)
- **Stage:** `0. Initialization & Brownfield Ingestion` (Inherits all global laws from [`AGENTS.md`](../../AGENTS.md)).
- **Requires:** New repository (Greenfield) OR existing legacy codebase/monorepo (Brownfield).
- **Produces:** `AGENTS.md`, `CLAUDE.md` (1-line pointer), `docs/_memlog.md`, `docs/00-INDEX.md`, `docs/spines/` (`01..05`), `docs/adr/`, `docs/slices/`, `docs/prototypes/`, and `docs/_cgspec/` (`01-script/`, `02-research/`, `03-council/`, `_archive/`), plus `docs/_cgspec/brownfield-manifest.json` and `docs/adr/ADR-000-legacy-baseline-adoption.md` for Brownfield.

---

## 2. Stage-Specific Rules
1. **Non-Destructive Legacy Adoption:** Never delete existing project docs or code. Move scattered legacy notes into `docs/_cgspec/_archive/`.
2. **AST-First Brownfield Extraction:** On existing codebases, never guess domain nouns from filenames alone; run `ingest.py` to extract routes, models, and schemas deterministically before populating `docs/spines/02-OOUX.md`.
3. **Specification Hub Topology:** Structure `docs/` with grouped living spines (`docs/spines/`), visible architecture decisions (`docs/adr/`), vertical slice contracts (`docs/slices/`), interactive wireframes (`docs/prototypes/`), and visible engine tooling (`docs/_cgspec/`).

---

## 3. Workflow
1. **Detect Mode & Topology:**
   - Inspect workspace for existing code (`src/`, `app/`, `packages/`) and topology configs (`pnpm-workspace.yaml`, `Cargo.toml`, `pyproject.toml`). If ambiguous, ask via `ask_question` (Monorepo vs Multi-Service Hub vs Single Service).
2. **Run Brownfield AST Ingestion (Existing Codebases Only):**
   ```bash
   python3 docs/_cgspec/01-script/ingest.py .
   ```
   Distill high-level domain entities from `docs/_cgspec/brownfield-manifest.json` into `docs/spines/02-OOUX.md` (zero raw SQL) and record the existing stack freeze in `docs/adr/ADR-000-legacy-baseline-adoption.md`.
3. **Install Constitution & Engine (`docs/_cgspec/`):**
   - Write root `AGENTS.md` and 1-line `CLAUDE.md` (`Read and strictly follow all instructions in [./AGENTS.md](./AGENTS.md).`).
   - Create `docs/_cgspec/` with strictly singular numbered directories:
     - `docs/_cgspec/01-script/` (`doctor.py`, `memlog.py`, `ingest.py`, `visual_audit.py`)
     - `docs/_cgspec/02-research/` (`README.md`, `RES-NNN-...`)
     - `docs/_cgspec/03-council/` (`COUNCIL-NNN-...`)
     - `docs/_cgspec/_archive/`
4. **Scaffold Reformed v0.2 Spines & First-Class Records:**
   - Initialize `docs/_memlog.md` (`M-001`), `docs/00-INDEX.md`, `docs/README.md`.
   - Scaffold `docs/spines/` (`01-INTENT.md`, `02-OOUX.md`, `03-EXPERIENCE.md`, `04-ARCHITECTURE.md`, `05-DELIVERY.md`).
   - Scaffold `docs/adr/` (`ADR-001-template.md`), `docs/slices/` (`SLICE-001-template.md`), and `docs/prototypes/`.

---

## 4. Exit Gate
Run `python3 docs/_cgspec/01-script/doctor.py --repo . --strict-emojis` and confirm `0 errors` before handing off to [`cgspec-forge`](../cgspec-forge/SKILL.md).
