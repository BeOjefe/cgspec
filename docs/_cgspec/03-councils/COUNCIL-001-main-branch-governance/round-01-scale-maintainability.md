# Round 1 — Scale & Maintainability lens

**Debater:** OpenCode / Big Pickle (opencode/big-pickle)

---

**Lens:** Scale & Maintainability

### Ranked Recommendation

#### 1) CI-based post-push detection (detection-first, centralized)
- **Why it scales:** Enforcement lives in CI, not on every developer/agent's machine. As the number of human or AI contributors grows, every new clone and every unsupervised agent inherits the same check automatically. There's no per-environment bootstrap to maintain.
- **Maintainability:** Rules can be updated in one place, alerted on, and can feed into merge workflows.
- **Caveat:** This *only detects* direct pushes to `main` after the fact, it does not prevent them. For a governance rule, this must be treated as a compensating control with alerting/escalation, and you must be explicit about that (per the brief's criteria).

#### 2) Check for an existing Org/Team/Enterprise billing path
- **Why:** If `mrojefe` can move this repo under an existing org with Team/Enterprise entitlements, native branch protection/rulesets could become available without a personal Pro upgrade. This is highly scalable (policy managed at org level) and billable to an entity that may already be paying.
- **Caveat:** Token scopes hint at `admin:org`/`admin:enterprise` but `gh api user` showed no plan data, so this is *uncertain*. It is also a membership/billing change that requires user approval (do not execute).

#### 3) GitHub Pro upgrade (native prevention)
- **Why:** If neither #1 nor #2 is viable, classic branch protection would give true prevention that scales cleanly.
- **Caveat:** Recurring ~$4/mo personal cost, couples governance to an individual subscription, and still requires configuration per repo. I wouldn't call this the most "scale-agnostic" choice, but it is maintainable once enabled.

### Not Recommended (for scale/maintainability)

- **Local pre-push hooks:** Bypassable with `--no-verify`, require setup on every clone, and are trivial for an unsupervised AI agent to ignore. Maintenance burden grows linearly with contributors and environments.
- **Making the repo public:** Changes visibility permanently, has non-technical consequences, and shouldn't be used as a billing workaround.
- **CODEOWNERS alone:** Blocked by the same plan gate and provides no enforcement without branch protection/rulesets.

**Notes on merge method:** From a maintainability lens, enforcement mechanism matters far more than merge style. A consistent, reviewable history is easier to audit with centralized controls regardless of merge commit/squash/rebase, so I won't pick one here.

**Sources (flagged for currency):**
- GitHub Docs - *About protected branches* (availability varies by plan; Free private cannot use classic branch protection in many org/personal contexts) — *verify current matrix*
- GitHub Docs - *About rulesets* (plan-gated for private repos in current offerings) — *verify current matrix*
- GitHub Pricing (github.com/pricing) — plan names/features change over time, treat as a point-in-time check.

**Overall verdict:** Prioritize **(1) CI detection-first** now (works within Free private constraints), while **(2) verifying an existing org billing path** in parallel. Only fall back to **(3) Pro** if centralized policy is required and no shared billing exists. This best keeps governance working as contributors (human or agent) multiply.
