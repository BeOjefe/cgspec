---
name: cgspec-council
description: Supervised 3-Agent Peer Debate Council. Host/Inspector runs N rounds on one locked question across 3 orthogonal lenses, emits 3-line round reports, archives logs, and writes ADR-NNN.md.
---

# cgspec-council

## Roles & Architecture

- **Main Agent (Pair Programmer / Coach):**
  - **Stays in the primary chat with the user at all times.**
  - **High-Information Mandate:** When launching the council, the Main Agent **MUST** provide a high-signal chat brief explaining:
    1. The Locked Question
    2. The Real-World Tension & Stakes (Trade-offs, performance, security, complexity)
    3. The Expected Architectural Invariant to be locked in `ADR-NNN`
  - Does NOT get bogged down in multi-turn debate loops.
  - Receives live round reports **ONLY from the Council Supervisor** (3-line updates relayed to the human).
  - Debater subagents are strictly isolated to disk and **MUST NEVER** message or spam the Main Agent's chat.

- **The 4 Council Subagents (Spawned via `invoke_subagent`):**
  1. **Council Supervisor (Host & Inspector Subagent):**
     - Role: `"Council Supervisor & Inspector"`
     - Stays neutral. Never takes a side.
     - Chairs the debate, reads debater disk positions, writes the `N + 2` live files to `docs/.working/council/COUNCIL-NNN-<slug>/`.
     - After each round, sends a 3-line Inspector update message back to the Main Agent.
     - Writes `summary.md` and drafts `docs/adr/ADR-NNN-<slug>.md` (`Status: Proposed`).
  2. **Debater 1 (Systems & Modularity Specialist):**
     - Role: `"Debater 1 — Systems & Modularity"`
     - Focus: Boundaries, Ports & Adapters, loose coupling, extensibility.
     - **Silent Disk Protocol:** Writes full positions to `docs/.working/council/COUNCIL-NNN-<slug>/debater-1-round-0k.md`. Replies to parent with only 5 words: *"Position written to council workspace."*
  3. **Debater 2 (Adversarial Security & Failure Modes Specialist):**
     - Role: `"Debater 2 — Security & Edge Cases"`
     - Focus: Race conditions, credential leaks, permission bypasses, lock collisions, path traversals.
     - **Silent Disk Protocol:** Writes full positions to `docs/.working/council/COUNCIL-NNN-<slug>/debater-2-round-0k.md`. Replies to parent with only 5 words: *"Position written to council workspace."*
  4. **Debater 3 (Pragmatic DX & Ship Velocity Specialist):**
     - Role: `"Debater 3 — Pragmatic DX & Ship Speed"`
     - Focus: Simplicity, v0.1 shipping velocity, developer ergonomics, human alignment, zero over-engineering.
     - **Silent Disk Protocol:** Writes full positions to `docs/.working/council/COUNCIL-NNN-<slug>/debater-3-round-0k.md`. Replies to parent with only 5 words: *"Position written to council workspace."*

---

## Execution Steps

1. **Lock Question & Announce High-Information Briefing in Chat:**
   - Formulate one exact technical, architectural, or product decision question.
   - Determine session ID: `COUNCIL-NNN-<slug>` (e.g. `COUNCIL-002-v01-architecture-and-governance-audit`).
   - Create the live working directory:
     `{project-root}/docs/.working/council/COUNCIL-NNN-<slug>/`
   - Write `{project-root}/docs/.working/council/COUNCIL-NNN-<slug>/00-topic.md` with full context, reviewed spines, and mandates.
   - **Post High-Information Briefing in Chat:**
     ```markdown
     🏛️ Architecture Council Initialized: [COUNCIL-NNN-<slug>]

     ### 📌 The Locked Question
     > "<Exact question being debated>"

     ### ⚖️ The Stakes & Trade-offs
     - **Core Tension:** <What architectural trade-off is at stake?>
     - **Failure Modes:** <What breaks or suffers if we get this wrong?>
     - **Target Invariant:** <What exact rule will be codified into ADR-NNN?>

     ### 👥 The Council Formation
     - **Supervisor & Inspector:** Coordinating debate rounds and synthesizing consensus.
     - **Debater 1 (Systems):** Ports & Adapters, virtual path resolution, clean boundaries.
     - **Debater 2 (Security):** Path traversal, permission bypasses, race conditions, memory bounds.
     - **Debater 3 (Pragmatic DX):** Shipping velocity, minimal complexity, developer ergonomics.
     ```

2. **MANDATORY: Main Agent Spawns the 4 Subagents (Zero Single-Agent Simulation):**
   - **ZERO-SIMULATION MANDATE:** The Main Agent is **STRICTLY FORBIDDEN** from roleplaying the debaters or typing simulated dialog into a file.
   - **MANDATORY TOOL CALL:** The Main Agent calls `invoke_subagent` to launch all 4 subagents in parallel.
   - **Debater Prompt Isolation Rule:** Debaters are instructed to write arguments directly to `docs/.working/council/COUNCIL-NNN-<slug>/debater-<k>-round-01.md` and reply with only: *"Position written to council workspace."*
   - This ensures **zero chat spam**—the Main Agent's chat remains clean and uncluttered.

3. **Live Round Monitoring (Supervisor -> Main Agent -> Human):**
   - The Council Supervisor reads the debater files from disk, synthesizes the round, logs `{project-root}/docs/.working/council/COUNCIL-NNN-<slug>/round-0k.md`, and sends a 3-line Inspector update to the Main Agent.
   - The Main Agent relays the 3-line update to the user:
     `📍 Council Status [Round k/N]: Clash: ... | Concession: ... | Consensus Shift: ...`

4. **Draft Proposal & Mandatory Human Validation (Law 1 & Law 7):**
   - Terminate debater subagents (`manage_subagents` with `kill` or `kill_all`).
   - The Council Supervisor outputs `{project-root}/docs/adr/ADR-NNN-<slug>.md` with **`Status: Proposed`** (NOT Accepted) and `summary.md`.
   - The Main Agent presents the `summary.md` executive brief to the user in chat.
   - **Atomic Invariant (Law 7):**
     - ONLY when the user explicitly approves:
       - Update ADR status to `Status: Accepted`.
       - Log to `docs/.memlog.md`:
         ```bash
         uv run {skill-dir}/scripts/memlog.py add {project-root}/docs/.memlog.md \
           --tags "lock,council,adr" \
           --summary "ADR-NNN: <decision>"
         ```
       - Update affected spines (`01`..`05`) and register in `docs/00-INDEX.md`.
       - Archive working files to `docs/archive/council/COUNCIL-NNN-<slug>/`.
