#!/usr/bin/env python3
"""journey.py: run user journeys with assertions per state, against test IDs (spec 6, 7).

A journey is JSON: {"name", "url", "viewports"?, "covers"?, "steps": [...]}. Steps act on
data-testid values: click, fill+value, press+key, select+value, check, hover, goto, state (label),
screenshot, expect: [{visible|hidden|text+equals/contains|value+equals|count+equals|enabled|disabled|url}].
The same journeys written at layer 4 run unchanged against the real frontend (url http://...).
Test IDs a local journey names must exist in the screen's files; that is checked without a browser.
Exit 0 all passed, 1 a journey failed or names a missing test ID, 2 blocked (no browser), 3 internal.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import browser, evidence  # noqa: E402
from _lib.common import EXIT_FAIL, EXIT_INTERNAL, EXIT_OK, CgspecError, resolve_root  # noqa: E402

EXIT_BLOCKED = 2
ACTIONS = {"click": (), "fill": ("value",), "press": ("key",), "select": ("value",), "check": (), "hover": (),
           "goto": (), "state": (), "screenshot": (), "expect": ()}
ASSERTIONS = {"visible", "hidden", "text", "value", "count", "enabled", "disabled", "url"}
TARGETS = ("click", "fill", "press", "select", "check", "hover")
PROTOTYPES = "docs/prototypes"


def discover(root: Path, targets: list[str]) -> list[Path]:
    if not targets:
        return sorted((root / PROTOTYPES).glob("*/journeys/*.json"))
    found = []
    for target in targets:
        path = root / target
        if path.is_file():
            found.append(path)
        elif path.is_dir():
            found += sorted(path.rglob("*.json"))
        elif (root / PROTOTYPES / target / "journeys").is_dir():
            found += sorted((root / PROTOTYPES / target / "journeys").glob("*.json"))
        else:
            raise CgspecError(f"no journey file, folder or screen named {target}")
    if not found:
        raise CgspecError("no journeys found")
    return found


def load(path: Path, root: Path) -> dict:
    rel = path.relative_to(root).as_posix()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise CgspecError(f"{rel}: not valid JSON ({exc})")
    if not isinstance(data, dict) or not isinstance(data.get("name"), str) or not isinstance(data.get("url"), str) \
            or not isinstance(data.get("steps"), list) or not data["steps"]:
        raise CgspecError(f"{rel}: a journey needs name, url and a non-empty steps list")
    if evidence.unsafe_name(data["name"]):
        raise CgspecError(f"{rel}: a journey name must be non-empty and contain no newlines or control characters")
    for i, step in enumerate(data["steps"]):
        keys = [k for k in step if k in ACTIONS and k != "state"] if isinstance(step, dict) else []
        keys = keys or (["state"] if isinstance(step, dict) and "state" in step else [])
        if len(keys) != 1 or any(extra not in step for extra in ACTIONS[keys[0]]):
            raise CgspecError(f"{rel}: step {i + 1} needs exactly one action (a state label may go with it) of {', '.join(ACTIONS)}")
        for a in step.get("expect", []):
            if not isinstance(a, dict) or not (set(a) & ASSERTIONS):
                raise CgspecError(f"{rel}: step {i + 1} has an unknown assertion {a}")
    viewports = data.get("viewports", ["desktop"])
    if not set(viewports) <= {"desktop", "mobile"}:
        raise CgspecError(f"{rel}: viewports are desktop and mobile")
    data["viewports"] = viewports
    return data


def test_ids(data: dict) -> set[str]:
    ids = {str(s[k]) for s in data["steps"] for k in TARGETS if k in s}
    ids |= {str(a[k]) for s in data["steps"] for a in s.get("expect", []) for k in ASSERTIONS - {"url"} if k in a}
    return ids


def resolve(root: Path, path: Path, data: dict) -> tuple[str, Path | None]:
    """(url, screen folder or None for a served app)."""
    if re.match(r"^https?://", data["url"]):
        return data["url"], None
    screen = path.parent.parent if path.parent.name == "journeys" else path.parent
    page = (screen / data["url"]).resolve()
    if not page.is_file() or root.resolve() not in page.parents:
        raise CgspecError(f"{path.relative_to(root).as_posix()}: {data['url']} is not a file in this project")
    return page.as_uri(), screen


def missing_ids(screen: Path, ids: set[str]) -> list[str]:
    text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in screen.rglob("*")
                     if p.is_file() and p.suffix.lower() in {".html", ".htm", ".js", ".mjs"} and "journeys" not in p.parts)
    return sorted(i for i in ids if not re.search(rf"""["'`=]{re.escape(i)}["'`\s>]""", text))


def step_failures(item: dict | None) -> list[str]:
    viewports = item.get("viewports") if isinstance(item, dict) else None
    problems = []
    for vp in viewports if isinstance(viewports, list) else []:
        if isinstance(vp, dict) and vp.get("ok") is not True:
            where = f"step {vp['step'] + 1} (state {vp.get('state')})" if isinstance(vp.get("step"), int) \
                else f"state {vp.get('state')}"
            errors = vp.get("errors") if isinstance(vp.get("errors"), list) else []
            reason = vp.get("error") or "; ".join(map(str, errors[:3])) or "not ok"
            problems.append(f"{vp.get('viewport')}: {where}: {reason}")
    return problems


def run(root: Path, targets: list[str], write: bool = True, video: bool = False,
        records: list[dict] | None = None) -> tuple[int, list[str]]:
    """(exit code, printed lines). `records` collects one structured {item, verdict, detail} per journey."""
    lines, runs, meta, failed = [], [], {}, False
    records = records if records is not None else []
    for path in discover(root, targets):
        data = load(path, root)
        url, screen = resolve(root, path, data)
        rel = path.relative_to(root).as_posix()
        label = evidence.slug(f"{screen.name if screen else 'app'}-{data['name']}")
        covers = data.get("covers") or ([f"{screen.relative_to(root).as_posix()}/**"] if screen else [rel])
        meta[label] = (data, covers, rel)
        gone = missing_ids(screen, test_ids(data)) if screen else []
        if gone:
            failed = True
            detail = f"test IDs not found in {screen.relative_to(root).as_posix()}: {', '.join(gone)}"
            lines.append(f"FAIL {data['name']}: {detail}")
            records.append({"item": data["name"], "verdict": "FAIL", "detail": detail})
            if write:
                evidence.write(root, "journeys", label, f"journey:{data['name']}", "FAIL", covers, detail, "journey.py")
            continue
        runs.append({"kind": "journey", "label": label, "url": url, "steps": data["steps"],
                     "viewports": data["viewports"], "video": video})
    if not runs:
        return (EXIT_FAIL if failed else EXIT_OK), lines
    shots = root / ".cgspec-scratch/journeys"
    result = browser.run(root, runs, shots, video=video)
    if "blocked" in result:
        for item in runs:
            data, covers, _ = meta[item["label"]]
            lines.append(f"BLOCKED {data['name']}: {result['blocked']}")
            records.append({"item": data["name"], "verdict": "BLOCKED", "detail": result["blocked"]})
            if write:
                evidence.write(root, "journeys", item["label"], f"journey:{data['name']}", "BLOCKED", covers,
                               result["blocked"], "journey.py")
        return (EXIT_FAIL if failed else EXIT_BLOCKED), lines
    reported = browser.results_by_label(result)
    for run_item in runs:
        data, covers, _ = meta[run_item["label"]]
        item = reported.get(run_item["label"])
        # A PASS needs a driver result for every expected viewport and every expected artifact on disk.
        problems = browser.proof_problems(run_item, item, shots) + step_failures(item)
        verdict = "FAIL" if problems else "PASS"
        failed = failed or bool(problems)
        detail = "\n".join(problems) or f"all steps passed on {', '.join(data['viewports'])}"
        lines.append(f"{verdict} {data['name']}" + (f":\n  " + "\n  ".join(problems) if problems else ""))
        records.append({"item": data["name"], "verdict": verdict, "detail": detail})
        if write:
            evidence.write(root, "journeys", item["label"], f"journey:{data['name']}", verdict, covers, detail,
                           "journey.py")
    return (EXIT_FAIL if failed else EXIT_OK), lines


def write_results(path: Path, tool: str, records: list[dict]) -> None:
    path.write_text(json.dumps({"schema": 1, "tool": tool, "records": records}, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("targets", nargs="*", help="journey files, folders or screen names (default: all screens)")
    parser.add_argument("--no-evidence", action="store_true", help="do not write evidence records")
    parser.add_argument("--video", action="store_true", help="record a WebM for each journey viewport")
    parser.add_argument("--json-out", help="write structured results (one record per journey) to this file")
    parser.add_argument("--root")
    args = parser.parse_args(argv)
    records: list[dict] = []
    try:
        code, lines = run(resolve_root(args.root), args.targets, not args.no_evidence, args.video, records)
        if args.json_out:
            write_results(Path(args.json_out), "journey", records)
    except CgspecError as exc:
        print(f"journey: {exc}", file=sys.stderr)
        return EXIT_FAIL
    except Exception as exc:  # report, never crash silently
        print(f"journey: internal error: {exc}", file=sys.stderr)
        return EXIT_INTERNAL
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
