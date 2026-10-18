# AGENTS.md — Constitutional Governance for AI Coding Agents

This repository is governed by the **Reformed CGSpec v0.2 Specification-Driven SDLC Methodology**. All AI coding agents, background workers, and subagents MUST strictly adhere to the 11 Core Coach Laws below.

---

## 1. The 11 Core Coach Laws

1. **Law 1 — Strict Privacy Invariant:**
   All repositories, artifacts, and documentation under this project are strictly PRIVATE. Never commit secrets, API keys, or private tokens.

2. **Law 2 — Zero-Tolerance Unicode Emoji Ban:**
   Decorative and status emojis (e.g. checkmarks, rockets, fire) are strictly banned across all markdown, documentation, and source code. Use semantic plain-text tags (`[PASS]`, `[FAIL]`, `[WARN]`, `[Accepted]`, `[Draft]`) or crisp inline SVGs (Lucide / Phosphor) in UI.

3. **Law 3 — Human Experience & UI/UX Precede Physical Architecture & Backend:**
   Physical database schemas, cryptographic envelopes, and backend code are prohibited until intent (`01-INTENT.md`), domain nouns (`02-OOUX.md`), and interactive HTML wireframes (`03-EXPERIENCE.md`) are validated.

4. **Law 4 — Singular Engine Subsystems in `docs/.cgspec/`:**
   All internal scripts, research, council transcripts, ADRs, prototypes, and slices reside in `docs/.cgspec/` using singular, zero-padded directory names (`01-script`, `02-research`, `03-council`, `04-adr`, `05-prototype`, `06-slice`, `.archive`). Never create a `.working/` directory.

5. **Law 5 — Non-Linear Memory Log Parity (`docs/.memlog.md`):**
   Every milestone entry in `docs/.memlog.md` must increment monotonically (`[M-001]`, `[M-002]`, etc.) and correspond to a clean Git commit. Never reorder or overwrite past entries.

6. **Law 6 — Plain English First, Engineering Jargon Second:**
   Never display naked internal acronyms (e.g. `DEK`, `KEK`, `DDL`, `OOUX`) in user-facing UI without clear, friendly human explanations.

7. **Law 7 — Zero Database Identifier Leakage:**
   Never expose raw database column names or snake_case identifiers (e.g. `user_id`, `created_at_utc`) in user-facing labels or table headers.

8. **Law 8 — Capability-Driven UI Hiding:**
   Never show disabled, non-functional buttons or controls without explaining why they are unavailable or hiding them entirely based on permissions.

9. **Law 9 — Strict Hexagonal Decoupling (Ports & Adapters):**
   UI components and business logic must never directly import databases, filesystems, or third-party APIs. All external dependencies must be isolated behind Port interfaces.

10. **Law 10 — Tier 0 Proactive Reference Scouting & Inversion of Design Burden:**
    The human is an executive curator, NOT a UI draftsman or bug-hunter. Before drafting wireframes, the AI must autonomously scout real-world exemplars, extract design DNA, and present 2–3 concrete visual/spatial archetypes with trade-offs.

11. **Law 11 — Disk-First Immediate Capture & 4-Bucket Triage:**
    Chat is ephemeral; disk is permanent truth. Before replying to multi-topic user feedback, triage and persist 100% of user input to disk:
    - **Bucket A (Active Screen / Current Step):** Apply immediately to the active artifact/spine.
    - **Bucket B (Downstream Stage Queue):** Append to the target downstream spine (`03-EXPERIENCE.md`, `04-ARCHITECTURE.md`, `05-DELIVERY.md`).
    - **Bucket C (Backlog & Out-of-Scope):** Record in `01-INTENT.md` Anti-Goals or `docs/.memlog.md`.
    - **Bucket D (Technical Spikes & Research):** Record in `docs/.cgspec/02-research/RES-NNN-<slug>.md`.

---

## 2. Session Initialization Protocol (What Every Agent Reads First)

Whenever a new agent session starts or resumes:
1. Read `AGENTS.md` (Constitutional Laws).
2. Read `docs/00-INDEX.md` (Current Project Compass & Active Stage).
3. Read the last 3 milestone entries in `docs/.memlog.md` (Current context and recent locks).
4. Run `python3 docs/.cgspec/01-script/doctor.py --repo . --strict-emojis` to verify system health.
