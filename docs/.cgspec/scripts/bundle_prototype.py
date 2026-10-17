#!/usr/bin/env python3
"""
CGSpec Zero-Token Prototype Bundler (bundle_prototype.py)

Compiles modular per-screen HTML/CSS/JS partials maintained by parallel
cgspec-builder subagents (<400 lines each) into a single, self-contained HTML
artifact for the Antigravity preview pane and docs/.cgspec/prototypes/ archive
in <50ms using ZERO LLM output tokens.

Supported Directives inside shell.html (or any template HTML):
  <!-- @include path/to/partial.html -->
  /* @include path/to/tokens.css */
  // @include path/to/data.js
"""

import argparse
import pathlib
import re
import shutil
import sys

INCLUDE_PATTERNS = [
    re.compile(r"<!--\s*@include\s+([^\s]+)\s*-->"),
    re.compile(r"/\*\s*@include\s+([^\s]+)\s*\*/"),
    re.compile(r"//\s*@include\s+([^\s]+)"),
]


def resolve_includes(text: str, base_dir: pathlib.Path, depth: int = 0) -> str:
    if depth > 10:
        raise RuntimeError("Maximum @include recursion depth (10) exceeded.")

    def replacer(match: re.Match) -> str:
        rel_path = match.group(1).strip()
        part_path = (base_dir / rel_path).resolve()
        if not part_path.exists():
            raise FileNotFoundError(f"Missing @include partial: {part_path} (referenced from {base_dir})")
        part_content = part_path.read_text(encoding="utf-8")
        return resolve_includes(part_content, part_path.parent, depth + 1)

    out = text
    for pat in INCLUDE_PATTERNS:
        out = pat.sub(replacer, out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="CGSpec Zero-Token Modular HTML Prototype Bundler")
    ap.add_argument("--shell", required=True, help="Path to the shell.html entry file containing @include directives")
    ap.add_argument("--out", required=True, help="Output path for the compiled self-contained HTML file")
    ap.add_argument("--mirror", default=None, help="Optional second output path (e.g., docs/.cgspec/prototypes/wireframe-vN.html)")
    args = ap.parse_args()

    shell_path = pathlib.Path(args.shell).resolve()
    if not shell_path.exists():
        print(f"[FAIL] Shell template not found: {shell_path}", file=sys.stderr)
        return 1

    try:
        raw_shell = shell_path.read_text(encoding="utf-8")
        bundled = resolve_includes(raw_shell, shell_path.parent)
    except Exception as exc:
        print(f"[FAIL] Bundle compilation error: {exc}", file=sys.stderr)
        return 1

    out_path = pathlib.Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(bundled, encoding="utf-8")
    line_count = len(bundled.splitlines())
    byte_count = len(bundled.encode("utf-8"))
    print(f"[PASS] Bundled {out_path} ({line_count} lines, {byte_count} bytes) in 0 LLM tokens.")

    if args.mirror:
        mirror_path = pathlib.Path(args.mirror).resolve()
        mirror_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(out_path, mirror_path)
        print(f"[PASS] Mirrored to {mirror_path}")

    # Auto-register Antigravity artifact metadata if output path is inside a brain directory
    if "/brain/" in str(out_path):
        import json, datetime
        meta_file = out_path.with_name(f"{out_path.name}.metadata.json")
        if not meta_file.exists():
            meta_data = {
                "summary": f"CGSpec Compiled Prototype: {out_path.stem}",
                "updatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "userFacing": True,
            }
            meta_file.write_text(json.dumps(meta_data, indent=2), encoding="utf-8")
            print(f"[PASS] Auto-registered artifact metadata: {meta_file.name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
