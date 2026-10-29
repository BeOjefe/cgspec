"""Language-independent semantic test identity and dependency-closure checks.

The engine owns the JSON contract and comparison.  An approved consumer adapter
owns language-specific discovery and canonicalization.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path, PurePosixPath

from .gitview import git

DEPENDENCY_KINDS = {"helper", "fixture", "import", "snapshot", "config"}


def _inside(tree: Path, rel: str) -> Path | None:
    path = (tree / rel).resolve()
    return path if path == tree or tree in path.parents else None


def _relative_path(value: object) -> str | None:
    if not isinstance(value, str) or not value or "\\" in value:
        return None
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or value.startswith("./"):
        return None
    return path.as_posix()


def known_closure(recorded: object) -> bool:
    """Missing or malformed closure metadata can never narrow invalidation."""
    if not isinstance(recorded, dict) or recorded.get("adapter") != "command-json-v1":
        return False
    digest = recorded.get("fingerprint")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        return False
    dependencies = recorded.get("dependencies")
    if not isinstance(dependencies, list):
        return False
    seen = set()
    for item in dependencies:
        if not isinstance(item, dict) or set(item) != {"path", "kind", "sha256"}:
            return False
        path, digest = _relative_path(item["path"]), item["sha256"]
        if (path is None or path in seen or not isinstance(item["kind"], str) or item["kind"] not in DEPENDENCY_KINDS or
                not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest)):
            return False
        seen.add(path)
    return True


def _identity(report: object, tree: Path, test_id: str, reader=None) -> tuple[dict | None, str | None]:
    if not isinstance(report, dict) or set(report) != {
            "schema", "test_id", "semantic_fingerprint", "closure_complete", "dependencies"}:
        return None, "semantic adapter returned an unknown or incomplete report shape"
    if report.get("schema") != 1 or report.get("test_id") != test_id:
        return None, "semantic adapter did not return the selected stable test ID"
    fingerprint = report.get("semantic_fingerprint")
    if not isinstance(fingerprint, str) or len(fingerprint) != 64 or any(c not in "0123456789abcdef" for c in fingerprint):
        return None, "semantic adapter returned an invalid semantic fingerprint"
    if report.get("closure_complete") is not True:
        return None, "semantic adapter did not attest a complete relevant dependency closure"
    raw_dependencies = report.get("dependencies")
    if not isinstance(raw_dependencies, list):
        return None, "semantic adapter dependencies must be an array"
    dependencies, seen = [], set()
    for item in raw_dependencies:
        if not isinstance(item, dict) or set(item) != {"path", "kind"}:
            return None, "semantic adapter dependency entries need exactly path and kind"
        rel, kind = _relative_path(item.get("path")), item.get("kind")
        if rel is None or not isinstance(kind, str) or kind not in DEPENDENCY_KINDS or rel in seen:
            return None, "semantic adapter returned an invalid or duplicate dependency"
        target = _inside(tree, rel)
        if target is None or not target.is_file():
            return None, f"semantic dependency {rel} is missing or escapes the checked revision"
        raw = reader(rel) if reader else target.read_bytes()
        if raw is None:
            return None, f"semantic dependency {rel} is absent from the committed revision"
        seen.add(rel)
        dependencies.append({"path": rel, "kind": kind,
                             "sha256": hashlib.sha256(raw).hexdigest()})
    dependencies.sort(key=lambda item: (item["path"], item["kind"]))
    return {"adapter": "command-json-v1", "fingerprint": fingerprint,
            "dependencies": dependencies}, None


def capture_at(root: Path, rev: str, runner: dict, environment: dict,
               test_file: str, test_id: str) -> tuple[dict | None, str | None]:
    """Run the approved semantics adapter at one revision and return canonical identity."""
    semantics = runner.get("semantics")
    if not isinstance(semantics, dict) or semantics.get("adapter") != "command-json-v1":
        return None, "runner has no supported semantic test adapter; dependency impact is unknown"
    with tempfile.TemporaryDirectory(prefix="cgspec-semantics-") as temp:
        tree = Path(temp) / "tree"
        if git(root, "worktree", "add", "--detach", "-q", str(tree), rev).returncode != 0:
            return None, f"{rev[:10]} cannot be checked out for semantic inspection"
        try:
            env_cwd, runner_cwd = _inside(tree, environment["cwd"]), _inside(tree, runner["cwd"])
            if not env_cwd or not runner_cwd or not env_cwd.is_dir() or not runner_cwd.is_dir():
                return None, "semantic adapter working directory is unavailable"
            for argv in (environment["setup"], environment["readiness"]):
                result = subprocess.run(argv, cwd=env_cwd, stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL, timeout=environment["timeout_seconds"], check=False)
                if result.returncode:
                    return None, "semantic adapter environment setup or readiness failed"
            command = [part.replace("{test_file}", test_file).replace("{test_id}", test_id)
                       for part in semantics["command"]]
            result = subprocess.run(command, cwd=runner_cwd, capture_output=True,
                                    timeout=runner["timeout_seconds"], check=False)
            if result.returncode:
                return None, "semantic adapter failed"
            try:
                report = json.loads(result.stdout)
            except (ValueError, UnicodeDecodeError):
                return None, "semantic adapter did not return valid JSON on stdout"
            def reader(rel):
                shown = git(root, "show", f"{rev}:{rel}", binary=True)
                return shown.stdout if shown.returncode == 0 else None
            return _identity(report, tree, test_id, reader)
        except (OSError, subprocess.TimeoutExpired, KeyError, TypeError) as exc:
            return None, f"semantic adapter could not run: {exc}"
        finally:
            git(root, "worktree", "remove", "--force", str(tree))


def preservation_error(root: Path, failed_at: str, runner: dict, environment: dict,
                       test_file: str, test_id: str, recorded: object, candidate: str = "HEAD") -> str | None:
    """Require the recorded identity and complete closure at red and green revisions."""
    if not isinstance(recorded, dict):
        return "proof has no recorded semantic test identity and dependency closure"
    before, problem = capture_at(root, failed_at, runner, environment, test_file, test_id)
    if problem:
        return f"red revision semantic inspection failed: {problem}"
    if before != recorded:
        return "recorded semantic test identity does not match the red revision"
    after, problem = capture_at(root, candidate, runner, environment, test_file, test_id)
    if problem:
        return f"green revision semantic inspection failed: {problem}"
    if after != before:
        return "test semantics or relevant dependency closure changed; fresh red/green proof is required"
    return None
