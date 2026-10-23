# CGSpec engine: file formats and hook contract
Created: unknown · Last edited: 2026-10-23T13:51:56Z

This file is the contract between the engine scripts, the hooks and the agent. The JSON
Schemas in `schemas/` are the machine-checked source; this page explains them. Spec section
numbers refer to `docs/METHOD-v0.2.md`.

All state files carry `"schema": 1`. A future breaking change bumps it and ships a migration
in `install.py upgrade`.

## Files

Human-readable CGSpec Markdown documents (except the append-only inbox and ledger, engine files, and archived originals) show `Created: ... · Last edited: ...` immediately below the title. New template documents get both dates at install. The v0.1 upgrader uses `Created: unknown` when source creation cannot be proven. The commit gate rejects missing or unchanged edit dates on changed documents, future dates, new documents dated before install or marked unknown outside install/upgrade, date-only edits, invented creation dates on pre-existing documents, and changed creation across renames; doctor warns about untouched legacy documents missing the line. Date metadata does not count as substantive spine content.

| File (in a project) | Schema | Written by | Notes |
| --- | --- | --- | --- |
| `docs/_cgspec/project.json` | `project` | `install.py` | Version marker. `path_classes` globs drive T0 detection (spec 3). |
| `docs/_cgspec/07-state/tier.json` | `tier` | main agent via `cgspec_hook.py tier set` | Declared before editing. `files` required for T0; `slice` required for T1+. |
| `docs/_cgspec/05-runs/<run-id>/run.json` | `run` | inspector | `criteria` and `tests` hold sha256 of each file; once `frozen_at` is set they may not change. `approval` is written only by the message hook or read from a commit trailer, never by the agent. |
| `docs/_cgspec/07-state/frozen.json` | `frozen` | `bundle_prototype.py`, `cgspec_hook.py freeze` | Append-only. CI rejects any change to an existing entry (spec 8, trust root). |
| `docs/_cgspec/04-checks/manifest.json` | `checks-manifest` | registration flow | Append-only for the same reason. A check runs as a gate only when listed here with a matching hash. Written only by `cgspec_hook.py check register` (script and optional Markdown guide must be regular files under `.cgspec-scratch/checks/`). Optional `guide` and `guide_sha256` pin the approved fix guidance beside the script; a missing or changed guide blocks execution. |
| `docs/_cgspec/07-state/checkpoint.json` | `checkpoint` | main agent via checkpoint command | `in_flight` is written before each batch and cleared after; clearing it is not project completion. Optional source observations and unresolved-stop diagnostics support recovery. |
| `docs/_cgspec/07-state/budget.json` | `budget` | hooks | Counts helpers, review rounds and research passes against limits. |
| `docs/_cgspec/07-state/quota.json` | `quota` | Host quota adapter; no collector/writer is included in this checkout | `quota.py --root <project> [--json]` and session packs validate freshness (five minutes), windows and thresholds. Missing or invalid readings give bounded advice; the command does not collect usage or enforce a task gate (spec 9). |
| `docs/_cgspec/06-evidence/tests/<test-id>.json` | `test-pair` | slice workflow | `failed_at` is the commit where the test failed; CI checks it out and re-runs `command` to confirm. |
| `docs/_cgspec/06-evidence/<scope>/<check>.json` | `evidence` | whoever ran the check | `state` becomes `Stale` when a covered file changes. |
| `docs/prototypes/<screen>/journeys/<name>.json` | journey (checked by `journey.py`) | main agent at layer 4 | `name`, `url` (file next to the screen, or `http://` for the real frontend), optional `viewports` (`desktop`, `mobile`) and `covers`, and `steps`. Each step has one action on a `data-testid` (`click`, `fill`+`value`, `press`+`key`, `select`+`value`, `check`, `hover`, `goto`, `screenshot`) or `expect` with `visible`, `hidden`, `text`+`equals`/`contains`, `value`+`equals`, `count`+`equals`, `enabled`, `disabled`, `url`; a `state` label may go with any step. Evidence goes to `06-evidence/journeys/`, visual audits to `06-evidence/visual/`, registered checks to `06-evidence/checks/`. Journey names (and screen names) must be non-empty with no newlines or control characters. `journey.py` and `visual_audit.py` take `--json-out FILE` (`{"schema": 1, "tool", "records": [{"item", "verdict", "detail"}]}`); `visual_summary.py` turns those into the CI `evidence.json` and step summary. |
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
| `pre-compact` | before compaction | no; captures bounded mechanical source context and prints the pack; does not invent semantic progress |
| `stop` | agent wants to end | yes, at most 2 times in a row (counter on disk) |
| `pre-commit` | git pre-commit | yes |
| `commit-msg` | git commit-msg | yes |
| `ci` | CI governance stage | yes |

Registered checks: `pre-commit`, `ci`, `check run` and doctor verify every registered script and guide
against its manifest hash on every run, whether or not the check applies to the changed files; a missing
or changed one fails the gate and its check does not run. `ci` verifies this separately for every commit
in the range against that commit's own manifest and tree (through its `View`), not only the final
checked-out tree: a commit that tampers with an approved script or guide and a later commit in the same
range that restores the exact approved bytes still fails the range. Each check runs with two environment
variables set by the engine:

| Variable | `pre-commit` | `ci` | `check run` |
| --- | --- | --- | --- |
| `CGSPEC_BASE_REV` | `HEAD` | the trusted range base the workflow passes as `--base` (after the install-commit floor) | `HEAD` |
| `CGSPEC_REPO_ROOT` | the real repository | the checkout | the project |
| working directory (candidate content) | exported staged snapshot (no `.git`) | the checked-out HEAD | the working tree |

A check that compares against history reads the base with `git -C "$CGSPEC_REPO_ROOT" show
"$CGSPEC_BASE_REV:<path>"` and the candidate from its working directory. `templates/checks/no_new_suppressions.py`
does this and refuses to guess (exit 2) when the variables are missing.

Browser runs: `CGSPEC_BROWSER=none` forces BLOCKED; `CGSPEC_CHROMIUM` names a Chromium executable. When `CGSPEC_PLAYWRIGHT_DIR` is set (an absolute directory outside the project; the CI workflow sets it), Playwright is loaded only from `$CGSPEC_PLAYWRIGHT_DIR/node_modules`, never from the project's `node_modules` or `NODE_PATH`; otherwise the project's Playwright is used. A journey or audit passes only when the driver reported every expected viewport and these files exist with non-zero size and a PNG/WebM signature: for each viewport, `<label>-<viewport>.png` (final journey state, or the audited page), `<label>-<viewport>-<name>.png` for each journey `screenshot` step, and `<label>-<viewport>.webm` with `--video`.

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


## Checkpoint updates and recovery

`cgspec_hook.py checkpoint --next '...' --in-flight '...'` updates validated existing state. `--done`, `--blocked`, `--awaiting` and `--in-flight` are mutually exclusive. `--awaiting '<question>'` records `awaiting_user` (`at`, `question`, `used`, `count`) and keeps `in_flight`: the stop check accepts one allowed stop on an unused question, then marks it used and checks in-flight work normally again; a refused stop does not use it. A new `--awaiting` before any stop replaces the question. `--done`, `--blocked`, or a change of `in_flight` value (flag or patch) clears it; restating the same `in_flight` does not. Nothing is parked when it clears: hosts without a stop check never mark a question used, so `used` does not mean answered. `count` counts questions put to the user during the current in-flight batch and is lost when the batch ends; only hosts with a stop check increase it, because only they mark a question used. The session pack shows an unused question as asked, not as unanswered. The session pack shows the question, worded as still waiting or as last asked, so a resumed session sees what the user was asked. Damaged or missing state is preserved and requires explicit repair from known records; the command never replaces it with empty defaults.

`checkpoint --update-file <path>` (or `--update-file -` for stdin) accepts a JSON object containing semantic checkpoint fields. Use a unique file under `.cgspec-scratch/` or `/tmp`. Each named field replaces its entire value; omitted fields remain unchanged, arrays/maps replace rather than merge, and `null` is valid only for nullable schema fields. Derived `source`, `unresolved_stop`, `schema` and `updated` cannot be patched. Do not mix a patch key with a flag updating the same field. These commands assume one checkpoint writer; cross-process ownership remains pending.

`checkpoint --capture` saves a bounded source observation without advancing the semantic `updated` time. It records HEAD, branch, hashes of the installed project/engine manifests and eligible dirty worktree files. The pack compares it with current disk state without refreshing the saved baseline. This is recovery context, not evidence that tests ran or that staged bytes match tested bytes. Capture is not an atomic snapshot across concurrent edits.

Limits: Git commands have two-second timeouts and two-MiB output limits; capture hashes at most 200 dirty entries, two MiB per file and eight MiB total including identity files. Untracked directories are not enumerated. Missing Git, byte/count limits, unreadable/unstable files and omitted content produce explicit partial coverage. Sensitive-named paths (`.env*`, secret/credential names and private-key extensions) are omitted without names or hashes; this name heuristic does not discover all secrets. Symlinks and special files are not read. The saved exclusion list names skipped build/cache directories and transient hook files. Actual dependency lockfiles remain observed. An unchanged partial observation cannot establish an unchanged checkout.

The pre-compaction hook captures only mechanical context; semantic goals, pending work and evidence still require the agent's update before a long batch or context pressure. Unavailable hooks cannot guarantee a last-minute save. After two stop refusals, the bounded exit retains exact unresolved reasons and their own timestamp, preserving `in_flight` and semantic `updated`. If checkpoint persistence fails, diagnostics fall back to `stop-retries.json`; if disk writes also fail, exit remains bounded with an explicit SAVE FAILED warning. The next pack shows retained diagnostics. A clean stop clears only the derived stop record, without rewriting an already clean checkpoint.

These observations are not authenticated receipts or approvals. Direct checkpoint/stop-state tool edits are protected where the host's pre-tool hook detects them; shell parsing is partial. Run reservations, remote receipt reconciliation and cross-run writer exclusion are not implemented by this checkpoint repair. New optional fields remain readable by this engine, but older strict schema readers may reject them; release and installed-CI compatibility must be established before rollout.
