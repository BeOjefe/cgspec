"""Test helpers: import path for the engine and throwaway project trees."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENGINE = REPO / "engine"
if str(ENGINE) not in sys.path:
    sys.path.insert(0, str(ENGINE))

PY = sys.executable


def run_script(script: str, *args: str, cwd: Path | None = None, stdin: str | None = None):
    return subprocess.run(
        [PY, str(ENGINE / script), *args],
        cwd=cwd, input=stdin, capture_output=True, text=True, timeout=60,
    )


class TempDir:
    def __enter__(self) -> Path:
        self.path = Path(tempfile.mkdtemp(prefix="cgspec-test-"))
        return self.path

    def __exit__(self, *exc) -> None:
        shutil.rmtree(self.path, ignore_errors=True)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
