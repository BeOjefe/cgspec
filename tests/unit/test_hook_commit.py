"""pre-commit gate (spec 8 commit hook column): tier limits, slice scope, test pairs, frozen, scripts, emojis."""

from __future__ import annotations

import hashlib
import json
import os
import unittest
from pathlib import Path

from tests.helpers import TempDir, approve, git, git_project, hook, make_slice, run_script, set_test_command, write_json


def tier(root, *args):
    return run_script("cgspec_hook.py", "tier", *args, "--root", str(root))


def precommit(root):
    return hook(root, "pre-commit", None, "--tool", "git")


class PreCommitTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git_project(self.root)

    def tearDown(self):
        for p in self.root.rglob("*"):
            if p.is_file() and not p.is_symlink():
                os.chmod(p, 0o644)
        self._tmp.__exit__(None, None, None)

    def stage(self, rel, content):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        git(self.root, "add", "-A")

    def assertBlocked(self, needle):
        result = precommit(self.root)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(needle, result.stdout + result.stderr)

    def assertAllowed(self):
        result = precommit(self.root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def slice(self, status="Approved", scope="src/login/**, tests/**", approval=None):
        make_slice(self.root, status, scope, approval)
        git(self.root, "add", "-A")

    def add_test_pair(self, covers=("src/login/form.ts",), failed_at=None):
        failed_at = failed_at or git(self.root, "rev-parse", "HEAD").stdout.strip()
        (self.root / "tests").mkdir(exist_ok=True)
        (self.root / "tests/login.test.ts").write_text("test('rejects empty', () => {});\n")
        write_json(self.root / "docs/_cgspec/06-evidence/tests/login-form.json", {
            "schema": 1, "test_id": "tests/login.test.ts::rejects_empty", "test_file": "tests/login.test.ts",
            "command": ["npx", "vitest", "run", "tests/login.test.ts"], "failed_at": failed_at, "passed_at": None, "covers": list(covers),
            "slice": "SLICE-001", "recorded": "2026-10-18T00:00:00Z"})
        git(self.root, "add", "-A")

    def test_docs_only_commit_needs_no_tier(self):
        self.stage("docs/spines/01-INTENT.md", "# Intent\n\nSome words about why this exists for the people using it every day.\n")
        self.assertAllowed()

    def test_code_without_tier_is_blocked(self):
        self.stage("src/a.ts", "export const a = 2;\n")
        self.assertBlocked("no change tier")

    def test_t0_within_limits_passes(self):
        tier(self.root, "set", "--tier", "T0", "--reason", "fix a constant", "--files", "src/a.ts")
        self.stage("src/a.ts", "export const a = 2;\n")
        self.assertAllowed()

    def test_t0_line_limit(self):
        tier(self.root, "set", "--tier", "T0", "--reason", "fix a constant", "--files", "src/a.ts")
        self.stage("src/a.ts", "".join(f"export const a{i} = {i};\n" for i in range(45)))
        self.assertBlocked("40")

    def test_t0_unlisted_file_and_new_file_blocked(self):
        tier(self.root, "set", "--tier", "T0", "--reason", "fix a constant", "--files", "src/a.ts")
        self.stage("src/login/form.ts", "export const f = 2;\n")
        self.assertBlocked("not in the T0 file list")
        git(self.root, "reset", "-q", "--hard")
        tier(self.root, "set", "--tier", "T0", "--reason", "fix a constant", "--files", "src/a.ts")
        self.stage("src/new.ts", "export const n = 1;\n")
        self.assertBlocked("T0 cannot create")

    def test_t1_scope_and_test_pair(self):
        set_test_command(self.root, ["npx", "vitest", "run", "{test_file}"])
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "test command")
        self.slice()
        tier(self.root, "set", "--tier", "T1", "--reason", "login validation", "--slice", "SLICE-001")
        self.stage("src/login/form.ts", "export const f = 2;\n")
        self.assertBlocked("failing-test record")
        self.add_test_pair()
        self.assertAllowed()
        self.stage("src/a.ts", "export const a = 9;\n")
        self.assertBlocked("outside the scope")

    def test_test_pair_with_unknown_commit_blocked(self):
        self.slice()
        tier(self.root, "set", "--tier", "T1", "--reason", "login validation", "--slice", "SLICE-001")
        self.stage("src/login/form.ts", "export const f = 2;\n")
        self.add_test_pair(failed_at="deadbeef")
        self.assertBlocked("failed_at")

    def test_changing_frozen_file_blocked(self):
        rel = "docs/prototypes/_snapshots/home-v1.html"
        content = "<html>v1</html>"
        self.stage(rel, content)
        frozen = self.root / "docs/_cgspec/07-state/frozen.json"
        data = json.loads(frozen.read_text())
        data["entries"].append({"path": rel, "sha256": hashlib.sha256(content.encode()).hexdigest(),
                                "kind": "snapshot", "added": "2026-10-18T00:00:00Z", "reason": "layer 3 locked"})
        write_json(frozen, data)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "freeze")
        self.stage(rel, "<html>v1 edited</html>")
        self.assertBlocked("frozen")

    def test_rewriting_frozen_entry_blocked(self):
        rel = "docs/prototypes/_snapshots/home-v1.html"
        self.stage(rel, "<html>v1</html>")
        frozen = self.root / "docs/_cgspec/07-state/frozen.json"
        data = json.loads(frozen.read_text())
        data["entries"].append({"path": rel, "sha256": hashlib.sha256(b"<html>v1</html>").hexdigest(),
                                "kind": "snapshot", "added": "2026-10-18T00:00:00Z", "reason": "layer 3 locked"})
        write_json(frozen, data)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "freeze")
        data["entries"][0]["sha256"] = hashlib.sha256(b"<html>v2</html>").hexdigest()
        write_json(frozen, data)
        self.stage(rel, "<html>v2</html>")
        self.assertBlocked("append-only")

    def test_new_script_in_docs_blocked(self):
        self.stage("docs/prototypes/generate.py", "print('x')\n")
        self.assertBlocked("script")

    def test_emoji_in_added_lines_blocked(self):
        self.stage("docs/spines/01-INTENT.md", "# Intent\n\nLaunch \U0001F680 soon for everyone who wants to read markets.\n")
        self.assertBlocked("emoji")

    def test_engine_change_blocked_unless_consistent_with_manifest(self):
        engine = self.root / "docs/_cgspec/01-engine/memlog.py"
        os.chmod(engine, 0o644)
        self.stage("docs/_cgspec/01-engine/memlog.py", engine.read_text() + "\n# tweak\n")
        self.assertBlocked("engine")

    def test_doctor_errors_block(self):
        self.stage("docs/random.md", "x\n")
        self.assertBlocked("doctor")


if __name__ == "__main__":
    unittest.main()


class CommitGateUnitTests(unittest.TestCase):
    """The commit rules on their own, without the doctor safety net."""

    def test_frozen_change_detected_by_gate_alone(self):
        from _lib.commit_gate import evaluate
        from _lib.gitview import View
        with TempDir() as root:
            git_project(root)
            rel = "docs/prototypes/_snapshots/home-v1.html"
            (root / rel).write_text("<html>v1</html>")
            frozen = root / "docs/_cgspec/07-state/frozen.json"
            data = json.loads(frozen.read_text())
            data["entries"].append({"path": rel, "sha256": hashlib.sha256(b"<html>v1</html>").hexdigest(),
                                    "kind": "snapshot", "added": "2026-10-18T00:00:00Z", "reason": "locked"})
            write_json(frozen, data)
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "freeze")
            (root / rel).write_text("<html>edited</html>")
            git(root, "add", "-A")
            reasons = evaluate(root, View.staged(root))
            self.assertTrue(any("frozen" in r for r in reasons), reasons)
            git(root, "rm", "-q", "--cached", rel)
            reasons = evaluate(root, View.staged(root))
            self.assertTrue(any("frozen" in r for r in reasons), reasons)
