"""Assertion-aware reports and isolated execution of approved named runners."""

from __future__ import annotations

import json
import hashlib
import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path

from .gitview import git
from .globs import match_any


def _vitest(report: dict) -> tuple[int, int] | None:
    if report.get("unhandledErrors") or report.get("errors"):
        return None
    if report.get("success") is True and report.get("numFailedTests"):
        return None
    if report.get("numRuntimeErrorTestSuites", 0) or report.get("numPendingTestSuites", 0):
        return None
    if not isinstance(report.get("testResults"), list):
        return None
    if any(not isinstance(suite, dict) or suite.get("message") or suite.get("status") == "failed" and
           not suite.get("assertionResults") for suite in report["testResults"]):
        return None
    assertions = [item for suite in report.get("testResults", []) if isinstance(suite, dict)
                  for item in suite.get("assertionResults", []) if isinstance(item, dict)]
    statuses = [a.get("status") for a in assertions]
    if not statuses or any(s not in ("passed", "failed") for s in statuses):
        return None
    if report.get("numTotalTests") != len(statuses) or report.get("numFailedTests") != statuses.count("failed"):
        return None
    for assertion in assertions:
        if assertion["status"] == "failed" and (not assertion.get("failureMessages") or any(
                not isinstance(message, str) or "AssertionError" not in message
                for message in assertion["failureMessages"])):
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
            if not errors or not all(isinstance(error, dict) and any(
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


def _command(argv: list[str], cwd: Path, env: dict, timeout: int, full_stdout: bool = False) -> dict:
    """Capture output and terminate the entire process group on timeout."""
    started = time.monotonic()
    try:
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                start_new_session=True)
    except OSError as exc:
        return {"command": argv, "exit_code": None, "status": "BLOCKED", "stdout": "", "stderr": str(exc)}
    try:
        out, err = proc.communicate(timeout=timeout)
        status = "DONE"
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        out, err = proc.communicate()
        status = "TIMEOUT"
    detail = {"command": argv, "exit_code": proc.returncode, "status": status,
            "stdout": out.decode("utf-8", "replace")[-65536:], "stderr": err.decode("utf-8", "replace")[-65536:],
            "duration_seconds": round(time.monotonic() - started, 3)}
    if full_stdout:
        detail["_report_bytes"] = out
    return detail


def _record(detail: dict, step: dict, phase: str, sensitive: list[str]) -> None:
    step["phase"] = phase
    for stream in ("stdout", "stderr"):
        for value in sensitive:
            step[stream] = step[stream].replace(value, "[REDACTED]")
    detail["steps"].append(step)


def _is_git_internal(rel: str) -> bool:
    return rel == ".git" or rel.startswith(".git/")


def _walk_scope(tree: Path, scope: list[str]) -> dict:
    """Hash every file under the runner's scope, gitignored or not, from the worktree disk."""
    hashes = {}
    for pattern in scope:
        index = min((i for i, char in enumerate(pattern) if char in "*?["), default=len(pattern))
        if index == len(pattern):  # literal path with no glob characters
            if not _is_git_internal(pattern):
                path = tree / pattern
                if path.is_file():
                    hashes[pattern] = hashlib.sha256(path.read_bytes()).hexdigest()
            continue
        base = pattern[: index]
        if "/" in base:
            base = base[: base.rfind("/")]
        base_path = tree if base in ("", ".") else tree / base
        if not base_path.is_dir():
            continue
        for path in base_path.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(tree).as_posix()
            if _is_git_internal(rel):
                continue
            if match_any(rel, scope):
                hashes[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def _scope_mutations(before: dict, after: dict) -> list[str]:
    added = [path for path in after if path not in before]
    removed = [path for path in before if path not in after]
    changed = [path for path in before if path in after and before[path] != after[path]]
    return sorted(added + removed + changed)


def _test(tree: Path, cwd: Path, report_path: Path, runner: dict, env: dict,
          test_file: str, detail: dict, sensitive: list[str], state: dict) -> None:
    mutated = _scope_mutations(state["source_before"], _walk_scope(tree, state["scope"]))
    if mutated:
        detail["mutated"] = mutated
        detail.update(reason=f"setup changed source scope ({mutated[0]})", result="INVALID")
        return
    command = [part.replace("{test_file}", test_file).replace("{report}", str(report_path))
               for part in runner["command"]]
    step = _command(command, cwd, env, runner["timeout_seconds"], full_stdout=runner["report"] == "stdout-json")
    raw_stdout = step.pop("_report_bytes", b"")
    _record(detail, step, "test", sensitive)
    if step["status"] != "DONE":
        detail["result"] = step["status"]
        return
    raw = report_path.read_bytes() if runner["report"] == "json" and report_path.is_file() else raw_stdout
    detail["report_sha256"] = hashlib.sha256(raw).hexdigest()
    try:
        report = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        detail["reason"] = "missing or malformed structured report"
        return
    outcome = classify(runner["adapter"], report, step["exit_code"], test_file)
    detail["result"] = "BLOCKED" if outcome == "INFRASTRUCTURE_ERROR" else outcome
    for pattern in runner.get("artifacts", []):
        for path in cwd.glob(pattern):
            if path.is_file() and tree in path.resolve().parents:
                detail.setdefault("artifacts", {})[str(path.relative_to(tree))] = hashlib.sha256(path.read_bytes()).hexdigest()


def _execute(tree: Path, temp: Path, runner: dict, environment: dict, test_file: str,
             detail: dict, state: dict) -> None:
    env = state["env"]
    cwd, runner_cwd = _inside(tree, environment["cwd"]), _inside(tree, runner["cwd"])
    state["cwd"] = cwd
    if not cwd or not runner_cwd or not cwd.is_dir() or not runner_cwd.is_dir():
        detail["reason"] = "working directory missing or escapes checkout"
        return
    missing = [key for key in environment.get("secrets", []) if not env.get(key)]
    if missing:
        detail["reason"] = "missing required secret references: " + ", ".join(missing)
        return
    for label, argv in [("setup", environment["setup"])] + [("build", a) for a in environment.get("build", [])]:
        step = _command(argv, cwd, env, environment["timeout_seconds"])
        _record(detail, step, label, state["sensitive"])
        if step["status"] != "DONE" or step["exit_code"]:
            detail["result"] = "TIMEOUT" if step["status"] == "TIMEOUT" else "BLOCKED"
            return
    for argv in environment.get("services", []):
        log = open(temp / f"service-{len(state['services'])}.log", "wb+")
        state["logs"].append(log)
        state["services"].append(subprocess.Popen(argv, cwd=cwd, env=env, stdout=log,
                                                   stderr=subprocess.STDOUT, start_new_session=True))
    step = _command(environment["readiness"], cwd, env, environment["timeout_seconds"])
    _record(detail, step, "readiness", state["sensitive"])
    if step["status"] != "DONE" or step["exit_code"]:
        detail["result"] = "TIMEOUT" if step["status"] == "TIMEOUT" else "BLOCKED"
    elif any(service.poll() is not None for service in state["services"]):
        detail["reason"] = "service exited before test execution"
    else:
        _test(tree, runner_cwd, temp / "report.json", runner, env, test_file, detail, state["sensitive"], state)


def _teardown(root: Path, tree: Path, environment: dict, detail: dict, state: dict) -> None:
    for service in state["services"]:
        try:
            os.killpg(service.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        if service.poll() is None:
            service.wait()
    for log in state["logs"]:
        log.flush()
        log.seek(0)
        output = log.read().decode("utf-8", "replace")[-65536:]
        for value in state["sensitive"]:
            output = output.replace(value, "[REDACTED]")
        detail["steps"].append({"phase": "service", "log": output})
        log.close()
    cwd = state.get("cwd")
    if environment.get("cleanup") and cwd and cwd.is_dir():
        step = _command(environment["cleanup"], cwd, state["env"], environment["timeout_seconds"])
        _record(detail, step, "cleanup", state["sensitive"])
        if step["status"] != "DONE" or step["exit_code"]:
            detail["result"] = "TIMEOUT" if step["status"] == "TIMEOUT" else "BLOCKED"
    git(root, "worktree", "remove", "--force", str(tree))


def run_detail(root: Path, rev: str, runner: dict, environment: dict, test_file: str) -> dict:
    """Execute only committed revision content, retaining diagnostics after teardown."""
    resolved = git(root, "rev-parse", "--verify", f"{rev}^{{commit}}")
    revision = resolved.stdout.strip() if resolved.returncode == 0 else ""
    detail = {"revision": revision, "runner_id": runner.get("id"), "environment_id": environment.get("id"),
              "network": environment.get("network"), "test_file": test_file, "steps": [], "result": "BLOCKED"}
    if not revision:
        detail["reason"] = "invalid revision"
        return detail
    from .runner_contracts import fingerprints
    def reader(rel):
        shown = git(root, "show", f"{revision}:{rel}", binary=True)
        if shown.returncode:
            raise ValueError(f"missing committed input {rel}")
        return shown.stdout
    try:
        detail["fingerprints"] = fingerprints(runner, environment, reader)
        detail["test_sha256"] = hashlib.sha256(reader(test_file)).hexdigest()
    except ValueError as exc:
        detail["reason"] = str(exc)
        return detail
    with tempfile.TemporaryDirectory(prefix="cgspec-runner-") as directory:
        temp = Path(directory)
        tree = temp / "tree"
        if git(root, "worktree", "add", "--detach", "-q", str(tree), revision).returncode != 0:
            detail["reason"] = "revision checkout failed"
            return detail
        env = os.environ.copy()
        for key in ("NODE_PATH", "PYTHONPATH", "VIRTUAL_ENV", "npm_config_prefix", "CGSPEC_PROOF_DIR"):
            env.pop(key, None)
        env.update(environment.get("variables", {}))
        if environment.get("network") == "offline-cache":
            env.update(npm_config_offline="true", PIP_NO_INDEX="1")
        state = {"env": env, "sensitive": [env[key] for key in environment.get("secrets", []) if env.get(key)],
                 "services": [], "logs": [],
                 "scope": list(runner.get("applies_to", [])) + [test_file],
                 "source_before": _walk_scope(tree, list(runner.get("applies_to", [])) + [test_file])}
        try:
            _execute(tree, temp, runner, environment, test_file, detail, state)
        except (OSError, ValueError) as exc:
            detail["reason"] = f"execution failed: {exc}"
        finally:
            _teardown(root, tree, environment, detail, state)
    return detail


def run_at(root: Path, rev: str, runner: dict, environment: dict, test_file: str) -> str:
    return run_detail(root, rev, runner, environment, test_file)["result"]
