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


def run(root: Path, targets: list[str], write: bool = True) -> tuple[int, list[str]]:
    lines, runs, meta, failed = [], [], {}, False
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
            if write:
                evidence.write(root, "journeys", label, f"journey:{data['name']}", "FAIL", covers, detail, "journey.py")
            continue
        runs.append({"kind": "journey", "label": label, "url": url, "steps": data["steps"],
                     "viewports": data["viewports"]})
    if not runs:
        return (EXIT_FAIL if failed else EXIT_OK), lines
    result = browser.run(root, runs, root / ".cgspec-scratch/journeys")
    if "blocked" in result:
        for item in runs:
            data, covers, _ = meta[item["label"]]
            lines.append(f"BLOCKED {data['name']}: {result['blocked']}")
            if write:
                evidence.write(root, "journeys", item["label"], f"journey:{data['name']}", "BLOCKED", covers,
                               result["blocked"], "journey.py")
        return (EXIT_FAIL if failed else EXIT_BLOCKED), lines
    for item in result["results"]:
        data, covers, _ = meta[item["label"]]
        problems = []
        for vp in item["viewports"]:
            if not vp["ok"]:
                where = f"step {vp['step'] + 1} (state {vp['state']})" if "step" in vp else f"state {vp['state']}"
                problems.append(f"{vp['viewport']}: {where}: {vp.get('error') or '; '.join(vp['errors'][:3])}")
        verdict = "FAIL" if problems else "PASS"
        failed = failed or bool(problems)
        detail = "\n".join(problems) or f"all steps passed on {', '.join(data['viewports'])}"
        lines.append(f"{verdict} {data['name']}" + (f":\n  " + "\n  ".join(problems) if problems else ""))
        if write:
            evidence.write(root, "journeys", item["label"], f"journey:{data['name']}", verdict, covers, detail,
                           "journey.py")
    return (EXIT_FAIL if failed else EXIT_OK), lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("targets", nargs="*", help="journey files, folders or screen names (default: all screens)")
    parser.add_argument("--no-evidence", action="store_true", help="do not write evidence records")
    parser.add_argument("--root")
    args = parser.parse_args(argv)
    try:
        code, lines = run(resolve_root(args.root), args.targets, not args.no_evidence)
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
