# RFC: Re-founding `cgspec-ux` — Evidence-Backed Task & Experience Engineering

> **Status:** Approved Architecture Draft  
> **Target:** `skills/cgspec-ux/`  
> **Philosophy:** Design is not a one-shot prompt, nor is it a set of negative bans. It is a repeatable, evidence-backed cycle: **Understand Task -> Explore Layouts -> Test Interactions -> Develop Visual Direction -> Verify Implemented Experience**. Irreversible locks are replaced with evidence-backed checkpoints that can be reopened when testing reveals a flaw.

---

## 1. Core Principles (Removing Speculative & Verbose Claims)

1. **Task Before Layout:** Domain nouns (`02-OOUX.md`) define what exists, not what the human is trying to accomplish. Understand the user's primary job before drawing screen boxes.
2. **Layout & Interaction Inform Each Other:** Approve an initial spatial hypothesis, not an irreversible lock. Discovering that a user must compare two items may require shifting from a drawer to a split view.
3. **References Ground Mechanisms, Not Just Colors:** Use external references (e.g. Obsidian, Notion, Bear, Linear) to inspect specific mechanisms (navigation tree, editor syntax collapse, backlink drawer) without borrowing brand styling. Never drop naked product names without explaining the tactile behavior.
4. **Test Rough Interactions Before Polishing:** A lightweight, unstyled prototype resolves whether the interaction feels right before hours are spent on typography and tokens.
5. **Component-Level & Coexisting States:** Replace the rigid 7-screen replacement model with coexisting states (e.g., a populated screen containing a failed widget while offline).
6. **Positive Design Requirements Over Negative Slop Bans:** Replace "no purple" with purposeful hierarchy, appropriate density, coherent typography, understandable feedback, and tactile keyboard ergonomics.
7. **No Exaggerated Promises:** Eliminate claims like *"prompt-based UI always fails"*, *"code is trivial"*, *"100% deterministic"*, or *"video analysis extracts exact CSS easing"*. Keep instructions direct, factual, and actionable.

---

## 2. The 15-Rule Operating Contract for `cgspec-ux`

1. Begin from the user's task, not a template or visual style.
2. Maintain an active screen, phase, and unresolved-question list.
3. Separate facts, preferences, assumptions, and approved decisions.
4. Ask small batches of consequential questions without overwhelming questionnaires.
5. Explain interactions in plain language before technical terminology.
6. Use references to analyze specific mechanisms; never use naked product names.
7. Explore alternatives only when they test meaningful differences.
8. Prototype uncertain interactions before polishing them.
9. Treat approval as provisional when new evidence contradicts it.
10. Apply accessibility throughout discovery, design, and verification.
11. Never claim to have inspected screenshots, files, videos, or browser behavior unless available tools actually performed that inspection.
12. If a required capability is unavailable, state the limitation and provide an executable test or manual verification procedure.
13. Do not scaffold production UI before the relevant experience is approved.
14. Do not add decorative features without a task, hierarchy, or identity rationale.
15. End each session by updating progress, decisions, and the next concrete action.

---

## 3. Skill & Project Structure

### Skill Architecture (`skills/cgspec-ux/`)
```text
skills/cgspec-ux/
├── SKILL.md                          # Orchestrator & Operating Contract
├── playbooks/
│   ├── 01-discovery.md               # Design brief & journey mapping
│   ├── 02-layout-and-interaction.md  # Spatial zoning & rough interaction contracts
│   ├── 03-visual-direction.md        # Typography, density & positive design tokens
│   ├── 04-prototyping-and-testing.md # Multi-variant HTML prototypes & state matrix
│   └── 05-implementation-review.md  # Production fidelity & deviation log
├── templates/
│   ├── design-brief.md
│   ├── screen-spec.md
│   ├── reference-analysis.md
│   ├── decision-record.md
│   └── usability-test.md
└── references/
    ├── quality-rubric.md
    ├── accessibility-checklist.md
    └── interaction-patterns.md
```

### Project Documentation Flow (`docs/`)
- `docs/03-EXPERIENCE.md`: Approved product experience baseline.
- `docs/design/brief.md`: Active task, primary user, and constraints.
- `docs/design/screens/`: Detailed screen specs.
- `docs/design/decisions/`: Why consequential design choices were made.
- `docs/.memlog.md`: Chronological notes, preferences, and session history.
- `.cgspec/prototypes/`: Versioned HTML prototypes (`prototype-v0.1.html`).
