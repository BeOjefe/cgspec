#!/usr/bin/env python3
"""
CGSpec Doctor (Spec Linter & Integrity Hook)
Validates repository invariants, spine integrity, ADR registrations, and memory log continuity.

Canonical 3-Zone Architecture (Model 1 Spines + Visible First-Class Records):
  <root>/docs/                     -> Specification Hub (00-INDEX.md, README.md, _memlog.md)
  <root>/docs/spines/              -> Living Core Spines (01-INTENT .. 05-DELIVERY)
  <root>/docs/adr/                 -> Permanent Architecture Decision Records (ADR-NNN-...)
  <root>/docs/slices/              -> Bounded Vertical Slice Delivery Contracts (SLICE-NNN-...)
  <root>/docs/prototypes/          -> Zero-Build Interactive HTML Wireframes
  <root>/docs/_cgspec/             -> Numbered Engine Space (Strictly Singular + _archive):
    01-script/                     -> Tooling (doctor.py, visual_audit.py, ingest.py, memlog.py)
    02-research/                   -> Technical Spikes & Benchmarks (RES-NNN-...)
    03-council/                    -> Multi-Agent Debate Logs & Deliberations
    _archive/                      -> Superseded Spines, Drafts & Stashed Provenance

Usage:
  python3 docs/_cgspec/01-script/doctor.py [project-root]
  python3 docs/_cgspec/01-script/doctor.py --repo [project-root]
"""

import sys
import re
import argparse
from pathlib import Path

# Comprehensive regex matching Unicode emojis, symbols, and status icons
EMOJI_PATTERN = re.compile(
    r"[\U00010000-\U0010ffff]|"  # SMP plane (emojis, pictographs)
    r"[\u2600-\u27bf]|"          # Misc symbols, dingbats
    r"[\u2300-\u23ff]|"          # Misc technical
    r"[\u2b50-\u2b55]|"          # Stars and circles
    r"[\u2190-\u21ff]"           # Arrows
)

CANONICAL_ENGINE_DIRS = [
    "01-script",
    "02-research",
    "03-council",
    "04-adr",
    "05-prototype",
    "06-slice",
    "_archive",
    ".archive",
]

def run_doctor(project_root: Path, strict_emojis: bool = False) -> int:
    errors = []
    warnings = []
    
    docs_dir = project_root / "docs"
    if not docs_dir.exists():
        print(f"FAIL: Missing docs directory at {docs_dir}")
        return 1

    print(f"CGSpec Doctor: Inspecting {project_root.resolve()}")
    print("-" * 60)

    # 1. Structural Invariant: Eradicate Legacy .working and Verify docs/_cgspec Engine
    legacy_working = docs_dir / ".working"
    if legacy_working.exists():
        errors.append(
            "Forbidden legacy directory 'docs/.working/' detected! "
            "CGSpec Invariant: All engine state must live in 'docs/_cgspec/03-council/' and 'docs/prototypes/'."
        )

    root_cgspec = project_root / "_cgspec"
    if not root_cgspec.exists():
        root_cgspec = project_root / ".cgspec"
    if root_cgspec.exists() and not root_cgspec.is_symlink():
        if (docs_dir / "_cgspec").exists() and root_cgspec != (docs_dir / "_cgspec"):
            warnings.append(
                "Duplicate root engine directory detected. The canonical engine directory is 'docs/_cgspec/'. "
                "Remove root engine folder once migration is complete."
            )

    cgspec_dir = docs_dir / "_cgspec"
    if not cgspec_dir.exists():
        cgspec_dir = docs_dir / ".cgspec"

    if cgspec_dir.exists():
        print(f"  [PASS] Engine Location: docs/{cgspec_dir.name}/ (inside docs/)")
        # Check singular naming consistency inside engine directory
        for sub in cgspec_dir.iterdir():
            if sub.is_dir() and not sub.name.startswith("."):
                name = sub.name
                if name.endswith("s") and not name.endswith("ss") and name != "scripts":
                    warnings.append(
                        f"Plural naming detected in 'docs/{cgspec_dir.name}/{name}'. "
                        "CGSpec Invariant: Engine directories must use strictly singular nouns "
                        "('01-script', '02-research', '03-council', '_archive')."
                    )

    # 2. Verify Core Spines (Supports Model 1 docs/spines/ and legacy docs/ flat)
    spines_dir = docs_dir / "spines"
    is_reformed = (
        (spines_dir / "01-INTENT.md").exists()
        or (docs_dir / "01-INTENT.md").exists()
        or (spines_dir / "01-INTENT").is_dir()
        or (docs_dir / "01-INTENT").is_dir()
    )

    if is_reformed:
        version_label = "Reformed CGSpec v0.2 (Law 3 Pure)"
        expected_spines = [
            "00-INDEX.md",
            "01-INTENT.md",
            "02-OOUX.md",
            "03-EXPERIENCE.md",
            "04-ARCHITECTURE.md",
            "05-DELIVERY.md",
        ]
    else:
        version_label = "Legacy CGSpec v0.1"
        expected_spines = [
            "00-INDEX.md",
            "01-PRD.md",
            "02-NOUNS-AND-FLOWS.md",
            "03-ARCHITECTURE.md",
            "04-DESIGN.md",
            "05-EXPERIENCE.md",
        ]

    print(f"  [SPEC] Active Standard: {version_label}")
    resolved_spine_paths = []

    for spine in expected_spines:
        if spine == "00-INDEX.md":
            spine_path = docs_dir / spine
            spine_dir = docs_dir / "00-INDEX"
        else:
            spine_stem = spine.replace(".md", "")
            spine_path = (spines_dir / spine) if (spines_dir / spine).exists() else (docs_dir / spine)
            spine_dir = (spines_dir / spine_stem) if (spines_dir / spine_stem).is_dir() else (docs_dir / spine_stem)

        if not spine_path.exists() and not spine_dir.is_dir():
            errors.append(f"Missing core spine: docs/{spine} (or in docs/spines/{spine} / sprouted directory)")
        else:
            resolved_spine_paths.append(spine_path if spine_path.exists() else spine_dir)
            status = "file" if spine_path.exists() else "sprouted dir"
            loc = spine_path.relative_to(project_root) if spine_path.exists() else spine_dir.relative_to(project_root)
            print(f"  [PASS] Spine {loc} ({status})")

    # 3. Check 00-INDEX.md Registration Completeness
    index_file = docs_dir / "00-INDEX.md"
    index_content = ""
    if index_file.exists():
        index_content = index_file.read_text(encoding="utf-8")
        for spine in expected_spines:
            spine_stem = spine.replace(".md", "")
            if spine != "00-INDEX.md" and spine not in index_content and spine_stem not in index_content:
                errors.append(f"docs/00-INDEX.md does not tabulate core spine: {spine} (or {spine_stem}/)")

    # 4. Check Memory Log Continuity & Parity (supports _memlog.md, MEMLOG.md, or legacy .memlog.md)
    memlog_file = docs_dir / "_memlog.md"
    if not memlog_file.exists():
        memlog_file = docs_dir / "MEMLOG.md"
    if not memlog_file.exists():
        memlog_file = docs_dir / ".memlog.md"
    if not memlog_file.exists() and (cgspec_dir / "memlog.md").exists():
        memlog_file = cgspec_dir / "memlog.md"

    memlog_entries = []
    if not memlog_file.exists():
        errors.append("Missing memory log (expected 'docs/_memlog.md' or 'docs/MEMLOG.md')")
    else:
        content = memlog_file.read_text(encoding="utf-8")
        entry_matches = list(re.finditer(r"###\s*\[?(M-\d+)\]?", content))
        if not entry_matches:
            warnings.append(f"{memlog_file.name} contains no entries (### [M-NNN])")
        else:
            ids = [m.group(1) for m in entry_matches]
            memlog_entries = ids
            print(f"  [PASS] Memory Log: {len(ids)} sequential entries in {memlog_file.relative_to(project_root)} (latest: {ids[-1]})")

            # Auto-synchronize 00-INDEX.md memlog counter from canonical memlog
            if index_content:
                count_match = re.search(r"(\d+)\s+entries\s*\((?:Latest:\s*)?(M-\d+)\)", index_content)
                if count_match:
                    claimed_count = int(count_match.group(1))
                    claimed_latest = count_match.group(2)
                    if claimed_count != len(ids) or claimed_latest != ids[-1]:
                        old_span = count_match.group(0)
                        prefix = "Latest: " if "Latest:" in old_span else ""
                        new_span = f"{len(ids)} entries ({prefix}{ids[-1]})"
                        index_content = index_content.replace(old_span, new_span, 1)
                        (docs_dir / "00-INDEX.md").write_text(index_content, encoding="utf-8")
                        print(f"  [SYNC] Auto-updated docs/00-INDEX.md memlog counter -> {new_span}")

    # 5. Check ADR Consistency & Bidirectional Parity (supports docs/adr/ or docs/_cgspec/04-adr/)
    adr_dir = docs_dir / "adr"
    if not adr_dir.exists():
        adr_dir = cgspec_dir / "04-adr"
    
    if not adr_dir.exists():
        warnings.append("No ADR directory found (expected 'docs/adr/' or 'docs/_cgspec/04-adr/')")
    else:
        adr_files = list(adr_dir.glob("ADR-*.md"))
        print(f"  [INFO] Found {len(adr_files)} ADR files in {adr_dir.relative_to(project_root)}")
        memlog_content = memlog_file.read_text(encoding="utf-8") if memlog_file.exists() else ""

        for adr in sorted(adr_files):
            adr_name = adr.name
            adr_id_match = re.search(r"(ADR-\d+)", adr_name)
            if not adr_id_match:
                warnings.append(f"ADR filename does not follow convention ADR-NNN: {adr_name}")
                continue
            
            adr_id = adr_id_match.group(1)
            adr_text = adr.read_text(encoding="utf-8")
            status_match = re.search(r"-?\s*\*\*Status:\*\*\s*[`\[]*([A-Za-z]+)", adr_text, re.IGNORECASE)
            
            st_disk = status_match.group(1).capitalize() if status_match else "Unknown"

            if not status_match:
                warnings.append(f"{adr_name} is missing a formal Status header (e.g. - **Status:** Proposed/Accepted)")

            # Check if registered in 00-INDEX.md
            if adr_id not in index_content:
                if st_disk == "Accepted":
                    errors.append(f"{adr_id} ({adr_name}) has Status: Accepted on disk but is NOT registered in docs/00-INDEX.md")
                else:
                    warnings.append(f"{adr_id} ({adr_name}, Status: {st_disk}) is drafted on disk but not yet registered in docs/00-INDEX.md")
            else:
                for line in index_content.splitlines():
                    if adr_id in line:
                        if "Accepted" in line and st_disk != "Accepted":
                            errors.append(
                                f"{adr_id} Status Desync: docs/00-INDEX.md marks it as Accepted, but {adr_name} on disk has Status: {st_disk}"
                            )
                        elif "Proposed" in line and st_disk == "Accepted":
                            warnings.append(
                                f"{adr_id} Status Desync: {adr_name} on disk has Status: Accepted, but docs/00-INDEX.md marks it as Proposed"
                            )
                        break

                print(f"  [PASS] {adr_id} registered in 00-INDEX.md (Status: {st_disk})")
                
            if st_disk == "Accepted" and adr_id not in memlog_content:
                warnings.append(f"{adr_id} has Status: Accepted on disk but is not recorded in {memlog_file.name}")

    # 6. Check Bounded Vertical Slices (supports docs/slices/ or docs/_cgspec/06-slice/)
    slice_dir = docs_dir / "slices"
    if not slice_dir.exists():
        slice_dir = cgspec_dir / "06-slice"
    if slice_dir.exists():
        slice_files = [f for f in slice_dir.glob("SLICE-*.md") if f.name != "README.md"]
        if slice_files:
            print(f"  [INFO] Found {len(slice_files)} Slice Contract(s) in {slice_dir.relative_to(project_root)}")

    # 7. Check Research Spikes & Technical Investigations (supports docs/research/ or docs/_cgspec/02-research/)
    research_dir = docs_dir / "research"
    if not research_dir.exists():
        research_dir = cgspec_dir / "02-research"

    if research_dir.exists():
        res_files = [f for f in research_dir.glob("RES-*.md") if f.name != "README.md"]
        if res_files:
            print(f"  [INFO] Found {len(res_files)} Research Spike(s) in {research_dir.relative_to(project_root)}")
            for res in sorted(res_files):
                res_match = re.search(r"(RES-\d+)", res.name)
                if res_match:
                    res_id = res_match.group(1)
                    if res_id not in index_content:
                        warnings.append(f"{res_id} ({res.name}) is in research registry but not registered in docs/00-INDEX.md")
                    else:
                        print(f"  [PASS] {res_id} registered in 00-INDEX.md")

    # 8. Check for Emojis in Spines
    for spine_item in resolved_spine_paths:
        if spine_item.is_file():
            text = spine_item.read_text(encoding="utf-8")
            matches = list(EMOJI_PATTERN.finditer(text))
            if matches:
                sample = list({m.group(0) for m in matches[:5]})
                msg = f"Emoji violation(s) {sample} found in {spine_item.relative_to(project_root)} ({len(matches)} total)"
                if strict_emojis:
                    errors.append(msg)
                else:
                    warnings.append(msg)

    # 9. Check AGENTS.md Constitution Parity (11 Laws + Closed-Loop Visual Self-Critique)
    agents_file = project_root / "AGENTS.md"
    if not agents_file.exists():
        warnings.append("Missing AGENTS.md at project root")
    else:
        agents_text = agents_file.read_text(encoding="utf-8")
        if "Law 11" not in agents_text:
            warnings.append("AGENTS.md is outdated (missing Law 11: Disk-First Immediate Capture & 4-Bucket Triage)")
        else:
            print("  [PASS] AGENTS.md Constitution Parity (11 Core Coach Laws active)")

    # 10. Check Prototype Architecture & File Size
    prototype_dir = docs_dir / "prototypes"
    if not prototype_dir.exists():
        prototype_dir = cgspec_dir / "05-prototype"
    if prototype_dir.exists():
        html_files = [f for f in prototype_dir.glob("*.html") if not f.is_symlink()]
        for hf in html_files:
            try:
                line_count = len(hf.read_text(encoding="utf-8", errors="ignore").splitlines())
                size_kb = hf.stat().st_size / 1024
                if line_count > 1500 or size_kb > 150:
                    warnings.append(
                        f"Prototype bloat warning: {hf.relative_to(project_root)} is large "
                        f"({line_count} lines, {size_kb:.1f} KB). "
                        "Recommend decomposing into modular partials with bundle_prototype.py to prevent token truncation."
                    )
            except Exception:
                pass

    # 11. Check Rogue Ad-Hoc Scripts in Workspace
    rogue_patterns = [r"^apply_.*\.py$", r"^patch_.*\.py$", r"^fix_.*\.py$", r"^overhaul_.*\.py$"]
    search_dirs = [project_root, project_root / "scratch"]
    for sdir in search_dirs:
        if sdir.exists() and sdir.is_dir():
            for f in sdir.iterdir():
                if f.is_file() and any(re.match(pat, f.name) for pat in rogue_patterns):
                    warnings.append(
                        f"Rogue modification script detected: '{f.relative_to(project_root)}'. "
                        "CGSpec Invariant: Ad-hoc regex string-patch scripts are forbidden. "
                        "Use canonical tooling in docs/_cgspec/01-script/ or modular partials."
                    )

    # Print Summary
    print("-" * 60)
    if warnings:
        print(f"WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  - {w}")

    if errors:
        print(f"\nFAIL: {len(errors)} specification integrity errors detected:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("\nSUCCESS: All CGSpec invariants and spine integrity checks PASSED.")
    return 0

def main():
    parser = argparse.ArgumentParser(description="CGSpec Doctor (Spec Linter & Integrity Hook)")
    parser.add_argument("repo_path", nargs="?", default=None, help="Path to project root (default: current directory)")
    parser.add_argument("--repo", dest="repo_flag", default=None, help="Explicit path to project root")
    parser.add_argument("--strict-emojis", action="store_true", help="Treat emoji violations as hard errors")
    
    args = parser.parse_args()
    target_str = args.repo_flag or args.repo_path or "."
    target = Path(target_str).resolve()
    
    sys.exit(run_doctor(target, strict_emojis=args.strict_emojis))

if __name__ == "__main__":
    main()
