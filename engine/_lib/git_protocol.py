"""Per-slice Git execution protocol: plan declaration, commit sequencing,
review binding, worker isolation, multi-repo links, and monolithic rejection."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from . import tiers
from .common import CgspecError, EXIT_OK, read_json, utc_now, write_json
from .globs import match_any
from .gitview import git
from .schema import validate_named


COMMIT_KINDS = ("red-test", "implementation", "green-test", "review-fix", "docs", "infra")
SUBSTANTIVE_KINDS = ("red-test", "implementation", "green-test", "review-fix")


def plan_path(root: Path, slice_id: str) -> Path:
    found = tiers.find_slice(root, slice_id)
    if not found:
        raise CgspecError(f"slice not found: {slice_id}")
    return found[0].with_suffix(".git-plan.json")


def validate_plan(data: dict) -> list[str]:
    errors = validate_named(data, "git-plan")
    if errors:
        return errors
    repo_ids = [r["id"] for r in data["repositories"]]
    if len(set(repo_ids)) != len(repo_ids):
        errors.append("repository IDs must be unique")
    all_branches = [data["branch_policy"]["default_branch"]]
    all_branches += [s["branch"] for s in data["branch_policy"]["stacked_branches"]]
    if len(set(all_branches)) != len(all_branches):
        errors.append("branch names must be unique across default and stacked branches")
    repo_branches = {repo["branch"] for repo in data["repositories"]}
    if data["branch_policy"]["default_branch"] not in repo_branches:
        errors.append("default_branch must identify a declared repository branch")
    for stacked in data["branch_policy"]["stacked_branches"]:
        if stacked["depends_on"] not in all_branches:
            errors.append(f"stacked branch {stacked['branch']} depends on unknown branch {stacked['depends_on']}")
    for repo in data["repositories"]:
        owners = repo.get("file_ownership") or {}
        worktrees = repo.get("worker_worktrees") or {}
        if len(owners) > 1 and set(worktrees) != set(owners):
            errors.append(f"repository {repo['id']} needs one isolated worker_worktree per file owner")
        if len(set(worktrees.values())) != len(worktrees):
            errors.append(f"repository {repo['id']} worker worktrees must be unique")
    if data.get("multi_repo"):
        mr = data["multi_repo"]
        mr_ids = [r["id"] for r in mr["repos"]]
        if len(set(mr_ids)) != len(mr_ids):
            errors.append("multi-repo repository IDs must be unique")
        order_ids = set(mr["integration_order"])
        declared_ids = set(mr_ids)
        if order_ids != declared_ids:
            errors.append("integration_order must list exactly the declared multi-repo repository IDs")
        if declared_ids != set(repo_ids):
            errors.append("multi-repo links must identify exactly the declared repositories")
        if mr["outcome_id"] not in {outcome for repo in data["repositories"] for outcome in repo["outcomes"]}:
            errors.append("multi-repo outcome_id must be declared by the linked repositories")
    return errors


def load(root: Path, slice_id: str) -> tuple[Path, dict]:
    path = plan_path(root, slice_id)
    if not path.is_file():
        raise CgspecError(f"{slice_id} has no git execution plan; run git-plan declare first")
    data = read_json(path)
    errors = validate_plan(data)
    if errors:
        raise CgspecError(f"invalid git plan {path.name}: " + "; ".join(errors))
    return path, data


def load_if_exists(root: Path, slice_id: str) -> tuple[Path, dict] | None:
    try:
        path = plan_path(root, slice_id)
    except CgspecError:
        return None
    if not path.is_file():
        return None
    data = read_json(path)
    if validate_plan(data):
        return None
    return path, data


def save(path: Path, data: dict) -> None:
    errors = validate_plan(data)
    if errors:
        raise CgspecError("invalid git plan: " + "; ".join(errors))
    data["updated_at"] = utc_now()
    write_json(path, data)


def declare(root: Path, slice_id: str, repos: list[dict], default_branch: str,
            stacked: list[dict] | None = None, multi_repo: dict | None = None) -> dict:
    path = plan_path(root, slice_id)
    if path.is_file():
        raise CgspecError(f"{slice_id} already has a git plan; update it instead of redeclaring")
    now = utc_now()
    data = {
        "schema": 1,
        "slice": slice_id,
        "repositories": repos,
        "branch_policy": {
            "default_branch": default_branch,
            "stacked_branches": stacked or [],
        },
        "commits": [],
        "review": None,
        "multi_repo": multi_repo,
        "created_at": now,
        "updated_at": now,
    }
    save(path, data)
    print(f"git plan declared: {slice_id} on {default_branch}")
    return data


def record_commit(root: Path, slice_id: str, sha: str, summary: str, kind: str) -> dict:
    if kind not in COMMIT_KINDS:
        raise CgspecError(f"commit kind must be one of {COMMIT_KINDS}")
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise CgspecError("commit sha must be a full 40-character hex string")
    path, data = load(root, slice_id)
    if git(root, "cat-file", "-e", f"{sha}^{{commit}}").returncode:
        raise CgspecError(f"commit {sha[:12]} does not exist in this repository")
    if git(root, "merge-base", "--is-ancestor", sha, "HEAD").returncode:
        raise CgspecError(f"commit {sha[:12]} is not in the current candidate history")
    bases = [repo["base"] for repo in data["repositories"]]
    if not any(git(root, "merge-base", "--is-ancestor", base, sha).returncode == 0 for base in bases):
        raise CgspecError(f"commit {sha[:12]} does not descend from a declared approved base")
    if any(c["sha"] == sha for c in data["commits"]):
        raise CgspecError(f"commit {sha[:12]} is already recorded in the plan")
    if data["commits"] and git(root, "merge-base", "--is-ancestor", data["commits"][-1]["sha"], sha).returncode:
        raise CgspecError(f"commit {sha[:12]} does not follow the previously recorded commit")
    problem = sequence_problem(data, kind)
    if problem:
        raise CgspecError(problem)
    entry = {"sha": sha, "summary": summary, "kind": kind, "recorded_at": utc_now()}
    data["commits"].append(entry)
    if data["review"] and data["review"]["valid"]:
        data["review"]["valid"] = False
        data["review"]["invalidated_by"] = sha
    save(path, data)
    print(f"recorded {kind} commit {sha[:12]}: {summary}")
    return data


def bind_review(root: Path, slice_id: str, head_sha: str, checks_passed: bool = False) -> dict:
    if not re.fullmatch(r"[0-9a-f]{40}", head_sha):
        raise CgspecError("review binding needs a full 40-character HEAD sha")
    path, data = load(root, slice_id)
    actual = git(root, "rev-parse", "--verify", "HEAD^{commit}").stdout.strip()
    if head_sha != actual:
        raise CgspecError(f"review must bind to current candidate HEAD {actual[:12]}")
    if not data["commits"] or data["commits"][-1]["sha"] != head_sha:
        raise CgspecError("review HEAD must be the latest commit recorded in the git plan")
    if data["commits"][-1]["kind"] not in ("green-test", "review-fix"):
        raise CgspecError("review requires a green-test or review-fix candidate")
    if not checks_passed:
        raise CgspecError("review binding requires the candidate checks to have passed")
    data["review"] = {
        "bound_head": head_sha,
        "bound_at": utc_now(),
        "checks_passed": checks_passed,
        "valid": True,
        "invalidated_by": None,
    }
    save(path, data)
    print(f"review bound to {head_sha[:12]}")
    return data


def check_review_valid(data: dict, candidate: str | None = None) -> str | None:
    review = data.get("review")
    if not review:
        return None
    if not review["valid"]:
        inv = review.get("invalidated_by", "unknown")
        return f"review bound to {review['bound_head'][:12]} was invalidated by commit {inv[:12] if inv else 'unknown'}"
    if not review.get("checks_passed"):
        return "review is not bound to passing required checks"
    if candidate and review["bound_head"] != candidate:
        return f"review is bound to {review['bound_head'][:12]}, not candidate HEAD {candidate[:12]}"
    return None


def sequence_problem(data: dict, kind: str) -> str | None:
    kinds = [item["kind"] for item in data.get("commits", []) if item["kind"] in SUBSTANTIVE_KINDS]
    latest = kinds[-1] if kinds else None
    if kind == "red-test" and latest not in (None, "green-test"):
        return "red-test can only start a new behavior cycle"
    if kind == "implementation" and latest not in ("red-test", "implementation"):
        return "implementation requires a recorded red-test"
    if kind == "green-test" and latest != "implementation":
        return "green-test requires a preceding implementation commit"
    if kind == "review-fix" and not data.get("review"):
        return "review-fix requires an earlier review binding"
    return None


def check_plan_declared(root: Path, slice_id: str) -> str | None:
    try:
        path = plan_path(root, slice_id)
    except CgspecError:
        return None
    if not path.is_file():
        return f"{slice_id} has no git execution plan; declare repository, base, branch, outcomes and file ownership before implementation"
    try:
        data = read_json(path)
    except (OSError, ValueError):
        return f"{slice_id} git execution plan is unreadable"
    if errors := validate_plan(data):
        return f"{slice_id} git execution plan is invalid: {'; '.join(errors)}"
    branch = git(root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    stack = next((item for item in data["branch_policy"]["stacked_branches"] if item["branch"] == branch), None)
    matches = [repo for repo in data["repositories"] if repo["branch"] == branch]
    if not matches and not stack:
        return f"current branch {branch} is not declared in the {slice_id} git execution plan"
    base_repos = matches or data["repositories"]
    if not any(git(root, "merge-base", "--is-ancestor", repo["base"], "HEAD").returncode == 0 for repo in base_repos):
        return f"current branch does not descend from its approved base for {slice_id}"
    declared_tree = stack.get("worktree") if stack else next((repo.get("worktree") for repo in matches if repo.get("worktree")), None)
    if declared_tree and Path(declared_tree).resolve() != root.resolve():
        return f"current checkout is not the worktree declared for {slice_id}"
    return None


def check_worker_ownership(data: dict, worker_id: str, rel_path: str) -> str | None:
    for repo in data["repositories"]:
        ownership = repo.get("file_ownership") or {}
        if not ownership:
            continue
        if worker_id not in ownership:
            all_owned = [p for paths in ownership.values() for p in paths]
            if match_any(rel_path, all_owned):
                return f"{rel_path} is owned by another worker; {worker_id} is not declared in file_ownership"
        else:
            allowed = ownership[worker_id]
            if not match_any(rel_path, allowed):
                other = {w: ps for w, ps in ownership.items() if w != worker_id and match_any(rel_path, ps)}
                if other:
                    owners = ", ".join(other.keys())
                    return f"{rel_path} is owned by {owners}, not {worker_id}"
    return None


def check_worker_context(root: Path, data: dict, rel_path: str) -> str | None:
    owners = {owner for repo in data["repositories"] for owner in (repo.get("file_ownership") or {})}
    if not owners:
        return None
    worker_id = os.environ.get("CGSPEC_WORKER_ID", "")
    if not worker_id:
        return f"{rel_path} has parallel ownership; set CGSPEC_WORKER_ID for this isolated worker"
    problem = check_worker_ownership(data, worker_id, rel_path)
    if problem:
        return problem
    paths = [repo.get("worker_worktrees", {}).get(worker_id) for repo in data["repositories"]]
    declared = next((path for path in paths if path), None)
    if declared and Path(declared).resolve() != root.resolve():
        return f"worker {worker_id} must edit from its declared isolated worktree"
    return None


def check_commit_bound(data: dict, sha: str) -> str | None:
    if not any(c["sha"] == sha for c in data.get("commits", [])):
        return f"commit {sha[:12]} is not recorded in the git plan; record it with git-plan record-commit"
    return None


def commit_plan_reasons(view, tier: dict) -> list[str]:
    if not tier or tier.get("tier") == "T0":
        return []
    slice_id = tier.get("slice", "")
    if not slice_id:
        return []

    def _candidate_plan(view, slice_id: str) -> dict | None:
        bare = slice_id.split(":")[-1]
        for rel in view.files_new("docs/slices"):
            if rel.endswith(".git-plan.json") and Path(rel).name.startswith(bare + "-"):
                raw = view.read_new(rel)
                try:
                    data = json.loads(raw.decode("utf-8")) if raw else {}
                except (UnicodeDecodeError, ValueError):
                    data = {}
                if isinstance(data, dict) and not validate_plan(data):
                    return data
        return None

    plan = _candidate_plan(view, slice_id)
    if not plan:
        return []
    reasons = []
    metadata_only = bool(view.changes()) and all(c.path.endswith(".git-plan.json") for c in view.changes())
    candidate = (getattr(view, "old", None) if view.new != ":" and metadata_only else view.new)
    if candidate == ":":
        candidate = git(view.root, "rev-parse", "HEAD").stdout.strip()
    review_problem = check_review_valid(plan, candidate)
    if review_problem:
        reasons.append(review_problem)
    if plan.get("review") and view.new == ":" and not metadata_only:
        reasons.append("staged candidate changes invalidate the bound review and checks")
    return reasons


def cli(root: Path, args) -> int:
    action = args.rest[0] if args.rest else ""
    if not args.slice:
        raise CgspecError("git-plan needs --slice SLICE-NNN")
    if action == "declare":
        if not args.file:
            raise CgspecError("git-plan declare needs --file <plan-draft.json>")
        draft = read_json(Path(args.file))
        repos = draft.get("repositories", [])
        branch = draft.get("default_branch", "")
        stacked = draft.get("stacked_branches")
        multi = draft.get("multi_repo")
        if not repos or not branch:
            raise CgspecError("plan draft needs repositories and default_branch")
        declare(root, args.slice, repos, branch, stacked, multi)
    elif action == "record-commit":
        sha = (args.rest[1:2] or [""])[0]
        summary = getattr(args, "description", None) or "commit"
        kind = getattr(args, "commit_kind", None) or "implementation"
        if not sha:
            raise CgspecError("git-plan record-commit needs a commit SHA")
        record_commit(root, args.slice, sha, summary, kind)
    elif action == "bind-review":
        head = (args.rest[1:2] or [""])[0]
        if not head:
            raise CgspecError("git-plan bind-review needs a HEAD SHA")
        checks = getattr(args, "checks_passed", False)
        bind_review(root, args.slice, head, checks_passed=bool(checks))
    elif action == "show":
        _, data = load(root, args.slice)
        print(json.dumps(data, indent=2))
    else:
        raise CgspecError("usage: cgspec_hook.py git-plan declare|record-commit|bind-review|show --slice SLICE-NNN")
    return EXIT_OK
