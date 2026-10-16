---
name: cgspec-slice
description: Atomic Vertical Slice Builder. Generates a bounded slice contract from locked spines (01..05), enforces Ports & Adapters modularity, and runs tests + browser verification.
---

# cgspec-slice

## Execution Steps

1. **Pre-Flight Check & Compass:**
   - Verify that requirements, nouns, and UI screens are agreed upon.
   - Show the 1-line compass (`📍 Where we are: ...`). Never use raw slice codes without plain-English descriptions.

2. **Propose Concrete Next Actions (Never Vague Open-Ended Questions):**
   - **Never** ask a vague *"How would you like to proceed?"*.
   - Always present concrete, numbered options using `ask_question` (or clear numbered choices):
     - `Option 1 (Recommended): Launch browser preview of prototype.html`
     - `Option 2: Scaffold the next vertical slice (code & database)`
     - `Option 3: Adjust or add another feature in requirements first`

3. **Write Bounded Slice Spec (`{project-root}/docs/slices/SLICE-NNN-<slug>.md`):**
   - Target nouns & permissions (`read|invoke|propose_edit|write|share|admin`).
   - Exact files/modules in scope.
   - Test & 7-state UI verification criteria.

4. **Implement & Verify:**
   - Enforce Ports & Adapters isolation (`uv` for Python, `bun`/`pnpm` for TS).
   - Run unit/integration tests + linter/typecheck.
   - For UI work: open in a headless browser, inspect screenshots, verify zero console errors.
   - Log completion:
     ```bash
     uv run {skill-dir}/scripts/memlog.py add {project-root}/docs/.memlog.md \
       --tags "lock,slice" \
       --summary "Completed SLICE-NNN"
     ```
   - Update `{project-root}/docs/00-INDEX.md`.
