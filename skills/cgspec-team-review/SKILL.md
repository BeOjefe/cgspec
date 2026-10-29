---
name: cgspec-team-review
description: Run a full independent specialist and adversarial review on any work when requested, or for a T3 change; return one evidence-based verdict.
---

# Review with a team

Read only what the current step needs, once per session: the [agent contract](../../engine/CONTRACT.md), [method section 7](../../docs/METHOD.md) (that section only), the named revision/artifacts and frozen criteria. This workflow is on demand at any tier and automatic at T3. The main agent coordinates the user's goal and ledger but does not build or judge inside the run. The inspector owns `docs/_cgspec/05-runs/<run-id>/run.json`, bounded units, owners, allowed paths and criteria hashes. Freeze criteria before builders receive work.

Use only specialists relevant to this task. A builder owns one unit and cannot edit its criteria. A reviewer gets the artifact, frozen criteria and checks, without the builder's self-assessment; use a different model when available and label a same-model review. A UX regression auditor re-runs locked baselines but cannot approve a new baseline. Keep helper concurrency within the declared tier cap. If the host lacks nested helpers, the inspector writes a queue and the main agent only dispatches it; state that arrangement.

Run deterministic source and rendered checks first, then independent judgment. Specialists may propose a new check, but it becomes a gate only after the section 8 registration path and the user's approval. Limit each unit to three review rounds; after two repeats change approach, and at the cap report BLOCKED with defects. Return one integrated report: revision, criteria hash, exact checks and results, defects with evidence, capabilities unavailable, and PASS/FAIL/PARTIAL/BLOCKED. Never claim zero defects outside the checked scope.
