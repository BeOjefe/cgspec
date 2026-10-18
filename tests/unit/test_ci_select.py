"""The CI release-selection script: newest of base/HEAD version, source from the base, never the repo's engine."""

from __future__ import annotations

import json
import os
import subprocess
import unittest
from pathlib import Path

from tests.helpers import REPO, TempDir, git, git_project, write_json


def make_release_source(tmp: Path, versions: list[str]) -> Path:
    """A git repo standing in for the published plugin, with one tag per version."""
    src = tmp / "plugin.git"
    git(tmp, "clone", "-q", "--no-hardlinks", str(REPO), str(src))
    for version in versions:
        (src / "engine/VERSION").write_text(version + "\n")
        git(src, "commit", "-q", "-am", f"release {version}", "--allow-empty")
        git(src, "tag", f"v{version}")
    return src


def select(root: Path, base: str, tmp: Path) -> dict:
    env_file = tmp / "github_env"
    env_file.write_text("")
    env = dict(os.environ, EVENT_BASE=base, DEFAULT_BRANCH="", RUNNER_TEMP=str(tmp), GITHUB_ENV=str(env_file))
    result = subprocess.run(["sh", str(root / ".github/cgspec-select.sh")], cwd=root, env=env,
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    return dict(line.split("=", 1) for line in env_file.read_text().splitlines())


class CiSelectTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.tmp = self._tmp.__enter__()
        self.root = self.tmp / "project"
        self.root.mkdir()
        self.source = make_release_source(self.tmp, ["2.0.0", "2.1.0"])
        git(self.root, "init", "-q", "-b", "main")
        from tests.helpers import run_script
        run_script("install.py", "install", "--root", str(self.root), "--profile", "headless", "--topology", "single",
                   "--tools", "git,ci", "--plugin-source", str(self.source))
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "--no-verify", "-m", "install")
        self.base = git(self.root, "rev-parse", "HEAD").stdout.strip()

    def tearDown(self):
        for p in self.tmp.rglob("*"):
            if p.is_file() and not p.is_symlink():
                os.chmod(p, 0o644)
        self._tmp.__exit__(None, None, None)

    def edit(self, rel, mutate):
        path = self.root / rel
        os.chmod(path, 0o644)
        mutate(path)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "--no-verify", "-m", f"edit {rel}")

    def test_picks_release_matching_version_and_base(self):
        env = select(self.root, self.base, self.tmp)
        self.assertEqual(env["CGSPEC_BASE"], self.base)
        self.assertEqual((Path(env["CGSPEC_RELEASE"]) / "engine/VERSION").read_text().strip(), "2.0.0")

    def test_downgrade_in_head_is_ignored(self):
        self.edit("docs/_cgspec/01-engine/VERSION", lambda p: p.write_text("1.0.0\n"))
        env = select(self.root, self.base, self.tmp)
        self.assertEqual((Path(env["CGSPEC_RELEASE"]) / "engine/VERSION").read_text().strip(), "2.0.0")

    def test_upgrade_in_head_uses_the_newer_release(self):
        self.edit("docs/_cgspec/01-engine/VERSION", lambda p: p.write_text("2.1.0\n"))
        env = select(self.root, self.base, self.tmp)
        self.assertEqual((Path(env["CGSPEC_RELEASE"]) / "engine/VERSION").read_text().strip(), "2.1.0")

    def test_redirected_plugin_source_in_head_is_ignored(self):
        def redirect(p):
            data = json.loads(p.read_text())
            data["plugin_source"] = "/nonexistent/evil.git"
            write_json(p, data)
        self.edit("docs/_cgspec/project.json", redirect)
        env = select(self.root, self.base, self.tmp)
        self.assertTrue((Path(env["CGSPEC_RELEASE"]) / "engine/cgspec_hook.py").is_file())

    def test_unknown_base_falls_back_without_crashing(self):
        env = select(self.root, "0" * 40, self.tmp)
        self.assertEqual(env["CGSPEC_BASE"], "")
        self.assertTrue((Path(env["CGSPEC_RELEASE"]) / "engine/cgspec_hook.py").is_file())

    def test_workflow_runs_the_base_version_of_the_selector(self):
        workflow = (self.root / ".github/workflows/cgspec.yml").read_text()
        self.assertIn('git show "$B:.github/cgspec-select.sh"', workflow)
        self.assertIn('"$CGSPEC_RELEASE/engine/cgspec_hook.py"', workflow)
        self.assertNotIn("docs/_cgspec/01-engine/cgspec_hook.py ci", workflow)


if __name__ == "__main__":
    unittest.main()


class SelectorFallbackTests(unittest.TestCase):
    """The workflow's first step, run for real in a simulated GitHub checkout."""

    def run_block(self, workflow: str) -> str:
        lines = workflow.splitlines()
        start = next(i for i, l in enumerate(lines) if "Run the selection script as it was BEFORE" in l)
        block = []
        for line in lines[start:]:
            if line.strip().startswith("- name:"):
                break
            block.append(line[10:] if line.startswith(" " * 10) else line.strip())
        return "\n".join(block)

    def test_new_branch_push_uses_the_default_branch_selector(self):
        with TempDir() as tmp:
            source = make_release_source(tmp, ["2.0.0"])
            origin = tmp / "origin"
            origin.mkdir()
            git(origin, "init", "-q", "-b", "main")
            from tests.helpers import run_script
            run_script("install.py", "install", "--root", str(origin), "--profile", "headless", "--topology", "single",
                       "--tools", "git,ci", "--plugin-source", str(source))
            git(origin, "add", "-A")
            git(origin, "commit", "-q", "--no-verify", "-m", "install")
            work = tmp / "work"
            git(tmp, "clone", "-q", str(origin), str(work))
            git(work, "checkout", "-q", "-b", "feature")
            selector = work / ".github/cgspec-select.sh"
            os.chmod(selector, 0o644)
            selector.write_text("#!/bin/sh\necho AGENT SCRIPT RAN\necho CGSPEC_RELEASE=/tmp/fake >> \"$GITHUB_ENV\"\n")
            git(work, "add", "-A")
            git(work, "commit", "-q", "--no-verify", "-m", "tamper selector")
            script = self.run_block((work / ".github/workflows/cgspec.yml").read_text())
            script = script.replace("${{ github.event.pull_request.base.sha || github.event.before }}", "0" * 40)
            env_file = tmp / "env"
            env_file.write_text("")
            env = dict(os.environ, RUNNER_TEMP=str(tmp), GITHUB_ENV=str(env_file), DEFAULT_BRANCH="main",
                       EVENT_BASE="0" * 40)
            result = subprocess.run(["sh", "-c", script], cwd=work, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("AGENT SCRIPT RAN", result.stdout)
            self.assertNotIn("/tmp/fake", env_file.read_text())
