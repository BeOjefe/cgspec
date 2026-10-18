#!/usr/bin/env python3
"""install.py: install, upgrade, verify or uninstall CGSpec in a project.

  install    copy the template and a vendored engine; write the version marker
  upgrade    refresh the vendored engine from this plugin; never touches project records
  verify     compare the vendored engine with its hash manifest
  uninstall  remove what install created, keep anything the user changed

No symlinks are ever created; the engine is copied so a project never breaks when the
plugin moves. Running install twice changes nothing.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib.common import (  # noqa: E402
    ENGINE_DIR, EXIT_FAIL, EXIT_OK, PROJECT_FILE, CgspecError, read_json, sha256_file, utc_now, write_json,
)
from _lib.layout import GUI_PROFILES  # noqa: E402

HERE = Path(__file__).resolve().parent
OWNED = ENGINE_DIR / "owned-files.json"
MANIFEST = ENGINE_DIR / "manifest.json"
ARCHIVE = Path("docs/_cgspec/_archive/pre-cgspec")
REPLACEABLE = {"AGENTS.md", "CLAUDE.md"}
GITIGNORE_LINES = [".cgspec-scratch/"]
SKIP_NAMES = {"__pycache__", ".pytest_cache", "owned-files.json", "manifest.json"}

PATH_CLASSES = {
    "schema": ["**/migrations/**", "**/schema.prisma", "**/*.sql", "**/schema.graphql"],
    "api": ["**/api/**", "**/openapi.yaml", "**/openapi.yml", "**/openapi.json", "**/*.proto"],
    "auth": ["**/auth/**", "**/*auth*.*"],
    "deps": ["**/package.json", "**/package-lock.json", "**/pnpm-lock.yaml", "**/yarn.lock",
             "**/pyproject.toml", "**/requirements*.txt", "**/poetry.lock", "**/uv.lock",
             "**/go.mod", "**/go.sum", "**/Cargo.toml", "**/Cargo.lock", "**/Gemfile*"],
    "code": ["src/**", "app/**", "lib/**", "packages/*/src/**", "apps/*/src/**", "services/*/src/**"],
    "tests": ["tests/**", "test/**", "**/*.test.*", "**/*.spec.*", "**/test_*.py", "**/*_test.go", "e2e/**"],
    "docs": ["docs/**", "*.md"],
}


def plugin_root() -> Path:
    root = HERE.parent
    if not (root / "templates").is_dir():
        raise CgspecError("templates not found: run install/upgrade from the CGSpec plugin, not a vendored copy")
    return root


def version() -> str:
    return (HERE / "VERSION").read_text(encoding="utf-8").strip()


def engine_files() -> list[Path]:
    files = []
    for path in sorted(HERE.rglob("*")):
        if any(part in SKIP_NAMES for part in path.relative_to(HERE).parts):
            continue
        if path.is_symlink():
            raise CgspecError(f"symlink in engine source is not allowed: {path}")
        if path.is_file() and path.suffix != ".pyc":
            files.append(path)
    return files


def copy_engine(root: Path) -> dict[str, str]:
    target = root / ENGINE_DIR
    hashes = {}
    for src in engine_files():
        rel = src.relative_to(HERE).as_posix()
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        if src.suffix == ".py" and src.parent == HERE:
            os.chmod(dst, 0o755)
        hashes[rel] = sha256_file(dst)
    stale = {p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()} - set(hashes) - {"manifest.json", "owned-files.json"}
    for rel in stale:
        (target / rel).unlink()
    write_json(root / MANIFEST, {"schema": 1, "cgspec_version": version(), "files": hashes})
    return hashes


def template_dirs(profile: str, topology: str) -> list[Path]:
    base = plugin_root() / "templates"
    dirs = [base / "base"]
    if profile in GUI_PROFILES:
        dirs.append(base / "gui")
    if (base / topology).is_dir():
        dirs.append(base / topology)
    return dirs


def cmd_install(root: Path, args: argparse.Namespace) -> int:
    if (root / "docs/_cgspec/01-script").exists() and not (root / PROJECT_FILE).exists():
        raise CgspecError("CGSpec v1 layout found (docs/_cgspec/01-script); use the cgspec-adopt upgrade mode")
    if (root / PROJECT_FILE).exists():
        current = read_json(root / PROJECT_FILE).get("cgspec_version")
        if current == version():
            print(f"already installed (CGSpec {current}); nothing changed")
            return EXIT_OK
        raise CgspecError(f"CGSpec {current} is installed; run 'install.py upgrade' to move to {version()}")
    if args.topology.startswith("polyrepo") and not args.repo_prefix:
        raise CgspecError("polyrepo topologies need --repo-prefix")

    owned = {"schema": 1, "cgspec_version": version(), "installed_at": utc_now(),
             "created": {}, "dirs": [], "replaced": {}, "gitignore_added": []}

    for tdir in template_dirs(args.profile, args.topology):
        for src in sorted(tdir.rglob("*")):
            rel = src.relative_to(tdir).as_posix()
            dst = root / rel
            if src.is_dir():
                if not dst.exists():
                    dst.mkdir(parents=True)
                    owned["dirs"].append(rel)
                continue
            if dst.exists():
                if rel not in REPLACEABLE:
                    continue  # never overwrite project files
                archive = root / ARCHIVE / rel
                archive.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dst, archive)
                owned["replaced"][rel] = (ARCHIVE / rel).as_posix()
            else:
                for parent in reversed(dst.relative_to(root).parents[:-1]):
                    if not (root / parent).exists():
                        (root / parent).mkdir()
                        owned["dirs"].append(parent.as_posix())
            shutil.copyfile(src, dst)
            owned["created"][rel] = sha256_file(dst)

    engine_existed = (root / ENGINE_DIR).exists()
    copy_engine(root)
    if not engine_existed:
        owned["dirs"].append(ENGINE_DIR.as_posix())

    project = {"schema": 1, "cgspec_version": version(), "profile": args.profile, "topology": args.topology,
               "path_classes": PATH_CLASSES, "tools": sorted(set(args.tools.split(",")) - {""})}
    if args.repo_prefix:
        project["repo_prefix"] = args.repo_prefix
    write_json(root / PROJECT_FILE, project)
    owned["created"][PROJECT_FILE.as_posix()] = sha256_file(root / PROJECT_FILE)

    gitignore = root / ".gitignore"
    lines = gitignore.read_text(encoding="utf-8").splitlines() if gitignore.exists() else []
    added = [line for line in GITIGNORE_LINES if line not in lines]
    if added:
        text = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
        if text and not text.endswith("\n"):
            text += "\n"
        gitignore.write_text(text + "\n".join(added) + "\n", encoding="utf-8")
        owned["gitignore_added"] = added
        if not lines:
            owned["created"][".gitignore"] = sha256_file(gitignore)

    write_json(root / OWNED, owned)
    print(f"installed CGSpec {version()} ({args.profile}, {args.topology}) in {root}")
    return EXIT_OK


def verify_engine(root: Path) -> list[str]:
    manifest = read_json(root / MANIFEST)
    target = root / ENGINE_DIR
    problems = []
    for rel, digest in manifest.get("files", {}).items():
        path = target / rel
        if not path.is_file():
            problems.append(f"missing engine file: {rel}")
        elif path.is_symlink():
            problems.append(f"engine file is a symlink: {rel}")
        elif sha256_file(path) != digest:
            problems.append(f"engine file changed: {rel}")
    listed = set(manifest.get("files", {})) | {"manifest.json", "owned-files.json"}
    for path in target.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts and path.relative_to(target).as_posix() not in listed:
            problems.append(f"unexpected engine file: {path.relative_to(target).as_posix()}")
    return problems


def cmd_verify(root: Path, _args: argparse.Namespace) -> int:
    problems = verify_engine(root)
    for problem in problems:
        print(problem)
    print("engine OK" if not problems else f"{len(problems)} engine problems")
    return EXIT_FAIL if problems else EXIT_OK


def cmd_upgrade(root: Path, _args: argparse.Namespace) -> int:
    if not (root / PROJECT_FILE).exists():
        raise CgspecError("CGSpec is not installed here; run 'install.py install'")
    plugin_root()
    project = read_json(root / PROJECT_FILE)
    copy_engine(root)
    owned_path = root / OWNED
    if owned_path.exists():
        owned = read_json(owned_path)
        owned["cgspec_version"] = version()
        write_json(owned_path, owned)
    old = project.get("cgspec_version")
    project["cgspec_version"] = version()  # the version marker is updated last (spec 5)
    write_json(root / PROJECT_FILE, project)
    print(f"engine refreshed; CGSpec {old} -> {version()}")
    return EXIT_OK


def cmd_uninstall(root: Path, _args: argparse.Namespace) -> int:
    owned = read_json(root / OWNED)
    kept = []
    for rel, digest in owned.get("created", {}).items():
        path = root / rel
        if rel in owned.get("replaced", {}) or not path.exists():
            continue
        if rel == PROJECT_FILE.as_posix() or sha256_file(path) == digest:
            path.unlink()
        else:
            kept.append(rel)
    for rel, archive in owned.get("replaced", {}).items():
        shutil.copy2(root / archive, root / rel)
    gitignore = root / ".gitignore"
    if gitignore.exists() and owned.get("gitignore_added"):
        remaining = [l for l in gitignore.read_text(encoding="utf-8").splitlines() if l not in owned["gitignore_added"]]
        if remaining:
            gitignore.write_text("\n".join(remaining) + "\n", encoding="utf-8")
        else:
            gitignore.unlink()
    shutil.rmtree(root / ENGINE_DIR, ignore_errors=True)
    if owned.get("replaced"):
        shutil.rmtree(root / ARCHIVE, ignore_errors=True)
    for rel in sorted(set(owned.get("dirs", [])) | {ARCHIVE.parent.as_posix()}, key=lambda d: d.count("/"), reverse=True):
        path = root / rel
        for keep in list(path.rglob(".gitkeep")) if path.is_dir() else []:
            if not any(p for p in keep.parent.iterdir() if p.name != ".gitkeep"):
                keep.unlink()
        try:
            path.rmdir()
        except OSError:
            pass
    for rel in kept:
        print(f"kept (changed since install): {rel}")
    print(f"uninstalled CGSpec; kept {len(kept)} changed files")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="install.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("install", "upgrade", "verify", "uninstall"):
        p = sub.add_parser(name)
        p.add_argument("--root", required=True)
        if name == "install":
            p.add_argument("--profile", required=True,
                           choices=["website", "web-workspace", "mobile", "cli", "headless", "small"])
            p.add_argument("--topology", required=True,
                           choices=["single", "monorepo", "large-monorepo", "polyrepo-governance", "polyrepo-member"])
            p.add_argument("--tools", default="git", help="comma-separated: claude,antigravity,codex,cursor,git,ci")
            p.add_argument("--repo-prefix", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handlers = {"install": cmd_install, "upgrade": cmd_upgrade, "verify": cmd_verify, "uninstall": cmd_uninstall}
    try:
        root = Path(args.root).resolve()
        if not root.is_dir():
            raise CgspecError(f"not a directory: {root}")
        return handlers[args.command](root, args)
    except CgspecError as exc:
        print(f"install: {exc}", file=sys.stderr)
        return EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
