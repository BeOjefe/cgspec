"""Run browser work through Playwright (Node). Reports BLOCKED, never guesses, when Node, Playwright or
Chromium is missing; set CGSPEC_BROWSER=none to force that.

Trusted mode: when CGSPEC_PLAYWRIGHT_DIR is set (the generated CI workflow installs a pinned Playwright
there, outside the checkout), the driver loads Playwright only from that directory and never from the
project's node_modules. In every mode a result proves nothing unless the driver reported every expected
viewport and every expected screenshot (and WebM video when requested) exists on disk; see proof_problems."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

DRIVER = Path(__file__).with_name("browser_driver.js")
TIMEOUT = 900
AUDIT_VIEWPORTS = ("desktop", "mobile")
MAGIC = {".png": b"\x89PNG\r\n\x1a\n", ".webm": b"\x1a\x45\xdf\xa3"}


def expected_viewports(item: dict) -> list[str]:
    if item.get("kind") == "audit":
        return list(AUDIT_VIEWPORTS)
    return list(item.get("viewports") or ["desktop"])


def expected_files(item: dict, shots: Path, viewport: str) -> list[Path]:
    """Artifacts the driver must leave for one viewport of one run (names match browser_driver.js)."""
    label = f"{item['label']}-{viewport}"
    files = [shots / f"{label}.png"]
    if item.get("kind") != "audit":
        files += [shots / f"{label}-{s['screenshot']}.png" for s in item.get("steps", [])
                  if isinstance(s, dict) and "screenshot" in s]
    if item.get("video"):
        files.append(shots / f"{label}.webm")
    return files


def _proved(path: Path) -> bool:
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
            return False
        with path.open("rb") as handle:
            return handle.read(8).startswith(MAGIC.get(path.suffix.lower(), b""))
    except OSError:
        return False


DUPLICATE = object()  # sentinel: distinct from "no result at all" (a missing key / None)


def results_by_label(result: dict) -> dict[str, dict]:
    """Maps each label the driver returned to its result, or to DUPLICATE when the driver returned
    that label more than once. A duplicate can never be trusted to belong to one run rather than
    another (it may silently stand in for a different run's failure), so it fails closed instead of
    the last one overwriting the others; it is distinguished from a label the driver never returned
    at all, which a plain dict lookup also reports as missing."""
    out: dict[str, dict] = {}
    for item in result.get("results", []) if isinstance(result.get("results"), list) else []:
        if isinstance(item, dict) and isinstance(item.get("label"), str):
            label = item["label"]
            out[label] = DUPLICATE if label in out else item
    return out


def proof_problems(item: dict, got: dict | None, shots: Path) -> list[str]:
    """Why the driver's answer for `item` does not prove a PASS; empty when it does.
    A journey viewport that reported a failed step is judged by that failure, not by its artifacts."""
    if got is DUPLICATE:
        return ["browser driver returned this run's label more than once; a duplicate result proves nothing"]
    if not isinstance(got, dict) or not isinstance(got.get("viewports"), list):
        return ["browser driver returned no result for this run"]
    reported = {vp.get("viewport"): vp for vp in got["viewports"] if isinstance(vp, dict)}
    problems = []
    for viewport in expected_viewports(item):
        vp = reported.get(viewport)
        if vp is None:
            problems.append(f"{viewport}: browser driver returned no result for this viewport")
            continue
        if item.get("kind") != "audit" and vp.get("ok") is not True:
            continue
        for path in expected_files(item, shots, viewport):
            kind = "video" if path.suffix == ".webm" else "screenshot"
            if not _proved(path):
                problems.append(f"{viewport}: expected {kind} {path.name} is missing, empty or not a real {path.suffix[1:]}")
    return problems


def _trusted_dir(root: Path) -> tuple[str | None, str | None]:
    """(trusted Playwright directory or None, blocked reason or None)."""
    raw = os.environ.get("CGSPEC_PLAYWRIGHT_DIR", "")
    if not raw:
        return None, None
    path = Path(raw)
    if not path.is_absolute() or not path.is_dir():
        return None, f"CGSPEC_PLAYWRIGHT_DIR {raw!r} is not an existing absolute directory"
    resolved, project = path.resolve(), root.resolve()
    if resolved == project or resolved.is_relative_to(project):
        return None, "CGSPEC_PLAYWRIGHT_DIR is inside the checked project; it must be outside the checkout"
    return str(resolved), None


def run(root: Path, runs: list[dict], shots: Path, video: bool = False) -> dict:
    """{'results': [...]} or {'blocked': reason}."""
    if os.environ.get("CGSPEC_BROWSER", "").lower() == "none":
        return {"blocked": "browser checks disabled (CGSPEC_BROWSER=none)"}
    trusted, refused = _trusted_dir(root)
    if refused:
        return {"blocked": refused}
    node = shutil.which("node")
    if not node:
        return {"blocked": "Node.js is not installed; browser checks need Node and Playwright"}
    shots.mkdir(parents=True, exist_ok=True)
    for item in runs:  # stale artifacts from an earlier run must not count as proof
        for viewport in expected_viewports(item):
            for path in expected_files(item, shots, viewport):
                if path.is_symlink() or path.is_file():
                    path.unlink()
    env = dict(os.environ)
    if trusted:
        env.pop("NODE_PATH", None)
        env.pop("NODE_OPTIONS", None)
        env["CGSPEC_PLAYWRIGHT_DIR"] = trusted
    else:
        env["NODE_PATH"] = os.pathsep.join(filter(None, [str(root / "node_modules"), env.get("NODE_PATH", "")]))
    job = {"runs": runs, "shots": str(shots), "executable": os.environ.get("CGSPEC_CHROMIUM") or None,
           "video": video}
    try:
        out = subprocess.run([node, str(DRIVER)], input=json.dumps(job), capture_output=True, text=True, cwd=root,
                             env=env, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"blocked": f"browser run exceeded {TIMEOUT}s"}
    lines = [line for line in out.stdout.splitlines() if line.startswith("{")]
    try:
        data = json.loads(lines[-1])
    except (IndexError, ValueError):
        return {"blocked": f"browser driver gave no result: {(out.stderr or out.stdout).strip()[-300:]}"}
    if not isinstance(data, dict):
        return {"blocked": "browser driver gave no result object"}
    if "error" in data:
        return {"blocked": f"browser driver failed: {str(data['error'])[:300]}"}
    return data
