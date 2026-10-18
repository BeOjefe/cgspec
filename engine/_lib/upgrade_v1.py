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
from .common import PROJECT_FILE, sha256_file, utc_now, write_json

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


def _prepare(stage: Path, options: dict, report: dict) -> None:
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
    args = argparse.Namespace(profile=options["profile"], topology=options["topology"],
                              tools=options["tools"], repo_prefix=options["repo_prefix"],
                              plugin_source=options["plugin_source"])
    with contextlib.redirect_stdout(io.StringIO()):
        cmd_install(stage, args)
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


def _inventory_diff(before: dict[str, bytes], after: dict[str, bytes]) -> list[dict]:
    out = []
    for rel in sorted(set(before) | set(after)):
        if before.get(rel) != after.get(rel):
            out.append({"path": rel, "before": digest(before.get(rel)), "after": digest(after.get(rel))})
    out.sort(key=lambda item: item["path"] == PROJECT_FILE.as_posix())
    return out


def _save_journal(root: Path, before: dict[str, bytes], diff: list[dict]) -> None:
    folder = root / JOURNAL
    folder.mkdir()
    with tarfile.open(folder / "before.tar.gz", "w:gz") as tar:
        for item in diff:
            rel = item["path"]
            if rel in before:
                data = before[rel]
                info = tarfile.TarInfo(rel)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
    (folder / "plan.json").write_text(json.dumps({"schema": 1, "diff": diff}, indent=2) + "\n")


def _safe_restore(root: Path, folder: Path) -> list[str]:
    from install import safe_target
    plan = json.loads((folder / "plan.json").read_text())
    diff = plan["diff"]
    conflicts = []
    for item in diff:
        try:
            path = safe_target(root, item["path"])
        except Exception:
            conflicts.append(item["path"])
            continue
        current = sha256_file(path) if path.is_file() else None
        if path.is_symlink() or current not in (item["before"], item["after"]):
            conflicts.append(item["path"])
        pending = path.with_name(path.name + ".upgrade-new")
        if pending.exists() and (not pending.is_file() or sha256_file(pending) != item["after"]):
            conflicts.append(str(pending.relative_to(root)))
    if conflicts:
        return conflicts
    with tarfile.open(folder / "before.tar.gz", "r:gz") as tar:
        original = {m.name: tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
    for item in diff:
        if item["before"] is not None and digest(original.get(item["path"])) != item["before"]:
            conflicts.append(f"corrupt backup: {item['path']}")
    if conflicts:
        return conflicts
    for item in diff:
        path = root / item["path"]
        path.with_name(path.name + ".upgrade-new").unlink(missing_ok=True)
        if item["before"] is None:
            path.unlink(missing_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(path.name + ".upgrade-restore")
            tmp.write_bytes(original[item["path"]])
            os.replace(tmp, path)
    for parent in sorted({(root / i["path"]).parent for i in diff}, key=lambda p: len(p.parts), reverse=True):
        while parent != root and parent.is_dir():
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent
    return []


def _publish(root: Path, stage: Path, before: dict[str, bytes], after: dict[str, bytes], report: dict) -> None:
    from install import safe_target
    if files(root) != before:
        raise ValueError("project changed during stage; rerun dry-run")
    diff = _inventory_diff(before, after)
    _save_journal(root, before, diff)
    try:
        for item in [i for i in diff if i["path"] != PROJECT_FILE.as_posix()]:
            path = safe_target(root, item["path"])
            if item["after"] is None:
                path.unlink(missing_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                temp = path.with_name(path.name + ".upgrade-new")
                temp.write_bytes(after[item["path"]])
                os.replace(temp, path)
        for old in ("docs/adr", "docs/_cgspec/03-council", "docs/_cgspec/01-script"):
            folder = safe_target(root, old)
            for child in sorted(folder.rglob("*"), key=lambda p: len(p.parts), reverse=True) if folder.is_dir() else []:
                if child.is_dir():
                    child.rmdir()
            if folder.is_dir():
                folder.rmdir()
        archive = root / ARCHIVE
        archive.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / JOURNAL / "before.tar.gz", archive / "before.tar.gz")
        shutil.copy2(root / JOURNAL / "plan.json", archive / "plan.json")
        marker = root / PROJECT_FILE
        marker.parent.mkdir(parents=True, exist_ok=True)
        temp = marker.with_name(marker.name + ".upgrade-new")
        temp.write_bytes(after[PROJECT_FILE.as_posix()])
        os.replace(temp, marker)
    except Exception:
        report["recovery"] = f"run upgrade --from-v1 --rollback; journal at {JOURNAL}"
        raise
    shutil.rmtree(root / JOURNAL)
    report["changed_files"] = len(diff)


def _stage_and_run(root: Path, options: dict, apply: bool, report: dict) -> tuple[int, dict]:
    before = files(root)
    with tempfile.TemporaryDirectory(prefix="cgspec-v1-stage-") as temp:
        stage = Path(temp) / "project"
        shutil.copytree(root, stage, ignore=shutil.ignore_patterns(".git", *L.SKIP_WALK, JOURNAL.name))
        (stage / PROJECT_FILE).unlink(missing_ok=True)
        _prepare(stage, options, report)
        if report["unresolved"]:
            return 2, report
        after = files(stage)
        report["archive"] = [(ARCHIVE / "before.tar.gz").as_posix()]
        report["archived_hashes"] = {rel: digest(before[rel]) for rel in report["path_map"] if rel in before}
        report["verdict"] = "READY"
        report["changed_files"] = len(_inventory_diff(before, after))
        if apply:
            _publish(root, stage, before, after, report)
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
            report["unresolved"].append(f"rollback backup cannot be read: {exc}")
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
