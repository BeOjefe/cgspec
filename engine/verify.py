#!/usr/bin/env python3
"""verify.py: run doctor, journeys and visual audit, printing a single summary table.

Exit 0 only if nothing FAILED and nothing is BLOCKED; PARTIAL exits non-zero too
unless --allow-partial. Machine-readable output with --json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _lib.common import EXIT_BLOCKED, EXIT_FAIL, EXIT_INTERNAL, EXIT_OK, EXIT_PARTIAL, CgspecError, resolve_root  # noqa: E402
from _lib.layout import GUI_PROFILES  # noqa: E402
import doctor  # noqa: E402
import journey  # noqa: E402
import visual_audit  # noqa: E402
import os
import tempfile
import parity  # noqa: E402


def _is_gui(root: Path) -> bool:
    try:
        project = json.loads((root / "docs/_cgspec/project.json").read_text(encoding="utf-8"))
        profile = project.get("profile", "")
        return not profile or profile in GUI_PROFILES
    except (OSError, ValueError):
        return True


def run_doctor(root: Path) -> tuple[str, int, int]:
    """(verdict, errors_count, warnings_count)."""
    findings = doctor.run_checks(root)
    errors = [f for f in findings if f.is_error]
    warnings = [f for f in findings if not f.is_error]
    verdict = "FAIL" if errors else "PASS"
    return verdict, len(errors), len(warnings)


def run_journeys(root: Path) -> tuple[str, int, int, list[str]]:
    """(verdict, errors_count, warnings_count, artifacts)."""
    if not _is_gui(root):
        return "PASS", 0, 0, []
    records: list[dict] = []
    try:
        code, lines = journey.run(root, targets=[], write=True, video=False, records=records)
    except CgspecError:
        return "FAIL", 1, 0, []

    artifacts = []
    shots_dir = root / ".cgspec-scratch/journeys"
    if shots_dir.is_dir():
        artifacts = sorted(p.relative_to(root).as_posix() for p in shots_dir.glob("*.png") if p.is_file())

    if not records:
        protos = root / "docs/prototypes"
        screens = [p for p in protos.iterdir() if p.is_dir() and not p.name.startswith("_")] if protos.is_dir() else []
        if screens:
            return "PARTIAL", 0, 0, artifacts
        return "PASS", 0, 0, artifacts

    verdicts = {r.get("verdict", "FAIL") for r in records}
    if "FAIL" in verdicts:
        overall = "FAIL"
    elif "BLOCKED" in verdicts:
        overall = "BLOCKED"
    elif "PARTIAL" in verdicts:
        overall = "PARTIAL"
    else:
        overall = "PASS"

    errors = sum(1 for r in records if r.get("verdict") == "FAIL")
    warnings = 0
    return overall, errors, warnings, artifacts


def run_visual_audit(root: Path) -> tuple[str, int, int, list[str]]:
    """(verdict, errors_count, warnings_count, artifacts)."""
    if not _is_gui(root):
        return "PASS", 0, 0, []
    records: list[dict] = []
    try:
        code, lines = visual_audit.audit(root, raw=[], write=True, video=False, records=records)
    except CgspecError:
        return "FAIL", 1, 0, []

    artifacts = []
    shots_dir = root / ".cgspec-scratch/visual"
    if shots_dir.is_dir():
        artifacts = sorted(p.relative_to(root).as_posix() for p in shots_dir.glob("*.png") if p.is_file())

    if not records:
        # Check if non-GUI profile
        for line in lines:
            if "NOT_APPLICABLE" in line:
                return "PASS", 0, 0, []
        return ("FAIL" if code == EXIT_FAIL else "PASS"), 0, 0, artifacts

    verdicts = {r.get("verdict", "FAIL") for r in records}
    if "FAIL" in verdicts:
        overall = "FAIL"
    elif "BLOCKED" in verdicts:
        overall = "BLOCKED"
    elif "PARTIAL" in verdicts:
        overall = "PARTIAL"
    else:
        overall = "PASS"

    errors = 0
    warnings = 0
    for r in records:
        for line in r.get("detail", "").splitlines():
            line = line.strip()
            if line.startswith("E-"):
                errors += 1
            elif line.startswith("W-"):
                warnings += 1

    return overall, errors, warnings, artifacts


def verify_json(root: Path, allow_partial: bool = False) -> dict:
    doc_v, doc_e, doc_w = run_doctor(root)
    jrn_v, jrn_e, jrn_w, jrn_a = run_journeys(root)
    vis_v, vis_e, vis_w, vis_a = run_visual_audit(root)

    checks = [
        {"check": "doctor", "result": doc_v, "errors": doc_e, "warnings": doc_w, "artifacts": []},
        {"check": "journeys", "result": jrn_v, "errors": jrn_e, "warnings": jrn_w, "artifacts": jrn_a},
        {"check": "visual_audit", "result": vis_v, "errors": vis_e, "warnings": vis_w, "artifacts": vis_a},
    ]

    base = os.environ.get("CGSPEC_BASE_REV")
    if _is_gui(root) and base:
        try:
            with tempfile.TemporaryDirectory(prefix="cgspec-parity-") as tmp:
                closure = parity.execute(root, base, Path(tmp))
            result = "FAIL" if any(r["verdict"] == "FAIL" for r in closure) else "PASS"
        except (CgspecError, OSError, ValueError) as exc:
            result = "BLOCKED"
        checks.append({"check": "built_app_parity", "result": result, "errors": int(result != "PASS"),
                       "warnings": 0, "artifacts": []})
    all_verdicts = {c["result"] for c in checks}
    if "FAIL" in all_verdicts:
        overall = "FAIL"
        exit_code = EXIT_FAIL
    elif "BLOCKED" in all_verdicts:
        overall = "BLOCKED"
        exit_code = EXIT_BLOCKED
    elif "PARTIAL" in all_verdicts:
        overall = "PARTIAL"
        exit_code = EXIT_OK if allow_partial else EXIT_PARTIAL
    else:
        overall = "PASS"
        exit_code = EXIT_OK

    return {
        "schema": 1,
        "verdict": overall,
        "exit_code": exit_code,
        "checks": checks,
    }


def verify(root: Path, allow_partial: bool = False) -> tuple[int, str]:
    data = verify_json(root, allow_partial=allow_partial)
    rows = []
    headers = ("Check", "Result", "Errors", "Warnings", "Artifacts")
    for c in data["checks"]:
        arts = ", ".join(c["artifacts"]) if c["artifacts"] else "-"
        rows.append((c["check"], c["result"], str(c["errors"]), str(c["warnings"]), arts))

    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(val))

    # Format table
    fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
    lines = [fmt.format(*headers)]
    lines.append("  ".join("-" * w for w in col_widths))
    for row in rows:
        lines.append(fmt.format(*row))

    lines.append("")
    lines.append(f"Verdict: {data['verdict']}")
    return data["exit_code"], "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", help="project root directory")
    parser.add_argument("--allow-partial", action="store_true", help="exit 0 on PARTIAL (when nothing FAILED or BLOCKED)")
    parser.add_argument("--json", action="store_true", help="output structured JSON")
    args = parser.parse_args(argv)

    try:
        root = resolve_root(args.root)
        if args.json:
            result = verify_json(root, allow_partial=args.allow_partial)
            print(json.dumps(result, indent=2))
            return result["exit_code"]
        code, out = verify(root, allow_partial=args.allow_partial)
        print(out)
        return code
    except CgspecError as exc:
        print(f"verify: {exc}", file=sys.stderr)
        return EXIT_FAIL
    except Exception as exc:
        print(f"verify: internal error: {exc}", file=sys.stderr)
        return EXIT_INTERNAL


if __name__ == "__main__":
    sys.exit(main())
