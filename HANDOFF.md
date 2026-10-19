# Handoff: CGSpec v2 rebuild (for Codex or any next agent)

**2026-10-19 current continuation:** this original Claude handoff is historical. Read [`../cgspec-audit-2026-10-18/18-CGSPEC-CLAUDE-HANDOFF-2026-10-19.md`](../cgspec-audit-2026-10-18/18-CGSPEC-CLAUDE-HANDOFF-2026-10-19.md) first for the current candidate HEAD, 315-test result, visible document dates, CortexGate dry-run gaps, and remaining work. Then read `docs/METHOD-v2.md` and `engine/FORMATS.md`.

Date: 2026-10-19. Previous owner: Claude (claude.ai session). Read this first, then
`docs/METHOD-v2.md` (the spec, source of truth) and `engine/FORMATS.md` (file formats and hook contract).

## Where things are

| What | Where |
| --- | --- |
| Spec (canonical, live doc) | Claude Doc "CGSpec Method v2 - Specification" (rev 48); repo copy `docs/METHOD-v2.md` is identical (sha256 9d2e5a96...) |
| Code | this repo `~/Documents/Project/cgspec-next`, branch `method-v2` (branched from `method-v1` = live cgspec 716306b) |
| Audit dossier, history, reviews | `~/Documents/Project/cgspec-audit-2026-10-18/` (09-RESUME-STATE.md is the running log; 10-13 are re-audit, reviews, research) |
| Live repos | `~/Documents/Project/cgspec` and `~/Documents/Project/cortexgate`: NOT touched. Do not edit them until step 5 of the plan. |

## What is built (spec build step 2: engine + enforcement)

Stdlib-only Python >= 3.10, no dependencies. Run all tests from the repo root:

    python3 -m unittest discover -s tests -t .     # 248 tests, about 50 s, needs git and ssh-keygen

| File | Does |
| --- | --- |
| `engine/install.py` | install / upgrade / verify / uninstall. Copies templates + a vendored engine with a hash manifest into `docs/_cgspec/01-engine/`, no symlinks, idempotent, archives and restores replaced AGENTS.md/CLAUDE.md, uninstall removes only untouched template files, refuses downgrades, wires adapters. |
| `engine/doctor.py` (+ `_lib/doctor_checks.py`, `doctor_layout.py`, `mdlinks.py`) | Checks a project against spec section 2: layout, schemas, empty spines (>=12 real words), links, record names/IDs/statuses, index both ways, frozen hashes, unlisted snapshots, unregistered scripts, engine integrity, ledger. Read-only unless `--fix`. |
| `engine/memlog.py` | Only writer of `docs/_memlog.md`: IDs `M-YYYYMMDD-xxxx`, OS file lock, no forged lines, Approved needs `--approval-ref`. |
| `engine/cgspec_hook.py` | One entry for all hooks: `tier set/show/clear`, `pre-tool`, `pre-commit`, `commit-msg`, `ci --base --release-dir`, `user-message`, `session-start`, `session-check`, `pre-compact`, `stop`. Exit 0 allow, 1 fail, 2 block, 3 internal error. Antigravity answers with JSON `{"decision": ...}`. |
| `_lib/gates.py`, `shellparse*.py` | Write gate for edit tools and shell commands (best effort by design). |
| `_lib/commit_gate.py`, `commit_trust.py`, `gitview.py`, `ci_gate.py` | Commit and CI rules: tiers, slice scope, append-only manifests, engine = plugin release, approvals (fresh, single-use, from the inbox or a signed trailer), failing-test proofs re-run at old and new commit. |
| `_lib/inbox.py`, `session.py`, `tiers.py`, `adapters.py` | Inbox + secret scrubbing + approvals; session pack and stop gate; tier rules; wiring for Claude Code, Antigravity, git hooks, GitHub Actions, Cursor. |
| `engine/schemas/*.json` | JSON Schemas for every state file. |
| `templates/` | base, gui, polyrepo-governance overlays. |
| `engine/CONTRACT.md` | DRAFT, 7 lines; finish in step 3. |

## Review status

Independent adversarial reviews (a separate agent, not the author) were run after every change:
engine round 1 NOT READY (17) -> fixed -> READY WITH FIXES -> fixed; enforcement round 1 NOT READY
(2 blockers) -> fixed; round 2 NOT READY (approval reuse, agent-written trailer, select-script
fallback, unbound test command) -> fixed in 9e6be76..e13a009. Final re-check of e13a009:
READY WITH FIXES. Four open items, do these first (tests first):

1. Approvals: an unrelated "yes"/"ok go" that names no record can be spent on any record in the
   same commit (e.g. approve `Scope: **` or a weak `test_command`). Fix: accept an approval only
   when the user's words name the record ("approve SLICE-004" / "approve test command"), or when
   the hook bound it to a pending approval request shown to the user.
2. Trailer: `approver_keys` is read from the commit being judged, so the agent can add its own key
   in the same commit. Fix: read `approver_keys` from the base commit; a change to it needs the
   user's signature or GitHub review.
3. Select script (`engine/_lib/adapters.py` workflow): still runs the commit's own copy when the
   fetch fails (`|| true`) and on a force push to the default branch. Fix: fail closed in both.
4. Spec section 8 "what remains possible" must also list (1) and (2) until they are closed, and say
   plainly that the guarantee holds only with the GitHub review rule on.
Low: `find -iname '*.JSON' -delete` slips past the tool hook (best effort; commit hook/CI still check).

## Decisions the user made (do not reopen without asking)

- Default review: scripts + 1 reviewer from a different model; full team review only on demand (skill `cgspec-team-review`) or automatically at T3.
- Design: AI brings references first (up to 6, contrasting); may propose an existing design system only if enforceable (spec 6b).
- Layers 0-4 are a throwaway grey prototype; from layer 5 the design is built in the real frontend (spec 6, decided 2026-10-18).
- Max testing, debated architecture (spec 7b). Token rules 25/15/5% (5-hour) and 10% weekly: below 10% weekly, no auto wake-up, wait for the user.
- CortexGate is optional, never required.

## Known limits (written in the spec)

- On the user's own machine an agent with shell access can forge an approval plus its inbox line in one change; GitHub branch protection + required review on `.github/`, `docs/_cgspec/`, `docs/slices/` closes it (install prints the steps).
- Antigravity hooks get no user message: no inbox/approval capture there.
- Spine word count can be beaten by filler prose; the layer-3 reviewer judges content.
- The tool hook's shell parsing is best effort; commit hook + CI are the guarantee.

## Next steps (spec section 14 plan)

1. Independent re-review of 9e6be76..e13a009; fix findings.
2. Built since this note was written: `post-tool` hook, `bundle_prototype.py`, `visual_audit.py`, `journey.py`, `impact.py`, check registration (`cgspec_hook.py check`), `cgspec_hook.py checkpoint`. See `cgspec-audit-2026-10-18/19-*.md` for the current state.
3. Publish: tag the plugin repo (`mrojefe/cgspec`) `v2.0.0`; CI in projects downloads that release.
4. Step 3: the 9 skills (`skills/<name>/SKILL.md`) and the short contract; roles in `agents/`. Remove the old v1 `skills/`, `agents/`, `cgspec_template/` once replaced.
5. Step 4: rehearse install/upgrade on a COPY of CortexGate. Step 5: upgrade real CortexGate. Step 6: fresh CortexGate session. Step 7: periodic check-ins. Step 8: pilot vs one careful agent.

## Working rules used so far

- Tests first for every change; for key rules, revert the fix once and confirm a test fails.
- Commit identity: reuse the repo's last author (`git -c user.name=... -c user.email=...`); never change git config.
- Keep files <= 400 lines, functions <= 60 (enforced by `tests/unit/test_code_rules.py`).
- Update `docs/METHOD-v2.md` and the live doc together when behavior changes; log progress in `cgspec-audit-2026-10-18/09-RESUME-STATE.md`.
