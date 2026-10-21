---
name: cgspec-ui-ux
description: Design or revise a product experience from real references through task flows, grey behavior prototypes, and the real frontend; handles responsive and mobile evidence explicitly.
---

# Design the experience

Read only what the current step needs, once per session: the [agent contract](../../engine/CONTRACT.md) and [method section 6](../../docs/METHOD-v0.2.md) (that section only). Start from the user's goal and the locked layers in `docs/spines/03-EXPERIENCE.md`. Advance only the layer affected; layers 0-4 are disposable grey work, 5b-7 are the real frontend. A tweak inside locked zones and tokens is applied directly; a changed flow, zone, token or register reopens only the dependent layers, and you run `impact.py` and show the map first.

## Start from the problem, not the look

Before you draw, check that `docs/spines/01-INTENT.md` says three things: who it is for, what job they are trying to get done, and how we will know it works. If any is missing, add it there. If the user cannot answer, offer your concrete reading of the problem and let them correct it. Do not ask for a blank brief.

Then classify the request, because each kind keeps something different:

| Kind | Changes | Must stay the same |
| --- | --- | --- |
| behavior | rules, states, permissions, flows | locked look; design these with the object model first (below) |
| layout | placement, grouping, order on a screen | every action, field, URL and step order for every role (list them first, then check them after) |
| appearance | type, colour, density, imagery | layout and behavior |
| content | words, labels, data shown | layout, behavior and stored data |
| motion | animation of existing behavior | behavior |

A request worded as visual can still be a behavior change (a new status, a new permission). Classify it by its effect, not its wording. Behavior work such as approvals, permissions and audit trails is designed from the back: states, who may do what, what is recorded. Then come the screens.

## Show the artifact that answers the open question

Pick the artifact by the question the user must answer now, not by a fixed sequence:

| Open question | Artifact |
| --- | --- |
| How does someone move through the product? | journey across screens |
| What happens under each condition? | state diagram (Mermaid) with a permission table |
| Where do things go on one screen? | grey wireframe |
| Which direction feels right? | side-by-side comparison of real pages, with your recommendation marked |
| Does it actually work? | clickable prototype with named states (see behavior coverage) |

Tell the user in one line: the current question, what you will show next, and the one decision you need from them. Explain the overall path once, in plain words, only when a new product starts. Pause for real choices: direction, scope, business rules, taste. Continue authorized craft work and checks without asking. Locking a layer still needs the user's recorded approval. Connected screens that serve one task are reviewed together as a journey, not approved one by one. If they want to go back, go back without arguing.

## Keep screens from rewriting the data

For each screen, write a data inventory next to its wireframe: what it reads, what it writes, and which noun in `docs/spines/02-OOUX.md` each item comes from. A field the screen needs but the model lacks goes to the object model as a data request. It does not become a migration on the spot. Keep these four apart:

- **Domain:** the lasting nouns, their states and rules.
- **Storage:** the tables and columns.
- **API:** the response shape.
- **Screen state:** open dialogs, drafts, selection, filters.

They often differ, so mock data is not a schema. Facts that must not change later, such as an issued total or a snapshot of an address, are stored. Display-only values, such as "due in 3 days", are calculated. Anything you filter, enforce or report on gets a real field, not loose JSON.

## Record decisions so nothing is lost

As you go, record each design decision with `memlog.py`:

- **The user's choices**, in their words.
- **Your own defaults**, with status `Delegated`.
- **Questions only the user can answer**, tagged `open-question`.

Put the next action in the checkpoint. A fresh session must be able to resume from these records without the user pasting the brief again.

## Push back on design shortcuts

Apply the contract's push-back rule to these design shortcuts:

- Asking for high fidelity before the task and flow are agreed.
- Approving a prototype without trying the main journey.
- Reacting only to colour when the problem is the workflow.
- Asking for a database change because a screen moved.

Name the cost and the smallest fix once, then follow the user's decision.

## What to do at each layer, and what to load

Prototype files other than ordinary Markdown need the active change scope. Before a layer lock, include `docs/prototypes/_snapshots/<screen>-v*.html` in the approved slice scope as well as that screen's sources and journeys; if missing, amend the scope through the existing approval path before cutting the snapshot. Use the tier appropriate to the total change size. The lock approval and frozen hash do not replace scope approval. Journey JSON is test material and does not require another test of itself.

| Layer | Do | Load |
| --- | --- | --- |
| 0 References | Start from the user's [personal inspiration library](references/inspiration-library.md) when it exists, then find two to four contrasting **real** references, with links and screenshots in `docs/prototypes/_vision/`, actually displayed per the [visual-choice guide](references/visual-choices.md); measure those the user likes. Search with available web tools and project links. If original images or video matter, align the user-visible IMAGE-WORD card before generation. If access fails, record the gap, invite optional links, and continue independent grey work without inventing references or locking reference-derived choices. | [inspiration library](references/inspiration-library.md), [reference-extraction](references/reference-extraction.md); load [IMAGE-WORD and motion](references/image-word-and-motion.md) only when media matters; [RES-001](../../docs/_cgspec/02-research/RES-001-ui-design-systems-and-surface-profiles-benchmark.md), [RES-004](../../docs/_cgspec/02-research/RES-004-vibecoded-design-tells-and-high-craft-ergonomics.md) |
| 0-3 Compare directions | Only when a real direction choice is open: build 2-3 quick variations of the key screen that differ in mechanism (structure, density, navigation, type, mood), not just colour or button position. Make them real HTML pages in `docs/prototypes/_vision/variations/`, open them in the browser and screenshot them side by side. Give each one line on what it bets on, and mark your recommendation. The user reacts ("this one", "mix 2 and 3"); iterate on the winner and delete the rest. Use more only for a stated reason. For a vague request, first offer your reading of the problem or a cheap labelled sketch. | [craft](references/craft.md) |
| 0-1 Register (5a) | Write the one-paragraph register (density, type, stance, mood, accent, signature element, avoid, deliberate choices), show it, lock it with the user's approval. | [register](references/register.md) |
| 1 Tasks | Actors and tasks in the spine, each with frequency and device. | — |
| 2 Screens and flows | One row per screen with its main need (the focal point). | [craft](references/craft.md) section 1 |
| 3 Wireframes | Grey shell, zone IDs, real-looking data in realistic amounts, density from the register. | [craft](references/craft.md) sections 1-5, 8 |
| 4 Behavior | Clickable grey prototype with the [tweaks panel](references/tweaks-panel.js) included, so the user can try type, density, accent, radius and light/dark live and paste the values back, all states, `data-testid` on every control; journeys in `docs/prototypes/<screen>/journeys/`; run `visual_audit.py` and `journey.py`. Cut a snapshot with `bundle_prototype.py` when the user locks the layer. | [behavior coverage](references/behavior-coverage.md), [RES-002](../../docs/_cgspec/02-research/RES-002-anti-slop-constrained-ui-and-deterministic-gates.md) |
| 5b Token sheet | Derive every token from the register and measured references; each value says where it comes from. Set `design_tokens` in `docs/_cgspec/project.json` to the token sheet's project-relative path, so visual audit checks the intended sheet. | [tokens template](references/tokens.dtcg.json), [reference-extraction](references/reference-extraction.md), [craft](references/craft.md) sections 3-7 |
| 6 High fidelity | Real frontend, one key screen first, the tweaks panel kept until the user locks the look (then removed), components from recipes; review screenshots against the rubric with a different reviewer before rolling out and before locking. | [craft](references/craft.md), [components](references/components.md), [critique rubric](references/critique-rubric.md) |
| 7 Motion | Behaviors from layer 4 animated with motion tokens only. If media and text carry a shared story, lay out a timed storyboard against the clip before implementing it. | [IMAGE-WORD and motion](references/image-word-and-motion.md) when media matters |

## Rules

- The AI leads: bring references and options; do not ask the user to research or write the brief.
- Apply the [visual-choice guide](references/visual-choices.md) whenever images help a brainstorming or design choice. Display real images beside the labelled options before asking the user to pick; links and screenshots saved only on disk do not count. Load this guide even when the work has not reached layer 0.
- References first, from anywhere public. For a new product or visual direction, show two to four real reference images before your own design and let the user react. Reuse supplied/chosen references; do not reopen this step for a tweak within locked choices. The image does not have to come from inside the product: when a product needs a login, use its public marketing pages, docs, app-store screenshots, review articles, Dribbble or Behance shots, or image search. Save each image with its source URL. Build your own variations only after the user has reacted to references.
- Go at the user's pace on real choices. Do not jump to high fidelity before behavior is agreed, and do not wait for approval of routine craft steps.
- "Grey" means no brand colour yet, not ugly. Early prototypes and variations still need clean type, spacing and alignment (see craft.md), or the user cannot judge the experience behind them.
- Browse quietly. Take screenshots and run checks with a headless browser (the project's Playwright, `visual_audit.py`, `journey.py`). Open a visible browser window only when the user asks to see something live, and do not open a new window for every step.
- Clean up after each step: stop servers you started, close browser windows and tabs you opened, delete throwaway files in `.cgspec-scratch/`. Leave only the intended changes.
- Show real things, not pictures of things. A design proposal or variation is always a real page: build it, open it in the browser tool, take the screenshot and show that, with the command to open it. A reference is a real site you visited and captured. Never present a generated image as a design option or as a reference, and do not describe a screen at length instead of showing it.
- Use generated image or video assets when original media improves the product, especially on landing pages and immersive spaces. First show real visual references, align the IMAGE-WORD card with the user, then show the exact generation prompt. Pass the approved prompt unchanged to a generator the session can actually reach; use connected Antigravity from any lead model when callable, otherwise a direct image/video tool such as Codex image generation. Do not paraphrase it through an intermediate model. Integrate generated assets in the real page, record their provenance and rights, and check responsive crops and motion. Follow [IMAGE-WORD and motion](references/image-word-and-motion.md). A paid service or new provider is suggested with its cost and data/license implications and requires the user's yes before use.
- Reference sources besides live products: Dribbble, Pinterest, Mobbin and similar galleries for references; 21st.dev and Taste Skill for component and layout ideas. Use them as references only; a component copied without mapping it to the project's tokens makes the design drift (section 6b), and its license must be checked before any code is reused.
- Optional polish check: on a web project, `npx impeccable detect <dir or http://localhost:PORT>` (Apache-2.0, free; run `npx impeccable telemetry off` first) lists generic-look patterns. Treat findings as warnings inside the locked register, like `visual_audit.py`; do not install its skills alongside this one without the user's yes, because two design instruction sets pull in different directions.
- An existing design system is an option only when its installable typed components, machine-readable tokens and permissive license are verified (section 6b). Otherwise derive project tokens with provenance.
- Generic-look warnings are defaults to challenge, not taste decisions. A flagged choice the user wants is recorded under "Deliberate choices" in the register; never silence a warning the user has not seen.
- Evidence is distinct by kind: a screenshot is not interaction; browser simulation is not a device. Missing browser or tools mean PARTIAL or BLOCKED, never PASS. Record revision and evidence before locking or presenting completion.
- Never claim a screen is finished without the screenshots and the rubric result; show the screenshots to the user.
