# CGSpec Tooling & Scripts (`docs/_cgspec/01-script/`)

This directory contains standalone Python utilities for specification validation, memory ledger logging, and AST codebase reverse-engineering.

---

## Tool Suite

### 1. `doctor.py` (Spec Integrity Linter)
Validates repository invariants, spine integrity, ADR registrations, and memory log continuity.
```bash
python3 docs/_cgspec/01-script/doctor.py --repo . --strict-emojis
```

### 2. `memlog.py` (Append-Only Decision Log CLI)
Appends and queries milestone locks in `docs/_memlog.md`.
```bash
# Add a milestone entry
python3 docs/_cgspec/01-script/memlog.py add --tags "core,scaffolding" --summary "Completed Model 1 refactoring"

# Check log status
python3 docs/_cgspec/01-script/memlog.py status
```

### 3. `ingest.py` (Deterministic AST Brownfield Ingestion Engine)
Parses legacy codebases (Python AST, TypeScript, Go, SQL DDL) and reverse-engineers domain models, tables, and endpoints into `docs/_cgspec/brownfield-manifest.json` and `docs/adr/ADR-000-legacy-baseline-adoption.md`.
```bash
python3 docs/_cgspec/01-script/ingest.py /path/to/repo --subsystem backend
```

### 4. `visual_audit.py` (Deterministic Anti-Slop Visual Gate)
Headless Chromium test runner that checks interactive prototypes against 65+ deterministic anti-slop rules and takes responsive viewport screenshots.
```bash
python3 docs/_cgspec/01-script/visual_audit.py docs/prototypes/wireframe.html --screenshot-dir /tmp/shots
```
