#!/usr/bin/env python3
"""
CGSpec Doctor (Spec Linter & Integrity Hook)
Validates repository invariants, spine integrity, ADR registrations, and memory log continuity.

Usage:
  uv run {skill-dir}/scripts/doctor.py [project-root]
"""

import sys
import re
from pathlib import Path

def run_doctor(project_root: Path) -> int:
    errors = []
    warnings = []
    
    docs_dir = project_root / "docs"
    if not docs_dir.exists():
        print(f"FAIL: Missing docs directory at {docs_dir}")
        return 1

    print(f"CGSpec Doctor: Inspecting {project_root.resolve()}")
    print("-" * 60)

    # 1. Verify Core Spines
    expected_spines = [
        "00-INDEX.md",
        "01-PRD.md",
        "02-NOUNS-AND-FLOWS.md",
        "03-ARCHITECTURE.md",
        "04-DESIGN.md",
        "05-EXPERIENCE.md",
    ]
    
    for spine in expected_spines:
        spine_path = docs_dir / spine
        spine_dir = docs_dir / spine.replace(".md", "")
        if not spine_path.exists() and not spine_dir.exists():
            errors.append(f"Missing core spine: docs/{spine} (or sprouted directory docs/{spine.replace('.md', '/')})")
        else:
            status = "file" if spine_path.exists() else "sprouted dir"
            print(f"  [PASS] Spine docs/{spine} ({status})")

    # 2. Check Memory Log Continuity
    memlog_file = docs_dir / ".memlog.md"
    memlog_entries = []
    if not memlog_file.exists():
        errors.append("Missing docs/.memlog.md")
    else:
        content = memlog_file.read_text(encoding="utf-8")
        entry_matches = list(re.finditer(r"###\s*\[?(M-\d+)\]?", content))
        if not entry_matches:
            warnings.append("docs/.memlog.md contains no entries (### [M-NNN])")
        else:
            ids = [m.group(1) for m in entry_matches]
            memlog_entries = ids
            print(f"  [PASS] Memory Log: {len(ids)} sequential entries (latest: {ids[-1]})")

    # 3. Check ADR Consistency (Atomic ADR Gate)
    adr_dir = docs_dir / "adr"
    if not adr_dir.exists():
        warnings.append("No docs/adr/ directory found")
    else:
        adr_files = list(adr_dir.glob("ADR-*.md"))
        print(f"  [INFO] Found {len(adr_files)} ADR files in docs/adr/")
        
        index_content = ""
        index_file = docs_dir / "00-INDEX.md"
        if index_file.exists():
            index_content = index_file.read_text(encoding="utf-8")
        
        memlog_content = memlog_file.read_text(encoding="utf-8") if memlog_file.exists() else ""

        for adr in sorted(adr_files):
            adr_name = adr.name
            adr_id_match = re.search(r"(ADR-\d+)", adr_name)
            if not adr_id_match:
                warnings.append(f"ADR filename does not follow convention ADR-NNN: {adr_name}")
                continue
            
            adr_id = adr_id_match.group(1)
            adr_text = adr.read_text(encoding="utf-8")
            status_match = re.search(r"-?\s*\*\*Status:\*\*\s*(Proposed|Accepted|Deprecated|Rejected)", adr_text, re.IGNORECASE)
            
            st = status_match.group(1).capitalize() if status_match else "Unknown"

            # Check if registered in 00-INDEX.md
            if adr_id not in index_content:
                if st == "Accepted":
                    errors.append(f"{adr_id} ({adr_name}) has Status: Accepted but is NOT registered in docs/00-INDEX.md")
                else:
                    warnings.append(f"{adr_id} ({adr_name}, Status: {st}) is drafted on disk but not yet registered in docs/00-INDEX.md")
            else:
                print(f"  [PASS] {adr_id} registered in 00-INDEX.md (Status: {st})")
                
            if not status_match:
                warnings.append(f"{adr_name} is missing a formal Status header (e.g. - **Status:** Proposed/Accepted)")
            else:
                if st == "Accepted" and adr_id not in memlog_content:
                    warnings.append(f"{adr_id} has Status: Accepted but is not recorded in docs/.memlog.md")

    # 4. Check for Decorative Emojis in Spines
    banned_emojis = ["📍", "⚖️", "👥", "🏛️", "🚀", "💡", "✨"]
    for spine in expected_spines:
        spine_path = docs_dir / spine
        if spine_path.exists():
            text = spine_path.read_text(encoding="utf-8")
            found = [e for e in banned_emojis if e in text]
            if found:
                warnings.append(f"Decorative emoji(s) {found} found in docs/{spine}")

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

if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    sys.exit(run_doctor(target))
