"""Registered project checks (spec 8): a proposed script becomes a gate only after the user's
approval, with its hash recorded; it then runs at commit and in CI on the files it applies to."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from .common import CHECKS_DIR, EVIDENCE_DIR, CgspecError, sha256_file, utc_now, write_json
from .globs import match_any

MANIFEST = CHECKS_DIR / "manifest.json"
PROPOSALS = ".cgspec-scratch/checks/"
RUNNERS = {".py": ["python3"], ".sh": ["sh"], ".js": ["node"], ".mjs": ["node"]}
TIMEOUT = 300


def _proposal(root: Path, rel: str) -> Path | None:
    path = Path(rel)
    if not rel.startswith(PROPOSALS) or ".." in path.parts:
        return None
    candidate = root / path
    if not candidate.is_file() or candidate.is_symlink():
        return None
    for length in range(1, len(path.parts) + 1):
        if (root.joinpath(*path.parts[:length])).is_symlink():
            return None
    allowed = (root / PROPOSALS.rstrip("/")).resolve()
    return candidate if candidate.resolve().is_relative_to(allowed) else None


def _manifest(root: Path) -> dict:
    try:
        data = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"schema": 1, "checks": []}
    except (OSError, ValueError):
        return {"schema": 1, "checks": []}


def register(root: Path, file: str, applies_to: list[str], description: str, approval: str,
             command: list[str] | None = None, guide: str | None = None) -> dict:
    from .inbox import approval_exists
    source = _proposal(root, file)
    if source is None:
        raise CgspecError(f"a check is proposed as a regular file under {PROPOSALS} first")
    if approval != "trailer" and not approval_exists(root, approval):
        raise CgspecError(f"approval {approval} is not in 07-state/approvals.json (only your own message creates one)")
    if not applies_to or not description.strip():
        raise CgspecError("say which files the check applies to (--applies-to) and what it checks (--description)")
    guide_source = None
    guide_text = None
    if guide:
        guide_source = _proposal(root, guide)
        if guide_source is None:
            raise CgspecError(f"a guide is proposed as a regular file under {PROPOSALS} first")
        guide_text = guide_source.read_text(encoding="utf-8")
        if not guide_text.startswith("# "):
            raise CgspecError("a check guide must start with a Markdown title")
    data = _manifest(root)
    dest = root / CHECKS_DIR / source.name
    if dest.exists():
        raise CgspecError(f"{dest.relative_to(root).as_posix()} already exists; registered checks never change")
    runner = command or RUNNERS.get(source.suffix.lower(), []) + ["{path}", "{files}"]
    if not command and source.suffix.lower() not in RUNNERS:
        raise CgspecError("unknown script type; pass --command as JSON, e.g. '[\"bash\", \"{path}\", \"{files}\"]'")
    shutil.copyfile(source, dest)
    guide_dest = root / CHECKS_DIR / guide_source.name if guide_source else None
    if guide_dest and guide_dest.exists():
        dest.unlink()
        raise CgspecError(f"{guide_dest.relative_to(root).as_posix()} already exists; registered checks never change")
    if guide_dest:
        from .document_dates import stamp_new
        guide_dest.write_text(stamp_new(guide_text, utc_now()), encoding="utf-8")
    numbers = [int(c["id"][4:]) for c in data.get("checks", []) if str(c.get("id", "")).startswith("CHK-")]
    entry = {"id": f"CHK-{max(numbers, default=0) + 1:03d}", "path": dest.relative_to(root).as_posix(),
             "sha256": sha256_file(dest), "command": runner, "applies_to": applies_to,
             "description": description.strip(),
             "approval": {"source": "commit-trailer" if approval == "trailer" else "message-hook", "ref": approval,
                          "at": utc_now()},
             "added": utc_now()}
    if guide_dest:
        entry["guide"] = guide_dest.relative_to(root).as_posix()
        entry["guide_sha256"] = sha256_file(guide_dest)
    data.setdefault("checks", []).append(entry)
    write_json(root / MANIFEST, data)
    return entry


def _revision(root: Path) -> str:
    out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root, capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else "working-tree"


def _command(entry: dict, root: Path, files: list[str]) -> list[str]:
    out = []
    for part in entry.get("command", []):
        if part == "{files}":
            out += files
        else:
            out.append(str(root / entry["path"]) if part == "{path}" else part)
    return out


def integrity(root: Path, entry: dict) -> str | None:
    """Why a registered check's script or guide no longer matches its approved hash, or None."""
    cid = entry.get("id")
    pinned = [(entry.get("path"), entry.get("sha256"))]
    if entry.get("guide") or entry.get("guide_sha256"):
        pinned.append((entry.get("guide"), entry.get("guide_sha256")))
    for rel, digest in pinned:
        path = root / str(rel or "")
        if not rel or not path.is_file():
            return f"{cid}: {rel} is missing; registered checks and guides never change"
        if sha256_file(path) != digest:
            return f"{cid}: {rel} changed since approval; registered checks and guides never change"
    return None


def _integrity_at(view, entry: dict) -> str | None:
    """Like `integrity`, but against the content a git View sees (one commit), not the filesystem.

    A commit range where a commit deletes or edits an approved script or guide and a later commit
    restores the exact approved bytes must still fail: the final tree alone is not proof that the
    approved content held at every commit in between."""
    cid = entry.get("id")
    pinned = [(entry.get("path"), entry.get("sha256"))]
    if entry.get("guide") or entry.get("guide_sha256"):
        pinned.append((entry.get("guide"), entry.get("guide_sha256")))
    for rel, digest in pinned:
        content = view.read_new(str(rel)) if rel else None
        if not rel or content is None:
            return f"{cid}: {rel} is missing; registered checks and guides never change"
        if hashlib.sha256(content).hexdigest() != digest:
            return f"{cid}: {rel} changed since approval; registered checks and guides never change"
    return None


def verify_manifest_at(view) -> list[str]:
    """Every check registered as of this commit's own manifest must match its approved hash in this
    commit's own tree (spec 8): checked per commit in the CI range, not only at the final tree."""
    raw = view.read_new(MANIFEST.as_posix())
    try:
        data = json.loads(raw.decode("utf-8")) if raw is not None else None
    except ValueError:
        data = None
    checks_list = data.get("checks") if isinstance(data, dict) else None
    if not isinstance(checks_list, list):
        return []
    return [problem for entry in checks_list if isinstance(entry, dict)
            for problem in [_integrity_at(view, entry)] if problem]


def check_env(base_rev: str, repo_root: Path) -> dict:
    """Environment every registered check receives: the trusted base revision to compare against and the
    Git repository holding it. The candidate content is the check's working directory (the staged snapshot
    at commit time, the checked-out HEAD in CI)."""
    import os
    env = dict(os.environ)
    env["CGSPEC_BASE_REV"] = base_rev
    env["CGSPEC_REPO_ROOT"] = str(repo_root)
    return env


def run(root: Path, files: list[str], run_all: bool = False, write_evidence: bool = True,
        base_rev: str = "HEAD", repo_root: Path | None = None) -> tuple[list[str], list[str]]:
    """(failures, notes). Every registered script and guide is verified against its approved hash on every
    run, whether or not the check applies to `files`; a tampered check fails without running.
    Checks run in `root` with CGSPEC_BASE_REV=`base_rev` and CGSPEC_REPO_ROOT=`repo_root` (default `root`)."""
    failures, notes = [], []
    env = check_env(base_rev, repo_root or root)
    for entry in _manifest(root).get("checks", []):
        cid, path = entry.get("id"), root / str(entry.get("path", ""))
        problem = integrity(root, entry)
        if problem:
            failures.append(f"{problem}; it was not run")
            continue
        matched = [f for f in files if match_any(f, entry.get("applies_to", []))]
        if not matched and not run_all:
            continue
        guide_text = None
        if entry.get("guide"):
            guide_text = (root / entry["guide"]).read_text(encoding="utf-8", errors="replace").strip()
        try:
            result = subprocess.run(_command(entry, root, matched), cwd=root, capture_output=True, text=True,
                                    timeout=TIMEOUT, env=env)
            verdict, output = ("PASS" if result.returncode == 0 else "FAIL"), (result.stdout + result.stderr)[-2000:]
        except (OSError, subprocess.TimeoutExpired) as exc:
            verdict, output = "FAIL", f"could not run: {exc}"
        notes.append(f"{cid} {verdict}: {entry.get('description', '')}")
        if verdict == "FAIL":
            message = f"{cid} failed ({entry.get('description', '')}):\n{output.strip()}"
            if guide_text:
                message += f"\n\nHow to fix this well ({cid} guide):\n{guide_text}"
            failures.append(message)
        if write_evidence:
            write_json(root / EVIDENCE_DIR / "checks" / f"{cid}.json", {
                "schema": 1, "check": cid, "revision": _revision(root), "verdict": verdict, "state": "Fresh",
                "covers": entry.get("applies_to", []), "details": output.strip()[:2000],
                "ran_at": utc_now(), "ran_by": "cgspec_hook check run"})
    if not notes and not failures:
        notes.append("no registered check applies to these files")
    return failures, notes


def cli(root: Path, args) -> int:
    """`cgspec_hook.py check register|run`. Exit 0 ok, 1 a check failed."""
    action = (args.rest[:1] or [""])[0]
    if action == "register":
        if not (args.file and args.applies_to and args.approval):
            raise CgspecError("usage: check register --file .cgspec-scratch/checks/x.py --applies-to 'src/**' "
                              "--description '...' --approval A-...")
        command = json.loads(args.command) if args.command else None
        entry = register(root, args.file, [g.strip() for g in args.applies_to.split(",") if g.strip()],
                         args.description or "", args.approval, command, args.guide)
        print(f"registered {entry['id']} at {entry['path']}")
        return 0
    if action == "run":
        files = [f.strip() for f in (args.files or "").split(",") if f.strip()]
        failures, notes = run(root, files, run_all=not files)
        print("\n".join(notes + failures))
        return 1 if failures else 0
    raise CgspecError("usage: cgspec_hook.py check register|run ...")
