# docs/04-DESIGN.md — CGSpec (`cgspec`) Canonical Document & UX Spine Templates

> **Pillar 4: Copy-Paste Templates (`00-INDEX` .. `05-EXPERIENCE`, `.memlog.md`, `ADR`, and `Slice`)**

---

## 1. Template: `docs/.memlog.md` (Append-Only Chronological Log)

Managed automatically via `uv run scripts/memlog.py`:

```markdown
# Project Memory Log (.memlog.md)
> Append-only chronological log of decisions, assumptions, cracks, parked ideas, and locks. Canonical spines (`01`..`05`) are derived from this log.

### [M-001] 2026-10-16T17:00:00Z | tags: lock, architecture | owner: @ojefe | perms: read,invoke,propose_edit
- **Summary:** Enforce Ports & Adapters modularity (`src/core/`, `src/modules/`, `src/adapters/`, `src/ui/`).
- **Rationale:** Allows Tier 1 module swaps without touching domain or UI code.
```

---

## 2. Template: Dual UX Spine (`04-DESIGN.md` + `05-EXPERIENCE.md` + `.working/`)

Adopted from **[Google Labs `design.md`](https://github.com/google-labs-code/design.md)** and **`BMAD-METHOD` (`bmad-ux`)**:

### A. Visual Explorations in `docs/.working/` (Before Locking)
- `docs/.working/color-themes.html` — Interactive palette & token comparison
- `docs/.working/wireframes.excalidraw` — Low-fidelity Excalidraw layout & flow wireframes
- `docs/.working/design-directions.html` — High-craft key screen variations

### B. `docs/04-DESIGN.md` (Visual System Spine — Google Labs Format)
```markdown
# docs/04-DESIGN.md — Visual Design System Spine
## 1. Aesthetic Direction & Domain Exemplars
## 2. Color Tokens (Semantic Roles, Light/Dark, Contrast Ratios)
## 3. Typography Scale & Rhythm
## 4. Layout Grid, Spacing & Breakpoints
## 5. Core Component Catalogue & Variants
```

### C. `docs/05-EXPERIENCE.md` (Behavioral UX & Screen-State Spine)
```markdown
# docs/05-EXPERIENCE.md — Behavioral Experience & Screen Inventory
## 1. Named Protagonists & Context of Use
- **Protagonist 1 (e.g., Mary on Desktop):** Primary workflow & high-frequency actions.
- **Protagonist 2 (e.g., Pary on Tablet / Mobile):** Constrained viewport or restricted permission (`read | invoke`) workflow.

## 2. Locked v0.1 Screen & State Inventory
| Screen ID | Primary Nouns Displayed | Required States (`loading \| empty \| error \| offline \| partial \| populated \| denied`) | Accessibility Target |
| :--- | :--- | :--- | :--- |
| `SCR-01` | ... | All 7 states defined | WCAG 2.2 AA |
```

---

## 3. Template: `docs/adr/ADR-NNN-<slug>.md`

```markdown
# ADR-NNN: <Title>
- **Status:** Accepted | Superseded by ADR-XXX
- **Date:** YYYY-MM-DD
- **Memlog Lock ID:** M-NNN
- **Owner & Permissions:** `@owner` (`read | invoke | propose_edit | write | share | admin`)
- **Context:** What tension, council debate, or pivot triggered this decision?
- **Decision:** The exact choice locked.
- **Consequences:** Which Pillar Docs (`01`..`05`) and Slices were updated.
```
