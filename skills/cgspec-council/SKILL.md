---
name: cgspec-council
description: Research and resolve a consequential architecture, security, data, hosting, or product trade-off with a logged council and a proposed decision.
---

# Decide a consequential choice

Read only what the current step needs, once per session: the [agent contract](../../engine/CONTRACT.md), affected spines, current ADRs and [method sections 7 and 7b](../../docs/METHOD.md) (that section only). Write one bounded question and decision criteria before proposals. Research authoritative sources; run a feasibility spike in `.cgspec-scratch/` when latency, cost, memory or failure behavior decides the choice.

For a consequential T3 choice, log a council in `docs/_cgspec/03-councils/COUNCIL-NNN-<slug>/`: `00-brief`, round files per lens, and `99-outcome`. Compare simplicity/cost, security/reliability and scale/maintenance. Use distinct models when available and label a single-model council PARTIAL. The supervisor synthesizes; debaters do not approve. Keep the council at its spec cap of four agents. For an ordinary reversible choice, a scoped ADR and one independent reviewer suffice when the tier allows it.

After a T3 council proposes its ADR, have an independent reviewer who did not write the proposal or supervise the council challenge it using the strongest suitable model available in the host. Give the reviewer the source evidence, assumptions, threat model and reversibility criteria, not just the council's conclusion. If the model or evidence is unavailable, mark this final challenge PARTIAL. The reviewer reports; the user approves. Check the live model catalogue before recommending a model, and do not claim a model is stronger or cheaper without reliable evidence.

The outcome is a `Proposed` ADR in `docs/adrs/`, with options, sources, measured trade-offs, reversibility and fitness checks. Explain the recommended option in plain terms and seek the user's decision where the spec requires it. Record explicit approval through a supported path; never infer it from an agent verdict. Reopen an ADR when its constraint or measured budget changes.
