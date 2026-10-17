---
name: cgspec-pivot
description: Stage 8 Course-Correction Impact Auditor & 3-Tier Migration Engine (Tier 1 Adapter Swap, Tier 2 Additive Scope Expansion, Tier 3 v1-to-v2 Soul Extraction).
---

# cgspec-pivot

## 1. Contract (Inputs -> Outputs)
- **Stage:** `8. Course Correction & Migration` (Inherits all global laws from [`AGENTS.md`](../../AGENTS.md)).
- **Requires:** Existing CGSpec vault (`docs/00..05`) and a requested architectural, scope, or paradigm change.
- **Produces:** Impact audit, stashed design assets (`docs/.cgspec/prototypes/stash/`), `docs/adr/ADR-NNN-<slug>.md`, and synchronized spines.

---

## 2. Stage-Specific Rules
1. **Classify Migration Tier Before Editing Spines:**
   - **Tier 1 (Module/Adapter Swap):** Tech swap behind an existing Port (e.g. SQLite -> Postgres). Leaves `01-INTENT`, `02-OOUX`, and `03-EXPERIENCE` untouched; updates only `ADR-NNN`, `04-ARCHITECTURE.md`, and `src/adapters/`.
   - **Tier 2 (Additive Scope Expansion):** New domain noun or screen added mid-flight. Triggers the Design Stash Protocol (`docs/.cgspec/prototypes/stash/`) and updates `01`..`05` additively.
   - **Tier 3 (Full `v1 -> v2` Soul Extraction):** Complete backend/architecture rewrite. Tags `archive/v1-baseline`, preserves the human-facing soul (`01-INTENT`, `02-OOUX`, `03-EXPERIENCE`), and rewrites `04-ARCHITECTURE.md` + `05-DELIVERY.md`.

---

## 3. Workflow
1. **6-Point Impact Audit:**
   - Check impact across (1) `01-INTENT`, (2) `02-OOUX`, (3) `03-EXPERIENCE`, (4) `04-ARCHITECTURE`, (5) `05-DELIVERY` / slices, and (6) database migrations.
   - Present the classified Tier (`Tier 1`, `Tier 2`, or `Tier 3`) and affected files to the user via `ask_question`.
2. **Execute Tiered Migration:**
   - Snapshot affected prototypes to `docs/.cgspec/prototypes/stash/` if Stage 2 is impacted, write the superseding `ADR-NNN`, update affected spines, and log to `docs/.memlog.md`.

---

## 4. Exit Gate
Run `python3 docs/.cgspec/scripts/doctor.py --repo . --strict-emojis` and confirm zero specification or ADR status drift.
