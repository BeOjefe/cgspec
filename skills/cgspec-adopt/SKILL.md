---
name: cgspec-adopt
description: Take over an existing project or upgrade an older CGSpec layout, including incomplete documentation, multiple repositories, and work already underway.
---

# Adopt an existing project

Read the [agent contract](../../engine/CONTRACT.md), [method section 5](../../docs/METHOD-v2.md), and the current project/version marker. Inspect reachable repos, git roots and history, docs, tests, deployments, configs and active work read-only. Ask only for gaps that materially change the map: missing repos or access, current docs, renames/incidents, incomplete history, infrastructure ownership, and the desired first outcome. Mark each statement observed, inferred or unknown. Where agents are available, give a read-only scout one bounded repo or area; no invented access.

Build a project map and a takeover map from every legacy document/rule to a canonical v2 home. Show contradictions and unresolved access explicitly. Import existing decisions as `Imported` with source, never `Approved`. Preserve the real stage of each part. Record legacy files in `SLICE-000-baseline` and `docs/_cgspec/07-state/legacy-baseline.json`; new changes need a new scoped slice.

For v1 upgrade, create the old-to-new path map, rewrite links, verify moved facts and doctor results, then update the version marker last. Keep an archive and rollback route until the user confirms the takeover. The current installer has `upgrade` for a v2 vendored engine; verify whether `--from-v1` exists before invoking it. If unavailable, make a reviewed migration plan and report the upgrade operation as BLOCKED rather than improvising moves. Use `ingest.py` only if present and against existing regular files; report unsupported syntax and partial coverage.

Close with what was inspected, what was imported, what remains unknown, and the exact checks at the named revision. Do not claim full project coverage when a repo, history segment or infrastructure is inaccessible.
