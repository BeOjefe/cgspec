"""The Finding record every doctor check yields."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Finding:
    code: str
    path: str
    message: str

    @property
    def is_error(self) -> bool:
        return self.code.startswith("E-")


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()
