# Round 3 — Independent final-challenge review

**Reviewer:** Antigravity / Gemini 4 Argon High, account instance `antigravity_4` (jf27). Did not debate a lens and did not write the synthesis in round-02.

---

# Final-Challenge Review: COUNCIL-001 (`main` Branch Governance)

**Role:** Independent Final-Challenge Reviewer (`cgspec-council`)
**Scope:** Desk review only. No GitHub API, billing, or repository settings were touched.

## 1. Source Quality & Plan/Pricing Accuracy

### Critical flaw: Personal GitHub Pro does not cover an org-owned repo
The supervisor established `BeOjefe` is a GitHub Organization on the Free plan, yet the round-02 Proposed ADR recommended "GitHub Pro on the `mrojefe` personal account." **This will not work as written** — GitHub billing/entitlements are scoped to the account that owns the repo. Two real paid paths exist:
1. Upgrade the `BeOjefe` organization to **GitHub Team** (~$4/seat/mo — only ~$4/mo total if `mrojefe` is the sole member).
2. Transfer `BeOjefe/cgspec` to the `mrojefe` personal account and upgrade that account to Pro.

### Critical flaw: "feature-branch-only token" does not exist on GitHub
Neither classic nor fine-grained PATs scope at the branch level — only at the repository level. A token that can push a feature branch can push to `main` too, absent a ruleset. Free credential isolation requires a fork (or an external broker), not a scoped token.

### What holds up
Feature gating (Pro/Team/Enterprise required for private-repo rulesets, free on public repos) is accurate. ~$4/mo Pro and ~$4/user/mo Team reflect long-standing list prices but were not verified live against the billing UI this session.

## 2. Assumptions challenge

- **Internal contradiction:** round-02 claims "only server-side Rulesets give true prevention, everything else is a detector," then separately credits credential isolation with "true prevention against the agent, $0." Both are real server-side prevention primitives: ref-level policy (Rulesets, paid) and repo-level IAM (giving a bot account the Read role + its own fork — free, and actually available here *because* `BeOjefe` is an org; personal-repo collaborators always get Write).
- **Missed option:** a local credential broker — move the GitHub token out of the agent's readable environment into a wrapper owned by a separate OS user that proxies `git`/`gh` and rejects ref-updates to `main` or `--admin` flags. Free, heavier to build, no GitHub-side dependency.
- **Broken technical detail:** a squash merge produces a single-parent commit, indistinguishable from a direct push by inspecting git parents alone. Any CI/audit check paired with squash-merge-as-default must call the GitHub API (`GET /repos/{owner}/{repo}/commits/{sha}/pulls`), not read commit parents.

## 3. Threat model challenge

- **Gap 1 — ruleset is self-deletable:** an agent holding an admin-scoped token can `DELETE` or edit the ruleset via the API, push, then restore it. The security lens explicitly flagged stripping `administration: write` from the agent's token; round-02's Proposed ADR dropped this as a hard requirement.
- **Gap 2 — same-identity approval deadlock:** the agent and the human share the GitHub identity `mrojefe` today. With Required Approvals = 0, the agent can self-merge any PR after CI passes with no human gate. With Required Approvals = 1 and no bypass, GitHub won't let `mrojefe` approve `mrojefe`'s own PR — the human gets locked out too, unless the agent operates through a separate bot account.

## 4. Reversibility challenge

- Making the repo public: confirmed one-way door, not worth it to save $4/mo.
- Personal Pro requires transferring the repo out of `BeOjefe` — real churn (URLs, org secrets/webhooks, collaborator roles). **GitHub Team on `BeOjefe` reaches the same $4/mo outcome with a clean two-way door** (cancel anytime, nothing to transfer back).

## Verdict

The recommended architecture (server-side Rulesets as primary, credential isolation as the free alternative) survives in principle, but the Proposed ADR needs four corrections before it goes to the user: billing target (Team on `BeOjefe`, not personal Pro), token down-scoping as a hard requirement (not a note), an explicit decision on the self-approval deadlock, and dropping "feature-branch-only token" + fixing the squash-merge CI check to use the GitHub API.
