# COUNCIL-001 — Outcome

**Lenses:** simplicity & cost (Claude Opus 5.5 / claude_jfe), security & reliability (Gemini 4 Argon High / antigravity_4), scale & maintainability (OpenCode Big Pickle). **Supervisor:** Claude Sonnet 5 (this session), synthesized, did not debate. **Independent final-challenge reviewer:** Gemini 4 Argon High / antigravity_4 — a second, separate delegated run, not the debater run; it did not author the synthesis.

Four distinct model families were used across the council (Claude, Gemini, an OpenCode-hosted model, plus Claude again as supervisor in a non-debating role) — not PARTIAL.

## What changed between round-02 and this outcome

The independent reviewer (round-03) found the round-02 synthesis had two factual errors and two unaddressed threat-model gaps. All four are corrected below; nothing in this outcome should be read without round-03's challenge, since it drives most of the correction.

1. **Billing target corrected.** `cgspec` is owned by the `BeOjefe` *organization*, not personal account `mrojefe`. Personal GitHub Pro does not unlock Rulesets on an org-owned repo. The paid path is **GitHub Team on the `BeOjefe` org** (~$4/mo if `mrojefe` is the only member) — not Pro, and not a repo transfer.
2. **"Feature-branch-only token" dropped.** GitHub PATs don't scope by branch. Free credential isolation for an agent means a fork + a bot account with the org's Read role, or a non-GitHub local credential broker — not a scoped token on the same repo.
3. **Token down-scoping is now a hard requirement, not a note.** If Team/Rulesets is adopted, the ruleset only holds if the agent's day-to-day token does **not** carry `administration: write` — otherwise it can delete or edit the ruleset itself via the API and push anyway.
4. **Self-approval deadlock surfaced — this is a decision for the user, not the council.** The agent and the human currently share one GitHub identity (`mrojefe`). If the ruleset requires 1 approval, GitHub won't let `mrojefe` approve `mrojefe`'s own PR, and with no bypass that locks the human out too. The choice is: (a) Required Approvals = 0, gate on CI status checks only, no human-review gate; or (b) give the agent a separate bot GitHub account so you can review and approve its PRs as yourself. This needs your call before setup.

## Where all three lenses and the reviewer agree

- Making the repo public to dodge the billing gate: rejected by every lens and the reviewer. One-way door, not worth $4/mo.
- Local pre-push hooks and CI-only post-push checks: real as defense-in-depth, but not sufficient alone — bypassable by `--no-verify`, a fresh clone, or direct API calls; they detect, they don't block.
- If a squash merge is used as the PR merge method, any CI/audit check verifying "did this land via a PR" must call the GitHub API (`commits/{sha}/pulls`), not inspect git commit parents — squash merges are single-parent, so parent inspection can't tell a squash-merged PR apart from a direct push.

## Proposed ADR — now Accepted

See [ADR-006: Branch governance for `main` on `BeOjefe/cgspec`](../../adr/ADR-006-main-branch-governance.md). The user chose the free path, no human approval gate, and squash merge. `BeOjefe/cgspec` is now set to squash-merge only, a deterministic CI detector and a local pre-push guard are in place; the fork-based credential isolation that gives true prevention against the agent is still the user's own action to complete.
