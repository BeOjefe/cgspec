# Bounded Vertical Slice Delivery Contracts (`docs/slices/`)

This directory houses the formal, bounded **Vertical Slice Contracts (`SLICE-NNN-<slug>.md`)**.

---

## 1. What is a Vertical Slice?
A vertical slice is an end-to-end, functional, testable slice of the system that cuts through all architectural layers (UI, Port interface, Domain logic, and Adapter persistence). 

Unlike horizontal layering ("build the entire database first, then the whole backend"), vertical slices deliver working, verified increments tied directly to a specific OOUX noun, screen interaction, or milestone.

---

## 2. Naming & Lifecycle
- **File Naming:** `SLICE-NNN-<slug>.md` (e.g. `SLICE-001-template.md`).
- **Contract Anatomy:**
  1. **User Story & Invariant:** What the slice accomplishes and what it must never break.
  2. **Boundary Contract:** Explicit Hexagonal Port definition and Adapter implementation requirements.
  3. **File Touch List:** Exact list of files to create or modify (strictly bounded).
  4. **Acceptance Test Gates:** Automated unit, integration, and visual tests that must pass.
  5. **Verification Protocol:** Command line invocations required before milestone lock.
