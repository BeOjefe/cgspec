---
name: cgspec-forge
description: Turn a new product idea or feature request into researched intent, actors, scope, and an object model before design or build.
---

# Forge product intent

Read only what the current step needs, once per session: the [agent contract](../../engine/CONTRACT.md) and relevant existing spines. Determine the goal type: money, learning, personal, or client. For a money goal, research who pays, competing options, price, demand evidence and risks in `docs/_cgspec/02-research/RES-NNN-<slug>.md`, with source links and dated facts. State uncertainty; do not invent market validation.

Write `docs/spines/01-INTENT.md` with the goal, actors, real tasks, anti-goals, v0.1 boundary and parked ideas. Write `02-OOUX.md` with nouns, attributes, relations, hierarchy, permissions and important states. Trace each actor task to its nouns; check that none are orphaned. In a larger project, update only the relevant spine parts and links rather than rewriting all of them.

Open with the orientation from the contract: in at most five short lines, what we will do together, how this first part works, and what you need from them. Give a short progress update only when something materially changes or the user asks; do not prefix every reply. When this part is confirmed, move into design without repeating the introduction.

When an idea or option is easier to choose visually, use the [visual-choice guide](../cgspec-ui-ux/references/visual-choices.md) now: show real images beside short labelled descriptions before asking for a choice. Do not wait for the design stage or make the user search for references. Keep purely technical or verbal choices concise without decorative imagery.

If the user says "just build it" before there is a minimum definition, push back once as the contract says. A minimum definition means three things: who it is for, the one job it must do, and how we will know it works. Write your own draft of those three lines and show it, so the fix takes minutes. A definition you wrote is not approval: build small work on it unless it is a costly guess, but anything that needs a slice waits for the user to approve the definition.

Show the user a concise, concrete interpretation and only the decisions that change product direction. Apply clear corrections directly. Log significant delegated choices and their reversibility through `memlog.py`. The user should not need to know CGSpec stages to express an idea.
