---
name: cgspec-init
description: Stage 0 Workspace Initializer & Brownfield AST Ingestor. Use when starting a new CGSpec project, initializing AGENTS.md and docs/00..05 spines, or onboarding an existing legacy codebase/monorepo via ingest.py.
---

# cgspec-init

## 1. Contract (Inputs -> Outputs)
- **Stage:** `0. Initialization & Brownfield Ingestion` (Inherits all global laws from [`AGENTS.md`](../../AGENTS.md)).
- **Requires:** New repository (Greenfield) OR existing legacy codebase/monorepo (Brownfield).
- **Produces:** `AGENTS.md`, `CLAUDE.md` (1-line pointer), `docs/.memlog.md`, `docs/00..05` pure spines, and `docs/.cgspec/` (`01-script/`, `02-research/`, `03-council/`, `04-adr/`, `05-prototype/`, `06-slice/`, `.archive/`), plus `docs/.cgspec/brownfield-manifest.json` and `docs/.cgspec/04-adr/ADR-000-legacy-baseline-adoption.md` for Brownfield.

---

## 2. Stage-Specific Rules
1. **Non-Destructive Legacy Adoption:** Never delete existing project docs or code. Move scattered legacy notes into `docs/.cgspec/.archive/`.
2. **AST-First Brownfield Extraction:** On existing codebases, never guess domain nouns from filenames alone; run `ingest.py` to extract routes, models, and schemas deterministically before populating `02-OOUX.md`.
3. **Pure docs/ Root:** Keep `docs/` clean with only the canonical human-readable spines (`00..05`, `.memlog.md`). All engine scripts, ADRs, research, and prototypes live inside `docs/.cgspec/`.

---

## 3. Workflow
1. **Detect Mode & Topology:**
   - Inspect workspace for existing code (`src/`, `app/`, `packages/`) and topology configs (`pnpm-workspace.yaml`, `Cargo.toml`, `pyproject.toml`). If ambiguous, ask via `ask_question` (Monorepo vs Multi-Service Hub vs Single Service).
2. **Run Brownfield AST Ingestion (Existing Codebases Only):**
   ```bash
   python3 docs/.cgspec/01-script/ingest.py .
   ```
   Distill high-level domain entities from `docs/.cgspec/brownfield-manifest.json` into `docs/02-OOUX.md` (zero raw SQL) and record the existing stack freeze in `docs/.cgspec/04-adr/ADR-000-legacy-baseline-adoption.md`.
3. **Install Constitution & Hidden Engine (`docs/.cgspec/`):**
   - Write root `AGENTS.md` and 1-line `CLAUDE.md` (`Read and strictly follow all instructions in [./AGENTS.md](./AGENTS.md).`).
   - Create `docs/.cgspec/` with strictly singular numbered directories:
     - `docs/.cgspec/01-script/` (`doctor.py`, `memlog.py`, `ingest.py`, `visual_audit.py`)
     - `docs/.cgspec/02-research/` (`README.md`, `RES-NNN-...`)
     - `docs/.cgspec/03-council/` (`COUNCIL-NNN-...`)
     - `docs/.cgspec/04-adr/` (`ADR-NNN-...`)
     - `docs/.cgspec/05-prototype/` (`wireframe-v1.html...`, `prototype-v0.1.html`)
     - `docs/.cgspec/06-slice/` (`SLICE-NNN-...`)
     - `docs/.cgspec/.archive/`
4. **Scaffold Reformed v2 Spines (`docs/00..05`):**
   - Initialize `docs/.memlog.md` (`M-001`), `00-INDEX.md`, `00-INBOX.md`, `01-INTENT.md`, `02-OOUX.md`, `03-EXPERIENCE.md`, `04-ARCHITECTURE.md`, and `05-DELIVERY.md`.

---

## 4. Exit Gate
Run `python3 docs/.cgspec/01-script/doctor.py --repo . --strict-emojis` and confirm `0 errors` before handing off to [`cgspec-forge`](../cgspec-forge/SKILL.md).
