---
name: cgspec-council
description: Supervised 3-Agent Peer Debate Council. Host/Inspector runs N rounds on one locked question across 3 orthogonal lenses, emits 3-line round reports, archives logs, and writes ADR-NNN.md.
---

# cgspec-council

## Roles & Architecture

- **Main Agent (Pair Programmer / Coach):**
  - **Stays in the primary chat with the user at all times.**
  - Does NOT get bogged down in multi-turn debate loops.
  - Spawns the 4-agent Council team via `invoke_subagent`.
  - Receives live round reports from the Council Supervisor and relays a concise 3-line update to the user.
  - Presents the final brief and proposed ADR to the user for validation.

- **The 4 Council Subagents (Spawned Concurrently via `invoke_subagent`):**
  1. **Council Supervisor (Host & Inspector Subagent):**
     - Role: `"Council Supervisor & Inspector"`
     - Stays neutral. Never takes a side.
     - Chairs the debate, coordinates the 3 Debaters, and writes the `N + 2` live files to `docs/.working/council/COUNCIL-NNN-<slug>/`.
     - After each round, sends a 3-line Inspector update back to the Main Agent.
     - Writes `summary.md` and the draft `docs/adr/ADR-NNN-<slug>.md` (`Status: Proposed`).
  2. **Debater 1 (Systems & Modularity Specialist):**
     - Role: `"Debater 1 — Systems & Modularity"`
     - Focus: Boundaries, Ports & Adapters, loose coupling, extensibility.
  3. **Debater 2 (Adversarial Security & Failure Modes Specialist):**
     - Role: `"Debater 2 — Security & Edge Cases"`
     - Focus: Race conditions, credential leaks, permission bypasses, lock collisions.
  4. **Debater 3 (Pragmatic DX & Ship Velocity Specialist):**
     - Role: `"Debater 3 — Pragmatic DX & Ship Speed"`
     - Focus: Simplicity, v0.1 shipping velocity, developer ergonomics, human alignment.

---

## Execution Steps

1. **Lock Question & Initialize Session Directory:**
   - Formulate one exact technical, architectural, or product decision question.
   - Determine session ID: `COUNCIL-NNN-<slug>` (e.g. `COUNCIL-001-cortexgate-gap-audit`).
   - Create the live working directory:
     `{project-root}/docs/.working/council/COUNCIL-NNN-<slug>/`
   - Write `{project-root}/docs/.working/council/COUNCIL-NNN-<slug>/00-topic.md`:
     Record the question, motivation, relevant docs, and the mandates for the Supervisor and 3 Debaters.

2. **MANDATORY: Main Agent Spawns the 4 Subagents (Zero Single-Agent Simulation):**
   - **ZERO-SIMULATION MANDATE:** The Main Agent is **STRICTLY FORBIDDEN** from roleplaying the debaters or typing simulated dialog into a file.
   - **MANDATORY TOOL CALL:** The Main Agent **MUST** call `invoke_subagent` to launch all 4 subagents in parallel:
     - **Subagent 1 (Supervisor):**
       - `TypeName`: `"self"` (or `"research"`)
       - `Role`: `"Council Supervisor & Inspector"`
       - `Prompt`: `"You are the Council Supervisor for session COUNCIL-NNN-<slug>. Your job is to orchestrate Debaters 1, 2, and 3 on the locked question: <QUESTION>. Run N rounds (default N=3). After each round, write {project-root}/docs/.working/council/COUNCIL-NNN-<slug>/round-0k.md, and send a 3-line report to the Main Agent. At the end, write summary.md and draft {project-root}/docs/adr/ADR-NNN-<slug>.md with Status: Proposed."`
     - **Subagent 2 (Debater 1):**
       - `TypeName`: `"research"` (or `"self"`)
       - `Role`: `"Debater 1 — Systems & Modularity"`
       - `Prompt`: `"You are Debater 1 on the CGSpec Architecture Council. Focus exclusively on clean boundaries, Ports & Adapters, loose coupling, and maintainability. Analyze this locked question: <QUESTION>. Read docs/adr/ and active docs, and output your initial 3-point position with concrete technical evidence."`
     - **Subagent 3 (Debater 2):**
       - `TypeName`: `"research"` (or `"self"`)
       - `Role`: `"Debater 2 — Security & Edge Cases"`
       - `Prompt`: `"You are Debater 2 on the CGSpec Architecture Council. Focus exclusively on security vulnerabilities, permission leaks, race conditions, lock collisions, and malicious abuse. Analyze this locked question: <QUESTION>. Attack all naive assumptions and present failure modes."`
     - **Subagent 4 (Debater 3):**
       - `TypeName`: `"research"` (or `"self"`)
       - `Role`: `"Debater 3 — Pragmatic DX & Ship Speed"`
       - `Prompt`: `"You are Debater 3 on the CGSpec Architecture Council. Focus exclusively on developer experience, simplicity, v0.1 shipping velocity, and avoiding over-engineering. Analyze this locked question: <QUESTION>. Challenge complexity and argue for the fastest, cleanest human-centric path."`

3. **Live Round Monitoring (Main Agent Relays to Human):**
   - The session directory `{project-root}/docs/.working/council/COUNCIL-NNN-<slug>/` collects `N + 2` files:
     - `00-topic.md` (Question & context)
     - `round-01.md` .. `round-0N.md` (One file saved per round)
     - `summary.md` (Executive brief synthesizing consensus & shift)
   - As the Council Supervisor logs each round, the Main Agent relays the 3-line status to the user in chat:
     `📍 Council Status [Round k/N]: Clash: ... | Concession: ... | Consensus Shift: ...`

4. **Draft Proposal & Mandatory Human Validation (Law 1):**
   - Terminate debater subagents (`manage_subagents` with `kill` or `kill_all`).
   - The Council Supervisor outputs `{project-root}/docs/adr/ADR-NNN-<slug>.md` with **`Status: Proposed`** (NOT Accepted).
   - The Main Agent presents the `summary.md` executive brief to the user in chat:
     *"The Council has concluded. The debate log is in `docs/.working/council/COUNCIL-NNN-<slug>/` and the proposal is drafted in `docs/adr/ADR-NNN-<slug>.md`. Do you approve this decision?"*
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




