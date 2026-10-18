# 05-DELIVERY: Vertical Slice Manifest, Milestones & Verification

- **Status:** `[Locked in 03 — Awaiting Stage 4]`

---

## 1. Monotonic Milestone Roadmap
- **`v0.1` — Foundation & Core Domain Slice:**
  - `SLICE-001`: Core domain object creation and retrieval.
  - `SLICE-002`: Secondary domain workflow and state transitions.
- **`v0.2` — Advanced Capabilities & Integrations:**
  - `SLICE-003`: Extended integrations and automated exports.

---

## 2. Bounded Vertical Slice Registry (`docs/.cgspec/06-slice/`)

| Slice ID | Contract File | Target Noun | Pre-requisites | Status |
| :--- | :--- | :--- | :--- | :--- |
| **`SLICE-001`** | [`docs/.cgspec/06-slice/SLICE-001-template.md`](.cgspec/06-slice/SLICE-001-template.md) | `[PrimaryNounA]` | `03-EXPERIENCE`, `ADR-001` | `[Queued]` |

---

## 3. Automated Quality & CI/CD Verification Gates
1. **`doctor.py` Baseline Gate:** Strict Law 3 order, singular directories, zero Unicode emojis.
2. **`visual_audit.py` Gate:** 0 errors across Checks 1–22 for all HTML prototypes.
3. **Automated Test Suite:** All unit, integration, and Playwright tests must pass before slice sign-off.
