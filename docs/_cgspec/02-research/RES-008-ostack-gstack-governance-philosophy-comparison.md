# RES-008: ostack/gstack — A Governance-Philosophy Comparison, Not a Feature Gap

Created: 2026-10-30T00:00:00Z · Last edited: 2026-10-30T00:00:00Z

- **Status:** `[Concluded]`
- **Date:** 2026-10-30
- **Authors:** `@jeanfranck`, research agent
- **Source:** `https://github.com/mr-daedalium/ostack-saas` (public, fork of Garry Tan's `gstack`) — README.md, ARCHITECTURE.md, ETHOS.md, CLAUDE.md, AGENTS.md, and the `autoplan`, `careful`, `freeze`, `canary`, `conductor.json` subdirectories/files read directly from the repo.
- **Licence:** Public repository; no code copied. Comparison only.
- **Trigger:** The user pointed at this repo mid-session, prompted by CGSpec's own hook-enforcement gaps found the same day (see the fake-approval and silent-hook-failure findings fixed as `BeOjefe/cgspec#55`, `#56`, `#57`), asking whether ostack's approach was "not really far from us."

---

## 1. Summary and verdict

It is close in *target* (both want an AI agent to behave like a disciplined engineer instead of a confident improviser) and far apart in *philosophy* (whether approval friction is the mitigation or the risk). ostack is **not** a feature-gap benchmark the way RES-007's hook survey was — adopting its pieces wholesale would contradict CGSpec's core premise. One specific mechanism is worth adapting regardless: post-ship continuous monitoring, which CGSpec does not have at all today.

## 2. What ostack actually is

ostack (fork of gstack) turns Claude Code into a simulated engineering org for a solo founder: slash-command personas — CEO, Eng Manager, Designer, Staff Engineer, QA Lead, Security Officer, Release Engineer — walk a plan through Think → Plan → Build → Review → Test → Ship → Reflect. It is **not** real multi-agent orchestration: each persona is a `SKILL.md` prompt scaffold invoked as a slash command, one agent swapping context by instruction, not separate processes.

Its `ETHOS.md` states the philosophy explicitly: a "holding company of one," speed and conviction over caution, "being wrong fast and often is how you converge," and — the load-bearing line — process gates and approval dogma are named as "the enemy." `/autoplan`'s own documentation says plainly that **no hooks or scripts enforce its plan**; it auto-decides on the user's behalf through six heuristics and leaves exactly one `AskUserQuestion` touchpoint (premise confirmation) before proceeding. `/plan-eng-review` stops per-issue but has no sign-off gate and does not block shipping.

The one place ostack *does* do real tool-level enforcement, the kind CGSpec relies on throughout — is `/careful` and `/freeze`: genuine `PreToolUse` hooks (`check-careful.sh`, `check-freeze.sh`) intercepting `Bash`/`Edit`/`Write` and returning `ask` or `deny`. But it is scoped narrowly to destructive commands or a frozen directory, never to approval of *what's being built*. `conductor.json` turned out to be unrelated (npm script aliases, not a governance file). `canary` is a post-deploy screenshot/console/perf monitor, not a pre-change gate.

## 3. Where the two agree

Both target "looks done but isn't": ostack via its QA/staff-engineer persona review and canary's persistent diffing; CGSpec via `verify.py`/doctor as a pre-claim gate that exits non-zero on anything FAILED or BLOCKED. Both structure handoffs between roles/phases instead of one undifferentiated agent pass. And tellingly, both land on exactly **one** layer of genuine tool-level enforcement in an otherwise prompt-driven system — ostack's freeze/careful hooks, CGSpec's tier/capability/approval hooks — which is independent confirmation of something CGSpec already assumes: a hook that intercepts the tool call is the only reliably unbypassable gate; everything else is advisory text an agent can choose to follow or not. (CGSpec's own `#55`/`#56`/`#57` findings this same day are a reminder that even a hook-based gate is only as strong as its weakest unguarded entry point — `cgspec_hook.py user-message` invoked directly, or a session where the hook config never loaded at all.)

## 4. Where they genuinely diverge — and why it matters

This is the real finding, not a feature-parity gap. CGSpec's premise is that implementation must wait on **genuine, captured human approval** of a slice's success definition, enforced broadly across substantive work (CONTRACT.md point 3). ostack's ETHOS is the *inverse* claim: approval chains are themselves the risk, not the mitigation — "when the full implementation costs minutes more than the shortcut, do the full thing, every time" stands in for sign-off, and `/autoplan` operationalizes minimizing human questions as a design goal.

Neither is simply wrong. ostack is optimized for a solo founder iterating fast on low-stakes surface area, where re-litigating every decision with a human (who may be the only human) is pure friction. CGSpec is optimized for situations — like CortexGate's v0.1, where a prior ad-hoc plan burned two weeks producing code that looked done and wasn't — where the thing approval friction prevents (a slice getting built against an unvalidated assumption, or a wrong fix getting merged) is more expensive than the friction itself. **The two tools are not competing solutions to the same problem; they encode different bets about which failure mode costs more for a given project.** CGSpec should not import ostack's low-friction default; a project could, in principle, declare that bet explicitly (e.g., a project-level setting trading approval breadth for speed on genuinely low-stakes slices) without touching the approval-capture mechanism's integrity itself — that would be a new, separate decision, not something this research note recommends.

## 5. What's actually worth adapting

**Canary's post-deploy drift monitoring**, specifically its "alert only if it persists across 2+ consecutive checks" debounce. CGSpec currently gates *before* a claim (`verify.py` passed, doctor clean) and stops there — it has no mechanism that keeps checking after the human has moved on to the next thing. A lightweight, canary-style post-ship check extending CGSpec's existing evidence model (PASS/FAIL/PARTIAL/BLOCKED, scoped and dated) into a recurring post-merge observation would close a real gap — "the thing we verified once might have silently regressed" — without touching the approval-capture core at all, and without importing any of ostack's low-friction-by-default philosophy.

## 6. What this is not

Not a recommendation to fork, embed, or install ostack. Not a claim that CGSpec's hook-enforcement gaps (found and fixed the same day as this note, `#55`–`#57`) are evidence CGSpec should loosen toward ostack's model — those were implementation bugs in CGSpec's own mechanism, not evidence the mechanism's premise is wrong. This spike is concluded with one adoptable idea (§5) and one named, deliberate non-adoption (§4), queued for a future decision if the user wants a project-level speed/approval trade-off, not decided here.
