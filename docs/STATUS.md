# CGSpec v0.2 implementation status
Created: 2026-10-20T17:46:07Z · Last edited: 2026-10-21T21:25:05Z

This is the current status reference. The method describes required behavior; this page identifies limits of its implementation. Historical audit results are tied to their source revision and do not automatically apply to later changes.

## One development stream

The merged source lives in the `BeOjefe/cgspec` repository. In the current workspace, develop in `/home/ojefe/Documents/Project/cgspec` on feature branches and use PRs for main. `cgspec-next` is a duplicate checkout retained for old references; do not start a separate implementation there. Before removing or repointing it, inspect local refs, archive tags and host/plugin/lab references. A single Git history does not automatically update installed plugins or consumer engines.

The source tree is a plugin package, not an installed consumer layout. Run the package tests and plugin validation here. Run doctor, hooks and upgrade rehearsals in disposable consumer projects; do not force-install over the source tree. Consumer changes, including CortexGate upgrades, need their own authorized scope.

## Implemented and bounded

- Nine workflow skills, one pivot compatibility alias and eight role definitions are packaged with the engine. Their presence does not prove every host loads or follows them.
- Installer, updater, v0.1 adoption, doctor, ledger, hooks, ingestion, impact map, prototype bundling, browser journeys and visual audit have source tests. Test results must cite a revision, environment and skipped checks.
- Prototype HTML, styles, scripts and configuration now participate in pre-tool and commit/CI scope checks; ordinary Markdown notes remain exempt from code-tier requirements. Live prototype sources participate in test-pair checks. Merged through PR #7 at d470e35 after independent jf27 Argon review; both Python versions ran 430 tests with six browser-dependent skips. Existing consumer installations require a separate upgrade; these checks are process gates, not a browser security boundary.
- Checkpoint recovery merged through PR #8 at 4eb6948 after independent review: validated updates, bounded worktree observations, richer session packs and durable unresolved-stop diagnostics. Task reservations/receipts and cross-run writer exclusion remain unimplemented. No consumer update is implied.
- Design collaboration guidance (Package E, guidance part): the contract requires the agent to push back when the user rushes to build, approves unread or skips definition, architecture or environment setup, and to record overrides as accepted risks. The design skill classifies a request by its effect, chooses the artifact by the open question, keeps a per-screen data inventory against the object model, records user and delegated decisions for recovery, and compares 2-3 mechanism-level variations only when a direction choice is open. Behavior coverage requires named states and repeated, stale and version-bound decision cases, labelled Executed or Specified. Text guards cover these rules; no agent trial has yet shown that agents follow them.
- `quota.py --root <project> [--json]` reads an existing quota file. Session packs use the same evaluator. Missing, malformed, future, older-than-five-minute and reset-window readings cannot be presented as current full quota. At 25% remaining the advice is frugal work; at 15% finish an atomic unit, checkpoint and pause; at 5% only save logs/state without new code. The ladder uses the lowest valid remaining window conservatively. Weekly quota at 10% or less blocks automatic wake-up advice; missing weekly data leaves that advice unknown. This is agent guidance, not a hard task gate, provider telemetry collector or scheduler.
- Model-fit advice, reference-led design, IMAGE-WORD alignment, exact media-prompt relay and independent architecture challenges are workflow requirements. They are not automatic routing or proof of design quality.
- This repository's squash-only merge setting, local main-push guard and post-push PR-origin workflow are in place. They do not prevent direct upstream pushes with the current owner credentials. See [ADR-006](adr/ADR-006-main-branch-governance.md).

## Release and adoption blockers

1. Publish and inspect the pinned `v0.2.0` release, complete the trusted installation bootstrap, and rehearse the installed CI path on a repository with the required server-side protection. This package's main-origin detector is a different workflow.
2. Establish effective credential isolation or appropriate server-side protection before promising PR-only enforcement. A bot/fork is insufficient if the agent's shell can still use owner credentials. The accepted free/squash preference remains in force; private-fork permissions and the end-to-end merge flow still need validation.
3. Build and test host quota collectors where real telemetry exists. Current schema sources are Claude statusline, manual and unavailable; Codex/Antigravity automatic adapters and context-pressure integration are absent. Never infer quota from model names, turn count or context size.
4. Close existing-project adoption findings through generic fixtures and an authorized copy rehearsal. Clean installation does not establish safe migration or multi-repository coverage.
5. Complete uncontaminated agent-driven design trials, desktop/phone interactions and blind visual judging. Native mobile/device behavior and cross-provider media integration require separate evidence. No general token savings or visual-quality improvement is established.

Keep blockers visible until evidence closes them. Do not turn this list into a blanket readiness claim after a passing test run.
