#!/usr/bin/env python3
"""
CGSpec Ingestion Engine (Brownfield Codebase Ingest)
Reverse-engineers existing codebases, extracts domain models, generates
brownfield manifests, and establishes baseline architectural decisions.

Usage:
  python3 scripts/ingest.py [project-root]
"""

import os
import sys
import json
import re
from pathlib import Path

def ingest_codebase(target_dir: Path):
    print(f"CGSpec Ingest: Analyzing codebase at {target_dir.resolve()}")
    print("-" * 60)

    working_dir = target_dir / "docs" / ".working"
    working_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = working_dir / "brownfield-manifest.json"

    findings = {
        "project_root": str(target_dir.resolve()),
        "languages": {},
        "frameworks": [],
        "models": [],
        "endpoints": [],
        "database_migrations": [],
    }

    # Detect package managers & project types
    if (target_dir / "package.json").exists():
        findings["frameworks"].append("Node.js / TypeScript / JavaScript")
    if (target_dir / "pyproject.toml").exists() or (target_dir / "requirements.txt").exists():
        findings["frameworks"].append("Python")
    if (target_dir / "Cargo.toml").exists():
        findings["frameworks"].append("Rust")
    if (target_dir / "go.mod").exists():
        findings["frameworks"].append("Go")

    # Scan for database migrations and schema definitions
    migration_patterns = ["migrations", "db/migrations", "prisma", "drizzle", "alembic"]
    for pattern in migration_patterns:
        mig_dir = target_dir / pattern
        if mig_dir.exists() and mig_dir.is_dir():
            for f in mig_dir.glob("**/*"):
                if f.is_file() and not f.name.startswith("."):
                    findings["database_migrations"].append(str(f.relative_to(target_dir)))

    # Scan for routes and endpoints
    route_indicators = ["router", "controller", "route", "api", "endpoint"]
    for root, dirs, files in os.walk(target_dir):
        # Exclude node_modules, .git, venv, target, dist
        dirs[:] = [d for d in dirs if d not in [".git", "node_modules", ".venv", "venv", "target", "dist", ".gemini", "archive"]]
        for f in files:
            lower = f.lower()
            if any(ind in lower for ind in route_indicators):
                rel_path = Path(root, f).relative_to(target_dir)
                findings["endpoints"].append(str(rel_path))

    # Save manifest
    manifest_path.write_text(json.dumps(findings, indent=2), encoding="utf-8")
    print(f"  [PASS] Brownfield manifest generated: {manifest_path}")
    print(f"  [INFO] Detected frameworks: {', '.join(findings['frameworks']) if findings['frameworks'] else 'Generic'}")
    print(f"  [INFO] Discovered {len(findings['database_migrations'])} migration files")
    print(f"  [INFO] Discovered {len(findings['endpoints'])} route/controller files")

    # Generate ADR-000 baseline adoption template if not exists
    adr_dir = target_dir / "docs" / "adr"
    adr_dir.mkdir(parents=True, exist_ok=True)
    adr_000 = adr_dir / "ADR-000-legacy-baseline-adoption.md"
    if not adr_000.exists():
        adr_content = f"""# ADR-000: Legacy System Baseline Adoption & Freeze

- **Status:** Accepted
- **Date:** {Path().cwd()}

---

## 1. Context
The codebase at `{target_dir.name}` contains pre-existing architectural patterns, database schemas, and API contracts. This ADR codifies the pre-CGSpec state as the immutable baseline before forward-slicing commences.

## 2. Ingestion Summary
- **Primary Frameworks:** {', '.join(findings['frameworks'])}
- **Discovered Routes/Controllers:** {len(findings['endpoints'])} files
- **Discovered Database Migrations:** {len(findings['database_migrations'])} files
- **Detailed Manifest:** `docs/.working/brownfield-manifest.json`

## 3. Decision
1. Freeze legacy interfaces and wrap non-modular components in Ports & Adapters facades.
2. Direct all new feature developments through CGSpec vertical slices (`docs/slices/`).
3. Maintain domain soul in `docs/01-PRD.md` and user-facing nouns in `docs/02-NOUNS-AND-FLOWS.md`.
"""
        adr_000.write_text(adr_content, encoding="utf-8")
        print(f"  [PASS] Baseline freeze ADR created: {adr_000}")

    print("-" * 60)
    print("SUCCESS: Codebase ingestion complete. Ready for OOUX noun distillation.")
    return 0

if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    sys.exit(ingest_codebase(target))
