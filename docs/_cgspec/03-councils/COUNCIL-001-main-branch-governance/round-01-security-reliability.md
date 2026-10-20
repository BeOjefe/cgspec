# Round 1 — Security & Reliability lens

**Debater:** Antigravity / Gemini 4 Argon High, account instance `antigravity_4` (jf27) — retry after the `antigravity` (jfe) instance exhausted its quota.

---

From a security and reliability standpoint, **client-side controls are advisory, not enforcement**. An unsupervised AI coding agent with `contents: write` push access operates in non-interactive shells, often in ephemeral worktrees or fresh clones, and will routinely bypass local guards—either accidentally (uninitialized hooks) or deliberately (`git push --no-verify`, direct GitHub REST/GraphQL API commits, or `gh pr merge --admin`) when trying to resolve a task loop. True prevention requires **server-side ref-update rejection** before `main` moves.

### Ranked Recommendations

#### 1. Server-Side Repository Rulesets (with `Do not allow bypassing`) via Existing Org/Enterprise Entitlement or GitHub Pro
* **Mechanism:** Unlock native server-side Rulesets on `main` (requiring a PR, blocking force-pushes, and—critically—removing the owner/admin from the Ruleset **Bypass list** so PATs/credentials inherited by an AI agent cannot override the rule).
* **How to unlock & Cost:**
  * **1a. Existing Paid Org/Enterprise ($0 incremental if already paid):** Verify whether `mrojefe` or `BeOjefe` already belongs to a paid GitHub Team/Enterprise organization ($4–$21/user/mo paid by the org). Note: moving to a *Free* organization does **not** help—GitHub Free organizations have the exact same private-repo ruleset restriction as personal Free accounts.
  * **1b. Upgrade to GitHub Pro (~$4/mo incurred by repo owner):** Unlocks Rulesets while keeping the repo private.
* **Failure mode:** Fail-closed at GitHub's Git receive-pack / API layer. Even an admin token held by an AI agent is rejected unless someone manually edits the Ruleset UI/API (`administration: write`). To prevent an agent from disabling the ruleset itself, strip `administration: write` from the agent's fine-grained PAT.

#### 2. Fork-and-PR Credential Isolation (Free, True Prevention for Agents)
* **Mechanism:** If staying on GitHub Free + Private ($0/mo), revoke direct `contents: write` access on `BeOjefe/cgspec` from the AI agent's token and local `origin` push URL (`git remote set-url --push origin no_push`). Give the agent push access only to a separate private fork or isolated staging repo, and require human-triggered PR merges into upstream `main`.
* **Bypass & Failure mode:** True server-side IAM prevention against the agent, though a human using admin credentials could still accidentally push if their local remote isn't locked.

#### 3. Local `pre-push` Hook + GitHub Actions Auto-Revert Watchdog (Free, Defense-in-Depth Fallback)
* **Mechanism:** Combine a versioned `.githooks/pre-push` script (prevents accidental human/agent `git push origin main`) with a GitHub Actions workflow on `push: branches: [main]` that inspects whether the commit parent/associated PR is valid and **automatically resets `main` or opens a revert** if a direct push landed ($0/mo within Free 2,000 Action minutes/mo).
* **Bypass & Silent Failure Risk:** **High.** Local hooks fail silently whenever `core.hooksPath` isn't configured in a new clone/worktree or `--no-verify` is passed. Post-push CI checks are **detectors, not preventers**: if Actions minutes run out, workflows are disabled, or a race occurs, direct commits remain on `main` silently. `CODEOWNERS` alone does nothing without branch protection (completely inert on Free private repos).

#### 4. Make Repository Public ($0/mo — Not Recommended for Security)
* **Why last:** Trading source/spec confidentiality and permanent public git history exposure to save $4/mo is an unacceptable security trade-off unless the project is intentionally open-source.

### Note on Merge Method (Lens Opinion Only)
Security & reliability favors **Squash merge** or **Merge commit (`--no-ff`)** over rebase-and-merge: merge commits preserve cryptographic parent lineage proving a PR merge occurred, while squash merges guarantee every commit on `main` maps 1:1 to an audited PR and green CI state.

### Sources & Currency Notes
* **GitHub Docs — About protected branches & About rulesets:** `https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches` and `.../managing-rulesets/about-rulesets` (states branch protection and rulesets are available in public repos and in private repos on GitHub Pro, Team, and Enterprise).
* **GitHub Plans / Pricing:** `https://github.com/pricing` and `https://docs.github.com/en/get-started/learning-about-github/githubs-plans` (*Currency note: Pro is historically $4/month USD; verify current localized pricing before billing changes*).
