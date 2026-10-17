# docs/00-INBOX.md — CGSpec (`cgspec`) Idea Parking Lot & Future Backlog

> **How This Works:** Any idea outside the active `v0.1` build is parked here (**Unsorted Sparks** or **Future Backlog `v0.2+`**). The AI must NEVER invent speculative roadmap items out of thin air; only capture sparks explicitly voiced by the human or deferred during active slices.

---

## 1. Unsorted Sparks (Just Captured — Triage Later)
- [ ] **Guided Design Discovery & Visual Reference Curator (`cgspec-ux` refoundation):** Transform UX skill from static prompt generation into a deep, guided dialogue. Post-OOUX ergonomics interrogation (direct manipulation, markdown editing mode), external visual reference hunting (proposing live exemplars like Linear, Cloudflare, Notion, Bear), and non-overwhelming micro-step ergonomic interviews before generating variants. Staged in `docs/.working/rfc-deep-taste-and-design-discovery.md`.

---

## 2. Future Backlog (`v0.2+`)
- [ ] **Live CortexGate MCP Two-Way Sync Adapter (`cgspec sync`):** Automatically sync local `docs/.memlog.md` entries and `docs/00..05-*.md` spines with CortexGate's MCP server, enforcing `Owner` and granular permissions (`read | invoke | propose_edit | write | share | admin`).
- [ ] **Automated Repo Linter (`uv run scripts/cgspec_lint.py`):** Verify `00-INDEX.md` links, check that `CLAUDE.md` stays a DRY 1-line pointer to `AGENTS.md`, and verify `.memlog.md` spine consistency.
- [ ] **Visual HTML Status Board (`cgspec board`):** Generate a self-contained HTML dashboard from `docs/00-INDEX.md` and `docs/.memlog.md` for non-technical stakeholders.
