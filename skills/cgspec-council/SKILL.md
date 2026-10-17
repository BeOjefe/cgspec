---
name: cgspec-council
description: Stage 3 Supervised 3-Agent Peer Debate Council. Use when resolving contested architectural, security, data-model, or UX trade-offs through multi-round adversarial debate and drafting ADR-NNN.md records.
---

# cgspec-council

## 1. Contract (Inputs -> Outputs)
- **Stage:** `3. Architecture & Trade-Off Debates` (Inherits all global laws from [`AGENTS.md`](../../AGENTS.md)).
- **Requires:** One locked architectural, security, or protocol question with genuine trade-offs.
- **Produces:** Debate logs (`docs/.cgspec/council/COUNCIL-NNN-<slug>/round-0k.md`, `summary.md`) and a formal Decision Record (`docs/adr/ADR-NNN-<slug>.md`).

---

## 2. Stage-Specific Rules
1. **Main Agent Spawns ONLY the Supervisor (`Law 9`):**
   - The Main Agent stays in the primary chat and calls `invoke_subagent` for **EXACTLY ONE** subagent: `Role: "Council Supervisor & Inspector"` (`TypeName: "self"`, `Workspace: "inherit"`).
   - **Never** include debaters in the Main Agent's `Subagents` array (direct child subagent completions leak into the user's primary chat window).
2. **3 Orthogonal Lenses Inside Background Workspace:**
   - The Supervisor spawns (or executes on disk if nested spawning is restricted) 3 orthogonal perspectives inside `docs/.cgspec/council/COUNCIL-NNN-<slug>/`:
     - **Debater 1 (Systems & Modularity):** Ports & Adapters, contract boundaries, routing (`debater-1-round-0k.md`).
     - **Debater 2 (Adversarial Security & Edge Cases):** Isolation, race conditions, permission bypasses, failure modes (`debater-2-round-0k.md`).
     - **Debater 3 (Pragmatic DX & Ship Speed):** Minimal complexity, developer ergonomics, delivery velocity (`debater-3-round-0k.md`).
3. **3-Line Round Relay:** After each round `k`, the Supervisor writes `round-0k.md` and sends a single 3-line message to the Main Agent:
   `Council Status [Round k/N]: Clash: <summary> | Concession: <summary> | Consensus Shift: <summary>`

---

## 3. Workflow
1. **Initialize Topic & Brief User:**
   - Write `docs/.cgspec/council/COUNCIL-NNN-<slug>/00-topic.md` (Locked Question, Stakes, Target Invariant).
   - Post a concise Markdown brief in chat (Locked Question, Core Tension, Target `ADR-NNN`).
2. **Launch Supervisor Subagent:**
   - Invoke `Council Supervisor & Inspector` to run $N$ rounds (default $N=3$), write `round-0k.md` and `summary.md`, and draft `docs/adr/ADR-NNN-<slug>.md` with `Status: Proposed`.
3. **Human Validation & Atomic Lock:**
   - Terminate the supervisor subagent (`manage_subagents`), present `summary.md` to the user, and upon user approval: set `Status: Accepted` in `ADR-NNN`, register in `docs/00-INDEX.md`, update affected spines, and log to `docs/.memlog.md`.

---

## 4. Exit Gate
Run `python3 docs/.cgspec/scripts/doctor.py --repo . --strict-emojis` to verify bidirectional `ADR-NNN` parity between `docs/adr/` and `docs/00-INDEX.md`.
