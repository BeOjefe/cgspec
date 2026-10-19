#!/usr/bin/env python3
"""bundle_prototype.py: cut a frozen milestone snapshot of a grey prototype screen (spec 6, 8).

Inlines the screen's local stylesheets, scripts, images and fonts into one self-contained
docs/prototypes/_snapshots/<screen>-vN.html, so the snapshot renders the same forever. Remote
resources are refused. Needs the user's approval of the layer lock. The snapshot is set read-only,
its hash appended to 07-state/frozen.json and the cut recorded in the ledger.
Exit 0 cut, 1 refused, 3 internal.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mimetypes
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib.common import EXIT_FAIL, EXIT_INTERNAL, EXIT_OK, STATE_DIR, CgspecError, resolve_root, utc_now, write_json  # noqa: E402

PROTOTYPES = Path("docs/prototypes")
SNAPSHOTS = PROTOTYPES / "_snapshots"
GREY_LAYERS = range(0, 5)  # layers 5-7 live in the real frontend, not in snapshots
REMOTE = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//)", re.I)
SCRIPT = re.compile(r"<script\b([^>]*?)\bsrc\s*=\s*([\"'])(.*?)\2([^>]*)>\s*</script\s*>", re.I | re.S)
STYLESHEET = re.compile(r"<link\b(?=[^>]*\brel\s*=\s*[\"']?stylesheet)[^>]*?\bhref\s*=\s*([\"'])(.*?)\1[^>]*>", re.I | re.S)
RESOURCE = re.compile(r"(<(?:img|source|video|audio|track|input|embed|iframe|link)\b[^>]*?\b(?:src|href|poster)\s*=\s*)([\"'])(.*?)\2",
                      re.I | re.S)
CSS_URL = re.compile(r"url\(\s*([\"']?)([^\"')]+)\1\s*\)", re.I)
CSS_IMPORT = re.compile(r"@import\s+(?:url\()?\s*([\"'])([^\"']+)\1\s*\)?\s*;", re.I)


class Bundler:
    def __init__(self, root: Path):
        self.root, self.base = root, (root / PROTOTYPES).resolve()
        self.problems: list[str] = []

    def _local(self, ref: str, here: Path) -> Path | None:
        if REMOTE.match(ref):
            if not ref.lower().startswith("data:"):
                self.problems.append(f"remote resource {ref} (a snapshot must not depend on the network)")
            return None
        clean = ref.split("#", 1)[0].split("?", 1)[0]
        if not clean:
            return None
        target = (here / clean).resolve()
        if self.base not in target.parents or (self.base / "_snapshots") in target.parents:
            self.problems.append(f"{ref} is outside docs/prototypes/")
        elif not target.is_file():
            self.problems.append(f"{ref} is referenced but missing")
        else:
            return target
        return None

    def data_uri(self, ref: str, here: Path) -> str:
        target = self._local(ref, here)
        if target is None:
            return ref
        if target.suffix.lower() == ".css":
            payload = self.css(target).encode("utf-8")
            kind = "text/css"
        else:
            payload, kind = target.read_bytes(), mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        return f"data:{kind};base64,{base64.b64encode(payload).decode('ascii')}"

    def css(self, path: Path, depth: int = 0) -> str:
        text = path.read_text(encoding="utf-8", errors="replace")
        def imp(m):
            target = self._local(m.group(2), path.parent)
            return self.css(target, depth + 1) if target is not None and depth < 5 else ""
        text = CSS_IMPORT.sub(imp, text)
        return CSS_URL.sub(lambda m: f'url("{self.data_uri(m.group(2), path.parent)}")', text)

    def html(self, entry: Path) -> str:
        text, here = entry.read_text(encoding="utf-8", errors="replace"), entry.parent
        def script(m):
            target = self._local(m.group(3), here)
            if target is None:
                return m.group(0)
            body = target.read_text(encoding="utf-8", errors="replace").replace("</script", "<\\/script")
            return f"<script{m.group(1).rstrip()}{m.group(4)}>\n{body}\n</script>"
        def sheet(m):
            target = self._local(m.group(2), here)
            return f"<style>\n{self.css(target)}\n</style>" if target is not None else m.group(0)
        text = SCRIPT.sub(script, text)
        text = STYLESHEET.sub(sheet, text)
        text = RESOURCE.sub(lambda m: f"{m.group(1)}{m.group(2)}{self.data_uri(m.group(3), here)}{m.group(2)}", text)
        return re.sub(r"(<style\b[^>]*>)(.*?)(</style>)",
                      lambda m: m.group(1) + CSS_URL.sub(lambda u: f'url("{self.data_uri(u.group(2), here)}")', m.group(2))
                      + m.group(3), text, flags=re.I | re.S)


def next_version(root: Path, screen: str) -> int:
    found = [int(m.group(1)) for p in (root / SNAPSHOTS).glob(f"{screen}-v*.html")
             if (m := re.fullmatch(rf"{re.escape(screen)}-v(\d+)\.html", p.name))]
    return max(found, default=0) + 1


def _revision(root: Path) -> str:
    out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root, capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else "no-git"


def cut(root: Path, screen: str, layer: int, approval: str, entry: str = "index.html", reason: str = "") -> Path:
    from _lib.inbox import approval_exists
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", screen):
        raise CgspecError("screen names are lowercase letters, digits and dashes")
    if layer not in GREY_LAYERS:
        raise CgspecError("snapshots are for grey prototype layers 0-4; layers 5-7 are the real frontend")
    source = root / PROTOTYPES / screen / entry
    if not source.is_file():
        raise CgspecError(f"no prototype entry at {source.relative_to(root).as_posix()}")
    if not approval_exists(root, approval):
        raise CgspecError(f"approval {approval} is not in 07-state/approvals.json; a layer is locked by the user")
    bundler = Bundler(root)
    html = bundler.html(source)
    if bundler.problems:
        raise CgspecError("snapshot not cut:\n- " + "\n- ".join(dict.fromkeys(bundler.problems)))
    version = next_version(root, screen)
    stamp = (f"<!-- CGSpec snapshot {screen} v{version}: layer {layer} locked, source {_revision(root)}, "
             f"cut {utc_now()}. Frozen; never edit, cut a new version instead. -->\n")
    doctype = re.match(r"\s*<!doctype[^>]*>\s*", html, re.I)
    html = html[:doctype.end()] + stamp + html[doctype.end():] if doctype else stamp + html
    dest = root / SNAPSHOTS / f"{screen}-v{version}.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "x", encoding="utf-8", newline="\n") as handle:
        handle.write(html)
    os.chmod(dest, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    frozen_path = root / STATE_DIR / "frozen.json"
    try:
        frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        frozen = {"schema": 1, "entries": []}
    rel = dest.relative_to(root).as_posix()
    frozen.setdefault("entries", []).append({
        "path": rel, "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(), "kind": "snapshot", "added": utc_now(),
        "reason": f"layer {layer} locked for {screen}" + (f": {reason}" if reason else "")})
    write_json(frozen_path, frozen)
    import memlog
    memlog.main(["--root", str(root), "add", "--summary", f"Snapshot {screen} v{version} cut (layer {layer} locked)",
                 "--tags", "prototype,snapshot", "--details", f"{rel}; approval {approval}"])
    return dest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("screen", help="folder name under docs/prototypes/")
    parser.add_argument("--layer", type=int, required=True, help="the grey layer just locked (0-4)")
    parser.add_argument("--approval", required=True, help="approval id from the user's message locking the layer")
    parser.add_argument("--entry", default="index.html")
    parser.add_argument("--reason", default="")
    parser.add_argument("--root")
    args = parser.parse_args(argv)
    try:
        dest = cut(resolve_root(args.root), args.screen, args.layer, args.approval, args.entry, args.reason)
    except CgspecError as exc:
        print(f"bundle_prototype: {exc}", file=sys.stderr)
        return EXIT_FAIL
    except Exception as exc:  # report, never crash silently
        print(f"bundle_prototype: internal error: {exc}", file=sys.stderr)
        return EXIT_INTERNAL
    print(f"cut {dest.name} (read-only, recorded in frozen.json and the ledger)")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
