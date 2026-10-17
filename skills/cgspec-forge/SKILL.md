---
name: cgspec-forge
description: Stage 1 Product Brainstorming & ORCA Object Map Compiler. Drives active thinking, problem statement, mission, day-in-the-life walkthrough (01-INTENT.md), and Sophia Prater ORCA domain nouns & relationships (02-OOUX.md). Enforces the Scope Firewall to park out-of-scope ideas in 00-INBOX.md.
---

# cgspec-forge

## Primary Responsibility (Stage 1)
- Answer: *Is this interesting? What does it do? Who is it for? What is the Day-in-the-Life walkthrough?*
- Compile the **ORCA Object Map**: Objects, Relationships (1:1, 1:N, M:N), Calls-to-Action (CTAs & permissions), and Attributes into `docs/02-OOUX.md`.
- Enforce the **Scope Firewall**: Guard the `v0.1` boundary by parking speculative future ideas into `docs/00-INBOX.md` (`Future Backlog v0.2+`).
- **Never jump into visual wireframes, styling, or coding:** Output must be locked `01-INTENT.md` and `02-OOUX.md`, which serve as the immutable input for `cgspec-ui-ux`.

## Execution Steps

1. **State Load & 1-Line Compass:**
   - Run `uv run {skill-dir}/scripts/memlog.py status {project-root}/docs/.memlog.md`.
   - **Pre-Flight ADR Check:** Inspect `{project-root}/docs/adr/` to respect existing architectural decisions and avoid contradicting locked system invariants.
   - Start every message with the 1-line plain-English compass (clean text, zero emojis):
     `Where we are: [Stage 1: Intent & Domain Nouns] -> Stage 2: UI/UX & Interactive Prototype -> Stage 3: Architecture & Physical DDL -> Stage 4: Build Slices`
   - **Strict Law 3 Invariant:** The user defines *why we build* (PRD & Day-in-the-Life journey) and *what they experience* (complete UI/UX, spatial zoning, and interactive prototype) **FIRST**. Technical "how" (database tables, SQL schemas, foreign keys, programming languages, backend frameworks, ORMs) is **strictly forbidden** until the human has tested and approved the interactive prototype!

2. **Explain First, Ask Second (1–2 Questions Max Per Turn):**
   - If the user asks *"what does that mean?"* or expresses confusion, **explain in plain conversational English first**—never pop up an `ask_question` modal without explaining first.
   - Never use fictional persona names ("Sam", "Maya", "Mary"); use explicit functional roles (`Resource Owner`, `Project Lead`, `Developer`, `AI Agent`).
   - When the user is ready to lock a choice, use `ask_question` with `(Recommended)` on the first option.
   - If an idea belongs in `v0.2+`, offer to park it in `docs/00-INBOX.md`.

3. **Log, ADR & Spine Derivation (No Long Silent Loops):**
   - Log every locked answer:
     ```bash
     uv run {skill-dir}/scripts/memlog.py add {project-root}/docs/.memlog.md \
       --tags "lock,<prd|nouns|arch|ux>" \
       --summary "<concise decision>" \
       --details "<rationale and rejected options>"
     ```
   - **Architectural Decision Mandate (ADR):** If the decision involves an architectural trade-off, database engine, auth/crypto protocol, multi-repo mount, or boundary contract, write `{project-root}/docs/adr/ADR-NNN-<slug>.md` (Context, Decision, Consequences) and register it in `docs/00-INDEX.md`.
   - Update the affected spine (`01-INTENT.md` .. `05-DELIVERY.md`) and `docs/00-INDEX.md`, and state in 1 short sentence what was saved.

