# ADR-006: Branch governance for `main` on `BeOjefe/cgspec`
Created: unknown · Last edited: 2026-10-20T17:54:17Z

- **Status:** Accepted
- **Date:** 2026-10-20
- **Council:** [COUNCIL-001-main-branch-governance](../_cgspec/03-councils/COUNCIL-001-main-branch-governance/) — 3 lenses (simplicity & cost, security & reliability, scale & maintainability) across 3 distinct model families, supervisor synthesis, independent final-challenge review.
- **Context:** `github.com:BeOjefe/cgspec` is private, owned by the `BeOjefe` organization (free plan, 0 paid seats), default branch `main`. Both classic branch protection and repository rulesets return `403: Upgrade to GitHub Pro or make this repository public` for this repo. The user wants direct pushes to `main` disallowed — changes land only through a pull request and merge — enforced against careless humans and against an unsupervised AI coding agent that holds push credentials and may try to bypass a guard to resolve a task loop.

## Decision (user-approved)

The user chose the **free path** over paying ~$4/mo for GitHub Team (which would have unlocked native server-side Rulesets), **no human approval gate** on PRs (the agent and the user currently share one GitHub identity, so a required-approval rule would have locked the user out of their own PRs too — see round-03 of the council), and **squash merge** as the only allowed merge method.

### Implemented now (this PR)

1. **Repo setting:** `BeOjefe/cgspec` is set to squash-merge only (`allow_squash_merge=true`, `allow_merge_commit=false`, `allow_rebase_merge=false`). Applied directly via the GitHub API; reversible any time.
2. **Deterministic CI detector** (`.github/workflows/main-branch-governance.yml`): on every push to `main`, checks each new commit against the GitHub API (`commits/{sha}/pulls`) for an associated PR merged into `main`. Fails loudly, with the offending commit SHA, if a commit bypassed the PR process. This works under squash merges (a squash commit has one parent, so parent-inspection alone cannot tell a squash-merged PR apart from a direct push — the API call is required).
3. **Local pre-push guard** (`.git/hooks/pre-push`, installed in both local clones, not committed — it's machine-local by design): blocks `git push origin main` from this machine by default. Documented explicitly as non-authoritative: bypassable with `CGSPEC_ALLOW_MAIN_PUSH=1`, `--no-verify`, a fresh clone without the hook, or a push via the GitHub API/web UI. This is defense-in-depth, not the real control.

### Still needs the user's own action (can't be done on their behalf)

**Credential isolation** — the actual free mechanism that gives true prevention against the agent, not just detection: create a separate bot/machine GitHub account, add it to `BeOjefe` with the org's Read role (free; a personal-repo collaborator can't be read-only, but an org member can), have that account fork `BeOjefe/cgspec`, and route the agent's day-to-day push access through that fork instead of the upstream repo directly. Until this is done, the agent (and anyone else with the current credentials) can still technically push straight to `main` on GitHub's side — only the local pre-push hook and the after-the-fact CI detector stand in the way, and both are explicitly non-authoritative. This ADR is marked Accepted for the mechanism and defaults; the credential-isolation step is the one piece of the accepted design not yet in place.

**Rejected:**
- Paying for GitHub Team/Pro or making the repo public — superseded by the user's explicit choice of the free path; public repo stays rejected on reversibility grounds regardless (a one-way door for $4/mo of savings).
- "Feature-branch-only token" — not real; GitHub PATs don't scope by branch. Fork-based isolation is the real free mechanism, noted above.
- Local pre-push hooks or CI-only post-push detection as the *primary* control — kept as defense-in-depth (see "implemented now" above), but neither is the actual boundary; both are silently bypassable.

## Reversibility and cost

- Squash-merge-only repo setting: trivially reversible via the GitHub API or UI at any time.
- CI workflow + local pre-push hook: $0, reversible by deleting the files; the local hook is already uncommitted/machine-local.
- Fork-based credential isolation (pending): $0 ongoing once set up, but real one-time setup cost (bot account, fork, sync) and ongoing fork-sync maintenance as a cost in time rather than money.
- Making the repo public: one-way door. Rejected.

## Fitness check (how we'll know this is actually working)

- Every commit on `main`, going forward, has a corresponding entry in the CI workflow's run log showing which merged PR it came from.
- Once credential isolation is in place: the agent's working token/remote cannot push to `BeOjefe/cgspec` directly, only to its own fork.
- Until then: a direct push to `main` from this machine is caught locally by the pre-push hook, and if that's bypassed, by the CI workflow after the fact — when the local hook or unchanged workflow actually runs. The same writer can alter or remove that workflow, so it is not an independent security boundary.

## Consequences

- No recurring cost. Real-time prevention is not yet in place for anyone with the current push credentials; what exists today is a local best-effort guard plus an after-the-fact, GitHub-API-backed detector that cannot be fooled by squash merges' single-parent history.
- The gap can close only after effective credential isolation is verified: a bot/fork alone does not suffice while the agent shell can still use owner GitHub logins or SSH credentials. Private-fork policy and the complete PR/merge flow also need rehearsal. The user performs the account setup.
- `main`'s merge button now only offers squash, matching the chosen default.
