---
name: cgspec-pivot
description: 6-Step Course-Correction Impact Audit and 3-Tier Migration Engine (Tier 1 Module Swap, Tier 2 Additive Scope Expansion, Tier 3 v1-to-v2 Soul Extraction).
---

# cgspec-pivot

## Execution Steps

1. **Silent 6-Step Impact Audit:**
   - Silently check `{project-root}/docs/.memlog.md` and `docs/00-INDEX.md` for impact across: (1) `01-INTENT`, (2) `02-OOUX`, (3) `03-EXPERIENCE`, (4) `04-ARCHITECTURE`, (5) `05-DELIVERY` / active slices, (6) `db/migrations/`.
   - Present the impact and recommended path naturally to the user via `ask_question` without using internal methodology jargon.
   - Maintain the clean text compass (zero emojis).

2. **Execute Migration Tier Silently:**
   - **Mid-Design Scope Pivots (Stage 2 -> Stage 1 Reopening):** If a pivot occurs during active design, execute the Design Stash Protocol (`skills/cgspec-ui-ux/SKILL.md`): snapshot current prototypes to `docs/.working/prototypes/stash/`, log pause in `.memlog.md`, re-lock `01-INTENT.md` & `02-OOUX.md`, then conduct a Design Delta Assessment upon re-entering Stage 2.
   - **Tier 1 (Module/Adapter Swap):** Leave `01`, `02`, `03` untouched. Silently log lock to `.memlog.md`, write `ADR-NNN`, update `04-ARCHITECTURE.md`, swap `src/adapters/<module>/`.
   - **Tier 2 (Additive Scope Expansion):** Silently log lock to `.memlog.md`, write `ADR-NNN`, update `02-OOUX.md` + `04-ARCHITECTURE.md`, add forward DB migration and slice.
   - **Tier 3 (Full `v1 -> v2` Architecture Switch):**
     1. Branch/tag current state as `archive/v1-baseline`.
     2. Preserve domain soul (`01-INTENT.md`, `02-OOUX.md`, `03-EXPERIENCE.md`). Law 3 invariant: Human Experience and user-facing mental model outlive backend implementation rewrites.
     3. Silently log architecture replacement in `.memlog.md`, rewrite `04-ARCHITECTURE.md`, and scaffold `v2` slices in `05-DELIVERY.md`.

3. **Post-Pivot Integrity Gate:**
   - Run `python3 scripts/doctor.py .` to ensure all spines, memory log entries, and ADRs are valid and consistent.

