# CGSpec contributor entry
Created: unknown · Last edited: 2026-10-20T17:48:52Z

This repository develops CGSpec v0.2. Read [current implementation status](docs/STATUS.md), then the relevant parts of [the method specification](docs/METHOD-v0.2.md), [engine formats](engine/FORMATS.md) and [the short contract](engine/CONTRACT.md).

On this workstation (paths below are workstation-only; on another machine use the checkout the user opened) there are exactly two CGSpec locations:

- `/home/ojefe/Documents/Project/cgspec` — this repository, the only development checkout.
- `/home/ojefe/Documents/Project/cgspec-workspace` — investigation history, trial evidence and archived history, not version controlled. Start at its `START-HERE.md`.

The former `cgspec-next` duplicate was deleted on 2026-10-22; its three branches that were never on `main` are preserved here as `refs/archive/cgspec-next-*`. There is no second development stream. Work on feature branches and land changes through PRs; never write directly to main or change Git configuration. Leave CortexGate and other consumer projects untouched unless their upgrade is explicitly authorized.

This plugin source tree is not an installed CGSpec consumer project. Do not install over it to silence consumer-layout errors from doctor. No engine event can run here: each one resolves a project root and exits with `no docs/_cgspec/project.json found`. For that reason the source tree carries no host hook config of its own — a checked-in `.agents/hooks.json` or `.claude/settings.json` here could only look like active wiring while doing nothing, and `tests/unit/test_source_gate.py` fails if one reappears.

What does gate this repository: `core.hooksPath` is `.githooks`, whose `pre-commit` runs `.githooks/source_precommit.py`. That applies the spec-1 content rules which need no project state — no secrets, no decorative emoji, no committed caches — importing the patterns from the engine so the source gate and the consumer gate cannot drift. It refuses the commit if it cannot find its checker, rather than exiting 0. A fabricated secret in a test may carry the marker `cgspec:test-fixture` on its line; that marker is honoured only under `tests/` and in `engine/_lib/inbox.py`. Beyond that, validate the source with its tests and plugin validator, and run consumer doctor and governance checks in disposable installed projects. Record source revision, checks and limitations; never treat the main-origin workflow as the engine suite.

The current method and skills define new work. The documentation index identifies v0.1 history; historical Accepted labels are not current v0.2 approval. ADR-006 records this repository's current governance decision, with credential isolation still pending. Preserve historical evidence and other sessions' work. Add regression tests for substantive defects. The user leads goals and taste; the agent carries the method.
