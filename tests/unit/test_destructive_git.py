"""Destructive Git/GitHub actions are refused before the agent can run them.

Method council 2026-10-24, finding 1 (Catastrophic): `shell_reasons()` checked file targets
and credential-store reads but inspected no Git command arguments at all. A delegated fixer
agent rewrote branch history with `git filter-branch` and force-pushed without asking. These
pin the fix: `destructive_git_reasons()` refuses the specific commands named in the council's
synthesis (push --force/-f/+refspec, push --delete, filter-branch, filter-repo, reset --hard,
branch -D/--delete --force, gh pr merge) before `pre_tool` lets the shell command run.

This guards the agent's own tool calls, not the user's terminal: the human can still run any
of these directly. It is a tripwire, not the only line of defence -- the commit hook, the
read-only disk lock and GitHub's own history still matter.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from tests.helpers import TempDir, claude_payload, git_project, hook

REPO = Path(__file__).resolve().parents[2]


class MethodStatesTheRule(unittest.TestCase):
    def test_method_v02_states_the_agent_never_runs_these_itself(self):
        method = (REPO / "docs/METHOD-v0.2.md").read_text(encoding="utf-8")
        for term in ("force-push", "filter-branch", "reset --hard", "merges a pull request"):
            self.assertIn(term, method)


class DestructiveGitTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git_project(self.root)

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def bash(self, command):
        return hook(self.root, "pre-tool", claude_payload(self.root, "Bash", command=command), "--tool", "claude")

    def blocked(self, command, hint):
        result = self.bash(command)
        self.assertEqual(result.returncode, 2, f"{command!r} should be refused:\n{result.stdout}{result.stderr}")
        self.assertIn(hint, result.stdout + result.stderr, f"{command!r}: missing reason containing {hint!r}")

    def allowed(self, command):
        result = self.bash(command)
        self.assertEqual(result.returncode, 0, f"{command!r} should be allowed:\n{result.stdout}{result.stderr}")

    # --- same guard on Antigravity (Gemini), the host where the incident actually happened -------
    def test_antigravity_run_command_is_covered_too(self):
        """The fixer agent that force-pushed without asking ran on Antigravity, not Claude Code.
        The guard must not be a Claude-only tripwire."""
        payload = {"conversationId": "c1", "workspacePaths": [str(self.root)],
                  "toolCall": {"name": "run_command", "args": {"CommandLine": "git push --force origin main"}},
                  "stepIdx": 1}
        result = hook(self.root, "pre-tool", payload, "--tool", "antigravity")
        self.assertIn('"decision":"deny"', result.stdout.replace(" ", ""), result.stdout + result.stderr)
        self.assertIn("force", result.stdout + result.stderr)

    # --- the incident: force-push and history rewrite -------------------------------------------
    def test_force_push_variants_are_blocked(self):
        for command in ("git push --force origin main", "git push -f origin main",
                        "git push origin +feature:main", "git push --force-with-lease origin main",
                        "git -C /tmp/other push --force origin main", "sudo git push --force origin main"):
            self.blocked(command, "force")

    def test_push_delete_is_blocked(self):
        self.blocked("git push origin --delete feature", "delete")
        self.blocked("git push -d origin feature", "delete")

    def test_filter_branch_and_filter_repo_are_blocked(self):
        self.blocked("git filter-branch --tree-filter 'rm -f secret' HEAD", "filter-branch")
        self.blocked("git filter-repo --invert-paths --path secret", "filter-repo")

    def test_reset_hard_is_blocked(self):
        self.blocked("git reset --hard HEAD~3", "reset --hard")
        self.blocked("git reset --hard", "reset --hard")

    def test_forced_branch_delete_is_blocked(self):
        self.blocked("git branch -D feature", "branch")
        self.blocked("git branch --delete --force feature", "branch")

    def test_pr_merge_is_blocked(self):
        self.blocked("gh pr merge 17", "merge")
        self.blocked("gh pr merge --admin --squash 19", "merge")

    def test_commit_check_bypass_is_blocked(self):
        self.blocked("git commit --no-verify -m fix", "--no-verify")
        self.blocked("git commit -n -m bypass", "--no-verify")
        self.blocked("git commit -an -m bypass", "--no-verify")
        self.blocked("git commit --no-veri -m bypass", "--no-verify")
        self.blocked("git -c core.hooksPath=/dev/null commit -m fix", "core.hooksPath")
        self.blocked("git -ccore.hooksPath=/dev/null commit -m fix", "core.hooksPath")
        self.blocked("git -c user.name=Test -c core.hooksPath=/dev/null commit -m fix", "core.hooksPath")
        self.blocked("CG_HOOKS=/dev/null git --config-env=core.hooksPath=CG_HOOKS commit -m bypass", "core.hooksPath")

    def test_commit_message_is_not_an_option(self):
        self.allowed('git commit --allow-empty -m "--no-verify"')
        self.allowed('git commit --allow-empty --message=--no-verify')
        self.allowed('git commit --allow-empty -m "-n"')

    # --- things that must NOT be blocked ---------------------------------------------------------
    def test_safe_branch_delete_is_allowed(self):
        """-d (lowercase) only deletes an already-merged branch; it is not --force."""
        self.allowed("git branch -d feature")
        self.allowed("git branch --delete feature")

    def test_ordinary_git_commands_are_allowed(self):
        for command in ("git push origin main", "git push", "git status", "git log --oneline -5",
                        "git reset HEAD~1", "git branch -a", "gh pr view 17", "gh pr list",
                        "gh pr checks 17", "git commit -m 'fix: thing'"):
            self.allowed(command)

    def test_prose_mentioning_these_commands_is_not_blocked(self):
        """A commit message explaining the incident must not trip the guard on its own words:
        tokenizing 'git' then 'filter-branch' as prose, not as an invocation, is the risk."""
        msg = ("fix: close the gap where an agent rewrote history with git filter-branch "
              "and force-pushed without asking; also mentions git reset --hard and gh pr merge "
              "in passing")
        self.allowed(f"git commit -m {msg!r}")

    def test_heredoc_body_text_about_these_commands_is_not_blocked(self):
        """The commit-message heredoc pattern used throughout this project must stay usable."""
        command = ("git commit -F - <<'MSG'\n"
                   "fix(installer): the fixer had run git filter-branch and force-pushed\n"
                   "Also explains git reset --hard and gh pr merge as the incident.\n"
                   "MSG")
        self.allowed(command)

    # --- the one gap this scope does not cover, pinned so it is never silently assumed fixed ----
    def test_known_gap_a_destructive_command_smuggled_inside_a_heredoc_body_is_not_caught(self):
        """Documented limitation: only command lines are scanned, never heredoc bodies, because a
        body can equally be prose (see above). A real command piped through a heredoc to another
        shell is not caught here. The commit hook and GitHub's own history remain the backstop."""
        command = "bash <<'EOF'\ngit push --force origin main\nEOF"
        self.allowed(command)


if __name__ == "__main__":
    unittest.main()
