# ADR-001: Adopting `BMAD-METHOD` (v7) + Thin Customizations Instead of Reinventing the Wheel

- **Status:** Accepted (Updated after full source-code inspection of `bmad-code-org/BMAD-METHOD` `main` branch)
- **Date:** 2026-10-16

---

## 1. Context & Source-Code Verification

Initially, based on older v4/v6 summaries, we assumed `BMAD-METHOD` was a rigid linear waterfall where `/party-mode` only roleplayed personas in a single prompt and only worked in single repositories.

After cloning and inspecting the actual `bmad-code-org/BMAD-METHOD` (v7) source code, we verified that **BMAD v7 already implements ~90% of our target architecture natively**:

1. **Non-Linear Spec Hub + `.memlog.md` (`skills/bmad-spec/SKILL.md` & `_bmad/scripts/memlog.py`):**
   - `bmad-spec` acts as a central hub. Every planning skill (`bmad-forge-idea`, `bmad-prd`, `bmad-ux`, `bmad-architecture`) logs decisions, locks, assumptions, and cracks into an append-only `.memlog.md` via `uv run _bmad/scripts/memlog.py` and **re-derives** the spec (`spec-<slug>.md`).
   - Because contracts are derived from `.memlog.md` rather than hand-merged, skills can run in **any order**, before or after the spec exists, without merge drift.
2. **Multi-Execution `bmad-party-mode` (`skills/bmad-party-mode/SKILL.md`):**
   - Supports 4 execution modes: `session` (single-prompt roleplay), `auto`, **`subagent`** (spawns a real standing subagent per persona each round and weaves their responses), and **`agent-team`** (persistent agent team communicating directly).
3. **Dual UX Spine (`skills/bmad-ux/SKILL.md`):**
   - Produces **[Google Labs `DESIGN.md`](https://github.com/google-labs-code/design.md)** (visual tokens, palette, typography, components) + **`EXPERIENCE.md`** (named-protagonist journeys like Mary/Pary/Skeeter, screen-state inventory, WCAG 2.2 AA), backed by `.working/` visual explorations (HTML color themes, design directions, and **Excalidraw** wireframes) and parallel Reviewer Gates (`finalize_reviewers`).
4. **Mid-Project Pivots (`skills/bmad-correct-course/SKILL.md`):**
   - Runs a 6-step impact audit across PRD, Architecture, UX, and Tickets (`Direct Adjustment`, `Rollback`, or `MVP Review`) and outputs a formal Sprint Change Proposal.
5. **Monorepo + Polyrepo + Git Worktrees (`skills/bmod-method/help/monorepo-and-polyrepo.md`):**
   - Natively supports placing `_bmad` and `_bmad-output` (as its own Git repo) at a polyrepo workspace root above multiple service repositories (`repo-a/`, `repo-b/`), combined with bare clones and Git worktrees for parallel agent execution.
6. **Zero-Fork Customization (`_bmad/custom/config.toml` & `_bmad/custom/<skill>.toml`):**
   - Allows overriding agent personas, instructions, creative tools, and reviewer gates via TOML overlays without forking BMAD's core skills.

---

## 2. Scientific Backing (Peer-Reviewed Literature)

1. **MetaGPT (Hong et al., ICLR 2024, `arXiv:2308.00352`):** Demonstrates that encoding Standardized Operating Procedures (SOPs) as structured intermediate documents (PRD, System Design, Interface Spec) drastically reduces cascading hallucinations in multi-agent software development.
2. **Lost in the Middle (Liu et al., TACL 2024, `arXiv:2307.03172`):** Shows a 30–50% accuracy drop when constraints are buried in the middle of long conversational histories—validating BMAD v7's separation of chronological `.memlog.md` history from terse, re-derived spine contracts (`spec-<slug>.md`, `DESIGN.md`, `EXPERIENCE.md`, `ARCHITECTURE.md`).
3. **Multiagent Debate & Failure Modes (Du et al., ICML 2024 `arXiv:2305.14325`; Cemri et al., 2025 `arXiv:2503.13657`):** Confirms that independent multi-agent critique improves reasoning accuracy, provided agents are prevented from sycophantic agreement by adversarial prompts (`bmad-forge-idea` / orthogonal reviewer gates) and a structured host/judge supervisor.
4. **ChatDev (Qian et al., ACL 2024, `arXiv:2307.07924`):** Proves that bounded phase transitions (`Design -> Coding -> Testing`) prevent silent stubs and assumption drift.

---

## 3. Decision

**Do NOT reinvent what `BMAD-METHOD` v7 already solves.** Instead of building a redundant competing SDLC framework from scratch, `flowspec` acts as a **thin extension and customization layer on top of `BMAD-METHOD` v7** (`_bmad/custom/*.toml` + `AGENTS.md`), adding only the 3 specific capabilities not bundled in default BMAD v7:

1. **Autopilot Mid-Stream Spark Parking (`AGENTS.md` + `memlog.py`):** Automatically parking off-scope ideas mentioned during coding into `.memlog.md` (`--tags "direction:parked"`) and `00-INBOX.md` without interrupting the active build slice.
2. **Antigravity Supervised Peer Council Adapter (`bmad-party-mode` `subagent` / `agent-team`):** Wiring `bmad-party-mode` directly to Antigravity's `invoke_subagent` and `send_message` tools with a dedicated **Host/Inspector Supervisor** that emits a 3-line Round Inspector progress report after each round.
3. **Live Browser Visual Verification Gate (`_bmad/custom/bmad-ux.toml`):** Adding Chrome DevTools / headless browser screenshot verification as a `creative_tools` / `finalize_reviewers` gate for UI screens.
