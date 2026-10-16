---
name: cgspec-council
description: Supervised 3-Agent Peer Debate Council. Host/Inspector runs N rounds on one locked question across 3 orthogonal lenses, emits 3-line round reports, archives logs, and writes ADR-NNN.md.
---

# cgspec-council

## Roles & Architecture

- **Council Supervisor (Host / Inspector):** The **Main Agent** running this skill.
  - The Supervisor **never takes a side or debates itself**.
  - Its exclusive duties:
    1. Lock the question and initialize the session directory.
    2. Invoke the 3 independent Debater subagents via `invoke_subagent`.
    3. Chair the rounds, pass messages between debaters, and log live round files.
    4. Emit the 3-line Inspector reports to the human after each round.
    5. Present the final executive brief and draft proposal to the human for approval.
- **The 3 Independent Debater Subagents (Spawned via `invoke_subagent`):**
  - **Debater 1 (Systems & Modularity):** Focuses strictly on boundaries, Ports & Adapters, and loose coupling.
  - **Debater 2 (Adversarial Security & Edge Cases):** Focuses strictly on failure modes, credential leaks, and race conditions.
  - **Debater 3 (Pragmatic DX & Ship Speed):** Focuses strictly on simplicity, shipping velocity, and cognitive clarity.

---

## Execution Steps

1. **Lock Question & Initialize Session Directory:**
   - Formulate one exact technical, architectural, or product decision question.
   - Determine session ID: `COUNCIL-NNN-<slug>` (e.g. `COUNCIL-001-cortexgate-gap-audit`).
   - Create the live working directory:
     `{project-root}/docs/.working/council/COUNCIL-NNN-<slug>/`
   - Write `{project-root}/docs/.working/council/COUNCIL-NNN-<slug>/00-topic.md`:
     Record the question, motivation, relevant docs, and the 3 debater mandates.

2. **MANDATORY: Supervisor Spawns 3 Real Subagents (Zero Single-Agent Simulation):**
   - **ZERO-SIMULATION MANDATE:** The Supervisor is **STRICTLY FORBIDDEN** from roleplaying the debaters or typing simulated dialog into a file.
   - **MANDATORY TOOL CALL:** The Supervisor **MUST** call `invoke_subagent` (or platform equivalent like `Agent`/`Task`) to launch 3 independent, concurrent subagent instances:
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

3. **Supervise N Rounds with (N + 2) File-by-Round Logging:**
   - The session directory `{project-root}/docs/.working/council/COUNCIL-NNN-<slug>/` will contain exactly `N + 2` files:
     - File 1: `00-topic.md` (Locked question & context)
     - Files 2 through `N + 1`: `round-01.md` .. `round-0N.md` (One file saved per round)
     - File `N + 2`: `summary.md` (Executive brief synthesizing consensus & shift)
   - For each round `k` (from `1` to `N`, default `N=3`):
     - Pass Debater 1's arguments to Debaters 2 and 3, and vice versa using `send_message`.
     - Collect each subagent's response: (a) Concessions, (b) Evidence-backed refutations, (c) Updated position.
     - **Write Live Round File:** Save the complete round transcript to:
       `{project-root}/docs/.working/council/COUNCIL-NNN-<slug>/round-0k.md`
     - Emit a 3-line Inspector report in the chat:
       `🔔 [Council Round k/N] Clash: ... | Concession: ... | Consensus Shift: ...`
   - After Round `N`, write:
     `{project-root}/docs/.working/council/COUNCIL-NNN-<slug>/summary.md`

4. **Draft Proposal & Mandatory Human Validation (Law 1):**
   - Terminate debater subagents (`manage_subagents` with `kill` or `kill_all`).
   - If the council resolved an architectural decision, write `{project-root}/docs/adr/ADR-NNN-<slug>.md` with **`Status: Proposed`** (NOT Accepted).
   - Present the proposal and `summary.md` brief to the user in chat:
     *"The Council has concluded. The debate log is in `docs/.working/council/COUNCIL-NNN-<slug>/` and the proposal is in `docs/adr/ADR-NNN-<slug>.md`. Do you approve this decision?"*
   - **ONLY when the user explicitly approves:**
     - Update ADR status to `Status: Accepted`.
     - Log to `docs/.memlog.md`:
       ```bash
       uv run {skill-dir}/scripts/memlog.py add {project-root}/docs/.memlog.md \
         --tags "lock,council,adr" \
         --summary "ADR-NNN: <decision>"
       ```
     - Update affected spines (`01`..`05`) and register in `docs/00-INDEX.md`.
     - Archive working files from `docs/.working/council/COUNCIL-NNN-<slug>/` to `docs/archive/council/COUNCIL-NNN-<slug>/`.



