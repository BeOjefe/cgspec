# Round 2 — Supervisor synthesis

**Supervisor:** Claude Sonnet 5 (this thread). Synthesizes; does not debate or approve.

## Verified fact added after round 1

`BeOjefe` (the org that owns `github.com:BeOjefe/cgspec`) is a **free-plan org** (`gh api orgs/BeOjefe` → `plan.name: "free"`, 0 paid seats). So the "maybe an existing paid org already covers this" branch all three debaters flagged as uncertain is now closed: there is no free ride. The real choice is between paying (~$4/mo, Pro on the personal account or Team on the org) or a free-but-weaker/more-complex workaround.

## Where the three lenses agree

1. **Only server-side Rulesets/branch protection give true prevention.** Everything else (local hooks, CI post-push checks, agent permission denylists) is a *detector*, not a *preventer* — it can only notice after a direct push already landed, and fails silently if the hook isn't installed, Actions minutes run out, or the agent uses `--no-verify` / the API directly.
2. **Making the repo public to dodge the billing gate is rejected by every lens.** Cost-wise it's "free," but it's a one-way door (history and any past secrets become public permanently) being used to save $4/month. Not proportionate.
3. **CODEOWNERS alone does nothing** without branch protection/rulesets already active underneath it — same 403 blocks it.
4. **If paying is acceptable, GitHub Pro (~$4/mo) is simplest and sufficient.** Enable it, add one ruleset on `main` ("require a pull request", "block force pushes", "do not allow bypassing" — critically, don't exempt admins/owner, or an AI agent holding an admin-scoped token walks straight through).

## Where they diverge, and how I resolve it

- The **security lens** surfaces a real free alternative the other two under-weighted: **credential isolation** — don't rely on blocking the push, remove the agent's ability to push to this repo's `main` at all (scope its token/remote to a fork or a separate branch, require a human-triggered PR into `BeOjefe/cgspec`'s `main`). This is genuinely preventive, not just a detector, and costs nothing — but the **simplicity lens** correctly ranks it last for *this* use case because of real ongoing friction (separate bot account, fork-sync upkeep, breaks the current single-repo workflow this agent already uses).
- My read: that trade-off (friction vs. $4/mo) is exactly the kind of call that's the user's to make, not mine to pick on their behalf. I'm presenting both, not collapsing to one.

## Proposed ADR (draft, pending independent review and user approval)

**Decision:** Enforce "PR + merge only on `main`" for `BeOjefe/cgspec` via **GitHub Rulesets**, unlocked by upgrading to **GitHub Pro on the `mrojefe` personal account (~$4/mo)**, with the ruleset's bypass list emptied (no admin exemption) so an agent holding an admin-scoped token still can't push directly. Layer a cheap, free `pre-push` hook + a CI "was this commit's parent a merged PR" check underneath as defense-in-depth — explicitly documented as non-authoritative, since the Ruleset is what actually blocks the push.

**Alternative (if the user doesn't want the $4/mo bill):** Credential isolation — revoke this agent's/this environment's direct push rights to `BeOjefe/cgspec`, route it through a fork or a dedicated feature-branch-only token, require a human (or an authorized CI identity) to actually land PRs into `main`. True prevention against the agent, $0, but more setup and ongoing fork-sync friction.

**Rejected:** making the repo public (irreversible exposure to save $4/mo); relying on local hooks or CI detection alone as the *primary* control (silently bypassable); moving to an org (the org is also free-plan, so it buys nothing extra over personal Pro at the same price).

**Merge method:** recommend **squash merge** as the default — one commit per PR on `main`, makes "did this land via a reviewed PR" trivial to audit (matches what any CI check above would look for), and is the easiest mental model for someone who isn't tracking the merge-commit-vs-rebase trade-offs closely. Offer merge-commit as the alternative if the user wants to preserve individual commits from a PR; recommend against rebase-merge for this repo since it rewrites history in a way that makes "which PR did this commit come through" harder to trace automatically. Final call stays with the user either way.
