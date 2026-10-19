# CGSpec engine: file formats and hook contract

This file is the contract between the engine scripts, the hooks and the agent. The JSON
Schemas in `schemas/` are the machine-checked source; this page explains them. Spec section
numbers refer to `docs/METHOD-v2.md`.

All state files carry `"schema": 1`. A future breaking change bumps it and ships a migration
in `install.py upgrade`.

## Files

Human-readable CGSpec Markdown documents (except the append-only inbox and ledger, engine files, and archived originals) show `Created: ... · Last edited: ...` immediately below the title. New template documents get both dates at install. The v1 upgrader uses `Created: unknown` when source creation cannot be proven. The commit gate rejects missing or unchanged edit dates on changed documents, future dates, new documents dated before install or marked unknown outside install/upgrade, date-only edits, invented creation dates on pre-existing documents, and changed creation across renames; doctor warns about untouched legacy documents missing the line. Date metadata does not count as substantive spine content.

| File (in a project) | Schema | Written by | Notes |
| --- | --- | --- | --- |
| `docs/_cgspec/project.json` | `project` | `install.py` | Version marker. `path_classes` globs drive T0 detection (spec 3). |
| `docs/_cgspec/07-state/tier.json` | `tier` | main agent via `cgspec_hook.py tier set` | Declared before editing. `files` required for T0; `slice` required for T1+. |
| `docs/_cgspec/05-runs/<run-id>/run.json` | `run` | inspector | `criteria` and `tests` hold sha256 of each file; once `frozen_at` is set they may not change. `approval` is written only by the message hook or read from a commit trailer, never by the agent. |
| `docs/_cgspec/07-state/frozen.json` | `frozen` | `bundle_prototype.py`, `cgspec_hook.py freeze` | Append-only. CI rejects any change to an existing entry (spec 8, trust root). |
| `docs/_cgspec/04-checks/manifest.json` | `checks-manifest` | registration flow | Append-only for the same reason. A check runs as a gate only when listed here with a matching hash. Written only by `cgspec_hook.py check register` (source must be under `.cgspec-scratch/checks/`). |
| `docs/_cgspec/07-state/checkpoint.json` | `checkpoint` | main agent, pre-compact hook | `in_flight` is written before each batch and cleared after. |
| `docs/_cgspec/07-state/budget.json` | `budget` | hooks | Counts helpers, review rounds and research passes against limits. |
| `docs/_cgspec/07-state/quota.json` | `quota` | status-line script | `source: unavailable` puts the agent in bounded mode (spec 9). |
| `docs/_cgspec/06-evidence/tests/<test-id>.json` | `test-pair` | slice workflow | `failed_at` is the commit where the test failed; CI checks it out and re-runs `command` to confirm. |
| `docs/_cgspec/06-evidence/<scope>/<check>.json` | `evidence` | whoever ran the check | `state` becomes `Stale` when a covered file changes. |
| `docs/_cgspec/07-state/legacy-baseline.json` | `legacy-baseline` | `cgspec-adopt` | Files listed here are exempt from size and test rules until their hash changes. |
| `docs/_cgspec/07-state/approvals.json` | `approvals` | `user-message` hook only | One entry per user message that reads as an approval. A ledger entry with status Approved must cite one of these IDs (`--approval-ref A-...`). |
| `docs/_cgspec/07-state/stop-retries.json` | none | `stop` hook | Counts consecutive stop refusals; reset when the agent ends cleanly. |

## IDs

| Kind | Form | Example |
| --- | --- | --- |
| Ledger entry | `M-YYYYMMDD-xxxx` (4 random hex) | `M-20261018-a3f9` |
| Tier declaration | `T-YYYYMMDD-xxxx` | `T-20261018-0c1d` |
| Run | `R-YYYYMMDD-xxxx` | `R-20261018-77be` |
| ADR / slice | `ADR-NNN-<slug>`, `SLICE-NNN-<slug>`; drafts `ADR-draft-<slug>` | `SLICE-004-login` |
| Registered check | `CHK-NNN` | `CHK-012` |

Polyrepo members prefix IDs with `repo_prefix:` (`api:ADR-004`). Legacy ledger IDs `M-001`
are still read so old projects can be upgraded.

## Ledger entry (`docs/_memlog.md`)

```
### [M-20261018-a3f9] 2026-10-18T21:40:00Z | tags: decision,design | owner: @ojefe | perms: public
- **Summary:** one line
- **Details:** optional
- **Status:** Delegated            (decisions only; spec 2 statuses)
- **Links:** ADR-004, SLICE-012    (optional)
```

Only `memlog.py` writes this file.

## Slice file fields read by the engine

```
# SLICE-004: Login form
- **Status:** Approved            (Draft, Approved, In progress, Done, Blocked)
- **Scope:** src/login/**, tests/login/**   (comma-separated globs; T1+ edits must match)
```

## `cgspec_hook.py` command line

```
python3 docs/_cgspec/01-engine/cgspec_hook.py <event> [--tool TOOL] [--root PATH]
```

The tool's own hook payload (JSON) arrives on stdin; the adapter for each tool passes it through
and `--tool` tells the hook how to read it. Events:

| Event | When | Blocks? |
| --- | --- | --- |
| `session-start` | session start and after compaction | no; prints the session pack |
| `session-check` | inside `session-start`, also runnable alone | no; reports, exit 1 if broken |
| `user-message` | each user message | never; scrubs secrets, saves to inbox, records approvals |
| `pre-tool` | before a write or shell tool | yes |
| `post-tool` | after a write, shell or helper-agent tool | no; marks evidence whose `covers` globs match a changed file `Stale`, counts helper agents in `budget.json` (exit 2 only to show a budget warning) |
| `pre-compact` | before compaction | no; writes checkpoint |
| `stop` | agent wants to end | yes, at most 2 times in a row (counter on disk) |
| `pre-commit` | git pre-commit | yes |
| `commit-msg` | git commit-msg | yes |
| `ci` | CI governance stage | yes |

Document dates: `cgspec_hook.py doc sync` dates new documents, advances `Last edited` on edited ones, reverts date-only edits and labels edited legacy documents `Created: unknown`; the `stop` hook runs it at the end of each turn.

Tier declarations: `cgspec_hook.py tier set --tier T0 --reason "..." --files a,b` (T0) or
`--slice SLICE-NNN` (T1+); `tier show`; `tier clear`. CI: `cgspec_hook.py ci --base <sha>`.

Per-tool payloads: `--tool claude` reads Claude Code hook JSON (`tool_name`, `tool_input`);
`--tool antigravity` reads `toolCall.name` / `toolCall.args` (`TargetFile`, `CommandLine`,
`Cwd`) and answers with `{"decision": "deny", "reason": ...}` on stdout (and `{"decision":
"continue"}` from `stop`) instead of exit 2; `--tool generic` reads
`{"tool": "write|edit|shell", "paths": [...], "content": ..., "command": ..., "cwd": ...}`.
Antigravity hooks receive no user message, so inbox and approval capture work only on Claude
Code; elsewhere approvals use the commit trailer path.

Exit codes (same for every engine script):

| Code | Meaning | Claude Code | git / CI |
| --- | --- | --- | --- |
| 0 | allow / pass | proceeds | passes |
| 1 | check failed (scripts) | shown, non-blocking | fails |
| 2 | blocked by a rule; reason on stderr | tool call refused, reason fed to the agent | fails |
| 3 | internal error in the engine | shown, non-blocking | fails |

`pre-tool` fails closed on internal errors only when the target path is protected (frozen,
engine, manifests, CI files); elsewhere it reports exit 3 so a bug in the engine cannot freeze
every session, and the commit hook and CI still catch the change.
