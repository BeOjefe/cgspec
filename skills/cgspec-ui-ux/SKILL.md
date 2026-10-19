---
name: cgspec-ui-ux
description: Design or revise a product experience from real references through task flows, grey behavior prototypes, and the real frontend; handles responsive and mobile evidence explicitly.
---

# Design the experience

Read the [agent contract](../../engine/CONTRACT.md) and [method section 6](../../docs/METHOD-v0.2.md). Start from the user's goal and the locked layers in `docs/spines/03-EXPERIENCE.md`. Advance only the layer affected; layers 0-4 are disposable grey work, 5b-7 are the real frontend. A tweak inside locked zones and tokens is applied directly; a changed flow, zone, token or register reopens only the dependent layers, and you run `impact.py` and show the map first.

## What to do at each layer, and what to load

| Layer | Do | Load |
| --- | --- | --- |
| 0 References | Start from the user's [personal inspiration library](references/inspiration-library.md) when it exists, then find up to six contrasting **real** references, with links and screenshots in `docs/prototypes/_vision/`; measure those the user likes. Search with available web tools and project links. If access fails, record the gap, invite optional links, and continue independent grey work without inventing references or locking reference-derived choices. | [inspiration library](references/inspiration-library.md), [reference-extraction](references/reference-extraction.md); [RES-001](../../docs/_cgspec/02-research/RES-001-ui-design-systems-and-surface-profiles-benchmark.md), [RES-004](../../docs/_cgspec/02-research/RES-004-vibecoded-design-tells-and-high-craft-ergonomics.md) |
| 0-3 Cast a wide net | Before narrowing, build 3-5 quick, deliberately different variations of the key screen (different density, type, layout and mood), as real HTML pages in `docs/prototypes/_vision/variations/`, opened in the browser and screenshotted side by side, each with one line on what it bets on. The user reacts ("this one", "mix 2 and 4"); iterate on the winner and delete the rest. Repeat with fewer, closer variations when a direction is unclear. Do this even when the user is vague; it replaces guessing. | [craft](references/craft.md) |
| 0-1 Register (5a) | Write the one-paragraph register (density, type, stance, mood, accent, signature element, avoid, deliberate choices), show it, lock it with the user's approval. | [register](references/register.md) |
| 1 Tasks | Actors and tasks in the spine, each with frequency and device. | — |
| 2 Screens and flows | One row per screen with its main need (the focal point). | [craft](references/craft.md) section 1 |
| 3 Wireframes | Grey shell, zone IDs, real-looking data in realistic amounts, density from the register. | [craft](references/craft.md) sections 1-5, 8 |
| 4 Behavior | Clickable grey prototype with the [tweaks panel](references/tweaks-panel.js) included, so the user can try type, density, accent, radius and light/dark live and paste the values back, all states, `data-testid` on every control; journeys in `docs/prototypes/<screen>/journeys/`; run `visual_audit.py` and `journey.py`. Cut a snapshot with `bundle_prototype.py` when the user locks the layer. | [behavior coverage](references/behavior-coverage.md), [RES-002](../../docs/_cgspec/02-research/RES-002-anti-slop-constrained-ui-and-deterministic-gates.md) |
| 5b Token sheet | Derive every token from the register and measured references; each value says where it comes from. Set `design_tokens` in `docs/_cgspec/project.json` to the token sheet's project-relative path, so visual audit checks the intended sheet. | [tokens template](references/tokens.dtcg.json), [reference-extraction](references/reference-extraction.md), [craft](references/craft.md) sections 3-7 |
| 6 High fidelity | Real frontend, one key screen first, the tweaks panel kept until the user locks the look (then removed), components from recipes; review screenshots against the rubric with a different reviewer before rolling out and before locking. | [craft](references/craft.md), [components](references/components.md), [critique rubric](references/critique-rubric.md) |
| 7 Motion | Behaviors from layer 4 animated with motion tokens only. | — |

## Rules

- The AI leads: bring references and options; do not ask the user to research or write the brief.
- References first, from anywhere public. Before showing any design of your own, show the user 4-6 real reference images and let them react. The image does not have to come from inside the product: when a product needs a login, use its public marketing pages, docs, app-store screenshots, review articles, Dribbble or Behance shots, or image search. Save each image with its source URL. Build your own variations only after the user has reacted to references.
- Go at the user's pace: one step, show it, wait for their reaction, then the next step. Never build several layers in one go.
- "Grey" means no brand colour yet, not ugly. Early prototypes and variations still need clean type, spacing and alignment (see craft.md), or the user cannot judge the experience behind them.
- Browse quietly. Take screenshots and run checks with a headless browser (the project's Playwright, `visual_audit.py`, `journey.py`). Open a visible browser window only when the user asks to see something live, and do not open a new window for every step.
- Clean up after each step: stop servers you started, close browser windows and tabs you opened, delete throwaway files in `.cgspec-scratch/`. Leave only the intended changes.
- Show real things, not pictures of things. A design proposal or variation is always a real page: build it, open it in the browser tool, take the screenshot and show that, with the command to open it. A reference is a real site you visited and captured. Never present a generated image as a design option or as a reference, and do not describe a screen at length instead of showing it.
- Generated images and video (when the host can make them, for example Antigravity) are only for content inside a design: a photo, an illustration, a placeholder. Say which assets were generated. Prefer free and built-in tools and permissively licensed assets. A paid service (for example Higgsfield) or a new design tool (for example Impeccable) is only mentioned as an option with its cost and license; never used without the user's explicit yes.
- Reference sources besides live products: Dribbble, Pinterest, Mobbin and similar galleries for references; 21st.dev and Taste Skill for component and layout ideas. Use them as references only; a component copied without mapping it to the project's tokens makes the design drift (section 6b), and its license must be checked before any code is reused.
- Optional polish check: on a web project, `npx impeccable detect <dir or http://localhost:PORT>` (Apache-2.0, free; run `npx impeccable telemetry off` first) lists generic-look patterns. Treat findings as warnings inside the locked register, like `visual_audit.py`; do not install its skills alongside this one without the user's yes, because two design instruction sets pull in different directions.
- An existing design system is an option only when its installable typed components, machine-readable tokens and permissive license are verified (section 6b). Otherwise derive project tokens with provenance.
- Generic-look warnings are defaults to challenge, not taste decisions. A flagged choice the user wants is recorded under "Deliberate choices" in the register; never silence a warning the user has not seen.
- Evidence is distinct by kind: a screenshot is not interaction; browser simulation is not a device. Missing browser or tools mean PARTIAL or BLOCKED, never PASS. Record revision and evidence before locking or presenting completion.
- Never claim a screen is finished without the screenshots and the rubric result; show the screenshots to the user.
