#!/usr/bin/env python3
"""doctor.py: check a project against the CGSpec spec. Read-only unless --fix.

Exit 0 when there are no errors (warnings allowed), 1 when there are errors.
--fix only does safe repairs: regenerate the index section, create missing folders,
make frozen files read-only. It never edits records, never touches frozen content.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # never leave caches in the vendored engine
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import doctor_checks as C  # noqa: E402
from _lib import layout as L  # noqa: E402
from _lib.capabilities import doctor_findings as capability_findings  # noqa: E402
from _lib.document_dates import STAMP, touch  # noqa: E402
from _lib.common import (  # noqa: E402
    ENGINE_DIR, EXIT_FAIL, EXIT_INTERNAL, EXIT_OK, PROJECT_FILE, STATE_DIR, CgspecError, atomic_write_text, resolve_root,
)
from install import verify_engine  # noqa: E402
from memlog import parse as parse_memlog  # noqa: E402


def load_project(root: Path) -> dict | None:
    try:
        return json.loads((root / PROJECT_FILE).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def load_stages(root: Path) -> dict:
    try:
        data = json.loads((root / STATE_DIR / "checkpoint.json").read_text(encoding="utf-8"))
        return data.get("stages", {}) if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def load_legacy(root: Path) -> set[str]:
    try:
        data = json.loads((root / STATE_DIR / "legacy-baseline.json").read_text(encoding="utf-8"))
        return set(data.get("files", {})) if isinstance(data, dict) else set()
    except (OSError, ValueError):
        return set()


def load_owned_skills(root: Path) -> set[str]:
    data, findings = C.load_json(root / ENGINE_DIR / "owned-files.json", root, None)
    if findings or not isinstance(data, dict):
        return set()
    adapters = data.get("adapters")
    antigravity = adapters.get("antigravity") if isinstance(adapters, dict) else None
    skills = antigravity.get("skills") if isinstance(antigravity, dict) else None
    return {item for item in skills if isinstance(item, str)} if isinstance(skills, list) else set()


def run_checks(root: Path) -> list[C.Finding]:
    project = load_project(root)
    profile = project.get("profile", "") if isinstance(project, dict) else ""
    classes = project.get("path_classes", {}) if isinstance(project, dict) else {}
    checks = [
        ("project", lambda: C.project(root, project)),
        ("layout", lambda: C.layout(root, profile)),
        ("symlinks", lambda: C.symlinks(root)),
        ("state", lambda: C.state_files(root)),
        ("capabilities", lambda: capability_findings(root)),
        ("implementation_policy", lambda: __import__("_lib.project_policy", fromlist=["doctor_findings"]).doctor_findings(root)),
        ("spines", lambda: C.spines(root, load_stages(root))),
        ("document_dates", lambda: C.document_dates(root)),
        ("links", lambda: C.links(root)),
        ("records", lambda: C.records(root)),
        ("index", lambda: C.index(root)),
        ("frozen", lambda: C.frozen(root)),
        ("scripts", lambda: C.scripts(root, classes if isinstance(classes, dict) else {}, load_legacy(root),
                                      load_owned_skills(root))),
        ("engine", lambda: C.engine_integrity(root, verify_engine)),
        ("memlog", lambda: C.memlog(root, parse_memlog)),
        ("evidence", lambda: C.blocked(root)),
    ]
    findings: list[C.Finding] = []
    for name, check in checks:
        try:
            findings += list(check())
        except Exception as exc:  # one broken check must not hide the others
            findings.append(C.Finding("E-INTERNAL", name, f"check crashed: {exc!r}"))
    unique = {(f.code, f.path, f.message): f for f in findings}
    return list(unique.values())


def render_index(root: Path) -> str:
    lines = [L.INDEX_BEGIN]
    sections = [("Decisions", "adrs/"), ("Slices", "slices/"), ("Research", "_cgspec/02-research/"),
                ("Councils", "_cgspec/03-councils/")]
    records = C.indexed_records(root)
    for title, prefix in sections:
        items = [r for r in records if r.startswith(prefix)]
        if items:
            lines += ["", f"### {title}", ""]
            lines += [f"- [{Path(r.rstrip('/')).name}]({r})" for r in items]
    lines.append(L.INDEX_END)
    return "\n".join(lines)


def fix(root: Path, profile: str) -> list[str]:
    done = []
    for rel in L.REQUIRED_DIRS + (L.GUI_DIRS if profile in L.GUI_PROFILES else []):
        if not (root / rel).exists():
            (root / rel).mkdir(parents=True)
            done.append(f"created folder {rel}")
    index = root / "docs/00-INDEX.md"
    if index.is_file():
        text = index.read_text(encoding="utf-8")
        if L.INDEX_BEGIN in text and L.INDEX_END in text:
            head, rest = text.split(L.INDEX_BEGIN, 1)
            tail = rest.split(L.INDEX_END, 1)[1]
            new = head + render_index(root) + tail
        else:
            new = text.rstrip("\n") + "\n\n" + render_index(root) + "\n"
        if new != text:
            if len(new.splitlines()) > 1 and STAMP.fullmatch(new.splitlines()[1]):
                from _lib.common import utc_now
                new = touch(new, utc_now())
            atomic_write_text(index, new)
            done.append("regenerated index section in docs/00-INDEX.md")
    frozen = root / STATE_DIR / "frozen.json"
    if frozen.is_file():
        try:
            entries = json.loads(frozen.read_text(encoding="utf-8")).get("entries", [])
        except json.JSONDecodeError:
            entries = []
        for entry in entries:
            target = C.inside(root, str(entry.get("path", "")))
            if target is not None and target.is_file() and target.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
                os.chmod(target, target.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
                done.append(f"made read-only {entry['path']}")
    return done


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="doctor.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root")
    parser.add_argument("--fix", action="store_true", help="apply safe repairs, then check again")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--quiet", action="store_true", help="hide warnings")
    args = parser.parse_args(argv)
    try:
        root = Path(args.root).resolve() if args.root else resolve_root(None)
        repairs = []
        if args.fix:
            project = load_project(root) or {}
            repairs = fix(root, project.get("profile", ""))
        findings = run_checks(root)
    except CgspecError as exc:
        print(f"doctor: {exc}", file=sys.stderr)
        return EXIT_FAIL
    except Exception as exc:  # an engine bug must be visible, never a silent pass
        print(f"doctor: internal error: {exc!r}", file=sys.stderr)
        return EXIT_INTERNAL

    errors = [f for f in findings if f.is_error]
    warnings = [f for f in findings if not f.is_error]
    if args.json:
        print(json.dumps({"errors": len(errors), "warnings": len(warnings), "repairs": repairs,
                          "findings": [f.__dict__ for f in findings]}, indent=2))
    else:
        for line in repairs:
            print(f"FIXED {line}")
        for f in errors + ([] if args.quiet else warnings):
            print(f"{'ERROR' if f.is_error else 'WARN '} {f.code} {f.path}: {f.message}")
        print(f"doctor: {len(errors)} errors, {len(warnings)} warnings")
    return EXIT_FAIL if errors else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
