---
name: cgspec-ui-ux
description: Design or revise a product experience from real references through task flows, grey behavior prototypes, and the real frontend; handles responsive and mobile evidence explicitly.
---

# Design the experience

Read the [agent contract](../../engine/CONTRACT.md) and [method section 6](../../docs/METHOD-v2.md). Start from the user's goal and the locked layers in `docs/spines/03-EXPERIENCE.md`. Advance only the layer affected; layers 0-4 are disposable grey work, 5b-7 are the real frontend. A tweak inside locked zones and tokens is applied directly; a changed flow, zone, token or register reopens only the dependent layers, and you run `impact.py` and show the map first.

## What to do at each layer, and what to load

| Layer | Do | Load |
| --- | --- | --- |
| 0 References | Find up to six contrasting **real** references, with links and screenshots in `docs/prototypes/_vision/`; measure those the user likes. Search with available web tools and project links. If access fails, record the gap, invite optional links, and continue independent grey work without inventing references or locking reference-derived choices. | [reference-extraction](references/reference-extraction.md); [RES-001](../../docs/_cgspec/02-research/RES-001-ui-design-systems-and-surface-profiles-benchmark.md), [RES-004](../../docs/_cgspec/02-research/RES-004-vibecoded-design-tells-and-high-craft-ergonomics.md) |
| 0-1 Register (5a) | Write the one-paragraph register (density, type, stance, mood, accent, signature element, avoid, deliberate choices), show it, lock it with the user's approval. | [register](references/register.md) |
| 1 Tasks | Actors and tasks in the spine, each with frequency and device. | — |
| 2 Screens and flows | One row per screen with its main need (the focal point). | [craft](references/craft.md) section 1 |
| 3 Wireframes | Grey shell, zone IDs, real-looking data in realistic amounts, density from the register. | [craft](references/craft.md) sections 1-5, 8 |
| 4 Behavior | Clickable grey prototype, all states, `data-testid` on every control; journeys in `docs/prototypes/<screen>/journeys/`; run `visual_audit.py` and `journey.py`. Cut a snapshot with `bundle_prototype.py` when the user locks the layer. | [behavior coverage](references/behavior-coverage.md), [RES-002](../../docs/_cgspec/02-research/RES-002-anti-slop-constrained-ui-and-deterministic-gates.md) |
| 5b Token sheet | Derive every token from the register and measured references; each value says where it comes from. Set `design_tokens` in `docs/_cgspec/project.json` to the token sheet's project-relative path, so visual audit checks the intended sheet. | [tokens template](references/tokens.dtcg.json), [reference-extraction](references/reference-extraction.md), [craft](references/craft.md) sections 3-7 |
| 6 High fidelity | Real frontend, one key screen first, components from recipes; review screenshots against the rubric with a different reviewer before rolling out and before locking. | [craft](references/craft.md), [components](references/components.md), [critique rubric](references/critique-rubric.md) |
| 7 Motion | Behaviors from layer 4 animated with motion tokens only. | — |

## Rules

- The AI leads: bring references and options; do not ask the user to research or write the brief.
- An existing design system is an option only when its installable typed components, machine-readable tokens and permissive license are verified (section 6b). Otherwise derive project tokens with provenance.
- Generic-look warnings are defaults to challenge, not taste decisions. A flagged choice the user wants is recorded under "Deliberate choices" in the register; never silence a warning the user has not seen.
- Evidence is distinct by kind: a screenshot is not interaction; browser simulation is not a device. Missing browser or tools mean PARTIAL or BLOCKED, never PASS. Record revision and evidence before locking or presenting completion.
- Never claim a screen is finished without the screenshots and the rubric result; show the screenshots to the user.
