---
name: cgspec-adopt
description: Take over an existing project or upgrade an older CGSpec layout, including incomplete documentation, multiple repositories, and work already underway.
---

# Adopt an existing project

Read only what the current step needs, once per session: the [agent contract](../../engine/CONTRACT.md), [method section 5](../../docs/METHOD.md) (that section only), and the current project/version marker. Begin with the read-only discovery step, `cgspec_hook.py adopt discover --root <project> [--repos a,b]`, before any mutation; it writes nothing unless `--json-out` is given. Then inspect reachable repos, git roots and history, docs, tests, deployments, configs and active work read-only. Ask only for gaps that materially change the map: missing repos or access, current docs, renames/incidents, incomplete history, infrastructure ownership, and the desired first outcome. Mark each statement observed, inferred, unknown or unreachable; carry the map's kinds forward rather than upgrading them. Where agents are available, give a read-only scout one bounded repo or area; no invented access.

Build a project map and a takeover map from every legacy document/rule to its canonical current home. Show contradictions and unresolved access explicitly. Import existing decisions as `Imported` with source, never `Approved`. Preserve the real stage of each part. Record legacy files in `SLICE-000-baseline` and `docs/_cgspec/07-state/legacy-baseline.json`; new changes need a new scoped slice. Legacy behavior keeps its actual provenance; new success agreements apply only to new or changed outcomes and are scoped to the slice's actual repos and files. Preserve active work (dirty files, branches, worktrees) as found.

For v0.1 adoption, create the old-to-new path map, rewrite links, verify moved facts and doctor results, then update the version marker last. Keep an archive and rollback route until the user confirms the takeover. The current installer has `upgrade` for an existing vendored engine; verify whether `--from-v1` exists before invoking it. If unavailable, make a reviewed migration plan and report the upgrade operation as BLOCKED rather than improvising moves. Use `ingest.py` only if present and against existing regular files; report unsupported syntax and partial coverage.

Before a slice depends on several repos, run `adopt ready --slice SLICE-NNN --repos a,b` for exactly the repos it needs. An unreachable repo is BLOCKED (or PARTIAL when reachable with missing signals), naming the owner and the timing by which access is needed; it blocks only dependent work, never unrelated slices, and is never a silent PASS or an invented fact. Before claiming stronger enforcement, verify the installed hooks and trusted CI bootstrap with a first harmless post-adoption change committed through the real hooks.

Close with what was inspected, what was imported, what remains unknown, and the exact checks at the named revision. Do not claim full project coverage when a repo, history segment or infrastructure is inaccessible.
