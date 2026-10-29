"""Real subprocesses and revision-local Git trees exercise the strict proof path."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.helpers import git, write_json
from tests.unit import test_named_runners
from _lib.ci_gate import prove_failed
from _lib.runner_execution import run_detail
from _lib.runner_contracts import resolve


class ReproducibleProofTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_named_runners.NamedRunnerIntegrationTests("test_real_red_green_uses_assertion_report_in_isolated_revisions")
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.root, self.record = self.fixture.root, self.fixture.record
        self.project_path = self.root / "docs/_cgspec/project.json"

    def change_environment(self, **changes):
        project = json.loads(self.project_path.read_text())
        project["test_environments"][0].update(changes)
        write_json(self.project_path, project)
        git(self.root, "add", "docs/_cgspec/project.json")
        git(self.root, "commit", "-q", "-m", "configure environment")
        runner, environment, _ = resolve(project, "unit")
        runner, environment, _ = resolve(project, "unit", lambda rel: (self.root / rel).read_bytes())
        return runner, environment

    def test_red_green_persists_full_revision_and_phase_logs(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, CGSPEC_PROOF_DIR=tmp):
            self.assertIsNone(prove_failed(self.root, self.record))
            red, green = [json.loads((Path(tmp) / file).read_text()) for file in
                          sorted(p.name for p in Path(tmp).glob("*.json"))]
            by_phase = {item["phase"]: item for item in (red, green)}
            self.assertEqual(by_phase["red"]["result"], "ASSERTION_FAILED")
            self.assertEqual(by_phase["green"]["result"], "PASS")
            for item in (red, green):
                self.assertEqual(len(item["revision"]), 40)
                self.assertEqual(item["candidate_revision"], git(self.root, "rev-parse", "HEAD").stdout.strip())
                self.assertEqual(len(item["test_sha256"]), 64)
                self.assertEqual(len(item["report_sha256"]), 64)
                self.assertTrue(item["steps"][-1]["command"])
                self.assertIn("stderr", item["steps"][-1])

    def test_missing_module_and_failing_build_block(self):
        runner, environment = self.change_environment(setup=["python3", "-c", "import missing_cgspec_dependency"])
        detail = run_detail(self.root, "HEAD", runner, environment, "tests/check.py")
        self.assertEqual(detail["result"], "BLOCKED")
        self.assertIn("ModuleNotFoundError", detail["steps"][0]["stderr"])
        runner, environment = self.change_environment(setup=["python3", "-c", "pass"],
                                                      build=[["python3", "-c", "raise SystemExit(2)"]])
        self.assertEqual(run_detail(self.root, "HEAD", runner, environment, "tests/check.py")["result"], "BLOCKED")

    def test_unavailable_service_and_missing_browser_block(self):
        runner, environment = self.change_environment(readiness=["python3", "-c", "raise SystemExit(1)"])
        self.assertEqual(run_detail(self.root, "HEAD", runner, environment, "tests/check.py")["result"], "BLOCKED")
        runner, environment = self.change_environment(readiness=["no-such-browser-cgspec"])
        self.assertEqual(run_detail(self.root, "HEAD", runner, environment, "tests/check.py")["result"], "BLOCKED")

    def test_cleanup_overrides_green_and_retains_log(self):
        runner, environment = self.change_environment(cleanup=["python3", "-c", "import sys; print('cleanup failed'); sys.exit(3)"])
        detail = run_detail(self.root, "HEAD", runner, environment, "tests/check.py")
        self.assertEqual(detail["result"], "BLOCKED")
        self.assertIn("cleanup failed", detail["steps"][-1]["stdout"])

    def test_setup_cannot_rewrite_selected_test(self):
        runner, environment = self.change_environment(setup=["python3", "-c", "open('tests/check.py','a').write('# tampered\\n')"])
        detail = run_detail(self.root, "HEAD", runner, environment, "tests/check.py")
        self.assertEqual(detail["result"], "INVALID")

    def test_setup_cannot_add_uncommitted_source_at_red_revision(self):
        inject = ("import pathlib; p = pathlib.Path('src/login/fixed.txt'); "
                  "p.parent.mkdir(parents=True, exist_ok=True); p.write_text('injected\\n')")
        runner, environment = self.change_environment(setup=["python3", "-c", inject])
        detail = run_detail(self.root, self.fixture.failed_at, runner, environment, "tests/check.py")
        self.assertEqual(detail["result"], "INVALID")

    def test_setup_cross_scope_rename_is_detected(self):
        move = ("import pathlib, subprocess; pathlib.Path('lib').mkdir(exist_ok=True); "
                "subprocess.run(['git', 'mv', 'src/login/fixed.txt', 'lib/renamed.txt'])")
        runner, environment = self.change_environment(setup=["python3", "-c", move])
        detail = run_detail(self.root, "HEAD", runner, environment, "tests/check.py")
        self.assertEqual(detail["result"], "INVALID")
        self.assertIn("src/login/fixed.txt", detail.get("mutated", []))

    def test_setup_gitignored_source_injection_is_detected(self):
        (self.root / ".gitignore").write_text("src/login/secret.py\n")
        git(self.root, "add", ".gitignore")
        git(self.root, "commit", "-q", "-m", "ignore generated source")
        inject = ("import pathlib; p = pathlib.Path('src/login/secret.py'); "
                  "p.parent.mkdir(parents=True, exist_ok=True); p.write_text('x = 1\\n')")
        runner, environment = self.change_environment(setup=["python3", "-c", inject])
        detail = run_detail(self.root, "HEAD", runner, environment, "tests/check.py")
        self.assertEqual(detail["result"], "INVALID")
        self.assertIn("src/login/secret.py", detail.get("mutated", []))

    def test_root_level_literal_source_is_covered_by_integrity_check(self):
        (self.root / "README.md").write_text("initial\n")
        git(self.root, "add", "README.md")
        git(self.root, "commit", "-q", "-m", "root literal source")
        project = json.loads(self.project_path.read_text())
        environment = dict(project["test_environments"][0], setup=["python3", "-c", "open('README.md','a').write('mutated\\n')"])
        runner = dict(project["test_runners"][0], applies_to=["README.md"])
        detail = run_detail(self.root, "HEAD", runner, environment, "tests/check.py")
        self.assertEqual(detail["result"], "INVALID")
        self.assertIn("README.md", detail.get("mutated", []))

    def test_large_stdout_report_is_not_truncated_into_blocked(self):
        from _lib.runner_execution import run_detail
        project = json.loads(self.project_path.read_text())
        environment = project["test_environments"][0]
        runner = dict(project["test_runners"][0], report="stdout-json", command=["python3", "{test_file}"])
        (self.root / "tests/check.py").write_text(
            "import json\n"
            "print(json.dumps({'selector':'tests/check.py','assertions':{'passed':1,'failed':0},"
            "'infrastructure':{'status':'ok'},'padding':'x' * 70000}))\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "large stdout report")
        detail = run_detail(self.root, "HEAD", runner, environment, "tests/check.py")
        self.assertEqual(detail["result"], "PASS")

    def test_service_descendants_are_killed_after_launcher_exits(self):
        marker_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, marker_dir, True)
        marker = Path(marker_dir) / "survivor"
        child = "import os, time; time.sleep(2.0); open(os.environ['SURVIVOR'], 'w').write('x')"
        service = ["python3", "-c", f"import subprocess; subprocess.Popen(['python3','-c',{child!r}])"]
        runner, environment = self.change_environment(readiness=["python3", "--version"],
                                                      services=[service], variables={"SURVIVOR": str(marker)})
        run_detail(self.root, "HEAD", runner, environment, "tests/check.py")
        time.sleep(2.5)
        self.assertFalse(marker.exists(), "service descendant survived proof teardown")

    def test_timeout_kills_descendants_and_cleanup_still_runs(self):
        runner, environment = self.change_environment(setup=["python3", "-c", "import time; time.sleep(3)"],
                                                      timeout_seconds=1, cleanup=["python3", "-c", "print('closed')"])
        detail = run_detail(self.root, "HEAD", runner, environment, "tests/check.py")
        self.assertEqual(detail["result"], "TIMEOUT")
        self.assertEqual(detail["steps"][-1]["phase"], "cleanup")

    def test_missing_required_secret_is_blocked_without_leaking_value(self):
        runner, environment = self.change_environment(secrets=["CGSPEC_TEST_SECRET"])
        with patch.dict(os.environ, {"CGSPEC_TEST_SECRET": ""}):
            detail = run_detail(self.root, "HEAD", runner, environment, "tests/check.py")
        self.assertEqual(detail["result"], "BLOCKED")
        self.assertIn("CGSPEC_TEST_SECRET", detail["reason"])

    @unittest.skipUnless(shutil.which("npm") and shutil.which("node"), "Node/npm unavailable")
    def test_offline_locked_workspace_installs_revision_local_package(self):
        package = self.root / "packages/local"
        package.mkdir(parents=True)
        write_json(self.root / "package.json", {"name": "proof-fixture", "version": "1.0.0", "private": True,
                                                "workspaces": ["packages/*"]})
        write_json(package / "package.json", {"name": "revision-local", "version": "1.0.0", "main": "index.js"})
        (package / "index.js").write_text("module.exports = false;\n")
        subprocess.run(["npm", "install", "--package-lock-only", "--offline", "--ignore-scripts", "--no-audit"],
                       cwd=self.root, check=True, capture_output=True, timeout=30)
        (self.root / "tests/check.js").write_text(
            "const fs = require('fs'); const ok = require('revision-local'); "
            "fs.writeFileSync(process.argv[2], JSON.stringify({selector:'tests/check.js'," 
            "assertions:{passed:Number(ok),failed:Number(!ok)},infrastructure:{status:'ok'}})); "
            "process.exit(ok ? 0 : 1);\n")
        project = json.loads(self.project_path.read_text())
        project["test_environments"][0].update(network="offline-cache", inputs=["package-lock.json"],
                                               setup=["npm", "ci", "--offline", "--ignore-scripts", "--no-audit"],
                                               readiness=["node", "--version"])
        project["test_runners"][0]["command"] = ["node", "{test_file}", "{report}"]

        adapter = self.root / "tools/js-semantic.py"
        adapter.write_text("import hashlib,json,pathlib,sys\nprint(json.dumps({'schema':1,'test_id':sys.argv[2],"
                           "'semantic_fingerprint':hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest(),"
                           "'closure_complete':True,'dependencies':[]}))\n")
        project["test_runners"][0]["semantics"] = {
            "adapter": "command-json-v1", "command": ["python3", "tools/js-semantic.py", "{test_file}", "{test_id}"],
            "inputs": ["tools/js-semantic.py"]}
        write_json(self.project_path, project)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "offline workspace red")
        red = git(self.root, "rev-parse", "HEAD").stdout.strip()
        (package / "index.js").write_text("module.exports = true;\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "offline workspace green")
        runner, environment, digest = resolve(project, "unit", lambda rel: (self.root / rel).read_bytes())
        from _lib.runner_contracts import selected_command
        record = dict(self.record, failed_at=red, test_file="tests/check.js", selector="tests/check.js",
                      runner_hash=digest, command=selected_command(runner, "tests/check.js"))

        from _lib.test_evolution import capture_at
        identity, problem = capture_at(self.root, red, runner, environment, record["test_file"], record["test_id"])
        self.assertIsNone(problem)
        record["test_semantics"] = identity
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, CGSPEC_PROOF_DIR=temp):
            self.assertIsNone(prove_failed(self.root, record))


if __name__ == "__main__":
    unittest.main()
