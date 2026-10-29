"""Read-only adoption discovery and polyrepo readiness (issue #36)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from tests.helpers import TempDir, git, git_live, git_project, install, make_slice, run_script, snapshot_tree
from _lib.common import EXIT_BLOCK
from _lib.schema import validate_named


def adopt(root: Path, *args: str):
    return run_script("cgspec_hook.py", "adopt", *args, "--root", str(root))


class AdoptionDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def discover(self, *args: str) -> dict:
        result = adopt(self.root, "discover", *args)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_single_underway_repo_is_observed(self):
        git_project(self.root)
        (self.root / "src/a.ts").write_text("export const a = 2;\n")
        (self.root / "notes.txt").write_text("work in progress\n")
        data = self.discover()
        self.assertEqual(len(data["repos"]), 1)
        repo = data["repos"][0]
        self.assertTrue(repo["reachable"])
        self.assertEqual(repo["git"]["branch"], "main")
        self.assertEqual(repo["git"]["head"], git(self.root, "rev-parse", "HEAD").stdout.strip())
        self.assertIn("src/a.ts", repo["dirty"]["modified"])
        self.assertIn("notes.txt", repo["dirty"]["untracked"])
        self.assertTrue(repo["cgspec"]["installed"])
        for field in ("branch", "head", "dirty", "cgspec"):
            self.assertEqual(repo["facts"][field], "observed")

    def test_unavailable_repo_blocks_only_dependent_work(self):
        git_project(self.root)
        (self.root / "tests").mkdir()
        (self.root / "tests/test_a.py").write_text("def test_a():\n    assert True\n")
        unrelated = self.root / "repos/c"
        unrelated.mkdir(parents=True)
        git(unrelated, "init", "-q", "-b", "main")
        make_slice(self.root)
        result = adopt(self.root, "ready", "--slice", "SLICE-001", "--repos", ".,repos/b")
        self.assertEqual(result.returncode, EXIT_BLOCK, result.stdout + result.stderr)
        lines = result.stdout.splitlines()
        self.assertIn("- .: OK owner=agent timing=before_proof", lines)
        blocked = [line for line in lines if line.startswith("- repos/b:")]
        self.assertEqual(len(blocked), 1, result.stdout)
        self.assertIn("BLOCKED owner=user timing=before_start", blocked[0])
        self.assertIn("repos/b is unreachable (missing)", blocked[0])
        self.assertNotIn("repos/c", result.stdout)  # unrelated repos are not judged
        self.assertNotIn("PASS", result.stdout)

        data = self.discover("--repos", "repos/b")
        missing = [r for r in data["repos"] if r.get("requested") == "repos/b"]
        self.assertEqual(missing[0], {"root": str((self.root / "repos/b").resolve()), "reachable": False,
                                      "reason": "missing", "requested": "repos/b"})
        self.assertEqual(data["facts_kinds"]["unreachable"], 1)

    def test_workspace_of_repos_and_a_plain_folder(self):
        for name in ("api", "web"):
            (self.root / name).mkdir()
            git(self.root / name, "init", "-q", "-b", "main")
        (self.root / "notes").mkdir()
        (self.root / "api/node_modules/dep").mkdir(parents=True)
        git(self.root / "api/node_modules/dep", "init", "-q")
        data = self.discover("--repos", "notes")
        roots = {Path(r["root"]).name: r for r in data["repos"]}
        self.assertEqual(set(roots), {"api", "web", "notes"})
        self.assertEqual(roots["notes"]["reason"], "not a git root")
        self.assertEqual(roots["api"]["git"]["head"], None)  # no commit yet: unknown, never invented
        self.assertEqual(roots["api"]["facts"]["head"], "unknown")

    def test_discover_is_read_only(self):
        git_project(self.root)
        (self.root / "src/a.ts").write_text("export const a = 3;\n")
        before = snapshot_tree(self.root)
        self.discover("--repos", "missing-repo")
        self.assertEqual(snapshot_tree(self.root), before)

    def test_json_out_writes_a_valid_map(self):
        git_project(self.root)
        (self.root / ".github/workflows").mkdir(parents=True, exist_ok=True)
        (self.root / ".github/workflows/ci.yml").write_text("on: push\n")
        out = self.root / ".cgspec-scratch/adoption-map.json"
        printed = self.discover("--repos", ".,gone", "--json-out", str(out))
        saved = json.loads(out.read_text())
        self.assertEqual(validate_named(saved, "adoption-map"), [])
        self.assertEqual(saved["repos"], printed["repos"])
        repo = next(r for r in saved["repos"] if r["reachable"])
        self.assertEqual(repo["facts"]["ci"], "inferred")  # CI files exist; behavior unproven
        bad = dict(saved, repos=[{"root": "x", "reachable": False}])
        self.assertTrue(validate_named(bad, "adoption-map"))

    def test_first_post_adoption_change_runs_real_hooks(self):
        git(self.root, "init", "-q", "-b", "main")
        result = install(self.root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        (self.root / "README.md").write_text("# Project\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "adopted scaffold")
        self.assertTrue((self.root / ".git/hooks/pre-commit").is_file())
        (self.root / "README.md").write_text("# Project\n\nAdopted.\n")
        tier = run_script("cgspec_hook.py", "tier", "set", "--tier", "T0", "--reason", "harmless doc change",
                          "--files", "README.md", "--verify", "commit hook check", "--root", str(self.root))
        self.assertEqual(tier.returncode, 0, tier.stdout + tier.stderr)
        git_live(self.root, "add", "README.md", "docs/_cgspec/07-state/tier.json")
        commit = git_live(self.root, "commit", "-m", "docs: first post-adoption change")
        self.assertIn("CGSpec commit check passed", commit.stdout + commit.stderr)
        ready = adopt(self.root, "ready", "--repos", ".,absent")
        self.assertNotEqual(ready.returncode, 0)  # --slice is required
        make_slice(self.root)
        ready = adopt(self.root, "ready", "--slice", "SLICE-001", "--repos", "absent")
        self.assertEqual(ready.returncode, EXIT_BLOCK)
        self.assertNotIn("OK", ready.stdout)
        self.assertNotIn("PASS", ready.stdout)


if __name__ == "__main__":
    unittest.main()
