"""Assertion-aware reports and isolated execution of approved named runners."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from .gitview import git


def _vitest(report: dict) -> tuple[int, int] | None:
    if not isinstance(report.get("testResults"), list):
        return None
    assertions = [item for suite in report.get("testResults", []) if isinstance(suite, dict)
                  for item in suite.get("assertionResults", []) if isinstance(item, dict)]
    statuses = [a.get("status") for a in assertions]
    if not statuses or any(s not in ("passed", "failed") for s in statuses):
        return None
    if report.get("numTotalTests") != len(statuses) or report.get("numFailedTests") != statuses.count("failed"):
        return None
    return statuses.count("passed"), statuses.count("failed")


def _playwright(report: dict) -> tuple[int, int] | None:
    if report.get("errors") or not isinstance(report.get("suites"), list):
        return None
    def suites(items):
        for suite in items:
            yield suite
            yield from suites(suite.get("suites", []))

    tests = [test for suite in suites(report["suites"])
             for spec in suite.get("specs", []) for test in spec.get("tests", [])]
    if not tests or any(not isinstance(test.get("results"), list) or not test["results"] or
                        test.get("expectedStatus", "passed") != "passed" for test in tests):
        return None
    results = [test["results"][-1].get("status") for test in tests]
    if not results or any(s not in ("passed", "failed") for s in results):
        return None
    for test in tests:
        result = test["results"][-1]
        if result["status"] == "failed":
            errors = result.get("errors") or [result.get("error")]
            if not any(isinstance(error, dict) and any(
                    marker in str(error.get("message", "")) for marker in ("expect(", "AssertionError", "AssertionError:")
                    ) for error in errors):
                return None
    stats = report.get("stats")
    if stats is not None and (not isinstance(stats, dict) or stats.get("unexpected") != results.count("failed")):
        return None
    return results.count("passed"), results.count("failed")


def classify(adapter: str, report: object, exit_code: int, selector: str | None = None) -> str:
    """An assertion failure is not an infrastructure failure or merely a nonzero exit."""
    if not isinstance(report, dict) or not isinstance(exit_code, int):
        return "INFRASTRUCTURE_ERROR"
    counts = None
    try:
        if selector is not None:
            if adapter == "cgspec-json" and report.get("selector") != selector:
                return "INFRASTRUCTURE_ERROR"
            suites = report.get("testResults" if adapter == "vitest-json" else "suites", [])
            if adapter in ("vitest-json", "playwright-json") and (
                    not isinstance(suites, list) or len(suites) != 1 or
                    any(not isinstance(s, dict) or not (reported := s.get("name" if adapter == "vitest-json" else "file"))
                        or not isinstance(reported, str) or not (
                            reported.endswith("/" + selector) or reported == selector or
                            selector.endswith("/" + reported)) for s in suites)):
                return "INFRASTRUCTURE_ERROR"
        if adapter == "vitest-json":
            counts = _vitest(report)
        elif adapter == "playwright-json":
            counts = _playwright(report)
        elif adapter == "cgspec-json":
            assertions = report.get("assertions", {})
            infrastructure = report.get("infrastructure", {})
            if isinstance(assertions, dict) and isinstance(infrastructure, dict) and infrastructure.get("status") == "ok":
                passed, failed = assertions.get("passed"), assertions.get("failed")
                if isinstance(passed, int) and not isinstance(passed, bool) and isinstance(failed, int) and \
                        not isinstance(failed, bool) and passed >= 0 and failed >= 0 and passed + failed:
                    counts = passed, failed
    except (TypeError, ValueError, KeyError, IndexError, AttributeError):
        return "INFRASTRUCTURE_ERROR"
    if not counts:
        return "INFRASTRUCTURE_ERROR"
    passed, failed = counts
    if failed and exit_code != 0:
        return "ASSERTION_FAILED"
    if passed and not failed and exit_code == 0:
        return "PASS"
    return "INFRASTRUCTURE_ERROR"


def _inside(tree: Path, cwd: str) -> Path | None:
    path = (tree / cwd).resolve()
    return path if path == tree or tree in path.parents else None


def run_at(root: Path, rev: str, runner: dict, environment: dict, test_file: str) -> str:
    """Run each revision in its own disposable worktree and output directory."""
    with tempfile.TemporaryDirectory(prefix="cgspec-runner-") as temp:
        tree = Path(temp) / "tree"
        report_path = Path(temp) / "report.json"
        if git(root, "worktree", "add", "--detach", "-q", str(tree), rev).returncode != 0:
            return "INFRASTRUCTURE_ERROR"
        try:
            env_cwd, runner_cwd = _inside(tree, environment["cwd"]), _inside(tree, runner["cwd"])
            if not env_cwd or not runner_cwd or not env_cwd.is_dir() or not runner_cwd.is_dir():
                return "INFRASTRUCTURE_ERROR"
            for argv in (environment["setup"], environment["readiness"]):
                result = subprocess.run(argv, cwd=env_cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                        timeout=environment["timeout_seconds"], check=False)
                if result.returncode:
                    return "INFRASTRUCTURE_ERROR"
            command = [part.replace("{test_file}", test_file).replace("{report}", str(report_path))
                       for part in runner["command"]]
            result = subprocess.run(command, cwd=runner_cwd, capture_output=True,
                                    timeout=runner["timeout_seconds"], check=False)
            raw = report_path.read_bytes() if runner["report"] == "json" and report_path.is_file() else result.stdout
            try:
                report = json.loads(raw)
            except (ValueError, UnicodeDecodeError):
                return "INFRASTRUCTURE_ERROR"
            return classify(runner["adapter"], report, result.returncode, test_file)
        except (OSError, subprocess.TimeoutExpired):
            return "INFRASTRUCTURE_ERROR"
        finally:
            git(root, "worktree", "remove", "--force", str(tree))
