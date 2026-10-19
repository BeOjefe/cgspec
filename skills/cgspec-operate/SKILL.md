---
name: cgspec-operate
description: Run release, observation, incident response, drift repair, runbooks, or retirement for an installed CGSpec project.
---

# Operate the project

Read the [agent contract](../../engine/CONTRACT.md), `docs/spines/05-DELIVERY.md`, active slices and [method section 10](../../docs/METHOD-v0.2.md). For a release, verify the CI governance check and profile checks at the exact revision, write release notes and rollback or forward-fix route, then seek the user's release approval before production. A preview is evidence only for its environment. Confirm smoke tests and observation with actual results.

For an incident, establish impact and current state first, contain within authorized access, keep a timestamped evidence trail, then record the incident as a project constraint and follow-up slice. For drift, compare deployed behavior, code and docs; show disagreements and their sources before deciding which truth to change. Keep deploy, restore and known-failure runbooks in the delivery spine or its folder.

Check real host capabilities before promising monitoring or a scheduled follow-up. Record an actual scheduler ID if created; otherwise leave a checkpoint and a resumption instruction. At known quota thresholds, follow the contract's bounded-work rule and the method's 25/15/5 and weekly 10 percent thresholds using actual telemetry only.
