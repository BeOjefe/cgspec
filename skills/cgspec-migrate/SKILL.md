---
name: cgspec-migrate
description: Plan and execute a large refactor, rename, repo split, data move, or other structural change while preserving behavior and a recovery route.
---

# Migrate safely

Read only what the current step needs, once per session: the [agent contract](../../engine/CONTRACT.md), [method section 10](../../docs/METHOD-v0.2.md) (that section only), relevant ADRs and the current repo map. Declare T3 when the change is structural; identify affected and unreachable repos, consumers, history, CI paths, deployment order and owners. Obtain a baseline of behavior and tests at a named revision, then define intended changes and preserved behavior before edits.

Write a migration contract in a scoped slice and ADR: old/new contracts, data transformation and validation, side-by-side period, checkpoints, performance/security acceptance, observation period, and a recovery route proven before irreversible steps. A repo rename must cover aliases in the registry, imports, remotes, CI and links. Use `impact.py` only when it exists; otherwise trace indexed dependencies explicitly and label coverage limits.

Execute in bounded steps with checks after each transition. Keep both states observable until cutover. Do not infer infrastructure access as authorization to deploy or delete. Require the user's decision for consequential or irreversible steps, then report revision, evidence, unresolved dependencies and recovery state. The `cgspec-pivot` alias directs to this workflow.
