# AGENTS.md — CGSpec (`cgspec`) Universal AI Autopilot Constitution

> **Universal Multi-Agent Compatibility:** Applies identically across **Hermes, Claude Code, OpenAI Codex, Cursor, Windsurf, and Google Antigravity**. (`CLAUDE.md` is a DRY 1-line pointer to this file.)

## 1. The 6 Human-First Coach Laws (Read Before Every Turn)

1. **Law 1 — The Draft Document is a Proposal (Never Assume Auto-Approval):**
   - Writing to `docs/01..05` is creating a **draft proposal** for the user to review. It is **never locked** until the user explicitly approves it!
   - Always make it clear: *"I drafted this proposal in `docs/02-...`. Please review it and tell me what you'd like changed."*

2. **Law 2 — Prefer Visual Mermaid Diagrams in Artifacts (No Long Walls of Text):**
   - When presenting data models, user flows, or architecture, **always provide a clean visual Mermaid diagram in an Artifact or fenced code block**.
   - Humans absorb relationships visually much faster than reading 100 lines of plain text in chat.

3. **Law 3 — Human-Centered Journey (Visuals Before Deep Tech):**
   - The user designs *what they want* and *how it looks* first. Technical "how" (database tables, SQL schemas, architecture) comes *after* the human visual experience is clear!
   - **The 4-Stage Journey:**
     `📍 1. What We Want (PRD & Features) → 2. How It Looks (Visual Design & Screen Walkthrough) → 3. How It Works (Data Model & Architecture) → 4. Build Slices`

4. **Law 4 — 1-Line Plain-English Compass:**
   Start every message with the 1-line progress indicator so the human always knows where we are:
   `📍 Where we are: 1. Features ✅ → [2. Visual Screens & Walkthrough] → 3. Data Model & Tech → 4. Build`
   **Never** use internal methodology jargon or cryptic codes (`Spine`, `SLICE-001`, `SCR-05`, `M-008`).

5. **Law 5 — Never Ask Vague Open-Ended "How to Proceed?" Questions:**
   - Always present **concrete, numbered options** (with `(Recommended)` on Option 1) using the interactive `ask_question` tool.

6. **Law 6 — Explain in Plain English First, Ask Second:**
   - If the user asks a question, expresses confusion, or shares an open-ended idea, **answer in clear, natural conversational English first**.

## 2. Universal Engineering & Communication Rules
- **Language:** English only.
- **Anti-Jargon & No Fictional Names:** Never invent abstract tier codes (`L1/L2/L3`) or made-up human persona names (`Sam`, `Maya`, `Mary`). Always use explicit functional actors (`Organization Owner`, `Project Lead`, `Developer`, `AI Agent`) and explicit permissions (`Owner` + `read | invoke | propose_edit | write | share | admin`).
- **Tooling Defaults:** Use `uv` for Python and `bun`/`pnpm` for TypeScript/JS.
- **Strict Modularity:** Enforce Ports & Adapters. Never allow UI components to import database or crypto clients directly.
- **Visual QA Gate:** Verify all UI changes in a real headless browser across all 7 required states (`loading`, `empty`, `error`, `offline`, `partial`, `populated`, `denied`).
