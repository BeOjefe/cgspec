#!/usr/bin/env python3
"""visual_summary.py: build the CI visual proof evidence and step summary from structured results.

The generated CI workflow runs journey.py and visual_audit.py with --json-out, then calls this script with
one --result NAME EXIT_CODE RESULTS_JSON per command. Printed text is never parsed. Each command is judged
on its own: a command that exits non-zero without its own structured result, or that exits non-zero while
reporting only PASS, adds a FAIL (or BLOCKED for exit 2) record for that command, whatever the other
commands reported. Record names with control characters are rejected, and every name rendered into the
Markdown table is escaped. Exit 0 when the files were written, 1 on bad arguments.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib.evidence import unsafe_name  # noqa: E402

VERDICTS = ("PASS", "FAIL", "PARTIAL", "BLOCKED")
EXIT_BLOCKED = 2
REVISION = re.compile(r"^[0-9a-f]{7,64}$")
ARTIFACT = re.compile(r"^[A-Za-z0-9._-]{1,200}$")


def _load(path: Path) -> list | None:
    """The command's own records, or None when it left no valid structured result."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    records = data.get("records") if isinstance(data, dict) else None
    return records if isinstance(records, list) else None


def _command_record(name: str, code: int, why: str) -> dict:
    verdict = "BLOCKED" if code == EXIT_BLOCKED else "FAIL"
    return {"item": f"{name}: {why}", "verdict": verdict, "command": name, "exit": code}


def build(invocations: list[tuple[str, int, Path]]) -> list[dict]:
    """Records for every (command name, exit code, results file), each command accounted for separately."""
    out = []
    for name, code, path in invocations:
        if unsafe_name(name):
            raise ValueError(f"invalid command name {name!r}")
        code = int(code)
        own = _load(path)
        if own is None:
            out.append(_command_record(name, code if code else 1, f"exited {code} without structured results"))
            continue
        records = []
        for raw in own:
            item = raw.get("item") if isinstance(raw, dict) else None
            if unsafe_name(item):
                records.append({"item": f"{name}: rejected a record whose name is empty or has control characters",
                                "verdict": "FAIL", "command": name})
                continue
            verdict = raw.get("verdict")
            detail = str(raw.get("detail", ""))[:2000]
            if verdict not in VERDICTS:
                detail, verdict = f"unknown verdict {str(verdict)[:40]!r}", "FAIL"
            records.append({"item": item, "verdict": verdict, "command": name, "detail": detail})
        if not records:
            records.append(_command_record(name, code, f"exited {code} with no records") if code
                           else {"item": f"{name}: nothing to check", "verdict": "PARTIAL", "command": name})
        elif code and all(r["verdict"] == "PASS" for r in records):
            records.append(_command_record(name, code, f"exited {code} although every record passed"))
        out += records
    return out


def cell(text: str) -> str:
    """Escape text for one Markdown table cell: no pipes, code spans, HTML, links or line breaks."""
    text = str(text)
    for old, new in (("\\", "\\\\"), ("&", "&amp;"), ("|", "\\|"), ("`", "\\`"), ("<", "&lt;"), (">", "&gt;"),
                     ("[", "\\["), ("]", "\\]")):
        text = text.replace(old, new)
    return re.sub(r"[\r\n  \x00-\x1f\x7f-\x9f]+", " ", text)


def render(records: list[dict], revision: str, artifact: str) -> str:
    lines = ["## CGSpec visual proof", "", f"PR head: `{revision}`", "",
             "| Journey or audit | Verdict | Artifact |", "|---|---|---|"]
    lines += [f"| {cell(r['item'])} | {cell(r['verdict'])} | `{artifact}` |" for r in records]
    return "\n".join(lines) + "\n"


def write(records: list[dict], revision: str, artifact: str, evidence: Path, summary: Path | None) -> None:
    if not REVISION.fullmatch(revision):
        raise ValueError(f"revision {revision!r} is not a commit SHA")
    if not ARTIFACT.fullmatch(artifact):
        raise ValueError(f"artifact name {artifact!r} has unexpected characters")
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps({"schema": 1, "revision": revision, "artifact": artifact, "journeys": records},
                                   indent=2) + "\n", encoding="utf-8")
    if summary is not None:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(render(records, revision, artifact))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--revision", required=True, help="PR head commit the commands ran on")
    parser.add_argument("--artifact", required=True, help="name of the uploaded artifact")
    parser.add_argument("--evidence", required=True, help="evidence JSON to write")
    parser.add_argument("--summary", help="Markdown file to append to (GITHUB_STEP_SUMMARY)")
    parser.add_argument("--result", nargs=3, action="append", default=[], metavar=("NAME", "EXIT", "JSON"),
                        help="one command: its name, exit code and --json-out file")
    args = parser.parse_args(argv)
    try:
        invocations = [(name, int(code), Path(path)) for name, code, path in args.result]
        if not invocations:
            raise ValueError("no --result given")
        records = build(invocations)
        write(records, args.revision, args.artifact, Path(args.evidence), Path(args.summary) if args.summary else None)
    except (OSError, ValueError) as exc:
        print(f"visual_summary: {exc}", file=sys.stderr)
        return 1
    for record in records:
        print(f"{record['verdict']} {cell(record['item'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
