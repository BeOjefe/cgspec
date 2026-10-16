# CGSpec (`cgspec`) — Universal AI-Agnostic Spec Engine & CortexGate SDLC Bridge

> **100% AI-Agent Agnostic (`SKILL.md` + `AGENTS.md` + MCP):** Works identically across **Hermes, Claude Code, OpenAI Codex, Cursor, Windsurf, and Google Antigravity**—zero `.gemini` or single-vendor lock-in.  
> **Built on Science + Open Source (`BMAD-METHOD` v7 + Peer-Reviewed arXiv Research):** Combines non-linear `.memlog.md` spine derivation, Google Labs `DESIGN.md` + `EXPERIENCE.md`, supervised multi-agent peer councils, and native **CortexGate MCP** governance.

---

## 1. Why Does `cgspec` Exist If `BMAD-METHOD` (v7) Already Exists?

We inspected the full source code of [`bmad-code-org/BMAD-METHOD` (v7)](https://github.com/bmad-code-org/BMAD-METHOD) and verified what it already solves vs. why **`cgspec`** is needed for a multi-AI, CortexGate-powered engineering organization:

| Dimension | **`BMAD-METHOD` (v7)** | **`CGSpec` (`cgspec`)** |
| :--- | :--- | :--- |
| **1. Non-Linear Spec Hub (`.memlog.md`)** | ✅ **Proven in BMAD v7:** Logs decisions to `.memlog.md` (`memlog.py`) and re-derives `spec-<slug>.md` so skills run in any order. | ✅ **Adopted in `cgspec`:** Uses `scripts/memlog.py` (`uv run`) locally **AND** bridges `.memlog.md` events directly to **CortexGate MCP** when connected. |
| **2. UX Dual Spine (`DESIGN.md` + `EXPERIENCE.md`)** | ✅ **Proven in `bmad-ux`:** Google Labs `DESIGN.md` + `EXPERIENCE.md` + `.working/` (Excalidraw wireframes & HTML mocks) + named protagonists. | ✅ **Adopted in `cgspec-ux`:** Plus adds **Live Browser Screenshot Verification** across required states (`loading`, `empty`, `error`, `populated`, `denied`). |
| **3. Multi-User Team Governance & Ownership (MCP)** | ❌ **Local Single-Player Files Only:** No MCP server sync, no resource `Owner`, no granular authorization (`read \| invoke \| propose_edit \| write \| share \| admin`). | ✅ **Native CortexGate MCP Bridge:** Every spec, decision lock, and ADR carries explicit `Owner` and granular permission metadata for team-wide sync via CortexGate. |
| **4. Day-to-Day Ceremony** | 🟡 **15+ Separate Skills:** Requires invoking `bmad-forge-idea`, `bmad-prd`, `bmad-ux`, `bmad-architecture`, `bmad-spec`, `bmad-ticket`, `bmad-correct-course`, `bmad-party-mode`, `bmad-build`, `bmad-walkthrough`. | ✅ **Autopilot Coach Mode (`AGENTS.md` + 6 Core Skills):** Talk naturally in any AI agent (Hermes, Claude, Codex, Antigravity); the agent automatically parks mid-stream ideas and routes updates. |
| **5. Multi-AI Portability** | ✅ Portable `SKILL.md` files. | ✅ **Strict Zero-Vendor Lock-In:** `AGENTS.md` + 1-line DRY `CLAUDE.md` + portable `skills/*/SKILL.md` + MCP. Never locked to `.gemini/` or a single IDE. |

---

## 2. Scientific Research Backing (Peer-Reviewed arXiv Evidence)

1. **MetaGPT** *(Hong et al., ICLR 2024, `arXiv:2308.00352`)* — Encoding **Standardized Operating Procedures (SOPs)** as structured intermediate artifacts (PRD, UX Spine, Architecture Spec) before code generation prevents cascading hallucinations in multi-agent workflows.
2. **Lost in the Middle** *(Liu et al., TACL 2024, `arXiv:2307.03172`)* — Constraint adherence drops **30–50%** when rules are buried inside long conversational logs. Validated solution: log chronological history in `.memlog.md` (`memlog.py`) and **re-derive terse, front-loaded spines** read in fresh contexts.
3. **Multiagent Debate & Failure Modes** *(Du et al., ICML 2024 `arXiv:2305.14325`; Cemri et al., 2025 `arXiv:2503.13657`)* — Independent multi-agent critique reduces reasoning blind spots **only** when governed by adversarial pressure-testing (`cgspec-forge`) and an independent **Host/Judge Supervisor** (`cgspec-council`) to prevent sycophantic agreement.
4. **ChatDev** *(Qian et al., ACL 2024, `arXiv:2307.07924`)* — Bounded phase handoffs (`Design -> Slice Build -> Verification Walkthrough`) eliminate silent stubs and assumption drift.

---

## 3. Repository Navigation

- [`AGENTS.md`](file:///home/ojefe/Documents/Project/cgspec/AGENTS.md) — Universal Autopilot Constitution (for Hermes, Claude Code, Codex, Cursor, Antigravity)
- [`CLAUDE.md`](file:///home/ojefe/Documents/Project/cgspec/CLAUDE.md) — 1-line DRY pointer to `./AGENTS.md`
- [`docs/00-INDEX.md`](file:///home/ojefe/Documents/Project/cgspec/docs/00-INDEX.md) — Live State & Slice Roadmap
- [`docs/00-INBOX.md`](file:///home/ojefe/Documents/Project/cgspec/docs/00-INBOX.md) — Idea Parking Lot & `v0.2+` Backlog
- [`docs/01-PRD.md`](file:///home/ojefe/Documents/Project/cgspec/docs/01-PRD.md) — Product Requirements, Glossary & Scope
- [`docs/02-NOUNS-AND-FLOWS.md`](file:///home/ojefe/Documents/Project/cgspec/docs/02-NOUNS-AND-FLOWS.md) — Domain Objects, Non-Linear `.memlog.md` Flow, 3-Tier Pivot Engine & Polyrepo Layout
- [`docs/03-ARCHITECTURE.md`](file:///home/ojefe/Documents/Project/cgspec/docs/03-ARCHITECTURE.md) — Vendor-Neutral Skill Architecture (`skills/*/SKILL.md` + `scripts/memlog.py` + CortexGate MCP)
- [`docs/04-DESIGN.md`](file:///home/ojefe/Documents/Project/cgspec/docs/04-DESIGN.md) — Copy-Paste Templates (including Google Labs `DESIGN.md` + `EXPERIENCE.md`)
- [`docs/adr/`](file:///home/ojefe/Documents/Project/cgspec/docs/adr/) — Architecture Decision Records
