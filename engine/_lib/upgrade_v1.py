"""Conservative v1 adoption: prove a staged conversion before changing a project."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import shutil
import tarfile
import tempfile
from pathlib import Path

from . import layout as L
from . import upgrade_v1_txn as txn
from .common import PROJECT_FILE, sha256_file, utc_now, write_json
from .upgrade_v1_git import plan as git_plan

JOURNAL = Path(".cgspec-upgrade-v1")
ARCHIVE = Path("docs/_cgspec/_archive/upgrade-v1")
MOVES = {
    "docs/adr": "docs/adrs",
    "docs/_cgspec/03-council": "docs/_cgspec/03-councils",
    "docs/.memlog.md": "docs/_memlog.md",
    "docs/01-INTENT.md": "docs/spines/01-INTENT.md",
    "docs/02-OOUX.md": "docs/spines/02-OOUX.md",
    "docs/03-EXPERIENCE.md": "docs/spines/03-EXPERIENCE.md",
    "docs/04-ARCHITECTURE.md": "docs/spines/04-ARCHITECTURE.md",
    "docs/05-DELIVERY.md": "docs/spines/05-DELIVERY.md",
}
REWRITES = {
    "docs/_cgspec/03-council/": "docs/_cgspec/03-councils/",
    "_cgspec/03-council/": "_cgspec/03-councils/",
    "docs/adr/": "docs/adrs/",
    "(adr/": "(adrs/",
    "(.cgspec/02-research/": "(_cgspec/02-research/",
    "(.cgspec/04-adr/": "(adrs/",
    "(.cgspec/06-slice/": "(slices/",
    "(./.memlog.md": "(./_memlog.md",
    "(./01-INTENT.md": "(./spines/01-INTENT.md",
    "(./02-OOUX.md": "(./spines/02-OOUX.md",
    "(./03-EXPERIENCE.md": "(./spines/03-EXPERIENCE.md",
    "(./04-ARCHITECTURE.md": "(./spines/04-ARCHITECTURE.md",
    "(./05-DELIVERY.md": "(./spines/05-DELIVERY.md",
}


def digest(data: bytes | None) -> str | None:
    return hashlib.sha256(data).hexdigest() if data is not None else None


def files(root: Path) -> dict[str, bytes]:
    result = {}
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if set(rel.parts) & (L.SKIP_WALK | {JOURNAL.name}):
            continue
        if path.is_symlink():
            raise ValueError(f"symlink needs manual review: {rel.as_posix()}")
        if path.is_file():
            result[rel.as_posix()] = path.read_bytes()
    return result


def _move(stage: Path, old: str, new: str, report: dict) -> None:
    source, target = stage / old, stage / new
    if not source.exists():
        return
    if source.is_dir():
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(source)
            dest = target / rel
            key = path.relative_to(stage).as_posix()
            if dest.exists() and path.read_bytes() != dest.read_bytes():
                report["unresolved"].append(f"destination conflict: {dest.relative_to(stage)}")
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                shutil.copy2(path, dest)
            report["path_map"][key] = dest.relative_to(stage).as_posix()
        if not report["unresolved"]:
            shutil.rmtree(source)
    elif source.is_file():
        if target.exists() and source.read_bytes() != target.read_bytes():
            report["unresolved"].append(f"destination conflict: {new}")
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(source, target)
        report["path_map"][old] = new
        source.unlink()


def _rewrite(stage: Path, report: dict) -> None:
    for path in sorted((stage / "docs").rglob("*.md")):
        if ARCHIVE in path.relative_to(stage).parents:
            continue
        text = path.read_text(encoding="utf-8")
        updated = text
        for old, new in REWRITES.items():
            updated = updated.replace(old, new)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            report["rewritten"].append(path.relative_to(stage).as_posix())


def _legacy_baseline(stage: Path, original: dict[str, bytes], report: dict) -> None:
    state = stage / "docs/_cgspec/07-state/legacy-baseline.json"
    slice_path = stage / "docs/slices/SLICE-000-baseline.md"
    if state.exists() or slice_path.exists():
        report["unresolved"].append("existing legacy baseline or SLICE-000 needs a reviewed merge")
        return
    entries = {}
    for rel, data in original.items():
        if rel in {"AGENTS.md", "CLAUDE.md", ".gitignore"}:
            continue
        if rel.startswith("docs/") and not rel.startswith("docs/prototypes/"):
            continue
        entries[rel] = {"sha256": digest(data), "lines": data.count(b"\n") + int(bool(data) and not data.endswith(b"\n"))}
    write_json(state, {"schema": 1, "created": utc_now(), "files": entries})
    slice_path.parent.mkdir(parents=True, exist_ok=True)
    slice_path.write_text("# SLICE-000: Legacy baseline\n\n- **Status:** Draft\n\n"
                          f"{len(entries)} pre-existing files are listed with hashes in "
                          "[legacy-baseline.json](../_cgspec/07-state/legacy-baseline.json). "
                          "This snapshot grants no approval to edit them; use a new approved slice.\n")
    report["legacy_files"] = len(entries)


def _prepare(stage: Path, options: dict, report: dict, hooks: list[dict]) -> None:
    original = files(stage)
    scripts = stage / "docs/_cgspec/01-script"
    if scripts.exists():
        legacy = [p for p in scripts.rglob("*") if p.is_file() and p.name != ".gitkeep"]
        if legacy:
            archive = stage / ARCHIVE / "legacy-engine.tar.gz"
            archive.parent.mkdir(parents=True, exist_ok=True)
            with tarfile.open(archive, "w:gz") as tar:
                tar.add(scripts, arcname="docs/_cgspec/01-script")
            report["archive"].append(archive.relative_to(stage).as_posix())
            report["unresolved"] += [f"legacy engine material needs mapping/review: {p.relative_to(stage)}"
                                      for p in legacy]
        shutil.rmtree(scripts)
        if not legacy:
            report["remove_empty"].append("docs/_cgspec/01-script")
    for old, new in MOVES.items():
        _move(stage, old, new, report)
    _rewrite(stage, report)
    from install import cmd_install, plugin_root
    from doctor import fix as doctor_fix, main as doctor_main
    import argparse
    for rel in ("AGENTS.md", "CLAUDE.md"):
        old, template = stage / rel, plugin_root() / "templates/base" / rel
        if old.is_file() and old.read_bytes() != template.read_bytes():
            report["unresolved"].append(f"legacy agent instructions need semantic mapping: {rel}")
    staged_tools = ",".join(t for t in options["tools"].split(",") if t and t != "git")
    args = argparse.Namespace(profile=options["profile"], topology=options["topology"],
                              tools=staged_tools, repo_prefix=options["repo_prefix"],
                              plugin_source=options["plugin_source"])
    with contextlib.redirect_stdout(io.StringIO()):
        cmd_install(stage, args)
    if "git" in options["tools"].split(","):
        marker = stage / PROJECT_FILE
        project = json.loads(marker.read_text())
        project["tools"] = sorted(set(project["tools"]) | {"git"})
        write_json(marker, project)
        owned_path = stage / "docs/_cgspec/01-engine/owned-files.json"
        owned = json.loads(owned_path.read_text())
        owned.setdefault("adapters", {})["git_abs"] = [h["path"] for h in hooks if h["created"]]
        write_json(owned_path, owned)
    _legacy_baseline(stage, original, report)
    doctor_fix(stage, options["profile"])
    capture = io.StringIO()
    with contextlib.redirect_stdout(capture):
        status = doctor_main(["--root", str(stage), "--json"])
    check = json.loads(capture.getvalue())
    report["doctor"] = check
    if status:
        report["unresolved"] += [f"{f['code']} {f['path']}: {f['message']}"
                                 for f in check["findings"] if f["code"].startswith("E-")]


def _inventory_diff(before: dict[str, bytes], after: dict[str, bytes], pre: dict | None = None,
                    post: dict | None = None) -> list[dict]:
    pre = pre or txn.metadata(Path.cwd(), before)
    post = post or txn.metadata(Path.cwd(), after)
    return txn.inventory_diff(before, after, pre, post)


def _save_journal(root: Path, before: dict[str, bytes], diff: list[dict], pre: dict, post: dict,
                  hooks: list[dict]) -> None:
    txn.save_journal(root, before, diff, pre, post, hooks)


def _safe_restore(root: Path, folder: Path) -> list[str]:
    return txn.restore(root, folder)


def _publish(root: Path, stage: Path, before: dict[str, bytes], after: dict[str, bytes], report: dict,
             pre: dict | None = None, post: dict | None = None, hooks: list[dict] | None = None) -> None:
    pre = pre or txn.metadata(root, before)
    post = post or txn.metadata(stage, after)
    txn.publish(root, before, after, pre, post, hooks or [], report, files, _save_journal)


def _stage_and_run(root: Path, options: dict, apply: bool, report: dict) -> tuple[int, dict]:
    before = files(root)
    pre = txn.metadata(root, before)
    if files(root) != before or txn.metadata(root, before) != pre:
        report["unresolved"].append("project changed while initial inventory was read")
        return 2, report
    hooks, issues = git_plan(root, options["tools"])
    report["git_hooks"] = [h["path"] for h in hooks]
    if issues:
        report["unresolved"] += issues
        return 2, report
    with tempfile.TemporaryDirectory(prefix="cgspec-v1-stage-") as temp:
        stage = Path(temp) / "project"
        shutil.copytree(root, stage, ignore=shutil.ignore_patterns(".git", *L.SKIP_WALK, JOURNAL.name))
        (stage / PROJECT_FILE).unlink(missing_ok=True)
        _prepare(stage, options, report, hooks)
        if report["unresolved"]:
            return 2, report
        after = files(stage)
        post = txn.metadata(stage, after)
        report["archive"] = [(ARCHIVE / "before.tar.gz").as_posix()]
        report["archived_hashes"] = {rel: digest(before[rel]) for rel in report["path_map"] if rel in before}
        report["verdict"] = "READY"
        report["changed_files"] = len(_inventory_diff(before, after, pre, post))
        if apply:
            _publish(root, stage, before, after, report, pre, post, hooks)
            report["verdict"] = "PASS"
        return 0, report


def _current_status(root: Path, report: dict) -> tuple[int, dict]:
    from doctor import main as doctor_main
    capture = io.StringIO()
    with contextlib.redirect_stdout(capture):
        status = doctor_main(["--root", str(root), "--json"])
    report["doctor"] = json.loads(capture.getvalue())
    if status:
        report["unresolved"].append("current version marker exists but doctor reports errors")
        return 2, report
    report["verdict"] = "ALREADY_CURRENT"
    return 0, report


def run(root: Path, options: dict, apply: bool, rollback: bool = False) -> tuple[int, dict]:
    report = {"verdict": "PARTIAL", "path_map": {}, "archive": [], "archived_hashes": {},
              "remove_empty": [], "rewritten": [], "unresolved": [],
              "rollback": "upgrade --from-v1 --rollback restores the pre-upgrade files if no later changes exist"}
    journal = root / JOURNAL
    archived = root / ARCHIVE
    if rollback:
        source = journal if journal.is_dir() else archived
        if not source.is_dir():
            report["unresolved"].append("no upgrade journal or archive exists")
            return 2, report
        try:
            conflicts = _safe_restore(root, source)
        except (OSError, ValueError, KeyError, tarfile.TarError) as exc:
            report["unresolved"].append(f"rollback stopped; recovery data retained: {exc}")
            return 2, report
        if conflicts:
            report["unresolved"] += [f"changed since upgrade: {p}" for p in conflicts]
            return 2, report
        if journal.is_dir():
            shutil.rmtree(journal)
        else:
            shutil.rmtree(archived)
            try:
                archived.parent.rmdir()
            except OSError:
                pass
        report["verdict"] = "ROLLED_BACK"
        return 0, report
    if journal.exists():
        report["unresolved"].append(f"interrupted upgrade journal at {JOURNAL}; run --rollback first")
        return 2, report
    old_marker = root / PROJECT_FILE
    if old_marker.exists():
        try:
            current = json.loads(old_marker.read_text()).get("cgspec_version", "")
        except (OSError, json.JSONDecodeError, AttributeError):
            current = ""
        from install import version
        if current == version():
            return _current_status(root, report)
        if not current.startswith("1."):
            report["unresolved"].append(f"unknown project version marker: {current!r}")
            return 2, report
    if archived.exists():
        report["unresolved"].append(f"existing upgrade archive at {ARCHIVE}; review it first")
        return 2, report
    if not (root / "docs/_cgspec/01-script").is_dir():
        report["unresolved"].append("v1 marker docs/_cgspec/01-script is missing")
        return 2, report
    if options["topology"].startswith("polyrepo") and not options["repo_prefix"]:
        report["unresolved"].append("polyrepo upgrade requires --repo-prefix")
        return 2, report
    try:
        return _stage_and_run(root, options, apply, report)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        report["verdict"] = "PARTIAL"
        report["unresolved"].append(f"upgrade could not be verified: {exc}")
        return 2, report


def add_cli_args(parser, plugin_source: str) -> None:
    parser.add_argument("--from-v1", action="store_true", help="stage and check an old-layout adoption")
    parser.add_argument("--apply", action="store_true", help="publish a verified v1 upgrade")
    parser.add_argument("--rollback", action="store_true", help="restore an unmodified v1 upgrade")
    parser.add_argument("--profile", default="web-workspace", choices=["website", "web-workspace", "mobile", "cli", "headless", "small"])
    parser.add_argument("--topology", default="single", choices=["single", "monorepo", "large-monorepo", "polyrepo-governance", "polyrepo-member"])
    parser.add_argument("--tools", default="git")
    parser.add_argument("--repo-prefix", default="")
    parser.add_argument("--plugin-source", default=plugin_source)
