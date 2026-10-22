"""cgspec_hook.py: tier declarations and the pre-tool gate (spec 3 and 8)."""

from __future__ import annotations

import hashlib
import json
import os
import unittest
from pathlib import Path

from tests.helpers import TempDir, claude_payload, hook, install, make_slice, write_json

BLOCK = 2


def tier(root: Path, *args: str):
    from tests.helpers import run_script
    return run_script("cgspec_hook.py", "tier", *args, "--root", str(root))


class PreToolTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        install(self.root)
        (self.root / "src/login").mkdir(parents=True)
        (self.root / "src/a.ts").write_text("export const a = 1;\n")
        (self.root / "src/login/form.ts").write_text("export const f = 1;\n")
        (self.root / "package.json").write_text("{}\n")

    def tearDown(self):
        for p in self.root.rglob("*"):
            if p.is_file() and not p.is_symlink():
                os.chmod(p, 0o644)
        self._tmp.__exit__(None, None, None)

    def edit(self, rel, tool="Edit", **extra):
        payload = claude_payload(self.root, tool, file_path=rel, old_string="a", new_string="b", **extra)
        return hook(self.root, "pre-tool", payload, "--tool", "claude")

    def write(self, rel, content="x = 1\n"):
        return hook(self.root, "pre-tool", claude_payload(self.root, "Write", file_path=rel, content=content), "--tool", "claude")

    def bash(self, command):
        return hook(self.root, "pre-tool", claude_payload(self.root, "Bash", command=command), "--tool", "claude")

    def slice(self, status="Approved", scope="src/login/**", approval=None):
        make_slice(self.root, status, scope, approval)

    def freeze(self, rel, content="<html>v1</html>"):
        target = self.root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        path = self.root / "docs/_cgspec/07-state/frozen.json"
        data = json.loads(path.read_text())
        data["entries"].append({"path": rel, "sha256": hashlib.sha256(content.encode()).hexdigest(),
                                "kind": "snapshot", "added": "2026-10-18T00:00:00Z", "reason": "locked"})
        write_json(path, data)

    # --- tier declarations -----------------------------------------------------------------
    def test_tier_set_t0_writes_state_and_ledger(self):
        result = tier(self.root, "set", "--tier", "T0", "--reason", "fix typo", "--files", "src/a.ts")
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads((self.root / "docs/_cgspec/07-state/tier.json").read_text())
        self.assertEqual(state["active"]["tier"], "T0")
        self.assertEqual(state["active"]["files"], ["src/a.ts"])
        self.assertIn("tier T0", (self.root / "docs/_memlog.md").read_text())

    def test_t0_refuses_too_many_files_new_files_and_forbidden_classes(self):
        for files, why in (("src/a.ts,src/b.ts,src/c.ts,src/d.ts", "3 files"),
                           ("src/new.ts", "new file"), ("package.json", "deps")):
            with self.subTest(why=why):
                result = tier(self.root, "set", "--tier", "T0", "--reason", "test change", "--files", files)
                self.assertEqual(result.returncode, 1, why)

    def test_t1_needs_an_approved_slice(self):
        self.assertEqual(tier(self.root, "set", "--tier", "T1", "--reason", "login").returncode, 1)
        self.slice(status="Draft")
        self.assertEqual(tier(self.root, "set", "--tier", "T1", "--reason", "test change", "--slice", "SLICE-001").returncode, 1)
        self.slice(approval="")  # Approved in the text, but no approval from the user
        self.assertEqual(tier(self.root, "set", "--tier", "T1", "--reason", "test change", "--slice", "SLICE-001").returncode, 1)
        self.slice(approval="A-20261018-ffff")  # made-up approval id
        self.assertEqual(tier(self.root, "set", "--tier", "T1", "--reason", "test change", "--slice", "SLICE-001").returncode, 1)
        self.slice()
        self.assertEqual(tier(self.root, "set", "--tier", "T1", "--reason", "test change", "--slice", "SLICE-001").returncode, 0)

    def test_tier_clear(self):
        tier(self.root, "set", "--tier", "T0", "--reason", "test change", "--files", "src/a.ts")
        self.assertEqual(tier(self.root, "clear").returncode, 0)
        self.assertIsNone(json.loads((self.root / "docs/_cgspec/07-state/tier.json").read_text())["active"])

    # --- tier enforcement --------------------------------------------------------------------
    def test_code_edit_without_tier_is_blocked(self):
        result = self.edit("src/a.ts")
        self.assertEqual(result.returncode, BLOCK)
        self.assertIn("tier", result.stderr)

    def test_docs_edit_without_tier_is_allowed(self):
        self.assertEqual(self.edit("docs/spines/01-INTENT.md").returncode, 0)

    def test_t0_allows_only_listed_existing_files(self):
        tier(self.root, "set", "--tier", "T0", "--reason", "test change", "--files", "src/a.ts")
        self.assertEqual(self.edit("src/a.ts").returncode, 0)
        self.assertEqual(self.edit("src/login/form.ts").returncode, BLOCK)
        self.assertEqual(self.write("src/brand_new.ts").returncode, BLOCK)

    def test_t1_allows_only_slice_scope(self):
        self.slice()
        tier(self.root, "set", "--tier", "T1", "--reason", "test change", "--slice", "SLICE-001")
        self.assertEqual(self.edit("src/login/form.ts").returncode, 0)
        self.assertEqual(self.write("src/login/new.ts").returncode, 0)
        self.assertEqual(self.edit("src/a.ts").returncode, BLOCK)

    def test_slice_downgraded_after_tier_set_blocks(self):
        self.slice()
        tier(self.root, "set", "--tier", "T1", "--reason", "test change", "--slice", "SLICE-001")
        self.slice(status="Blocked")
        self.assertEqual(self.edit("src/login/form.ts").returncode, BLOCK)

    # --- protected paths -----------------------------------------------------------------------
    def test_frozen_file_is_blocked_even_with_a_tier(self):
        rel = "docs/prototypes/_snapshots/home-v1.html"
        self.freeze(rel)
        self.assertEqual(self.edit(rel).returncode, BLOCK)
        self.assertEqual(self.write(rel, "<html>v2</html>").returncode, BLOCK)

    def test_shell_writes_to_frozen_files_are_blocked(self):
        rel = "docs/prototypes/_snapshots/home-v1.html"
        self.freeze(rel)
        for command in (f"sed -i 's/v1/v2/' {rel}", f"echo x > {rel}", f"echo x >> ./{rel}",
                        f"cp /tmp/x {rel}", f"mv other.html {rel}", f"tee {rel} < in.html",
                        f"python3 -c \"open('{rel}','w').write('x')\"", f"chmod u+w {rel}",
                        f"cd docs/prototypes/_snapshots && sed -i s/a/b/ home-v1.html"):
            with self.subTest(command=command):
                self.assertEqual(self.bash(command).returncode, BLOCK, command)

    def test_shell_reads_are_allowed(self):
        rel = "docs/prototypes/_snapshots/home-v1.html"
        self.freeze(rel)
        for command in (f"cat {rel}", f"grep v1 {rel}", "git status", f"cp {rel} /tmp/copy.html"):
            with self.subTest(command=command):
                self.assertEqual(self.bash(command).returncode, 0, command)

    def test_engine_manifests_and_state_are_protected(self):
        for rel in ("docs/_cgspec/01-engine/doctor.py", "docs/_cgspec/07-state/frozen.json",
                    "docs/_cgspec/04-checks/manifest.json", "docs/_cgspec/project.json"):
            with self.subTest(rel=rel):
                self.assertEqual(self.edit(rel).returncode, BLOCK)

    # --- scripts and content -------------------------------------------------------------------
    def test_new_script_in_docs_is_blocked(self):
        result = self.write("docs/prototypes/generate_v15_screenshots.py", "print('x')\n")
        self.assertEqual(result.returncode, BLOCK)
        self.assertIn("script", result.stderr)

    def test_scratch_scripts_are_allowed(self):
        self.assertEqual(self.write(".cgspec-scratch/probe.py", "print('x')\n").returncode, 0)

    def test_emojis_in_written_content_are_blocked(self):
        tier(self.root, "set", "--tier", "T0", "--reason", "test change", "--files", "src/a.ts")
        result = hook(self.root, "pre-tool", claude_payload(self.root, "Edit", file_path="src/a.ts",
                                                            old_string="1", new_string="2 \U0001F680"), "--tool", "claude")
        self.assertEqual(result.returncode, BLOCK)
        self.assertIn("emoji", result.stderr)

    def test_secret_in_written_content_is_blocked(self):
        tier(self.root, "set", "--tier", "T0", "--reason", "test change", "--files", "src/a.ts")
        result = hook(self.root, "pre-tool", claude_payload(self.root, "Edit", file_path="src/a.ts",
                                                            old_string="1", new_string="2 AKIAABCDEFGHIJKLMN12"), "--tool", "claude")
        self.assertEqual(result.returncode, BLOCK)
        self.assertIn("secret", result.stderr)

    def test_reading_bash_history_is_blocked(self):
        result = self.bash("cat ~/.bash_history | grep token")
        self.assertEqual(result.returncode, BLOCK)
        self.assertIn("credential store", result.stderr)

    def test_paths_outside_project_are_not_our_business(self):
        self.assertEqual(self.edit("/tmp/elsewhere.txt").returncode, 0)

    def test_malformed_payload_is_non_blocking_internal_error(self):
        result = hook(self.root, "pre-tool", None, "--tool", "claude")
        self.assertEqual(result.returncode, 3)

    def test_non_write_tools_pass(self):
        payload = claude_payload(self.root, "Read", file_path="docs/_cgspec/07-state/frozen.json")
        self.assertEqual(hook(self.root, "pre-tool", payload, "--tool", "claude").returncode, 0)

    def test_generic_payload_for_other_tools(self):
        payload = {"tool": "write", "paths": ["docs/_cgspec/01-engine/doctor.py"], "content": "x"}
        self.assertEqual(hook(self.root, "pre-tool", payload, "--tool", "generic").returncode, BLOCK)


if __name__ == "__main__":
    unittest.main()


class TierReasonTests(unittest.TestCase):
    def test_reason_must_say_why(self):
        with TempDir() as root:
            install(root)
            (root / "src").mkdir()
            (root / "src/a.ts").write_text("x\n")
            self.assertEqual(tier(root, "set", "--tier", "T0", "--reason", "x", "--files", "src/a.ts").returncode, 1)
