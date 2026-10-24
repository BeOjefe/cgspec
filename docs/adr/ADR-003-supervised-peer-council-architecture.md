# ADR-003: Supervised Peer-to-Peer Council (`cgspec-council`) Architecture
Created: unknown · Last edited: 2026-10-20T17:54:17Z

> Historical v0.1 record; not current v0.2 rules or approval. See [the ADR index](README.md) and [the current method](../METHOD-v0.2.md).

- **Status:** Accepted
- **Date:** 2026-10-16

## Context
In earlier `/open-debate` runs:
1. The Main Agent acted as the moderator, blocking the user interface.
2. Subagents argued about completely different topics (e.g., UX vs. database engine) instead of debating the **same locked question** from different lenses.
3. Unmoderated multi-agent chat without an independent supervisor suffers from sycophancy ("groupthink") or context bloat (*Cemri et al., 2025, arXiv:2503.13657*).

## Decision
Implement **`cgspec-council`** (`skills/cgspec-council/SKILL.md`):
1. The Main Agent spawns a dedicated **Council Host & Inspector Supervisor**.
2. The Supervisor spawns 3 peer debaters locked to the **exact same subject** from 3 orthogonal lenses (Systems/Modularity, Adversarial Security/Failure Modes, Pragmatic DX/Cost).
3. At the end of each round (`1..N`), the Supervisor sends a **3-line Live Inspector Report** to the Main Agent so the user sees live progress.
4. After Round `N`, the Supervisor terminates the debaters, archives raw transcripts in `docs/archive/debates/ADR-NNN/`, logs the lock to `docs/.memlog.md`, and writes a single `docs/adr/ADR-NNN-<slug>.md`.

## Consequences
- `docs/03-ARCHITECTURE.md` (v0.1 spine; now `docs/spines/04-ARCHITECTURE.md`)
