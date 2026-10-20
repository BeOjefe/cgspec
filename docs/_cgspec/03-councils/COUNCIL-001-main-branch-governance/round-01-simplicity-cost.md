# Round 1 — Simplicity & Cost lens

**Debater:** Claude Opus 5.5, account instance `claude_jfe` — retry after the `codex`/gpt-6-astra debater hit its usage limit.

---

# Simplicity & cost lens: COUNCIL-001

I read the brief in full. I changed nothing and ran no commands against GitHub.

## Ranked recommendation

**1. Upgrade the personal account to GitHub Pro.** This is my top pick.
- **Cost:** about $4 a month or about $48 a year, paid by the account owner (`mrojefe`/`BeOjefe`).
- **Setup:** about 5 minutes. Turn on billing, then add one branch rule or ruleset on `main` with "require a pull request before merging" and "block force pushes".
- **Upkeep:** almost none. GitHub enforces the rule on its servers, so there are no scripts to maintain.
- **Against an agent:** it is the only option here that blocks the push itself, at no setup or upkeep cost. The rule must not exempt admins ("do not allow bypassing"), or a token with admin rights gets through.
- **Lowest cost per unit of real prevention.** It does add a monthly bill, so the user has to approve it.

**2. Free, layered stopgap. It only discourages and detects; it does not block.**
- **Agent permission rule:** add a deny entry in the agent's settings for `git push * main` and `git push --force*`. This takes about 2 minutes. A differently worded command or a different tool can get around it.
- **Local `pre-push` hook:** blocks pushes to `refs/heads/main`. `--no-verify`, a fresh clone, or the web UI skips it.
- **Actions alarm:** a workflow that runs on `push: main` and fails or opens an issue if the head commit has no linked PR (`GET /repos/{o}/{r}/commits/{sha}/pulls` returns empty). It finds the problem only after the push. Actions minutes on Free private repos are limited (2,000 a month, as I recall), and this job uses very little.
- **Cost:** $0. Setup is about an hour. Upkeep is low but real: hooks don't copy to new clones, so a setup script or `core.hooksPath` is needed.
- Use this only if the user turns down option 1, or as extra protection alongside it.

**3. Make the repo public.** It costs $0 and takes one click, but the brief's own criteria count it as a real consequence: all history, including any past secrets, becomes public. Making it private again doesn't undo copies already made. It's cheap to do but hard to reverse, so I rank it below a $4 bill.

**4. Move it into an organization.** A Free organization does **not** unlock protection for private repos; it has the same limit. GitHub Team costs about $4 per user per month, which is the same as Pro for one person and adds org admin work. Only worth it if the user already has a paid org. The `admin:org` scope on the token doesn't mean such an org exists.

**5. Read-only bot account plus a fork workflow, in a Free org.** This truly prevents the agent from pushing, at $0. The agent's machine account gets the Read role, works in its own fork, and opens PRs. It needs a Free org because collaborators on personal repos always get write access.
- **Cost:** the most setup (an extra account, a token for it, fork syncing) and ongoing friction.
- It only constrains the agent; the human owner can still push.
- I'd use it only if the user refuses every payment.

**Ruled out:** CODEOWNERS (does nothing without protection) and pre-receive hooks (GitHub Enterprise Server only, not github.com).

## On the merge method

My lens isn't deciding this; it's an observation only. Whichever method makes "this landed through a PR" easiest to check costs least to monitor. With option 2's API check, any method works.

## Sources (from memory, not fetched this session)

- GitHub Docs, "About protected branches" and "About rulesets": available for public repos on Free, and for private repos on Pro, Team and Enterprise. https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository
- GitHub pricing: https://github.com/pricing. Pro about $4/mo, Team about $4/user/mo. **Check that these prices are still current.**
- GitHub Docs, "Repository roles for an organization" (Read role) and "Permission levels for a personal account repository" (collaborators get write access).
- GitHub Docs, "About pre-receive hooks" (GitHub Enterprise Server only).
- REST API: "List pull requests associated with a commit".
- **Not certain it's current:** the Actions minutes quota for Free private repos.
