# CGSpec Methodology Changelog

All notable changes, architectural invariants, and skill evolutions to `cgspec` are documented in this file.

---

## [v0.1.4] — 2026-10-16
### Fixed
- **Council Subagent Isolation (Silent Debater Protocol):** Eliminated chat pollution where Debaters 1, 2, and 3 sent direct completion messages to the Main Agent. Debaters now write exclusively to disk (`docs/.working/council/COUNCIL-NNN-<slug>/debater-k-round-0k.md`) and remain completely silent in chat.
- **Council High-Information Subject Briefing:** Fixed omission where Main Agent launched council with an empty subagent ID table. Mandated that the Main Agent must state the **Locked Question**, the **Underlying Tension & Trade-offs**, and the **Target Invariant** in chat before spawning.
- **Law 7 Atomic ADR Gate:** Added an unskippable gate preventing AI agents from taking "memlog-only" shortcuts. If an architectural or security decision is made, the `docs/adr/ADR-NNN-<slug>.md` file must be written and committed in the exact same turn before advancing to the next stage.

---

## [v0.1.3] — 2026-10-16
### Added
- **Anti-Slop UI & UX Codex (`skills/cgspec-ux/references/anti-slop-codex.md`):** Formulated strict 10 Negative Constraints (banning purple gradients, unstyled Inter/Arial, 3-column circle-icon boxes, centered fluffy cards, bubbly radii) and 8 Positive Craft Standards (1px hairlines, tonal surface elevation, monospaced metadata, `<kbd>` shortcuts, 7-state UI lifecycle).
- **Universal Anti-Slop Master Prompt:** Portable prompt block compatible with Claude, Cursor, v0.dev, ChatGPT, and Antigravity.
- **Prototype Staging Lab Arena (`docs/.working/prototypes/staging/`):** Interactive browser testbed with responsive viewport toggles (1440px / 1024px / 375px), live 10-point Anti-Slop Scorecard, and side-by-side comparison.

---

## [v0.1.2] — 2026-10-16
### Added
- **Law 9: Real 4-Subagent Council Architecture:** Mandated that the Main Agent stays with the human and spawns 4 background subagents (1 dedicated neutral Supervisor/Host + 3 Debaters). Prohibited single-agent simulation.
- **Prototype Versioning Invariant:** Mandated immutable milestone baselines (`prototype-v0.1.html`), ADR-specific exploratory mockups (`prototype-ADR-NNN.html`), and `prototype.html` as the canonical pointer.

---

## [v0.1.1] — 2026-10-16
### Added
- **Law 7: Architectural Choices Produce ADRs (`docs/adr/`):** Every cross-cutting choice must create an ADR registered in `docs/00-INDEX.md`. Pre-flight ADR check mandated.
- **Law 8: Deterministic Sprouting with Numeric Preservation:** Sprouting from single files to directories only occurs when `wc -l > 500` or in `v0.2+` multi-squad, retaining two-digit numeric prefixes (`01-PRD/`, `02-NOUNS-AND-FLOWS/`).

---

## [v0.1.0] — 2026-10-16
### Added
- Initial release of CGSpec methodology: 5-spine architecture (`01-PRD` .. `05-EXPERIENCE`), `docs/.memlog.md` with CLI tool, and skill suite (`cgspec-init`, `cgspec-forge`, `cgspec-council`, `cgspec-slice`, `cgspec-pivot`, `cgspec-ux`).
