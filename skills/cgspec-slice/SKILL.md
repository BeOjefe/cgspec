---
name: cgspec-slice
description: Stage 4–7 Atomic Vertical Slice Builder. Use when generating bounded slice contracts (SLICE-NNN.md) from locked spines (01..05), implementing modular Ports & Adapters production code, or running automated tests and visual verification.
---

# cgspec-slice

## 1. Contract (Inputs -> Outputs)
- **Stage:** `4–7. Milestones, Coding, Testing & CI/CD` (Inherits all global laws from [`AGENTS.md`](../../AGENTS.md)).
- **Requires:** Approved `docs/spines/01-INTENT.md`, `02-OOUX.md`, `03-EXPERIENCE.md` (with verified prototype), `04-ARCHITECTURE.md`, and `docs/adr/*.md`.
- **Produces:** Bounded slice contract (`docs/slices/SLICE-NNN-<slug>.md`), modular production code + tests, and updated `docs/spines/05-DELIVERY.md` + `docs/00-INDEX.md`.

---

## 2. Stage-Specific Rules
1. **Strict Experience & ADR Pre-Flight:** Never scaffold production code if `03-EXPERIENCE.md` is unlocked or if any `ADR-NNN` invariant would be violated.
2. **Contract-First Mock Isolation:** When Slice A depends on an unbuilt external service or Slice B, define the Port interface and mock adapter first so the vertical slice is 100% testable in isolation.
3. **Zero Direct Infrastructure Imports in UI:** UI components must never import database drivers, filesystem APIs, or crypto primitives directly.

---

## 3. Workflow (5-Tier Insulated Swarm)
1. **Draft Slice Contract (`docs/slices/SLICE-NNN-<slug>.md`):**
   - Define target OOUX nouns, actor permissions, exact files in scope, Port/Adapter interfaces, and test/UI state acceptance criteria.
2. **Dispatch Tier 1 Swarm Supervisor (`cgspec-inspector`):**
   - Main Agent spawns **ONLY ONE** child subagent: [`cgspec-inspector`](../../agents/cgspec-inspector.md) (never spawning multiple builders directly in root chat, and never spawning `type="research"` for builders/adversaries).
   - `cgspec-inspector` spawns $K$ peer-to-peer [`cgspec-builder`](../../agents/cgspec-builder.md) agents (with a Peer Directory via `send_message`), which implement modular code/UI files directly on disk and run **Phase A Self-Verification** (unit/integration tests, typechecks, `visual_audit.py`, and `view_file` screenshot inspection).
3. **Dual Adversarial Loop (`while verdict != PASS`):**
   - **Inner Loop (Tier 3):** Each `Builder_i` is audited by a dedicated, cold-facts-only [`cgspec-unit-adversary`](../../agents/cgspec-unit-adversary.md) (coordinating laterally with peer Unit Adversaries via `send_message`) **while `unit_verdict_i != PASS`**.
   - **Outer Loop (Tier 4):** Once all $K$ Unit Adversaries return `PASS`, [`cgspec-chief-adversary`](../../agents/cgspec-chief-adversary.md) audits the integrated slice across all spines **while `global_verdict != PASS`**.
4. **Tier 5 Human Validation & Deep Root-Cause Interview (`If User Says No`):**
   - If the user rejects any part of the slice, the Main Agent conducts a deep coaching interview to uncover the root cause, updates `docs/_memlog.md` and affected spines (`01..05`), confirms with the user, and only then re-invokes `cgspec-inspector`.

---

## 4. Exit Gate
Confirm all $K$ Unit Adversaries + `cgspec-chief-adversary` returned `GLOBAL_VERDICT: PASS (0 defects)`, log `SLICE-NNN` completion to `docs/_memlog.md`, update `00-INDEX.md` and `docs/spines/05-DELIVERY.md`, and run `python3 docs/_cgspec/01-script/doctor.py --repo . --strict-emojis`.
