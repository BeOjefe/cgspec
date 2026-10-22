#!/usr/bin/env python3
"""Spec-1 content gate for the CGSpec plugin source tree.

This tree is not an installed consumer project (AGENTS.md), so the consumer
commit gate cannot run here: `commit_gate.evaluate` needs docs/_cgspec/project.json
and the tier, slice and approval records that go with it. The rules below need no
project state, so the repository that ships them is held to them too.

The patterns are imported from the engine rather than restated, so the source gate
and the consumer gate cannot drift apart.

Fixture exemption: a line carrying the marker below is allowed to contain a
secret-shaped or emoji string, because the detector's own regression tests must hold
fabricated keys, and the module that defines the patterns necessarily contains
pattern-shaped text (the `url-password` regex matches its own source). The marker is
honoured only under `tests/` and in the pattern module itself, so it cannot be used to
smuggle a real credential into shipped code.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "engine"))

from _lib.gates import EMOJI  # noqa: E402
from _lib.gitview import View  # noqa: E402
from _lib.inbox import contains_secret  # noqa: E402

FIXTURE_MARKER = "cgspec:test-fixture"
PATTERN_MODULE = "engine/_lib/inbox.py"  # defines the patterns, so it matches itself
BINARY_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg", ".pdf",
                   ".zip", ".gz", ".tgz", ".bundle", ".woff", ".woff2", ".ttf")


def _exempt(path: str, line: str) -> bool:
    if FIXTURE_MARKER not in line:
        return False
    return path.startswith("tests/") or path == PATTERN_MODULE


def reasons(root: Path) -> list[str]:
    """Reasons to refuse the staged commit. Empty list means allowed."""
    view = View.staged(root)
    found: list[str] = []
    for change in view.changes():
        if change.status != "D" and ("__pycache__/" in change.path or change.path.endswith(".pyc")):
            found.append(f"{change.path}: cache files may not be committed")
    for path, lines in view.added_lines().items():
        if path.endswith(BINARY_SUFFIXES):
            continue
        if any(EMOJI.search(line) for line in lines if not _exempt(path, line)):
            found.append(f"{path}: decorative emoji added (spec 1: no emojis)")
        kind = next((k for line in lines
                     if not _exempt(path, line) and (k := contains_secret(line))), None)
        if kind:
            article = "an" if kind[0] in "aeiou" else "a"
            found.append(f"{path}: added content looks like {article} {kind} (spec 1: no secrets "
                         "committed; use environment variables, and reference them by name only)")
    return list(dict.fromkeys(found))


def main() -> int:
    try:
        found = reasons(ROOT)
    except Exception as exc:  # a broken gate must not silently permit the commit
        print(f"cgspec source gate failed to run: {exc}", file=sys.stderr)
        print("cgspec: refusing the commit because it could not be checked.", file=sys.stderr)
        return 1
    if not found:
        return 0
    print("cgspec source gate blocked this commit:", file=sys.stderr)
    for reason in found:
        print(f"  - {reason}", file=sys.stderr)
    print("", file=sys.stderr)
    print(f"A fabricated secret in a test may carry the marker {FIXTURE_MARKER} on its line.",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
