# docs/00-INBOX.md — CGSpec (`cgspec`) Idea Parking Lot & Future Backlog

> **How This Works:** Any idea outside the active milestone (`v0.1`) is parked here (**Unsorted Sparks** or **Future Backlog `<Current+1>+`**).
> - **Milestone Rollover:** When the active version advances (e.g. from `v0.1` to `v0.2`), approved sparks become active vertical slices in `docs/slices/`, and this future backlog heading rolls over to the next release (e.g. `Future Backlog (v0.3+)`).
> - **Zero Hallucinated Roadmaps:** The AI must NEVER invent speculative future features; only record sparks explicitly stated by the human or deferred during active slices.
> - **Sprouting Rule (> 500 lines):** Stays a single file until 500 lines. If it exceeds 500 lines or team scales to multi-squad, sprout into `docs/00-INBOX/` (retaining numeric prefix) with `00-INBOX/sparks.md` and `00-INBOX/backlog.md`, archiving closed milestone items to `docs/archive/`.

---

## 1. Unsorted Sparks (Just Captured — Triage Later)
- [ ] **Guided Design Discovery & Visual Reference Curator (`cgspec-ux` refoundation):** Transform UX skill from static prompt generation into a deep, guided dialogue. Post-OOUX ergonomics interrogation (direct manipulation, markdown editing mode), external visual reference hunting (proposing live exemplars like Linear, Cloudflare, Notion, Bear), and non-overwhelming micro-step ergonomic interviews before generating variants. Staged in `docs/.working/rfc-deep-taste-and-design-discovery.md`.
- [ ] **alphaXiv MCP Research Bridge:** Connect the alphaXiv Model Context Protocol server (`https://api.alphaxiv.org/mcp/v1`) to enable autonomous discovery and grounding of architectural decisions and trade-offs in peer-reviewed arXiv papers during the Council and Intent phases.

---

## 2. Future Backlog (`v0.2+`)
- [ ] **Live CortexGate MCP Two-Way Sync Adapter (`cgspec sync`):** Automatically sync local `docs/.memlog.md` entries and `docs/00..05-*.md` spines with CortexGate's MCP server, enforcing `Owner` and granular permissions (`read | invoke | propose_edit | write | share | admin`).
- [ ] **Automated Repo Linter (`uv run scripts/cgspec_lint.py`):** Verify `00-INDEX.md` links, check that `CLAUDE.md` stays a DRY 1-line pointer to `AGENTS.md`, and verify `.memlog.md` spine consistency.
- [ ] **Visual HTML Status Board (`cgspec board`):** Generate a self-contained HTML dashboard from `docs/00-INDEX.md` and `docs/.memlog.md` for non-technical stakeholders.
