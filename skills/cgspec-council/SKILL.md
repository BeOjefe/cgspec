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
  - **Zero Decorative Emoji Spam:** Never decorate chat text, headers, or bullet points with decorative emojis (such as 🏛️, 📌, ⚖️, 👥, 📍, 🟢, 🔴). Use clean Markdown headers and standard bullet points.
  - **Single Subagent Delegation Invariant:** The Main Agent calls `invoke_subagent` for **EXACTLY ONE subagent**: `Council Supervisor & Inspector`.
  - **ABSOLUTE BAN ON DEBATER SUBAGENTS IN MAIN AGENT:** The Main Agent is **STRICTLY FORBIDDEN** from putting debaters in its `Subagents` array. When debater subagents are spawned directly by the Main Agent, their turn completion messages pop up directly in the user's primary chat window, causing unacceptable chat spam.
  - Receives live round reports **ONLY from the Council Supervisor** (3-line updates relayed to the human).

- **The Council Supervisor & Background Workspace:**
  - **Role:** `"Council Supervisor & Inspector"`
  - **TypeName:** `"self"`
  - Runs in an isolated background conversation context.
  - Conducts the multi-perspective debate across the 3 orthogonal lenses directly in the background workspace `{project-root}/docs/.working/council/COUNCIL-NNN-<slug>/`:
    1. **Debater 1 Lens (Systems & Modularity):** Ports & Adapters, virtual mount routing, clean contracts, interface boundaries. Writes `debater-1-round-0k.md`.
    2. **Debater 2 Lens (Adversarial Security & Edge Cases):** Race conditions, transaction isolation, permission bypasses, path traversal, memory limits, fail-safe fallbacks. Writes `debater-2-round-0k.md`.
    3. **Debater 3 Lens (Pragmatic DX & Ship Speed):** Minimal onboarding friction, scaffolding velocity, ergonomic API signatures, eliminating speculative complexity. Writes `debater-3-round-0k.md`.
  - Synthesizes each round into `round-0k.md`.
  - Sends a concise 3-line status report to the Main Agent after each round via `send_message`:
    `Council Status [Round k/N]: Clash: <summary> | Concession: <summary> | Consensus Shift: <summary>`
  - Writes `{project-root}/docs/.working/council/COUNCIL-NNN-<slug>/summary.md`.
  - Drafts `{project-root}/docs/adr/ADR-NNN-<slug>.md` with **`Status: Proposed`**.

---

## Execution Steps

1. **Lock Question & Announce High-Information Briefing in Chat:**
   - Formulate one exact technical, architectural, or product decision question.
   - Determine session ID: `COUNCIL-NNN-<slug>` (e.g. `COUNCIL-003-specification-precision-and-scaffold-readiness`).
   - Create the live working directory:
     `{project-root}/docs/.working/council/COUNCIL-NNN-<slug>/`
   - Write `{project-root}/docs/.working/council/COUNCIL-NNN-<slug>/00-topic.md` with full context, reviewed spines, and mandates.
   - **Post High-Information Briefing in Chat (Clean Markdown, Zero Emojis):**
     ```markdown
     ### Architecture Council Initialized: [COUNCIL-NNN-<slug>]

     #### The Locked Question
     > "<Exact question being debated>"

     #### The Stakes & Trade-offs
     - **Core Tension:** <What architectural trade-off is at stake?>
     - **Failure Modes:** <What breaks or suffers if we get this wrong?>
     - **Target Invariant:** <What exact rule will be codified into ADR-NNN?>

     #### Council Formation
     - **Supervisor & Inspector:** Coordinating debate rounds and synthesizing consensus in background.
     - **Debater 1 (Systems):** Ports & Adapters, virtual path resolution, clean boundaries.
     - **Debater 2 (Security):** Path traversal, permission bypasses, race conditions, memory bounds.
     - **Debater 3 (Pragmatic DX):** Shipping velocity, minimal complexity, developer ergonomics.
     ```

2. **MANDATORY: Main Agent Spawns ONLY the Supervisor:**
   - **ZERO-SIMULATION MANDATE:** The Main Agent is **STRICTLY FORBIDDEN** from roleplaying the debaters or typing simulated dialog into a file.
   - **MANDATORY TOOL CALL:** The Main Agent calls `invoke_subagent` for **ONE single subagent**:
     ```json
     {
       "Subagents": [
         {
           "Model": "inherit",
           "Role": "Council Supervisor & Inspector",
           "TypeName": "self",
           "Workspace": "inherit",
           "Prompt": "You are the Council Supervisor for session COUNCIL-NNN-<slug> in {project-root}.\nYour mission is to orchestrate a true multi-perspective architectural debate on the locked question:\n'<QUESTION>'\n\nYOUR FIRST ACTION is to call invoke_subagent to spawn your 3 Debaters in parallel:\n1. Role: 'Debater 1 — Systems & Modularity' (Focus: Ports & Adapters, clean boundaries, interface precision)\n2. Role: 'Debater 2 — Security & Edge Cases' (Focus: Transaction isolation, permission bypasses, failure modes)\n3. Role: 'Debater 3 — Pragmatic DX & Ship Speed' (Focus: Zero over-engineering, minimal onboarding friction, ship speed)\n\nBecause YOU spawn them, their completion messages arrive exclusively in YOUR conversation pane, completely insulating the Main Agent and human chat from clutter.\n\nCoordinate N rounds (default N=3):\n- In Round 1, debaters write initial positions to docs/.working/council/COUNCIL-NNN-<slug>/debater-k-round-01.md.\n- Read debater disk files, synthesize into round-0k.md, and send a 3-line update to your parent (Main Agent) via send_message:\n  'Council Status [Round k/N]: Clash: ... | Concession: ... | Consensus Shift: ...'\n- In subsequent rounds, send rebuttals to debaters with send_message, read their updated disk files, and synthesize.\n- (Fallback: If child subagent spawning is restricted by the orchestrator, conduct the 3 orthogonal analyses on disk directly).\n\nAfter Round N:\n- Terminate child debater subagents.\n- Write docs/.working/council/COUNCIL-NNN-<slug>/summary.md.\n- Draft docs/adr/ADR-NNN-<slug>.md with Status: Proposed.\n- Conclude and send your final executive summary to the Main Agent."
         }
       ]
     }
     ```
   - **Zero Debater Chat Spam:** Because only the Supervisor is a child of the Main Agent, zero debater messages ever touch the Main Agent or user chat window.

3. **Live Round Monitoring (Supervisor -> Main Agent -> Human):**
   - The Council Supervisor runs the rounds in the background, logs `{project-root}/docs/.working/council/COUNCIL-NNN-<slug>/round-0k.md`, and sends a 3-line Inspector update to the Main Agent.
   - The Main Agent relays the 3-line update to the user:
     `Council Status [Round k/N]: Clash: ... | Concession: ... | Consensus Shift: ...`

4. **Draft Proposal & Mandatory Human Validation (Law 1 & Law 7):**
   - Terminate the supervisor subagent (`manage_subagents` with `kill` or `kill_all`).
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
