# RES-007: Community Claude Code Hook Taxonomy — Pre-Write Hygiene, Anti-Deflection, and Template Checks

Created: 2026-10-24T10:42:00Z · Last edited: 2026-10-24T10:42:00Z

- **Status:** `[Concluded]`
- **Date:** 2026-10-24
- **Authors:** `@jeanfranck`, `Antigravity research agent`
- **Source:** Public community discussion `https://www.reddit.com/r/ClaudeCode/comments/1t93ikr/best_hooks_you_use/` (specifically `u/Obscurrium`'s prompt and `u/raisedbypoubelle`'s 100+ hook architecture breakdown).
- **Licence:** Public forum commentary; no third-party code copied. All CGSpec implementations are clean-room stdlib scripts.

---

## 1. Summary and verdict

The `r/ClaudeCode` thread (`1t93ikr`) surveys production hook setups used by heavy Claude Code practitioners, most notably a 100+ hook deployment categorized into four architectural layers:
1. **Pre-write hooks (`PreToolUse`) as a fast linter:** catching line-ending corruption, monster files, hardcoded workstation paths, and security sinks before bytes touch disk.
2. **Stop and checkpoint hooks (`Stop`) as a QA and honesty gate:** preventing the agent from declaring completion while tests are unrun or from deflecting blame with phrases like `"pre-existing"` or `"out of scope"` without concrete evidence.
3. **User-prompt and compaction hooks (`UserPromptSubmit`, `PreCompact`):** preserving state across context compaction and injecting relevant context when errors are pasted.
4. **Shell command guardrails (`PreToolUse` on `Bash`):** blocking destructive commands, credential reads, and tool-bypassing shell invocations.

**Verdict for CGSpec:** CGSpec v0.2's multi-layer enforcement (`pre-tool` + staged `pre-commit` snapshot + isolated `ci` trust root) is already architecturally stronger than standalone `PreToolUse` hooks because local tool hooks can be bypassed or disabled if not backed by a commit and CI gate. However, shifting three specific checks earlier into `pre-tool` and `commit_gate`—and expanding `templates/checks/` with ready-to-register scripts—closes real day-to-day failure modes without adding external dependencies.

---

## 2. Mapping community hooks against CGSpec v0.2

| Community hook pattern | What it targets | Prior CGSpec status | Action taken in CGSpec |
|---|---|---|---|
| **Compaction recovery** | Context compaction wipes active rules and task state | Implemented in `engine/_lib/session.py` (`pre-compact` + `session-start` pack with dirty-worktree hash observations) | Kept as-is; CGSpec's stateful recovery pack is strictly richer than re-injecting static `CLAUDE.md` text. |
| **Destructive Git & credential-store shell blocker** | Force-push, `reset --hard`, `gh pr merge`, reading `~/.aws` or `.bash_history` | Implemented in `engine/_lib/shellparse.py` and `engine/_lib/gates.py` | Kept as-is; covers subshells, heredocs, and git global flags (`-C`). |
| **File size cop (`PreToolUse`)** | Agents writing monolithic >400-line files and only discovering the limit at test/CI time | Spec 7b stated the 400-line / 60-line rule, and `test_code_rules.py` checked the engine itself, but `gates.py:check_write` did not check consumer code writes | **Adopted in `engine/_lib/gates.py`** (`check_write` refuses writes >400 lines on non-legacy `code` files) and shipped as **`templates/checks/code_size_and_crlf.py`**. |
| **Line-ending enforcer (`CRLF`)** | Agents writing `\r\n` content that pollutes `git diff` and breaks shebangs | Not checked in `gates.py` or `commit_gate.py` | **Adopted in `engine/_lib/gates.py` and `engine/_lib/commit_gate.py`** (blocks `CRLF` in tool writes and staged non-binary files). |
| **Devcontainer / workstation portability enforcer** | Hardcoded `/home/<user>/`, `/Users/<user>/`, or `C:\Users\<user>\` paths leaking into code or configs | Encountered in CGSpec's own PR #14 audit (`git_hooks` host paths), but not gated generally | **Adopted in `engine/_lib/gates.py`, `engine/_lib/commit_gate.py`, and `templates/checks/no_host_paths.py`**. |
| **Anti-deflection detector** | Agent stopping or marking work blocked with blame-dodging phrases (`"pre-existing"`, `"out of scope"`, `"not from my changes"`, `"defer to later"`) | `checkpoint --blocked` accepted any non-empty string | **Adopted in `engine/_lib/checkpoint_cmd.py`**: `--blocked` refuses deflection phrases unless accompanied by a concrete file path, error code (`E-...`), or record ID (`SLICE-NNN`, `ADR-NNN`, `CHK-NNN`). |
| **Vague comment / deferred placeholder detector** | Untracked `TODO`, `FIXME`, `HACK`, `XXX` comments left in shipped code | Only spine markdown had placeholder detection (`L.PLACEHOLDER_LINE`) | **Adopted as `templates/checks/no_deferred_todos.py`** (+ `.md` guide): requires every `TODO`/`FIXME`/`HACK`/`XXX` to link to a tracked record such as `TODO(SLICE-004): ...`. |
| **Read-before-Edit gate** | 77% of bad edits in community session logs occurred on files not read since session start or post-compaction | Not enforced in `pre-tool` | **Deferred / Open:** requires cross-host read-tool payload normalization (`Read` in Claude Code vs `view_file`/`client_view_file` in Antigravity, where read hooks are not always emitted by the host). |

---

## 3. What was implemented and verified

1. **Pre-tool and commit-gate hygiene (`engine/_lib/gates.py`, `engine/_lib/commit_gate.py`):**
   - Rejects `CRLF` (`\r\n`) line endings in `check_write` and on staged text files in `commit_gate.evaluate`.
   - Rejects writes to files in the `code` path class that exceed `MAX_CODE_LINES` (400 lines), unless the file is exempted in `07-state/legacy-baseline.json`.
   - Rejects hardcoded workstation paths (`/home/<user>/`, `/Users/<user>/`, `C:\Users\<user>\`) in `code` and config files at both write time and commit time.
2. **Anti-deflection gate on blocked checkpoints (`engine/_lib/checkpoint_cmd.py`):**
   - `cgspec_hook.py checkpoint --blocked '<reason>'` rejects deflection phrases (`pre-existing`, `out of scope`, `not from my changes`, `defer to later`, `bigger refactor`, `unrelated to my`) when no concrete file path, `E-*` finding code, or `SLICE`/`ADR`/`CHK` identifier is cited.
3. **Expanded registered-check starter catalog (`templates/checks/`):**
   - `code_size_and_crlf.py` + `code_size_and_crlf.md`
   - `no_host_paths.py` + `no_host_paths.md`
   - `no_deferred_todos.py` + `no_deferred_todos.md`
   - Covered by `tests/unit/test_hygiene_gates.py`.
