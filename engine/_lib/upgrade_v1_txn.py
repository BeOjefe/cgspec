"""Journaled publication and rollback for a staged v1 project upgrade."""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import tarfile
from pathlib import Path

from . import layout as L
from .common import PROJECT_FILE, CgspecError, sha256_file
from .upgrade_v1_git import check as check_hooks, publish as publish_hooks

JOURNAL = Path(".cgspec-upgrade-v1")
ARCHIVE = Path("docs/_cgspec/_archive/upgrade-v1")


def digest(data: bytes | None) -> str | None:
    return hashlib.sha256(data).hexdigest() if data is not None else None


def metadata(root: Path, content: dict[str, bytes]) -> dict:
    file_modes = {rel: (root / rel).stat().st_mode & 0o777 for rel in content}
    dirs = {}
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if set(rel.parts) & (L.SKIP_WALK | {JOURNAL.name}):
            continue
        if path.is_dir() and not path.is_symlink():
            dirs[rel.as_posix()] = path.stat().st_mode & 0o777
    return {"files": file_modes, "dirs": dirs}


def inventory_diff(before: dict[str, bytes], after: dict[str, bytes], pre: dict, post: dict) -> list[dict]:
    out = []
    for rel in sorted(set(before) | set(after)):
        bmode, amode = pre["files"].get(rel), post["files"].get(rel)
        if before.get(rel) != after.get(rel) or bmode != amode:
            out.append({"path": rel, "before": digest(before.get(rel)), "after": digest(after.get(rel)),
                        "before_mode": bmode, "after_mode": amode})
    out.sort(key=lambda item: item["path"] == PROJECT_FILE.as_posix())
    return out


def save_journal(root: Path, before: dict[str, bytes], diff: list[dict], pre: dict, post: dict,
                 hooks: list[dict]) -> None:
    folder = root / JOURNAL
    folder.mkdir()
    with tarfile.open(folder / "before.tar.gz", "w:gz") as tar:
        for item in diff:
            rel = item["path"]
            if rel in before:
                data = before[rel]
                info = tarfile.TarInfo(rel)
                info.size = len(data)
                info.mode = item["before_mode"]
                tar.addfile(info, io.BytesIO(data))
    plan = {"schema": 1, "diff": diff, "before_dirs": pre["dirs"], "after_dirs": post["dirs"],
            "hooks": hooks}
    (folder / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")


def _file_state(path: Path) -> tuple[str | None, int | None]:
    if not path.exists():
        return None, None
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"unsafe file target: {path}")
    return sha256_file(path), path.stat().st_mode & 0o777


def _check_restore_files(root: Path, diff: list[dict]) -> list[str]:
    from install import safe_target
    issues = []
    for item in diff:
        try:
            path = safe_target(root, item["path"])
            current = _file_state(path)
            allowed = {(item["before"], item["before_mode"]), (item["after"], item["after_mode"])}
            if current not in allowed:
                issues.append(f"changed since upgrade: {item['path']}")
            pending = safe_target(root, item["path"] + ".upgrade-new")
            if pending.exists() and _file_state(pending) != (item["after"], item["after_mode"]):
                issues.append(f"unsafe pending file: {pending.relative_to(root)}")
            restore = safe_target(root, item["path"] + ".upgrade-restore")
            if restore.exists() or restore.is_symlink():
                issues.append(f"unexpected restore temp: {restore.relative_to(root)}")
        except (OSError, ValueError, CgspecError) as exc:
            issues.append(str(exc))
    return issues


def _check_restore_dirs(root: Path, plan: dict) -> list[str]:
    from install import safe_target
    issues = []
    before, after = plan["before_dirs"], plan["after_dirs"]
    for rel in set(before) | set(after):
        try:
            path = safe_target(root, rel)
            if path.exists() and not path.is_dir():
                issues.append(f"directory changed: {rel}")
            elif path.is_dir() and rel in before and rel in after:
                mode = path.stat().st_mode & 0o777
                if mode not in (before[rel], after[rel]):
                    issues.append(f"directory mode changed: {rel}")
        except (OSError, ValueError, CgspecError) as exc:
            issues.append(str(exc))
    return issues


def _backup_content(folder: Path, diff: list[dict]) -> tuple[dict[str, bytes], list[str]]:
    with tarfile.open(folder / "before.tar.gz", "r:gz") as tar:
        original = {m.name: tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
    problems = [f"corrupt backup: {i['path']}" for i in diff if i["before"] is not None
                and digest(original.get(i["path"])) != i["before"]]
    return original, problems


def _restore_files(root: Path, diff: list[dict], original: dict[str, bytes]) -> None:
    from install import safe_target
    for item in diff:
        path = safe_target(root, item["path"])
        safe_target(root, item["path"] + ".upgrade-new").unlink(missing_ok=True)
        if item["before"] is None:
            path.unlink(missing_ok=True)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = safe_target(root, item["path"] + ".upgrade-restore")
        with temp.open("xb") as handle:
            handle.write(original[item["path"]])
        os.chmod(temp, item["before_mode"])
        os.replace(temp, path)


def _restore_dirs(root: Path, plan: dict) -> None:
    from install import safe_target
    before, after = plan["before_dirs"], plan["after_dirs"]
    for rel, mode in sorted(before.items(), key=lambda pair: pair[0].count("/")):
        path = safe_target(root, rel)
        path.mkdir(parents=True, exist_ok=True)
        os.chmod(path, mode)
    for rel in sorted(set(after) - set(before), key=lambda p: p.count("/"), reverse=True):
        path = safe_target(root, rel)
        if path.is_dir():
            try:
                path.rmdir()
            except OSError:
                pass


def restore(root: Path, folder: Path) -> list[str]:
    from .upgrade_v1_git import check_rollback, remove_created
    plan = json.loads((folder / "plan.json").read_text())
    diff = plan["diff"]
    issues = _check_restore_files(root, diff) + _check_restore_dirs(root, plan)
    issues += check_rollback(root, plan.get("hooks", []))
    if issues:
        return issues
    original, issues = _backup_content(folder, diff)
    if issues:
        return issues
    _restore_files(root, diff, original)
    _restore_dirs(root, plan)
    remove_created(plan.get("hooks", []))
    return []


def _write_file(root: Path, item: dict, data: bytes | None) -> None:
    from install import safe_target
    path = safe_target(root, item["path"])
    if _file_state(path) != (item["before"], item["before_mode"]):
        raise ValueError(f"changed after journal: {item['path']}")
    if data is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = safe_target(root, item["path"] + ".upgrade-new")
    with temp.open("xb") as handle:
        handle.write(data)
    os.chmod(temp, item["after_mode"])
    os.replace(temp, path)


def _check_final(root: Path, before: dict[str, bytes], after: dict[str, bytes], pre: dict, post: dict,
                 files_reader) -> None:
    current = files_reader(root)
    for rel in list(current):
        if rel.startswith(ARCHIVE.as_posix() + "/") and rel not in before:
            current.pop(rel)
    expected = dict(after)
    marker = PROJECT_FILE.as_posix()
    if marker in before:
        expected[marker] = before[marker]
    else:
        expected.pop(marker, None)
    if current != expected:
        raise ValueError("project changed during publication; journal retained for recovery")
    current_modes = metadata(root, current)["files"]
    expected_modes = dict(post["files"])
    if marker in before:
        expected_modes[marker] = pre["files"][marker]
    else:
        expected_modes.pop(marker, None)
    if current_modes != expected_modes:
        raise ValueError("file modes changed during publication; journal retained for recovery")


def publish(root: Path, before: dict[str, bytes], after: dict[str, bytes], pre: dict, post: dict,
            hooks: list[dict], report: dict, files_reader, save_callback=save_journal) -> None:
    from install import safe_target
    if files_reader(root) != before or metadata(root, before) != pre:
        raise ValueError("project changed during stage; rerun dry-run")
    diff = inventory_diff(before, after, pre, post)
    save_callback(root, before, diff, pre, post, hooks)
    try:
        if files_reader(root) != before or metadata(root, before) != pre:
            raise ValueError("project changed after journal; no upgrade files written")
        hook_issues = check_hooks(root, hooks, published=False)
        if hook_issues:
            raise ValueError("; ".join(hook_issues))
        for item in [i for i in diff if i["path"] != PROJECT_FILE.as_posix()]:
            _write_file(root, item, after.get(item["path"]))
        for old in ("docs/adr", "docs/_cgspec/03-council", "docs/_cgspec/01-script"):
            folder = safe_target(root, old)
            for child in sorted(folder.rglob("*"), key=lambda p: len(p.parts), reverse=True) if folder.is_dir() else []:
                if child.is_dir():
                    child.rmdir()
            if folder.is_dir():
                folder.rmdir()
        for rel, mode in post["dirs"].items():
            path = safe_target(root, rel)
            if path.is_dir() and (rel not in pre["dirs"] or pre["dirs"][rel] != mode):
                os.chmod(path, mode)
        archive = safe_target(root, ARCHIVE.as_posix())
        archive.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / JOURNAL / "before.tar.gz", archive / "before.tar.gz")
        shutil.copy2(root / JOURNAL / "plan.json", archive / "plan.json")
        publish_hooks(root, hooks)
        _check_final(root, before, after, pre, post, files_reader)
        marker = next(i for i in diff if i["path"] == PROJECT_FILE.as_posix())
        _write_file(root, marker, after[PROJECT_FILE.as_posix()])
    except Exception:
        report["recovery"] = f"run upgrade --from-v1 --rollback; journal at {JOURNAL}"
        raise
    shutil.rmtree(root / JOURNAL)
    report["changed_files"] = len(diff)
