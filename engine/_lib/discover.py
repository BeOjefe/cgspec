"""Read-only adoption discovery: an observed project map and per-repo readiness (issue #36).

Nothing here writes to a repository. Git is called only with read commands and
`--no-optional-locks`, so `git status` does not refresh the index either. Every field
value carries a fact kind: `observed` (read from disk or git), `inferred` (present but its
behavior is unproven, such as CI files), `unknown` (not determinable) or `unreachable`.
"""

from __future__ import annotations

import fnmatch
import json
import os
import shutil
import subprocess
from pathlib import Path

from . import tiers
from .common import EXIT_BLOCK, EXIT_OK, PROJECT_FILE, CgspecError, utc_now
from .gitview import git

FACT_KINDS = ("observed", "inferred", "unknown", "unreachable")
FIELDS = ("branch", "head", "dirty", "worktrees", "cgspec", "docs", "tests", "ci")
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", ".cgspec-scratch", "__pycache__"}
TEST_FILES = ("*_test.py", "test_*.py", "*.test.ts", "*.test.tsx", "*.spec.ts")
WALK_LIMIT = 20000
TIMEOUT = 30


def _git(path: Path, *args: str) -> str | None:
    """stdout of a read-only git command, or None when git is missing, fails or times out."""
    try:
        result = git(path, "--no-optional-locks", *args, timeout=TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None


def git_available() -> bool:
    return shutil.which("git") is not None


def git_ok(root: Path) -> bool:
    return (_git(root, "rev-parse", "--is-inside-work-tree") or "").strip() == "true"


def git_root(path: Path) -> bool:
    """True when `path` is itself the top of a work tree, not merely inside one."""
    top = _git(path, "rev-parse", "--show-toplevel")
    return top is not None and Path(top.strip()).resolve() == path.resolve()


def unreachable_repo(path: Path, reason: str) -> dict:
    return {"root": str(path), "reachable": False, "reason": reason}


def _walk(path: Path):
    """Yield relative file paths, skipping hidden and generated dirs; None marks truncation."""
    count = 0
    for current, dirs, files in os.walk(path):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
        for name in files:
            count += 1
            if count > WALK_LIMIT:
                yield None
                return
            yield Path(current, name).relative_to(path).as_posix()


def _dirty(path: Path) -> dict | None:
    raw = _git(path, "status", "--porcelain", "-z")
    if raw is None:
        return None
    modified, untracked = [], []
    entries = raw.split("\0")
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if len(entry) < 4:
            continue
        code, name = entry[:2], entry[3:]
        if code == "??":
            untracked.append(name)
        else:
            modified.append(name)
            if "R" in code or "C" in code:
                index += 1  # the next entry is the rename/copy source
    return {"modified": modified, "untracked": untracked}


def _worktrees(path: Path) -> list[str] | None:
    raw = _git(path, "worktree", "list", "--porcelain")
    if raw is None:
        return None
    return [line[len("worktree "):] for line in raw.splitlines() if line.startswith("worktree ")]


def _cgspec(path: Path) -> dict:
    marker = path / PROJECT_FILE
    version = None
    if marker.is_file():
        try:
            data = json.loads(marker.read_text(encoding="utf-8"))
            version = data.get("cgspec_version") if isinstance(data, dict) else None
        except (OSError, ValueError):
            version = None
    return {"installed": marker.is_file(), "cgspec_version": version if isinstance(version, str) else None}


def _signals(path: Path) -> tuple[bool, bool | None]:
    """(docs present, tests present); tests is None when the bounded walk could not finish."""
    docs = path / "docs"
    has_docs = docs.is_dir() and any(docs.rglob("*.md"))
    if (path / "tests").is_dir() or (path / "test").is_dir():
        return has_docs, True
    for rel in _walk(path):
        if rel is None:
            return has_docs, None
        if any(fnmatch.fnmatch(rel.rsplit("/", 1)[-1], pattern) for pattern in TEST_FILES):
            return has_docs, True
    return has_docs, False


def _ci(path: Path) -> bool:
    workflows = path / ".github/workflows"
    return bool((workflows.is_dir() and (list(workflows.glob("*.yml")) + list(workflows.glob("*.yaml"))))
                or (path / ".gitlab-ci.yml").is_file() or (path / ".circleci").is_dir())


def repo_facts(path: Path) -> dict:
    """Observe one repository without mutating it."""
    if not path.exists():
        return unreachable_repo(path, "missing")
    if not path.is_dir():
        return unreachable_repo(path, "not a directory")
    if not os.access(path, os.R_OK | os.X_OK):
        return unreachable_repo(path, "unreadable")
    has_git = git_available()
    if has_git and not git_root(path):
        return unreachable_repo(path, "not a git root")
    if not has_git and not (path / ".git").exists():
        return unreachable_repo(path, "not a git root")
    facts: dict[str, str] = {}
    branch = _git(path, "rev-parse", "--abbrev-ref", "HEAD") if has_git else None
    head = _git(path, "rev-parse", "HEAD") if has_git else None
    short = _git(path, "rev-parse", "--short=7", "HEAD") if has_git else None
    facts["branch"] = "observed" if branch is not None else "unknown"
    facts["head"] = "observed" if head is not None else "unknown"
    dirty = _dirty(path) if has_git else None
    facts["dirty"] = "observed" if dirty is not None else "unknown"
    worktrees = _worktrees(path) if has_git else None
    facts["worktrees"] = "observed" if worktrees is not None else "unknown"
    facts["cgspec"] = "observed"
    has_docs, has_tests = _signals(path)
    facts["docs"] = "observed"
    facts["tests"] = "observed" if has_tests is not None else "unknown"
    has_ci = _ci(path)
    facts["ci"] = "inferred" if has_ci else "observed"  # files exist; their behavior is unproven
    return {
        "root": str(path), "reachable": True,
        "git": {"branch": branch.strip() if branch else None, "head": head.strip() if head else None,
                "head_short": short.strip() if short else None},
        "dirty": dirty, "worktrees": worktrees, "cgspec": _cgspec(path),
        "docs": {"present": has_docs}, "tests": {"present": has_tests}, "ci": {"present": has_ci},
        "facts": facts,
    }


def _is_repo_dir(path: Path) -> bool:
    return (path / ".git").exists()


def workspace_facts(start: Path, depth: int = 3) -> dict:
    """Find git roots at or below `start` (not inside other repos) and observe each one."""
    start = start.resolve()
    if _is_repo_dir(start):
        return {"repos": [repo_facts(start)]}
    found: list[Path] = []

    def visit(folder: Path, level: int) -> None:
        if level > depth:
            return
        try:
            children = sorted(p for p in folder.iterdir() if p.is_dir() and not p.is_symlink())
        except OSError:
            return
        for child in children:
            if child.name in SKIP_DIRS or child.name.startswith("."):
                continue
            if _is_repo_dir(child):
                found.append(child)  # never descend into a repo's own contents
            else:
                visit(child, level + 1)

    visit(start, 1)
    return {"repos": [repo_facts(path) for path in found]}


def _resolve(root: Path, name: str) -> Path:
    path = Path(name).expanduser()
    return (path if path.is_absolute() else root / path).resolve()


def _kind_counts(repos: list[dict]) -> dict:
    counts = {kind: 0 for kind in FACT_KINDS}
    for repo in repos:
        if not repo.get("reachable"):
            counts["unreachable"] += 1
            continue
        for kind in repo.get("facts", {}).values():
            counts[kind] += 1
    return counts


def classify(root: Path, repos: list[str] | None = None) -> dict:
    """The adoption map: discovered repos plus every explicitly named one, missing or not."""
    root = root.resolve()
    entries: list[dict] = []
    seen: set[str] = set()
    for name in repos or []:
        entry = repo_facts(_resolve(root, name))
        entry["requested"] = name
        if entry["root"] not in seen:
            seen.add(entry["root"])
            entries.append(entry)
    for entry in workspace_facts(root)["repos"]:
        if entry["root"] not in seen:
            seen.add(entry["root"])
            entries.append(entry)
    return {
        "schema": 1, "generated_at": utc_now(),
        "probe": {"git": "observed" if git_available() else "unknown"},
        "repos": entries, "facts_kinds": _kind_counts(entries),
    }


def _state(entry: dict, name: str) -> dict:
    status = {"repo": name, "state": "OK", "reason": None, "owner": "agent", "timing": "before_proof"}
    if not entry.get("reachable"):
        reason = entry.get("reason") or "unreachable"
        if reason == "unreadable":
            status.update(state="UNKNOWN", owner="unknown", timing="before_start",
                          reason=f"cannot determine reachability of {name} ({reason})")
        else:
            status.update(state="BLOCKED", owner="user", timing="before_start",
                          reason=f"{name} is unreachable ({reason}); the user must provide access before "
                                 "dependent work starts")
        return status
    gaps = [field for field, kind in entry.get("facts", {}).items() if kind == "unknown"]
    gaps += [signal for signal in ("docs", "tests")
             if entry.get(signal, {}).get("present") is False]
    if gaps:
        status.update(state="PARTIAL", reason="limited verification, not PASS: missing or unknown "
                                              + ", ".join(dict.fromkeys(gaps)))
    return status


def readiness(root: Path, slice_id: str | None, repos: list[str] | None) -> tuple[list[dict], int]:
    """Readiness of exactly the repos an adoption slice needs; unrelated repos are not judged."""
    root = root.resolve()
    if slice_id and not tiers.find_slice(root, slice_id):
        raise CgspecError(f"slice not found: {slice_id}")
    names = list(dict.fromkeys(repos or ["."]))
    statuses = [_state(repo_facts(_resolve(root, name)), name) for name in names]
    blocked = any(s["state"] in ("BLOCKED", "UNKNOWN") for s in statuses)
    return statuses, EXIT_BLOCK if blocked else EXIT_OK


def _repo_list(args) -> list[str] | None:
    raw = getattr(args, "repos", None)
    return [r.strip() for r in raw.split(",") if r.strip()] if raw else None


def cli(root: Path, args) -> int:
    from .common import STATE_DIR, write_json
    action = (args.rest[:1] or [""])[0]
    if action in ("discover", "save"):
        data = classify(root, _repo_list(args))
        text = json.dumps(data, indent=2, ensure_ascii=False)
        print(text)
        if args.json_out:
            write_json(Path(args.json_out), data)
        if action == "save":
            write_json(root / STATE_DIR / "adoption-map.json", data)
        return EXIT_OK
    if action == "ready":
        if not args.slice:
            raise CgspecError("adopt ready needs --slice SLICE-NNN")
        statuses, code = readiness(root, args.slice, _repo_list(args))
        print(f"adoption readiness for {args.slice} (required repos only):")
        for s in statuses:
            line = f"- {s['repo']}: {s['state']} owner={s['owner']} timing={s['timing']}"
            print(line + (f" - {s['reason']}" if s["reason"] else ""))
        return code
    raise CgspecError("usage: cgspec_hook.py adopt discover|save|ready [--repos a,b] [--json-out FILE] [--slice SLICE-NNN]")
