"""Outcome-based closure and independent review (issue #28).

A slice is closed only when every active outcome of its agreed success definition (#30) has fresh,
passing evidence for the exact current source revision, real-environment proof where the agreement
requires it, and an independent final review with no open findings. Evidence is read from
`docs/_cgspec/06-evidence/**.json`; this module never writes evidence, only the human checklist.
"""

from __future__ import annotations

from pathlib import Path

from . import start
from .common import CgspecError, EVIDENCE_DIR, EXIT_BLOCK, EXIT_OK, read_json, utc_now
from .gitview import git
from .schema import validate_named

# Changes under these paths are bookkeeping (evidence, state) and never invalidate earlier evidence.
NEUTRAL = ("docs/_cgspec/06-evidence/", "docs/_cgspec/07-state/", ".cgspec-scratch/")
NOT_PASSING = ("FAIL", "BLOCKED", "PARTIAL")


def material_changes(root: Path, rev: str) -> list[str] | None:
    """Files that changed since `rev` outside bookkeeping paths; None when `rev` is not a known commit."""
    if not rev or rev == "working-tree" or git(root, "cat-file", "-e", f"{rev}^{{commit}}").returncode != 0:
        return None
    changed = git(root, "diff", "--name-only", rev).stdout.splitlines()
    changed += git(root, "ls-files", "--others", "--exclude-standard").stdout.splitlines()
    return sorted({p for p in changed if p and not p.startswith(NEUTRAL)})


def load_evidence(root: Path) -> list[dict]:
    """Valid evidence records, each with its project-relative `_path`. Malformed files are ignored, never trusted."""
    out = []
    base = root / EVIDENCE_DIR
    for path in sorted(base.rglob("*.json")) if base.is_dir() else []:
        try:
            data = read_json(path)
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and not validate_named(data, "evidence"):
            data["_path"] = path.relative_to(root).as_posix()
            out.append(data)
    return out


def latest_per_check(records: list[dict]) -> list[dict]:
    """Only the most recent record of each check counts; an earlier FAIL replaced by a later PASS is history."""
    latest: dict[tuple, dict] = {}
    for rec in records:
        key = (rec["check"], rec.get("claim"), rec.get("runner_id"), rec.get("test_id"))
        if key not in latest or rec["ran_at"] >= latest[key]["ran_at"]:
            latest[key] = rec
    return list(latest.values())


def is_current(root: Path, rec: dict, cache: dict) -> bool:
    if rec.get("state") == "Stale":
        return False
    rev = rec["revision"]
    if rev not in cache:
        cache[rev] = material_changes(root, rev)
    return cache[rev] == []


def review_errors(rec: dict) -> list[str]:
    """Why a review record cannot count as independent (the builder never silently reviews itself)."""
    errs = []
    reviewer, builder = str(rec.get("reviewer", "")).strip(), str(rec.get("builder", "")).strip()
    if not reviewer or not builder:
        errs.append("records must name both reviewer and builder")
    elif reviewer == builder:
        errs.append(f"reviewer '{reviewer}' is the builder")
    if rec.get("same_model_review") is True:
        errs.append("declares same-model review")
    if not rec.get("reviewer_model"):
        errs.append("lacks reviewer_model")
    if not rec.get("inspected"):
        errs.append("lists no inspected diff or artifacts")
    return errs


def open_findings(rec: dict) -> list[str]:
    bad = []
    for f in rec.get("findings", []):
        resolved = f.get("status") == "resolved" and str(f.get("resolution", "")).strip()
        if not resolved:
            bad.append(f"{f.get('id', '?')} ({f.get('severity', 'unrated')})")
    return bad


def outcome_report(root: Path, data: dict, records: list[dict], builder: str, cache: dict) -> tuple[dict, list[str]]:
    """Per active outcome: the proof that closes it, and every reason it does not close."""
    report, errors = {}, []
    for out_id in data.get("active_outcomes", []):
        spec = start.outcome(data, out_id) or {}
        mine = latest_per_check([r for r in records if out_id in r.get("covers", []) and r.get("claim") != "review"])
        fresh = [r for r in mine if is_current(root, r, cache)]
        stale = [r for r in mine if r not in fresh]
        bad = [r for r in fresh if r["verdict"] in NOT_PASSING]
        passing = [r for r in fresh if r["verdict"] == "PASS"]
        problems = [f"{r['_path']} is {r['verdict']}" for r in bad]
        if not passing:
            problems.append("no passing evidence for the current revision" +
                            (f" (stale: {', '.join(r['_path'] for r in stale)})" if stale else ""))
        if spec.get("evaluation", {}).get("requires_real"):
            real = [r for r in passing if r.get("data_source") == "real_backend" and r.get("claim") == "integration"
                    and r["ran_by"] != builder]
            if not real:
                problems.append("requires real-environment integration proof (claim integration, data_source real_backend, "
                                "executed by someone other than the builder); fixtures, mocks and static evidence do not count")
            passing = real or passing
        report[out_id] = {"statement": spec.get("statement", ""), "accept": spec.get("accept", []),
                          "proof": [r["_path"] for r in passing], "revisions": sorted({r["revision"] for r in passing}),
                          "problems": problems}
        errors += [f"{out_id}: {p}" for p in problems]
    return report, errors


def check(root: Path, slice_id: str) -> tuple[dict, list[str]]:
    """Closure verdict for a slice: (per-outcome report with the final review, blocking problems)."""
    _, data = start.load(root, slice_id)
    active = data.get("active_outcomes", [])
    if not active:
        return {}, [f"{slice_id} has no active outcomes; nothing was begun, so nothing can be closed"]
    records, cache = load_evidence(root), {}
    reviews = latest_per_check([r for r in records if r.get("claim") == "review"])
    current = [r for r in reviews if is_current(root, r, cache)]
    final = [r for r in current if r["verdict"] == "PASS" and set(active) <= set(r.get("covers", []))
             and not review_errors(r) and not open_findings(r)]
    builder = str((final[-1] if final else (current[-1] if current else {})).get("builder", ""))
    report, errors = outcome_report(root, data, records, builder, cache)
    errors += [f"review {r['_path']}: unresolved finding {f}" for r in current for f in open_findings(r)]
    errors += [f"review {r['_path']} is {r['verdict']}" for r in current if r["verdict"] in NOT_PASSING]
    if not final:
        why = [f"review {r['_path']} {e}" for r in current if r["verdict"] == "PASS" for e in review_errors(r)]
        stale = [r["_path"] for r in reviews if r not in current]
        errors.append("no current independent review of the integrated system covering every active outcome"
                      + (f" (stale: {', '.join(stale)})" if stale else ""))
        errors += why
    return {"outcomes": report, "review": final[-1]["_path"] if final else None}, errors


def checklist(root: Path, slice_id: str, report: dict, prs: list[str]) -> Path:
    """Human verification checklist organised by user outcome, linking proof and commits."""
    lines = [f"# Closure checklist: {slice_id}", f"Generated: {utc_now()} · Independent review: `{report['review']}`", ""]
    if prs:
        lines += ["Pull requests: " + ", ".join(prs), ""]
    for out_id, info in report["outcomes"].items():
        lines += [f"## {out_id}: {info['statement']}", ""]
        for rev in info["revisions"]:
            subject = git(root, "log", "-1", "--format=%h %s", rev).stdout.strip() or rev
            lines.append(f"- Reviewed source revision: `{subject}`")
        lines += [f"- Proof: `{p}`" for p in info["proof"]]
        lines += [f"- [ ] Confirm: {item}" for item in info["accept"]]
        lines.append("")
    path = root / EVIDENCE_DIR / "closure" / f"{slice_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def cli(root: Path, args) -> int:
    action = args.rest[0] if args.rest else ""
    if action not in ("check", "checklist") or not args.slice:
        raise CgspecError("usage: cgspec_hook.py close check|checklist --slice SLICE-NNN [--pr URL,...]")
    report, errors = check(root, args.slice)
    if errors:
        print(f"{args.slice} cannot close:")
        for e in errors:
            print(f"- {e}")
        return EXIT_BLOCK
    if action == "checklist":
        prs = [p.strip() for p in (getattr(args, "pr", None) or "").split(",") if p.strip()]
        print(f"checklist written: {checklist(root, args.slice, report, prs).relative_to(root).as_posix()}")
    else:
        print(f"{args.slice} can close: {len(report['outcomes'])} outcome(s) proven, review {report['review']}")
    return EXIT_OK
