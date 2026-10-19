#!/usr/bin/env python3
"""impact.py: show what a change touches before anything is updated (spec 9, change flow).

Plain code, no AI: from the changed records (paths, record IDs, a noun with --term, a screen with
--screen) it follows Markdown links and record-ID mentions backwards through docs/, then lists the
records to update, the code in the affected slices' scope, the evidence that will go stale and the
frozen baselines that need a new version. Read-only. Exit 0, 1 on an unknown seed, 3 internal.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import deque
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import layout as L  # noqa: E402
from _lib.common import EXIT_FAIL, EXIT_INTERNAL, EXIT_OK, CgspecError, resolve_root  # noqa: E402
from _lib.globs import match_any  # noqa: E402
from _lib.mdlinks import link_targets  # noqa: E402

ID = re.compile(r"\b([A-Z]{2,8}-\d{3})\b")
OWN_ID = re.compile(r"^([A-Z]{2,8}-\d{3})")
SKIP_DOCS = ("docs/00-INDEX.md", "docs/00-INBOX.md", "docs/_memlog.md")
SKIP_PREFIX = ("docs/_cgspec/_archive/", "docs/_cgspec/01-engine/", "docs/_cgspec/05-runs/")
SCOPE = re.compile(r"^\s*[-*]?\s*\*\*Scope:\*\*\s*(.+)$", re.M | re.I)


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _walk(root: Path, base: Path):
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(d for d in dirnames if d not in L.SKIP_WALK and d != ".git")
        for name in sorted(filenames):
            yield Path(dirpath) / name


def load_docs(root: Path) -> dict[str, str]:
    docs = {}
    for path in _walk(root, root / "docs"):
        rel = _rel(path, root)
        if path.suffix == ".md" and rel not in SKIP_DOCS and not rel.startswith(SKIP_PREFIX):
            docs[rel] = path.read_text(encoding="utf-8", errors="replace")
    return docs


def _resolve_link(root: Path, doc: str, target: str) -> str | None:
    target = target.split("#", 1)[0].split("?", 1)[0]
    if not target or re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith("/"):
        return None
    full = os.path.normpath(os.path.join(root, os.path.dirname(doc), target))
    rel = os.path.relpath(full, root).replace(os.sep, "/")
    return None if rel.startswith("..") else rel


def doc_id(rel: str) -> str | None:
    found = OWN_ID.match(Path(rel).name)
    return found.group(1) if found else None


def referrers(root: Path, docs: dict[str, str]) -> dict[str, dict[str, str]]:
    """target path -> {doc that depends on it: why}."""
    by_id = {doc_id(rel): rel for rel in docs if doc_id(rel)}
    back: dict[str, dict[str, str]] = {}
    for rel, text in docs.items():
        for target in link_targets(text):
            dest = _resolve_link(root, rel, target)
            if dest and dest != rel:
                back.setdefault(dest, {}).setdefault(rel, f"links to {dest}")
        for rid in set(ID.findall(text)) - {doc_id(rel)}:
            if rid in by_id:
                back.setdefault(by_id[rid], {}).setdefault(rel, f"mentions {rid}")
    return back


def slice_scopes(text: str) -> list[str]:
    found = SCOPE.search(text)
    return [g.strip().strip("`").strip() for g in found.group(1).split(",") if g.strip()] if found else []


def resolve_seeds(root: Path, docs: dict[str, str], targets: list[str], term: str | None,
                  screen: str | None) -> list[str]:
    seeds: list[str] = []
    for target in targets:
        if ID.fullmatch(target):
            hits = [rel for rel in docs if doc_id(rel) == target]
            if not hits:
                raise CgspecError(f"no record {target} under docs/")
            seeds += hits
            continue
        path = (root / target).resolve()
        if not path.exists() or (path != root and root not in path.parents):
            raise CgspecError(f"{target} does not exist in this project")
        seeds += [_rel(p, root) for p in _walk(root, path)] if path.is_dir() else [_rel(path, root)]
    if term:
        word = re.compile(rf"\b{re.escape(term)}", re.I)
        seeds += [rel for rel, text in docs.items() if word.search(text)]
    if screen:
        proto = root / "docs/prototypes"
        seeds += [_rel(p, root) for p in _walk(root, proto / screen)] if (proto / screen).is_dir() else []
        snaps = proto / "_snapshots"
        if snaps.is_dir():
            seeds += [_rel(p, root) for p in sorted(snaps.glob(f"{screen}-v*.html"))]
    if (term or screen) and not seeds:
        raise CgspecError(f"nothing in this project names {term or screen}")
    return list(dict.fromkeys(seeds))


def build(root: Path, targets: list[str], term: str | None = None, screen: str | None = None,
          depth: int = 3) -> dict:
    docs = load_docs(root)
    seeds = resolve_seeds(root, docs, targets, term, screen)
    back = referrers(root, docs)
    slices = {rel: slice_scopes(text) for rel, text in docs.items() if rel.startswith("docs/slices/")}
    records: dict[str, dict] = {}
    queue = deque((s, 0) for s in seeds)
    for seed in seeds:  # a changed code file pulls in the slices whose scope holds it
        if not seed.startswith("docs/"):
            for rel, scopes in slices.items():
                if match_any(seed, scopes) and rel not in records:
                    records[rel] = {"path": rel, "depth": 1, "why": f"scope covers {seed}"}
                    queue.append((rel, 1))
    while queue:
        node, hops = queue.popleft()
        if hops >= depth:
            continue
        for rel, why in sorted(back.get(node, {}).items()):
            if rel not in records and rel not in seeds:
                records[rel] = {"path": rel, "depth": hops + 1, "why": why}
                queue.append((rel, hops + 1))
    scopes = [g for rel in list(records) + seeds if rel in slices for g in slices[rel]]
    code = [s for s in seeds if not s.startswith("docs/")]
    if scopes:
        for path in _walk(root, root):
            rel = _rel(path, root)
            if not rel.startswith("docs/") and rel not in code and match_any(rel, scopes):
                code.append(rel)
    touched = set(seeds) | set(records) | set(code)
    evidence = []
    ev_dir = root / "docs/_cgspec/06-evidence"
    for path in (_walk(root, ev_dir) if ev_dir.is_dir() else []):
        rel = _rel(path, root)
        if path.suffix != ".json" or rel.startswith("docs/_cgspec/06-evidence/tests/"):
            continue
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        covers = record.get("covers") if isinstance(record, dict) else None
        if isinstance(covers, list) and any(match_any(f, covers) for f in touched):
            evidence.append({"path": rel, "state": record.get("state", "unknown"), "covers": covers})
    frozen = []
    try:
        entries = json.loads((root / "docs/_cgspec/07-state/frozen.json").read_text(encoding="utf-8"))["entries"]
    except (OSError, ValueError, KeyError, TypeError):
        entries = []
    for entry in entries:
        if isinstance(entry, dict) and entry.get("path") in touched:
            frozen.append({"path": entry["path"], "kind": entry.get("kind"), "reason": entry.get("reason")})
    return {"seeds": seeds, "records": sorted(records.values(), key=lambda r: (r["depth"], r["path"])),
            "code": sorted(code), "evidence": evidence, "frozen": frozen, "depth": depth}


def render(data: dict) -> str:
    out = ["Impact map", "", "Changed: " + ", ".join(data["seeds"]), ""]
    out.append(f"Records to update ({len(data['records'])}):")
    out += [f"- {r['path']} (hop {r['depth']}: {r['why']})" for r in data["records"]] or ["- none"]
    out += ["", f"Code in the affected scope ({len(data['code'])}):"] + ([f"- {c}" for c in data["code"]] or ["- none"])
    out += ["", f"Evidence that goes stale and must be re-run ({len(data['evidence'])}):"]
    out += [f"- {e['path']} (now {e['state']})" for e in data["evidence"]] or ["- none"]
    out += ["", f"Frozen baselines touched; they never change, so a new version is needed ({len(data['frozen'])}):"]
    out += [f"- {f['path']} ({f['kind']}: {f['reason']})" for f in data["frozen"]] or ["- none"]
    out += ["", "Nothing was changed. Show this to the user and update everything together after approval."]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("targets", nargs="*", help="changed paths or record IDs (ADR-001, SLICE-004)")
    parser.add_argument("--term", help="a noun or word; documents naming it are treated as changed")
    parser.add_argument("--screen", help="a prototype screen name under docs/prototypes/")
    parser.add_argument("--depth", type=int, default=3, help="link hops to follow (default 3)")
    parser.add_argument("--root")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        if not (args.targets or args.term or args.screen):
            raise CgspecError("say what changed: paths, record IDs, --term or --screen")
        data = build(resolve_root(args.root), args.targets, args.term, args.screen, max(args.depth, 1))
    except CgspecError as exc:
        print(f"impact: {exc}", file=sys.stderr)
        return EXIT_FAIL
    except Exception as exc:  # report, never crash silently
        print(f"impact: internal error: {exc}", file=sys.stderr)
        return EXIT_INTERNAL
    print(json.dumps(data, indent=2) if args.json else render(data))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
