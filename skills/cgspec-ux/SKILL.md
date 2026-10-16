---
name: cgspec-ux
description: Dual-Spine UX & Design Architect. Generates docs/.working/ explorations (Excalidraw wireframes, HTML mocks), locks 04-DESIGN.md + 05-EXPERIENCE.md, and verifies UI in a live browser.
---

# cgspec-ux

## Execution Steps

1. **Silent Noun & Permission Check:**
   - Silently read `{project-root}/docs/02-NOUNS-AND-FLOWS.md`. Do not narrate `cgspec-ux` mechanics in chat—speak naturally about the UI and user experience.
   - Never use fictional persona names ("Sam", "Maya", "Mary"); use explicit **Functional Actors** (`Organization Owner`, `Project Lead`, `Developer / Vault Owner`, `Security Auditor`, `AI Agent Session`).

2. **Visual Workbench & Versioned Prototypes (`{project-root}/docs/.working/prototypes/`):**
   - **Anti-Slop Craft Mandate (Strict Negative & Positive Invariants):**
     - Review `{skill-dir}/references/anti-slop-codex.md`.
     - Zero AI Slop: No purple/indigo gradients, no unstyled Inter/Arial, no 3-column circle-icon boxes, no centered fluffy cards, no emojis as UI icons, no disembodied drop shadows.
     - Enforce 1px hairline borders (`border-white/10`), tonal elevation (`#09090b` -> `#121316` -> `#18191e`), `font-mono` for IDs/metrics, `tabular-nums`, `<kbd>` hotkeys, and full 7-state UI coverage.
   - **Prototype Versioning Invariant (Never Overwrite Baselines in Place):**
     - When building or evolving interactive UI mocks, store versioned files:
       - `{project-root}/docs/.working/prototypes/prototype-v0.1.html` (Locked milestone baseline).
       - `{project-root}/docs/.working/prototypes/prototype-ADR-NNN-<slug>.html` (ADR-specific visual experiments).
       - `{project-root}/docs/.working/prototypes/prototype-v0.2-draft.html` (Next milestone exploration).
       - `{project-root}/docs/.working/prototypes/staging/` (Staging/test lab for prompt evaluation, side-by-side comparison, and archetype sandboxing).
       - `prototype.html` acts as the active canonical pointer/symlink to the current milestone baseline.
   - Explorations also include:
     - `wireframes.excalidraw` (spatial zones & navigation flows).
     - `design-tokens.html` (semantic color palette, dark/light contrast, typography).

3. **Interactive 7-State Switcher Invariant:**
   - Every prototype HTML must include an interactive state switcher pill bar allowing the user to toggle views instantly: `Populated` | `Loading Skeleton` | `Empty State` | `Error State` | `Denied 403`.

4. **Silent Lock & Spine Update:**
   - When the user approves a design choice (via `ask_question`), silently log:
     ```bash
     uv run {skill-dir}/scripts/memlog.py add {project-root}/docs/.memlog.md \
       --tags "lock,ux" \
       --summary "<locked UX/design decision>"
     ```
   - Silently update `docs/04-DESIGN.md` (Google Labs `design.md` tokens, typography, layout rhythm, components) and `docs/05-EXPERIENCE.md` (Functional Actors, `v0.1` screen table covering all 7 states: `loading|empty|error|offline|partial|populated|denied`, WCAG 2.2 AA).

5. **Browser Visual Verification Gate:**
   - Render the HTML mockup or app route in a headless browser, capture desktop/compact screenshots, verify zero console or layout errors, and present visual proof.
