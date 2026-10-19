---
name: cgspec-forge
description: Turn a new product idea or feature request into researched intent, actors, scope, and an object model before design or build.
---

# Forge product intent

Read only what the current step needs, once per session: the [agent contract](../../engine/CONTRACT.md) and relevant existing spines. Determine the goal type: money, learning, personal, or client. For a money goal, research who pays, competing options, price, demand evidence and risks in `docs/_cgspec/02-research/RES-NNN-<slug>.md`, with source links and dated facts. State uncertainty; do not invent market validation.

Write `docs/spines/01-INTENT.md` with the goal, actors, real tasks, anti-goals, v0.1 boundary and parked ideas. Write `02-OOUX.md` with nouns, attributes, relations, hierarchy, permissions and important states. Trace each actor task to its nouns; check that none are orphaned. In a larger project, update only the relevant spine parts and links rather than rewriting all of them.

Show the user a concise, concrete interpretation and only the decisions that change product direction. Apply clear corrections directly. Log significant delegated choices and their reversibility through `memlog.py`. The user should not need to know CGSpec stages to express an idea.
