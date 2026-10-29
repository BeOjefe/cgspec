"""Safe test evolution through a real consumer adapter in disposable Git worktrees."""

from __future__ import annotations

import json
import shutil
import unittest

from tests.helpers import REPO, TempDir, git, git_project, write_json
from _lib import ci_gate, commit_trust, runner_contracts, test_evolution
from _lib.ci_gate import prove_failed
from _lib.gitview import View


class TestEvolutionIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = TempDir()
        self.root = self.temp.__enter__()
        git_project(self.root)
        tools = self.root / "tools"
        tools.mkdir()
        shutil.copy2(REPO / "tests/fixtures/semantic-python-adapter.py", tools / "semantic_adapter.py")
        for rel, text in {
            "tests/helper.py": "EXPECTED = 'fixed'\n",
            "tests/fixture.txt": "fixture-v1\n",
            "tests/imported.py": "VALUE = 1\n",
            "tests/snapshots/result.snap": "fixed\n",
            "pyproject.toml": "[tool.example]\nmode = 'strict'\n",
        }.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        self.test_file = self.root / "tests/check.py"
        self.test_file.write_text(self._test_source(), encoding="utf-8")
        project_path = self.root / "docs/_cgspec/project.json"
        project = json.loads(project_path.read_text())
        project["test_environments"] = [{
            "id": "python", "cwd": ".", "setup": ["python3", "-c", "pass"],
            "readiness": ["python3", "--version"], "inputs": ["tools/semantic_adapter.py"],
            "timeout_seconds": 10,
        }]
        project["test_runners"] = [{
            "id": "unit", "adapter": "cgspec-json",
            "command": ["python3", "{test_file}", "{report}"], "cwd": ".",
            "selection": "test_file", "applies_to": ["src/**"], "environment": "python",
            "timeout_seconds": 10, "isolation": "per-run-worktree", "report": "json", "artifacts": [],
            "semantics": {"adapter": "command-json-v1",
                          "command": ["python3", "tools/semantic_adapter.py", "{test_file}", "{test_id}"],
                          "inputs": ["tools/semantic_adapter.py"]},
        }]
        project["test_runners_approval"] = "trailer"
        write_json(project_path, project)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "failing selected test with semantic adapter")
        self.red = git(self.root, "rev-parse", "HEAD").stdout.strip()
        runner, environment, digest = runner_contracts.resolve(
            project, "unit", lambda rel: (self.root / rel).read_bytes())
        identity, problem = test_evolution.capture_at(
            self.root, self.red, runner, environment, "tests/check.py", "tests/check.py::test_original")
        self.assertIsNone(problem)
        (self.root / "src/fixed.txt").write_text("fixed\n", encoding="utf-8")
        git(self.root, "add", "src/fixed.txt")
        git(self.root, "commit", "-q", "-m", "fix product behavior")
        self.green = git(self.root, "rev-parse", "HEAD").stdout.strip()
        self.record = {
            "_file": "docs/_cgspec/06-evidence/tests/check.json", "test_id": "tests/check.py::test_original",
            "test_file": "tests/check.py", "failed_at": self.red, "runner_id": "unit", "runner_hash": digest,
            "selector": "tests/check.py", "command": runner_contracts.selected_command(runner, "tests/check.py"),
            "covers": ["src/fixed.txt"], "slice": "SLICE-001", "test_semantics": identity,
        }

    def tearDown(self):
        self.temp.__exit__(None, None, None)

    @staticmethod
    def _test_source() -> str:
        return (
            "# cgspec-dependency helper tests/helper.py\n"
            "# cgspec-dependency fixture tests/fixture.txt\n"
            "# cgspec-dependency import tests/imported.py\n"
            "# cgspec-dependency snapshot tests/snapshots/result.snap\n"
            "# cgspec-dependency config pyproject.toml\n"
            "import json, pathlib, sys\n\n"
            "def test_original():\n"
            "    return pathlib.Path('src/fixed.txt').exists()\n\n"
            "ok = test_original()\n"
            "pathlib.Path(sys.argv[1]).write_text(json.dumps({'selector': 'tests/check.py', "
            "'assertions': {'passed': int(ok), 'failed': int(not ok)}, "
            "'infrastructure': {'status': 'ok'}}))\n"
            "raise SystemExit(0 if ok else 1)\n"
        )

    def _commit_test(self, text: str, message: str) -> None:
        self.test_file.write_text(text, encoding="utf-8")
        git(self.root, "add", "tests/check.py")
        git(self.root, "commit", "-q", "-m", message)

    def _commit_record(self) -> str:
        record = {key: value for key, value in self.record.items() if key != "_file"}
        record.update(schema=1, passed_at=self.green, recorded="2026-10-28T00:00:00Z")
        write_json(self.root / self.record["_file"], record)
        git(self.root, "add", self.record["_file"])
        git(self.root, "commit", "-q", "-m", "record immutable red green proof")
        return git(self.root, "rev-parse", "HEAD").stdout.strip()

    def test_unrelated_addition_and_formatting_preserve_selected_proof(self):
        self._commit_test(self.test_file.read_text() + "\ndef test_unrelated():\n    return False\n",
                          "add unrelated coverage")
        self.assertIsNone(prove_failed(self.root, self.record))
        formatted = self.test_file.read_text().replace(
            "def test_original():\n    return pathlib.Path('src/fixed.txt').exists()",
            "def test_original( ):\n\n    return pathlib.Path( 'src/fixed.txt' ).exists()")
        self._commit_test(formatted, "format selected test")
        self.assertIsNone(prove_failed(self.root, self.record))

    def test_helper_fixture_import_snapshot_and_config_changes_invalidate(self):
        for rel in ("tests/helper.py", "tests/fixture.txt", "tests/imported.py",
                    "tests/snapshots/result.snap", "pyproject.toml"):
            with self.subTest(dependency=rel):
                git(self.root, "reset", "--hard", self.green)
                path = self.root / rel
                path.write_text(path.read_text() + "changed\n", encoding="utf-8")
                git(self.root, "add", rel)
                git(self.root, "commit", "-q", "-m", f"change {rel}")
                problem = prove_failed(self.root, self.record)
                self.assertIn("dependency closure changed", problem)

    def test_weakened_assertion_requires_fresh_proof_and_history_stays_unchanged(self):
        original_record = json.loads(json.dumps(self.record))
        weakened = self.test_file.read_text().replace(
            "return pathlib.Path('src/fixed.txt').exists()", "return True")
        self._commit_test(weakened, "weaken selected assertion")
        self.assertIn("test semantics", prove_failed(self.root, self.record))
        self.assertEqual(self.record, original_record)

    def test_unknown_semantic_adapter_fails_closed(self):
        project_path = self.root / "docs/_cgspec/project.json"
        project = json.loads(project_path.read_text())
        project["test_runners"][0].pop("semantics")
        project["test_environments"][0]["inputs"] = []
        write_json(project_path, project)
        self.test_file.write_text(self.test_file.read_text() + "\ndef test_other(): return True\n", encoding="utf-8")
        git(self.root, "add", "docs/_cgspec/project.json", "tests/check.py")
        git(self.root, "commit", "-q", "-m", "change tests without semantic adapter")
        runner, _, digest = runner_contracts.resolve(project, "unit")
        record = dict(self.record, runner_hash=digest)
        record.pop("test_semantics")
        self.assertTrue(any("approved semantic adapter" in problem for problem in
                            runner_contracts.pair_errors(project, record)))
        self.assertIn("configuration hash", prove_failed(self.root, record))

    def test_later_dependency_change_selects_existing_immutable_proof_for_ci_revalidation(self):
        base = self._commit_record()
        proof_path = self.root / self.record["_file"]
        data = json.loads(proof_path.read_text())
        data["covers"].append("src/other.txt")
        write_json(proof_path, data)
        git(self.root, "add", self.record["_file"])
        self.assertTrue(any("immutable historical" in problem for problem in
                            commit_trust.append_only(View.staged(self.root))))
        git(self.root, "reset", "--hard", base)
        helper = self.root / "tests/helper.py"
        helper.write_text("EXPECTED = 'changed'\n", encoding="utf-8")
        git(self.root, "add", "tests/helper.py")
        git(self.root, "commit", "-q", "-m", "change a proof dependency later")
        affected = ci_gate.affected_test_records(self.root, base)
        self.assertEqual([record["_file"] for record in affected], [self.record["_file"]])
        self.assertIn("dependency closure changed", prove_failed(self.root, affected[0]))

    def test_pre_semantic_record_cannot_escape_unknown_helper_invalidation(self):
        legacy = {key: value for key, value in self.record.items()
                  if key not in ("_file", "test_semantics")}
        legacy.update(schema=1, passed_at=self.green, recorded="2026-10-28T00:00:00Z")
        write_json(self.root / self.record["_file"], legacy)
        git(self.root, "add", self.record["_file"])
        git(self.root, "commit", "-q", "-m", "record pre-semantic proof")
        base = git(self.root, "rev-parse", "HEAD").stdout.strip()
        unknown_helper = self.root / "tests/unknown_helper.py"
        unknown_helper.write_text("VALUE = 2\n", encoding="utf-8")
        git(self.root, "add", "tests/unknown_helper.py")
        git(self.root, "commit", "-q", "-m", "change helper outside unknown closure")
        affected = ci_gate.affected_test_records(self.root, base)
        self.assertEqual([record["_file"] for record in affected], [self.record["_file"]])
        self.assertIn("semantic fingerprint and complete dependency closure",
                      prove_failed(self.root, affected[0]))

    def test_unknown_legacy_and_pre_semantics_closures_revalidate_on_helper_change(self):
        for named in (False, True):
            with self.subTest(named=named):
                record = {key: value for key, value in self.record.items() if key not in ("_file", "test_semantics")}
                if not named:
                    for key in ("runner_id", "runner_hash", "selector"):
                        record.pop(key)
                write_json(self.root / self.record["_file"], record)
                git(self.root, "add", "-A")
                git(self.root, "commit", "-q", "-m", "historical unknown closure")
                base = git(self.root, "rev-parse", "HEAD").stdout.strip()
                helper = self.root / "tests/helper.py"
                helper.write_text(helper.read_text() + "# evolved helper\n")
                git(self.root, "add", "-A")
                git(self.root, "commit", "-q", "-m", "change unrecorded helper")
                self.assertEqual([r["_file"] for r in ci_gate.affected_test_records(self.root, base)], [self.record["_file"]])
                from unittest.mock import patch
                with patch.object(ci_gate, "evaluate", return_value=[]), patch.object(ci_gate.checks, "verify_manifest_at", return_value=[]), \
                     patch.object(ci_gate.checks, "run", return_value=([], [])):
                    problems, _ = ci_gate.run(self.root, base)
                self.assertTrue(any("unknown dependency closure" in p for p in problems), problems)

    def test_fingerprints_hash_semantic_inputs_outside_environment_inputs(self):
        project = json.loads((self.root / "docs/_cgspec/project.json").read_text())
        runner = project["test_runners"][0]
        environment = dict(project["test_environments"][0], inputs=[])
        first = runner_contracts.fingerprints(runner, environment, lambda _: b"adapter-v1")
        second = runner_contracts.fingerprints(runner, environment, lambda _: b"adapter-v2")
        self.assertIn("tools/semantic_adapter.py", first["inputs"])
        self.assertNotEqual(first["inputs"], second["inputs"])

    def test_dependency_hashes_use_committed_bytes_even_if_setup_rewrites_helper(self):
        project = json.loads((self.root / "docs/_cgspec/project.json").read_text())
        runner = project["test_runners"][0]
        environment = dict(project["test_environments"][0], setup=["python3", "-c",
            "open('tests/helper.py', 'w').write('overwritten by setup\\n')"])
        identity, problem = test_evolution.capture_at(self.root, self.red, runner, environment,
                                                     "tests/check.py", self.record["test_id"])
        self.assertIsNone(problem)
        self.assertEqual(identity, self.record["test_semantics"])

    def test_strengthening_selected_assertion_requires_new_red_proof(self):
        stronger = self.test_file.read_text().replace("return pathlib.Path('src/fixed.txt').exists()",
            "return pathlib.Path('src/fixed.txt').exists() and pathlib.Path('src/fixed.txt').read_text() == 'fixed\\n'")
        self._commit_test(stronger, "strengthen selected assertion")
        self.assertIn("test semantics", prove_failed(self.root, self.record))

    def test_missing_and_malformed_dependency_inventories_are_unknown(self):
        identity = self.record["test_semantics"]
        self.assertTrue(test_evolution.known_closure(identity))
        from copy import deepcopy
        for dependencies in (None, [None], [{"path": "tests/helper.py"}], [{"path": "tests/helper.py", "kind": "helper", "sha256": "invalid"}]):
            broken = deepcopy(identity)
            if dependencies is None:
                broken.pop("dependencies")
            else:
                broken["dependencies"] = dependencies
            self.assertFalse(test_evolution.known_closure(broken))
            self.record["test_semantics"] = broken
            base = self._commit_record()
            helper = self.root / "tests/helper.py"
            helper.write_text(helper.read_text() + "# changed dependency\n")
            git(self.root, "add", "-A")
            git(self.root, "commit", "-q", "-m", "helper changed with unknown closure")
            self.assertEqual([r["_file"] for r in ci_gate.affected_test_records(self.root, base)], [self.record["_file"]])


if __name__ == "__main__":
    unittest.main()
