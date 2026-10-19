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
        self.source = make_release_source(self.tmp, ["0.2.0", "0.3.0"])
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
        (self.root / "README.md").write_text("project change\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "--no-verify", "-m", "project change")
        env = select(self.root, self.base, self.tmp)
        self.assertEqual(env["CGSPEC_BASE"], self.base)
        self.assertEqual((Path(env["CGSPEC_RELEASE"]) / "engine/VERSION").read_text().strip(), "0.2.0")

    def test_downgrade_in_head_is_ignored(self):
        self.edit("docs/_cgspec/01-engine/VERSION", lambda p: p.write_text("0.1.0\n"))
        env = select(self.root, self.base, self.tmp)
        self.assertEqual((Path(env["CGSPEC_RELEASE"]) / "engine/VERSION").read_text().strip(), "0.2.0")

    def test_upgrade_in_head_uses_the_newer_release(self):
        self.edit("docs/_cgspec/01-engine/VERSION", lambda p: p.write_text("0.3.0\n"))
        env = select(self.root, self.base, self.tmp)
        self.assertEqual((Path(env["CGSPEC_RELEASE"]) / "engine/VERSION").read_text().strip(), "0.3.0")

    def test_redirected_plugin_source_in_head_is_ignored(self):
        def redirect(p):
            data = json.loads(p.read_text())
            data["plugin_source"] = "/nonexistent/evil.git"
            write_json(p, data)
        self.edit("docs/_cgspec/project.json", redirect)
        env = select(self.root, self.base, self.tmp)
        self.assertTrue((Path(env["CGSPEC_RELEASE"]) / "engine/cgspec_hook.py").is_file())

    def test_unknown_base_cannot_take_plugin_source_from_head(self):
        env_file = self.tmp / "github_env"
        env_file.write_text("")
        env = dict(os.environ, EVENT_BASE="0" * 40, DEFAULT_BRANCH="", RUNNER_TEMP=str(self.tmp),
                   GITHUB_ENV=str(env_file))
        result = subprocess.run(["sh", str(self.root / ".github/cgspec-select.sh")], cwd=self.root, env=env,
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("trusted", result.stderr.lower())
        self.assertNotIn("CGSPEC_RELEASE=", env_file.read_text())

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

    def installed_checkout(self, tmp: Path) -> Path:
        source = make_release_source(tmp, ["0.2.0"])
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
        return work

    def run_workflow_selector(self, work: Path, tmp: Path, *, branch: str,
                              before: str = "0" * 40) -> subprocess.CompletedProcess:
        script = self.run_block((work / ".github/workflows/cgspec.yml").read_text())
        script = script.replace("${{ github.event.pull_request.base.sha || github.event.before }}", before)
        env_file = tmp / "env"
        env_file.write_text("")
        env = dict(os.environ, RUNNER_TEMP=str(tmp), GITHUB_ENV=str(env_file), DEFAULT_BRANCH="main",
                   EVENT_BASE=before, EVENT_REF=f"refs/heads/{branch}", EVENT_NAME="push")
        return subprocess.run(["sh", "-c", script], cwd=work, env=env, capture_output=True, text=True)

    def tamper_selector(self, work: Path) -> None:
        selector = work / ".github/cgspec-select.sh"
        os.chmod(selector, 0o644)
        selector.write_text("#!/bin/sh\necho AGENT SCRIPT RAN\necho CGSPEC_RELEASE=/tmp/fake >> \"$GITHUB_ENV\"\n")
        git(work, "add", "-A")
        git(work, "commit", "-q", "--no-verify", "-m", "tamper selector")

    def test_failed_fetch_rejects_stale_fetch_head(self):
        with TempDir() as tmp:
            work = self.installed_checkout(tmp)
            git(work, "checkout", "-q", "-b", "feature")
            self.tamper_selector(work)
            git(work, "fetch", "-q", "origin", "main")  # leaves a trusted but stale FETCH_HEAD
            git(work, "remote", "set-url", "origin", str(tmp / "missing-origin"))
            result = self.run_workflow_selector(work, tmp, branch="feature")
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("cannot fetch the default branch selector", result.stderr)
            self.assertNotIn("AGENT SCRIPT RAN", result.stdout)

    def test_force_push_to_default_branch_rejects_new_selector(self):
        with TempDir() as tmp:
            work = self.installed_checkout(tmp)
            self.tamper_selector(work)
            git(work, "remote", "set-url", "origin", str(work))  # default branch now resolves to HEAD
            result = self.run_workflow_selector(work, tmp, branch="main")
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("no trusted selector before this change", result.stderr)
            self.assertNotIn("AGENT SCRIPT RAN", result.stdout)

    def test_first_install_on_default_branch_requires_trusted_bootstrap(self):
        with TempDir() as tmp:
            work = self.installed_checkout(tmp)
            git(work, "remote", "set-url", "origin", str(work))
            result = self.run_workflow_selector(work, tmp, branch="main")
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("no trusted selector before this change", result.stderr)

    def test_preinstall_event_base_uses_default_branch_source(self):
        with TempDir() as tmp:
            trusted = make_release_source(tmp, ["0.2.0"])
            evil_parent = tmp / "evil"
            evil_parent.mkdir()
            evil = make_release_source(evil_parent, ["0.2.0"])
            origin = tmp / "origin"
            origin.mkdir()
            git(origin, "init", "-q", "-b", "main")
            (origin / "README.md").write_text("before CGSpec\n")
            git(origin, "add", "-A")
            git(origin, "commit", "-q", "-m", "baseline")
            before = git(origin, "rev-parse", "HEAD").stdout.strip()
            from tests.helpers import run_script
            run_script("install.py", "install", "--root", str(origin), "--profile", "headless", "--topology", "single",
                       "--tools", "git,ci", "--plugin-source", str(trusted))
            git(origin, "add", "-A")
            git(origin, "commit", "-q", "--no-verify", "-m", "install")
            work = tmp / "work"
            git(tmp, "clone", "-q", str(origin), str(work))
            git(work, "checkout", "-q", "-b", "feature")
            config = work / "docs/_cgspec/project.json"
            data = json.loads(config.read_text())
            data["plugin_source"] = str(evil)
            write_json(config, data)
            git(work, "add", "-A")
            git(work, "commit", "-q", "--no-verify", "-m", "redirect plugin source")
            result = self.run_workflow_selector(work, tmp, branch="feature", before=before)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            release = tmp / "cgspec-release"
            remote = git(release, "remote", "get-url", "origin").stdout.strip()
            self.assertEqual(remote, str(trusted))

    def test_new_branch_push_uses_the_default_branch_selector(self):
        with TempDir() as tmp:
            source = make_release_source(tmp, ["0.2.0"])
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
                       EVENT_BASE="0" * 40, EVENT_NAME="push", EVENT_REF="refs/heads/feature")
            result = subprocess.run(["sh", "-c", script], cwd=work, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("AGENT SCRIPT RAN", result.stdout)
            self.assertNotIn("/tmp/fake", env_file.read_text())
