# docs/00-INBOX.md — CGSpec (`cgspec`) Idea Parking Lot & Future Backlog

> **How This Works:** Any idea outside the active `v0.1` build is parked in one of 3 clear buckets (**Unsorted Sparks**, **Next Release `v0.2`**, or **Later `v0.3+`**) so not everything is forced into `v0.2`.

---

## 1. Unsorted Sparks (Just Captured — Triage Later)
- [ ] **Guided Design Discovery & Visual Reference Curator (`cgspec-ux` refoundation):** Transform UX skill from static prompt generation into a deep, guided dialogue. Post-OOUX ergonomics interrogation (direct manipulation, markdown editing mode), external visual reference hunting (proposing live exemplars like Linear, Cloudflare, Notion, Bear), and non-overwhelming micro-step ergonomic interviews before generating variants. Staged in `docs/.working/rfc-deep-taste-and-design-discovery.md`.

---

## 2. Next Release (v0.2 Candidates — Right After v0.1 Is Battle-Tested)

- [ ] **Live CortexGate MCP Two-Way Sync Adapter (`cgspec sync`):** Automatically sync local `docs/.memlog.md` entries and `docs/00..05-*.md` spines with CortexGate's MCP server, enforcing `Owner` and granular permissions (`read | invoke | propose_edit | write | share | admin`).
- [ ] **Automated Repo Linter (`uv run scripts/cgspec_lint.py`):** Verify `00-INDEX.md` links, check that `CLAUDE.md` stays a DRY 1-line pointer to `AGENTS.md`, and verify `.memlog.md` spine consistency.

---

## 3. Later / Future Horizon (`v0.3+`)

- [ ] **Visual HTML Status Board (`cgspec board`):** Generate a self-contained HTML dashboard from `docs/00-INDEX.md` and `docs/.memlog.md` for non-technical stakeholders.
