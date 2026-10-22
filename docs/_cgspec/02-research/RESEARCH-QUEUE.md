# Research queue
Created: 2026-10-22T20:50:49Z · Last edited: 2026-10-22T20:50:49Z

Spikes that are queued but not yet run. A queued item is a question, not a finding: nothing
here may be cited as evidence. When a spike concludes it becomes a `RES-NNN-<slug>.md` file
in this directory, is listed in [`README.md`](README.md), and its entry is removed from here.

Every item states its source, why CGSpec needs it, and what would make the spike finished.
An item nobody can state a use for is deleted rather than carried.

---

## QUEUE-001 — AIS-OS: a prose-governed AI operating system

- **Source:** <https://github.com/nateherkai/AIS-OS> (MIT, © 2026 Nate Herk). Same author as
  `scroll-craft`, which is already imported under this directory as `scrollcraft/`.
- **Status:** queued, not read. Nothing below is a finding.
- **Added:** 2026-10-22, at the user's request, to deeply explore.

### What it appears to be

Per its own README, an "AI Operating System starter kit for Claude Code and Codex": `CLAUDE.md`
and `AGENTS.md` as operating manuals, a `context/` directory of business and personal
information, a `decisions/log.md`, a `references/` framework directory, and six skills
(`/onboard`, `/grill-me`, `/audit`, `/link`, `/level-up`, `/3d-brain`). It personalises itself
through an onboarding interview.

This characterisation comes from the README alone and has not been checked against the tree.
Confirm or correct it as the first step of the spike.

### Why CGSpec needs it

It is the nearest thing to a direct counterpart, and it is structurally the opposite bet.
CGSpec's central claim is that **every rule a machine can check is enforced by one, not left
to the AI's goodwill** (`docs/METHOD-v0.2.md`). AIS-OS appears to govern an agent almost
entirely through prose instructions in `CLAUDE.md` / `AGENTS.md` plus skills the agent chooses
to invoke. If that holds, it is the best available natural experiment in what prose-only
governance does and does not hold on to, and the comparison tells us which CGSpec gates earn
their complexity and which are ceremony.

Its parts also map onto CGSpec's with suspicious neatness, and each mapping is a question:

| AIS-OS | CGSpec counterpart | The question |
|---|---|---|
| `decisions/log.md` | ADRs + the append-only ledger (`memlog.py`) | Is an append-only machine-written ledger worth its cost over a hand-maintained log, and what does theirs lose? |
| `/audit` | `doctor` + the registered-checks manifest | Does an agent-run audit catch what a deterministic checker catches? What does it catch that ours misses? |
| `/onboard` interview | `engine/install.py` | Theirs captures taste and context; ours captures layout and tiers. Should install interview the user at all? |
| `context/` | spines, slices, `project.json` | Is the tier/spine/slice structure load-bearing, or does a flat context directory hold up in practice? |
| `/level-up` weekly review | councils, audit reports | Is a scheduled self-improvement pass a thing CGSpec lacks and needs? |
| `/grill-me` | the inbox + approval capture | They actively extract context from the user. CGSpec only records what the user volunteers. |

### What finishes this spike

A `RES-005` that answers, with file-and-line evidence from the tree rather than from the README:

1. Which of its rules are mechanically enforced (a script, a hook, a check that can fail) and
   which are prose the agent may ignore. Count both.
2. What it does that CGSpec cannot, that we would want. Each item either becomes a queued
   proposal with a named CGSpec home, or is recorded as deliberately rejected with a reason.
3. What CGSpec does that it cannot, stated as a falsifiable claim rather than a boast.
4. Whether its onboarding interview and `/grill-me` context extraction are compatible with the
   rule that approvals and business promises come only from the user's own messages.
5. Licence and attribution constraints on borrowing any of it. The frameworks named in its
   README are trademarked and usable with attribution; nothing may be copied into CGSpec
   without recording that.

Import the tree under this directory as a local-only reference (see `README.md`) before
reading it, so the spike's citations point at a pinned revision rather than a moving branch.
Record the commit SHA that was read.
