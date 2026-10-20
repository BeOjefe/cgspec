# COUNCIL-001: Enforcing PR-only governance on `main`

## Locked question

For `github.com:BeOjefe/cgspec` (private repo, GitHub Free plan, default branch `main`), how should we enforce "no direct pushes to `main` — changes land only through a pull request and merge" given that GitHub's native branch protection rules AND repository rulesets both return `403: Upgrade to GitHub Pro or make this repository public` on this repo?

Propose the mechanism(s) to enforce this rule, and separately recommend a default merge method (merge commit / squash / rebase) for when a PR lands, given the user is not deeply familiar with the trade-offs and wants a sensible default they can override.

## Context and stakes

- Verified facts (do not re-derive, just use): repo is private, `default_branch: main`, account `mrojefe`. `gh api repos/BeOjefe/cgspec/branches/main/protection` → 403 Pro-required. `gh api repos/BeOjefe/cgspec/rulesets` → same 403. Token scopes include `admin:org`, `admin:enterprise` but `gh api user` shows no `plan` field for this token (inconclusive on whether an org/Team plan is reachable).
- This is a **governance/process** decision, not a one-off code change: whatever we pick needs to keep working as the repo evolves, must not be trivially bypassable by a rushed future commit (including by an AI agent working unsupervised), and should not require an ongoing subscription cost the user didn't agree to.
- Candidate directions to evaluate (don't treat this list as exhaustive — the point of the lens is to find the real trade-offs, including options not listed here):
  1. Upgrade to GitHub Pro (~$4/mo) to unlock classic branch protection or rulesets.
  2. Make the repo public (removes the billing gate, but changes repo visibility — a real consequence, not just a technicality).
  3. Check if `mrojefe` has reachable org/enterprise access (token scopes suggest `admin:org`/`admin:enterprise`) where the repo could live under Team/Enterprise billing instead of the personal Free plan.
  4. Non-native enforcement: local `pre-push` hook (bypassable with `--no-verify` or a fresh clone — says so explicitly, don't oversell it), CI status check that fails if a commit lands directly on `main` without a merge commit from a PR (detects after the fact, doesn't prevent push), CODEOWNERS file (requires branch protection to actually gate anything, so blocked by the same 403).
  5. Anything else you find with real sourcing (GitHub docs, pricing page, changelog) that fits a private solo/small-team repo on a budget.

## Decision criteria

- Must actually prevent (not just detect) a direct push to `main` reaching the remote, OR be explicit in the proposal that it only detects after the fact if true prevention isn't achievable within constraints.
- Must not silently change repo visibility, billing, or org membership — any such change is a recommendation for the user to approve, never something to execute.
- Should state ongoing cost (one-time vs. monthly) and who incurs it.
- Should be realistic about being enforced against an AI coding agent with push access, not just a careless human.

## Lens assignment

- **Simplicity & cost lens** → weigh setup effort, ongoing cost, and maintenance burden of each option.
- **Security & reliability lens** → weigh how hard each option is to bypass (accidentally or by an agent), and what happens when it fails silently.
- **Scale & maintainability lens** → weigh what happens as more contributors (human or agent) touch this repo, and whether the mechanism keeps working then.

## Output format per debater

Return a short written proposal (plain markdown, no code execution needed — this is desk research, not a spike): your lens, your recommended option(s) ranked, why, and the sources you're drawing on (GitHub docs/pricing links, your own knowledge of GitHub's product tiers — flag anything you're not fully certain is current). 300-500 words is plenty. Do not pick a merge method on your own; that is reserved for the final recommendation to the user, but you may note if your lens has an opinion on it.
