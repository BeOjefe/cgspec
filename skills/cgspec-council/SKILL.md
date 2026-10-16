---
name: cgspec-council
description: Supervised 3-Agent Peer Debate Council. Host/Inspector runs N rounds on one locked question across 3 orthogonal lenses, emits 3-line round reports, archives logs, and writes ADR-NNN.md.
---

# cgspec-council

## Execution Steps

1. **Lock Single Question:**
   - Formulate one exact technical or product decision question.

2. **Spawn Host/Inspector Supervisor & 3 Orthogonal Debaters:**
   - Spawn `Council Host` (or execute subagent orchestration) with 3 peers locked to the **same question**:
     - **Debater 1 (Systems & Modularity):** Boundaries, extensibility, Ports & Adapters.
     - **Debater 2 (Adversarial Security & Failure Modes):** Race conditions, permission bypasses, edge cases.
     - **Debater 3 (Pragmatic DX & Ship Speed):** Simplicity, footprint, `v0.1` velocity.

3. **Execute `N` Rounds (Default `N=3`) with Live Inspector Summaries:**
   - Each round `k`, debaters challenge peers directly and state: (a) concessions, (b) evidence-backed refutations, (c) updated position.
   - After each round `k`, output a 3-line Inspector summary:
     `🔔 [Council Round k/N] Clash: ... | Concession: ... | Consensus shift: ...`

4. **Finalize & Clean Up:**
   - Terminate debater subagents and move raw transcripts to `{project-root}/docs/archive/debates/ADR-NNN-<slug>/`.
   - Log lock:
     ```bash
     uv run {skill-dir}/scripts/memlog.py add {project-root}/docs/.memlog.md \
       --tags "lock,council,adr" \
       --summary "ADR-NNN: <decision>"
     ```
   - Write `{project-root}/docs/adr/ADR-NNN-<slug>.md`, re-derive affected spine (`01`..`05`), and update `docs/00-INDEX.md`.
