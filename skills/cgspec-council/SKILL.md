---
name: cgspec-council
description: Supervised 3-Agent Peer Debate Council. Host/Inspector runs N rounds on one locked question across 3 orthogonal lenses, emits 3-line round reports, archives logs, and writes ADR-NNN.md.
---

# cgspec-council

## Execution Steps

1. **Lock Single Question & Initialize Working Directory:**
   - Formulate one exact technical, architectural, or design decision question.
   - Create the live debate directory:
     `{project-root}/docs/.working/council/ADR-NNN-<slug>/`
   - Write `{project-root}/docs/.working/council/ADR-NNN-<slug>/00-topic.md`:
     Record the question, motivation, relevant docs, and the 3 debater mandates.

2. **MANDATORY: Spawn 3 Real Subagents (Strict Prohibition on Simulation):**
   - **ZERO-SIMULATION MANDATE:** You are **STRICTLY FORBIDDEN** from roleplaying the debaters yourself, writing simulated debater dialog in a file, or pretending to be multiple personas in one conversation.
   - **MANDATORY TOOL CALL:** You **MUST** call `invoke_subagent` (or platform equivalent like `Agent`/`Task`) to launch 3 independent, concurrent subagent instances with distinct prompts:
     - **Debater 1 (Systems & Modularity):**
       - `TypeName`: `"research"` (or `"self"`)
       - `Role`: `"Debater 1 — Systems & Modularity"`
       - `Prompt`: `"You are Debater 1 on the CGSpec Architecture Council. Focus exclusively on clean boundaries, Ports & Adapters, loose coupling, and maintainability. Analyze this locked question: <QUESTION>. Read docs/adr/ and active docs, and output your initial 3-point position with concrete technical evidence."`
     - **Debater 2 (Adversarial Security & Failure Modes):**
       - `TypeName`: `"research"` (or `"self"`)
       - `Role`: `"Debater 2 — Security & Edge Cases"`
       - `Prompt`: `"You are Debater 2 on the CGSpec Architecture Council. Focus exclusively on security vulnerabilities, permission leaks, race conditions, lock collisions, and malicious abuse. Analyze this locked question: <QUESTION>. Attack all naive assumptions and present failure modes."`
     - **Debater 3 (Pragmatic DX & Ship Velocity):**
       - `TypeName`: `"research"` (or `"self"`)
       - `Role`: `"Debater 3 — Pragmatic DX & Ship Speed"`
       - `Prompt`: `"You are Debater 3 on the CGSpec Architecture Council. Focus exclusively on developer experience, simplicity, v0.1 shipping velocity, and avoiding over-engineering. Analyze this locked question: <QUESTION>. Challenge complexity and argue for the fastest, cleanest human-centric path."`

3. **Supervise N Rounds with File-by-Round Logging:**
   - For each round `k` (from `1` to `N`, default `N=3`):
     - Pass Debater 1's arguments to Debaters 2 and 3, and vice versa using `send_message`.
     - Collect each subagent's response: (a) Concessions, (b) Evidence-backed refutations, (c) Updated position.
     - **Write Live Round File:** Save the complete transcript of round `k` to:
       `{project-root}/docs/.working/council/ADR-NNN-<slug>/round-0k.md`
     - Emit a 3-line Inspector report in the chat:
       `🔔 [Council Round k/N] Clash: ... | Concession: ... | Consensus Shift: ...`
   - After Round `N`, write:
     `{project-root}/docs/.working/council/ADR-NNN-<slug>/summary.md`
     (Executive brief: consensus, agreed invariants, and the proposed decision).

4. **Draft ADR Proposal (Law 1: Never Auto-Accept):**
   - Terminate debater subagents (`manage_subagents` with `kill` or `kill_all`).
   - Write `{project-root}/docs/adr/ADR-NNN-<slug>.md` with **`Status: Proposed`** (NOT Accepted).
   - Present the proposal to the user in chat:
     *"The Council has concluded. I drafted the proposal in `docs/adr/ADR-NNN-<slug>.md`. Do you approve this ADR?"*
   - **ONLY when the user explicitly approves:**
     - Update ADR status to `Status: Accepted`.
     - Log to `docs/.memlog.md`:
       ```bash
       uv run {skill-dir}/scripts/memlog.py add {project-root}/docs/.memlog.md \
         --tags "lock,council,adr" \
         --summary "ADR-NNN: <decision>"
       ```
     - Update affected spines (`01`..`05`) and register in `docs/00-INDEX.md`.
     - Archive working files from `docs/.working/council/ADR-NNN-<slug>/` to `docs/archive/council/ADR-NNN-<slug>/`.


