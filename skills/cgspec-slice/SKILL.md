---
name: cgspec-slice
description: Plan, build, test, and review a bounded feature or fix within an approved slice and its declared file scope.
---

# Deliver a bounded change

Read only what the current step needs, once per session: the [agent contract](../../engine/CONTRACT.md), active project state, affected spines and [method sections 3 and 7b](../../docs/METHOD-v0.2.md) (that section only). Size the change before editing. Use `python3 docs/_cgspec/01-engine/cgspec_hook.py tier set --root <path> --tier <T0|T1|T2|T3> --reason <reason> --files <comma-separated-existing-files> --verify <how-to-check>` for T0, or `--slice <SLICE-NNN>` for T1+. Confirm exact syntax with `--help`. A true T0 stays within three existing files and forty changed lines, with no restricted change; otherwise escalate.

For T1+, create or update `docs/slices/SLICE-NNN-<slug>.md` with file scope, interfaces, acceptance criteria and named checks. Draft its `.start.json` with observable outcomes, evaluation, coverage, prerequisites and human checkpoints; obtain fresh approval, run `start ready`, then `start begin` for each eligible outcome before dependent implementation. Material definition changes require renewed approval/readiness. Criteria and test files are written and frozen before code by someone other than the builder; an author cannot approve or weaken its own tests. Capture a failing test at a real revision before implementation, then the passing test pair in `docs/_cgspec/06-evidence/`. Small projects and headless projects use their profile's actual checks; do not invent UI work.

Implement only within the slice scope and agreed ownership. Run the profile and tier checks from the method table, then doctor. At T1+ use one clean-context reviewer, different model when available, and label same-model review honestly. Findings block on correctness or stated requirements; taste suggestions stay optional. After two rounds on the same defect, change approach; at three rounds report BLOCKED with remaining defects. A PASS names the revision and checks run, and lists checks not run. Log the result and checkpoint.
