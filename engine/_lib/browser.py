"""Run browser work through the project's own Playwright (Node). Reports BLOCKED, never guesses,
when Node, Playwright or Chromium is missing; set CGSPEC_BROWSER=none to force that."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

DRIVER = Path(__file__).with_name("browser_driver.js")
TIMEOUT = 900


def run(root: Path, runs: list[dict], shots: Path, video: bool = False) -> dict:
    """{'results': [...]} or {'blocked': reason}."""
    if os.environ.get("CGSPEC_BROWSER", "").lower() == "none":
        return {"blocked": "browser checks disabled (CGSPEC_BROWSER=none)"}
    node = shutil.which("node")
    if not node:
        return {"blocked": "Node.js is not installed; browser checks need Node and Playwright"}
    shots.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
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
    if "error" in data:
        return {"blocked": f"browser driver failed: {data['error'][:300]}"}
    return data
