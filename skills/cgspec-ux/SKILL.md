---
name: cgspec-ux
description: Dual-Spine UX & Design Architect. Generates docs/.working/ explorations (Excalidraw wireframes, HTML mocks), locks 04-DESIGN.md + 05-EXPERIENCE.md, and verifies UI in a live browser.
---

# cgspec-ux

## Execution Steps

1. **Silent Noun & Permission Check:**
   - Silently read `{project-root}/docs/02-NOUNS-AND-FLOWS.md`. Do not narrate `cgspec-ux` mechanics in chat—speak naturally about the UI and user experience.
   - Never use fictional persona names ("Sam", "Maya", "Mary"); use explicit **Functional Actors** (`Organization Owner`, `Project Lead`, `Developer / Vault Owner`, `Security Auditor`, `AI Agent Session`).

2. **Visual Workbench (`{project-root}/docs/.working/`):**
   - Generate exploration artifacts in `docs/.working/` before locking:
     - `wireframes.excalidraw` (spatial zones & flow)
     - `color-themes.html` (semantic tokens & contrast)
     - `design-directions.html` (interactive screen mockup)

3. **Silent Lock & Spine Update:**
   - When the user approves a design choice (via `ask_question`), silently log:
     ```bash
     uv run {skill-dir}/scripts/memlog.py add {project-root}/docs/.memlog.md \
       --tags "lock,ux" \
       --summary "<locked UX/design decision>"
     ```
   - Silently update `docs/04-DESIGN.md` (Google Labs `design.md` tokens, typography, layout rhythm, components) and `docs/05-EXPERIENCE.md` (Functional Actors, `v0.1` screen table covering all 7 states: `loading|empty|error|offline|partial|populated|denied`, WCAG 2.2 AA).

4. **Browser Visual Verification Gate:**
   - Render the HTML mockup or app route in a headless browser, capture desktop/compact screenshots, verify zero console or layout errors, and present visual proof.
