---
name: cgspec-forge
description: Stage 1 Product Brainstorming & ORCA Object Map Compiler. Drives problem statement, mission, day-in-the-life walkthrough (01-INTENT.md), and Sophia Prater ORCA domain nouns & relationships (02-OOUX.md).
---

# cgspec-forge

## 1. Contract (Inputs -> Outputs)
- **Stage:** `1. Brainstorming & Intent` (Inherits all global laws from [`AGENTS.md`](../../AGENTS.md)).
- **Requires:** Initialized CGSpec vault (`docs/00..05`) and user product vision.
- **Produces:** Locked `docs/01-INTENT.md` (problem, actors, anti-goals, day-in-the-life flow), locked `docs/02-OOUX.md` (ORCA objects, `erDiagram` relationships, permissions,conceptual attributes), and `docs/00-INBOX.md` (`Future Backlog v0.2+`).

---

## 2. Stage-Specific Rules
1. **Zero Premature UI or Physical Schema:** Do not draw screen layouts, pick colors, or write SQL/ORM types in Stage 1. Focus strictly on *why we build* (`01-INTENT.md`) and *what domain nouns exist* (`02-OOUX.md`).
2. **Noun Foraging Before Verbs (ORCA Sequence):** Isolate core domain objects first, map their cardinality (`1:1`, `1:N`, `M:N`), attach actor permissions (`Owner` + `read | invoke | propose_edit | write | share | admin`), and list conceptual attributes.
3. **v0.1 Scope Firewall:** Challenge feature creep immediately. Park any non-essential `v0.2+` idea in `docs/00-INBOX.md` before it bloats the `v0.1` object map.

---

## 3. Workflow
1. **Anchor Problem & Day-in-the-Life (`docs/01-INTENT.md`):**
   - Interview the user on the core frustration, target functional actors, target Surface Profile (`A: Website`, `B: Mobile`, `C: Web Workspace`, `D: CLI`), strict anti-goals, and end-to-end Day-in-the-Life narrative.
2. **Compile ORCA Object Map (`docs/02-OOUX.md`):**
   - Extract the canonical nouns from the narrative, render the conceptual `erDiagram`, and define the CTA/permission matrix and conceptual attributes for each noun.
3. **Sync & Persist:**
   - Record each locked decision in `docs/.memlog.md`, write `docs/adr/ADR-NNN-<slug>.md` if a cross-cutting domain invariant is established, and update `docs/00-INDEX.md`.

---

## 4. Exit Gate
Confirm explicit user approval of `docs/01-INTENT.md` and `docs/02-OOUX.md`, run `python3 docs/.cgspec/scripts/doctor.py --repo . --strict-emojis`, and hand off to [`cgspec-ui-ux`](../cgspec-ui-ux/SKILL.md).
