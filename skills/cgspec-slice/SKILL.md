---
name: cgspec-slice
description: Stage 4–7 Atomic Vertical Slice Builder. Use when generating bounded slice contracts (SLICE-NNN.md) from locked spines (01..05), implementing modular Ports & Adapters production code, or running automated tests and visual verification.
---

# cgspec-slice

## 1. Contract (Inputs -> Outputs)
- **Stage:** `4–7. Milestones, Coding, Testing & CI/CD` (Inherits all global laws from [`AGENTS.md`](../../AGENTS.md)).
- **Requires:** Approved `01-INTENT.md`, `02-OOUX.md`, `03-EXPERIENCE.md` (with verified prototype), `04-ARCHITECTURE.md`, and `docs/adr/*.md`.
- **Produces:** Bounded slice contract (`docs/slices/SLICE-NNN-<slug>.md`), modular production code + tests, and updated `docs/05-DELIVERY.md` + `docs/00-INDEX.md`.

---

## 2. Stage-Specific Rules
1. **Strict Experience & ADR Pre-Flight:** Never scaffold production code if `03-EXPERIENCE.md` is unlocked or if any `ADR-NNN` invariant would be violated.
2. **Contract-First Mock Isolation:** When Slice A depends on an unbuilt external service or Slice B, define the Port interface and mock adapter first so the vertical slice is 100% testable in isolation.
3. **Zero Direct Infrastructure Imports in UI:** UI components must never import database drivers, filesystem APIs, or crypto primitives directly.

---

## 3. Workflow
1. **Draft Slice Contract (`docs/slices/SLICE-NNN-<slug>.md`):**
   - Define target OOUX nouns, actor permissions, exact files in scope, Port/Adapter interfaces, and test/UI state acceptance criteria.
2. **Implement & Test:**
   - Build domain logic, adapters, and UI views matching the locked `03-EXPERIENCE.md` tokens and state matrix.
   - Run unit/integration tests, typechecks, and linter.
3. **Closed-Loop UI Verification (For Frontend Slices):**
   - Run `visual_audit.py`, inspect headless browser screenshots via `view_file`, and verify zero console/page errors across required states.

---

## 4. Exit Gate
Log `SLICE-NNN` completion to `docs/.memlog.md`, update `00-INDEX.md` and `05-DELIVERY.md`, and run `python3 docs/.cgspec/scripts/doctor.py --repo . --strict-emojis`.
