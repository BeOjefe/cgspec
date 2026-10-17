#!/usr/bin/env python3
"""
CGSpec Ingestion Engine (Deterministic AST Codebase Ingest)
Reverse-engineers legacy codebases, extracts domain models, API routes,
and database tables deterministically across major programming languages.

Usage:
  python3 scripts/ingest.py [target-path]
  python3 scripts/ingest.py [target-path] --subsystem src/billing
  python3 scripts/ingest.py [target-path] --live-schema db/schema.sql
"""

import os
import sys
import json
import re
import ast
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

IGNORE_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__",
    "target", "dist", "build", ".gemini", "archive", ".next", ".turbo"
}

class PythonASTExtractor:
    """Extracts routes and ORM/data models using Python's standard library AST."""
    
    @staticmethod
    def extract(file_path: Path, rel_path: str) -> Dict[str, List[Any]]:
        models = []
        endpoints = []
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=str(file_path))
        except Exception:
            return {"models": models, "endpoints": endpoints}

        for node in ast.walk(tree):
            # Model detection: Classes inheriting from Model, BaseModel, Base, Document
            if isinstance(node, ast.ClassDef):
                base_names = []
                for b in node.bases:
                    if isinstance(b, ast.Name):
                        base_names.append(b.id)
                    elif isinstance(b, ast.Attribute):
                        base_names.append(b.attr)
                
                is_model = any(b in {"BaseModel", "Model", "Base", "Document", "Entity"} for b in base_names)
                if is_model:
                    fields = []
                    for item in node.body:
                        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                            fields.append(item.target.id)
                        elif isinstance(item, ast.Assign):
                            for t in item.targets:
                                if isinstance(t, ast.Name):
                                    fields.append(t.id)
                    models.append({
                        "name": node.name,
                        "source_file": rel_path,
                        "framework": f"Python ({', '.join(base_names) if base_names else 'Generic'})",
                        "fields": fields[:20]
                    })

            # Endpoint detection: Functions decorated with @app.get, @router.post, etc.
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    dec_call = None
                    if isinstance(dec, ast.Call):
                        dec_call = dec.func
                    elif isinstance(dec, ast.Attribute):
                        dec_call = dec

                    if isinstance(dec_call, ast.Attribute):
                        method = dec_call.attr.upper()
                        if method in {"GET", "POST", "PUT", "DELETE", "PATCH", "ROUTE"}:
                            route_path = "/"
                            if isinstance(dec, ast.Call) and dec.args:
                                first_arg = dec.args[0]
                                if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                                    route_path = first_arg.value
                            endpoints.append({
                                "method": method if method != "ROUTE" else "ANY",
                                "path": route_path,
                                "source_file": rel_path,
                                "handler": node.name
                            })

        return {"models": models, "endpoints": endpoints}

class TypeScriptExtractor:
    """Extracts routes and schemas from TypeScript/JavaScript files (Express, NestJS, Prisma, Drizzle)."""
    
    ROUTE_PATTERN = re.compile(
        r"(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]+)['\"]",
        re.IGNORECASE
    )
    NEST_ROUTE_PATTERN = re.compile(
        r"@(Get|Post|Put|Delete|Patch)\s*\(\s*['\"]?([^'\")]*)['\"]?\s*\)",
        re.IGNORECASE
    )
    PRISMA_MODEL_PATTERN = re.compile(r"model\s+(\w+)\s*\{([^}]+)\}")
    DRIZZLE_TABLE_PATTERN = re.compile(r"export\s+const\s+(\w+)\s*=\s*(?:pgTable|sqliteTable|mysqlTable)\s*\(\s*['\"]([^'\"]+)['\"]")

    @classmethod
    def extract(cls, file_path: Path, rel_path: str) -> Dict[str, List[Any]]:
        models = []
        endpoints = []
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return {"models": models, "endpoints": endpoints}

        # Express / Fastify routes
        for match in cls.ROUTE_PATTERN.finditer(content):
            endpoints.append({
                "method": match.group(1).upper(),
                "path": match.group(2),
                "source_file": rel_path,
                "handler": "anonymous"
            })

        # NestJS decorators
        for match in cls.NEST_ROUTE_PATTERN.finditer(content):
            endpoints.append({
                "method": match.group(1).upper(),
                "path": match.group(2) or "/",
                "source_file": rel_path,
                "handler": "controller_method"
            })

        # Prisma models
        if file_path.suffix == ".prisma":
            for match in cls.PRISMA_MODEL_PATTERN.finditer(content):
                m_name = match.group(1)
                m_body = match.group(2)
                fields = [line.strip().split()[0] for line in m_body.splitlines() if line.strip() and not line.strip().startswith("//")]
                models.append({
                    "name": m_name,
                    "source_file": rel_path,
                    "framework": "Prisma",
                    "fields": fields[:20]
                })

        # Drizzle schemas
        for match in cls.DRIZZLE_TABLE_PATTERN.finditer(content):
            models.append({
                "name": match.group(1),
                "source_file": rel_path,
                "framework": "Drizzle ORM",
                "fields": []
            })

        return {"models": models, "endpoints": endpoints}

class SQLDDLExtractor:
    """Extracts physical tables and foreign keys from live SQL schema dumps."""
    
    CREATE_TABLE_PATTERN = re.compile(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[\"`]?(\w+)[\"`]?\s*\((.*?)\);",
        re.IGNORECASE | re.DOTALL
    )
    FK_PATTERN = re.compile(r"FOREIGN\s+KEY\s*\([^)]+\)\s*REFERENCES\s+[\"`]?(\w+)[\"`]?", re.IGNORECASE)

    @classmethod
    def extract(cls, file_path: Path, rel_path: str) -> List[Dict[str, Any]]:
        tables = []
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return tables

        for match in cls.CREATE_TABLE_PATTERN.finditer(content):
            table_name = match.group(1)
            body = match.group(2)
            columns = []
            fks = []
            for line in body.splitlines():
                cleaned = line.strip().rstrip(",")
                if not cleaned:
                    continue
                first_word = cleaned.split()[0].replace('"', '').replace('`', '')
                if first_word.upper() in {"CONSTRAINT", "PRIMARY", "UNIQUE", "FOREIGN", "KEY", "INDEX", "CHECK"}:
                    fk_m = cls.FK_PATTERN.search(cleaned)
                    if fk_m:
                        fks.append(fk_m.group(1))
                else:
                    columns.append(first_word)

            tables.append({
                "table_name": table_name,
                "source_file": rel_path,
                "columns": columns[:25],
                "foreign_keys": list(set(fks))
            })

        return tables

class GoExtractor:
    """Extracts Gin/Fiber/Chi routes and GORM structs from Go source files."""
    
    GO_ROUTE_PATTERN = re.compile(r"(?:r|router|app|api|group)\.(GET|POST|PUT|DELETE|PATCH)\s*\(\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)
    GO_STRUCT_PATTERN = re.compile(r"type\s+(\w+)\s+struct\s*\{([^}]+)\}")

    @classmethod
    def extract(cls, file_path: Path, rel_path: str) -> Dict[str, List[Any]]:
        models = []
        endpoints = []
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return {"models": models, "endpoints": endpoints}

        for match in cls.GO_ROUTE_PATTERN.finditer(content):
            endpoints.append({
                "method": match.group(1).upper(),
                "path": match.group(2),
                "source_file": rel_path,
                "handler": "go_handler"
            })

        for match in cls.GO_STRUCT_PATTERN.finditer(content):
            s_name = match.group(1)
            s_body = match.group(2)
            if "gorm.Model" in s_body or "json:" in s_body or "db:" in s_body:
                fields = [l.strip().split()[0] for l in s_body.splitlines() if l.strip() and not l.strip().startswith("//")]
                models.append({
                    "name": s_name,
                    "source_file": rel_path,
                    "framework": "Go Struct / GORM",
                    "fields": fields[:20]
                })

        return {"models": models, "endpoints": endpoints}

def distill_nouns(models: List[Dict[str, Any]], tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Synthesizes high-level OOUX business nouns from models and tables."""
    nouns_map = {}
    for m in models:
        name = m["name"]
        if name not in nouns_map:
            nouns_map[name] = {
                "noun": name,
                "description": f"Domain entity extracted from {m['source_file']} ({m['framework']})",
                "inferred_attributes": m.get("fields", [])[:8]
            }

    for t in tables:
        name = t["table_name"]
        clean_noun = "".join(part.capitalize() for part in name.split("_"))
        if clean_noun not in nouns_map:
            nouns_map[clean_noun] = {
                "noun": clean_noun,
                "description": f"Physical persistence entity extracted from {t['source_file']} ({t['table_name']})",
                "inferred_attributes": t.get("columns", [])[:8]
            }
    return list(nouns_map.values())

def ingest_codebase(target_dir: Path, subsystem: Optional[str] = None, live_schema: Optional[str] = None, output_path: Optional[str] = None) -> int:
    scan_root = (target_dir / subsystem).resolve() if subsystem else target_dir.resolve()
    print(f"CGSpec Ingest: Deterministic AST Analysis of {scan_root}")
    if subsystem:
        print(f"  [SCOPE] Bounded Subsystem: {subsystem} (Strangler Fig pattern)")
    print("-" * 60)

    frameworks = []
    if (target_dir / "package.json").exists():
        frameworks.append("Node.js / TypeScript ecosystem")
    if (target_dir / "pyproject.toml").exists() or (target_dir / "requirements.txt").exists():
        frameworks.append("Python ecosystem")
    if (target_dir / "Cargo.toml").exists():
        frameworks.append("Rust / Cargo")
    if (target_dir / "go.mod").exists():
        frameworks.append("Go ecosystem")

    all_models = []
    all_endpoints = []
    all_tables = []

    # 1. Parse live schema if provided
    if live_schema:
        schema_file = (target_dir / live_schema).resolve()
        if schema_file.exists():
            print(f"  [PARSER] Ingesting live database schema from {schema_file.name}...")
            tables = SQLDDLExtractor.extract(schema_file, str(schema_file.relative_to(target_dir)))
            all_tables.extend(tables)
            print(f"    -> Extracted {len(tables)} tables with physical foreign keys.")

    # 2. Walk scan root and execute AST extractors
    file_count = 0
    for root, dirs, files in os.walk(scan_root):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            file_path = Path(root, f)
            rel_path = str(file_path.relative_to(target_dir))
            suffix = file_path.suffix.lower()

            if suffix == ".py":
                res = PythonASTExtractor.extract(file_path, rel_path)
                all_models.extend(res["models"])
                all_endpoints.extend(res["endpoints"])
                file_count += 1
            elif suffix in {".ts", ".js", ".tsx", ".jsx", ".prisma"}:
                res = TypeScriptExtractor.extract(file_path, rel_path)
                all_models.extend(res["models"])
                all_endpoints.extend(res["endpoints"])
                file_count += 1
            elif suffix == ".go":
                res = GoExtractor.extract(file_path, rel_path)
                all_models.extend(res["models"])
                all_endpoints.extend(res["endpoints"])
                file_count += 1
            elif suffix == ".sql" and not live_schema:
                # Fallback to scanning SQL files if no live schema was explicitly specified
                if any(k in rel_path.lower() for k in ["schema", "structure", "create"]):
                    tables = SQLDDLExtractor.extract(file_path, rel_path)
                    all_tables.extend(tables)
                    file_count += 1

    distilled = distill_nouns(all_models, all_tables)

    manifest = {
        "schema_version": "1.0.0",
        "project_root": str(target_dir.resolve()),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "subsystem": subsystem,
        "frameworks": frameworks or ["Generic / Polyglot"],
        "models": all_models,
        "endpoints": all_endpoints,
        "database_tables": all_tables,
        "distilled_nouns": distilled
    }

    out_file = Path(output_path).resolve() if output_path else (target_dir / "docs" / ".working" / "brownfield-manifest.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"  [PASS] Scanned {file_count} source files across {scan_root.name}")
    print(f"  [PASS] Manifest generated: {out_file.relative_to(target_dir) if out_file.is_relative_to(target_dir) else out_file}")
    print(f"  [METRIC] Discovered {len(all_endpoints)} deterministic endpoints")
    print(f"  [METRIC] Discovered {len(all_models)} data/ORM models")
    print(f"  [METRIC] Discovered {len(all_tables)} relational tables")
    print(f"  [METRIC] Distilled {len(distilled)} high-level OOUX business nouns")

    # Generate ADR-000 baseline freeze
    adr_dir = target_dir / "docs" / "adr"
    adr_dir.mkdir(parents=True, exist_ok=True)
    adr_000 = adr_dir / "ADR-000-legacy-baseline-adoption.md"
    if not adr_000.exists():
        adr_content = f"""# ADR-000: Legacy System Baseline Adoption & Freeze

- **Status:** Accepted
- **Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d')}
- **Context:** Reverse-engineered via `scripts/ingest.py` (AST Ingestion Engine).

---

## 1. Baseline Ingestion Summary
- **Target Root:** `{target_dir.name}` (Subsystem: `{subsystem or 'Full Repository'}`)
- **Frameworks:** {', '.join(frameworks) if frameworks else 'Generic'}
- **Discovered Endpoints:** {len(all_endpoints)} routes
- **Discovered Models & Tables:** {len(all_models)} models, {len(all_tables)} tables
- **Distilled OOUX Nouns:** {', '.join(n['noun'] for n in distilled[:10])}{'...' if len(distilled) > 10 else ''}
- **Deterministic Manifest:** `docs/.working/brownfield-manifest.json`

## 2. Invariants & Decision
1. **Legacy Baseline Freeze:** Existing routes and tables are codified as the immutable baseline.
2. **Ports & Adapters Isolation:** Legacy code must not be refactored wholesale; new functionality must interface with legacy via adapter facades.
3. **Law 3 Compliance:** All future features strictly follow CGSpec vertical slices (`Stage 1 Intent -> Stage 2 UI/UX -> Stage 3 Architecture -> Stage 4 Slices`).
"""
        adr_000.write_text(adr_content, encoding="utf-8")
        print(f"  [PASS] Baseline freeze ADR created: docs/adr/{adr_000.name}")

    print("-" * 60)
    print("SUCCESS: Deterministic codebase ingestion complete. Zero context window dilution.")
    return 0

def main():
    parser = argparse.ArgumentParser(description="CGSpec Deterministic AST Ingestion Engine")
    parser.add_argument("target_path", nargs="?", default=".", help="Project root to ingest")
    parser.add_argument("--subsystem", help="Bounded subsystem path for Strangler Fig ingestion")
    parser.add_argument("--live-schema", help="Path to live database schema dump (schema.sql)")
    parser.add_argument("--output", help="Explicit path for brownfield-manifest.json")

    args = parser.parse_args()
    target = Path(args.target_path).resolve()
    sys.exit(ingest_codebase(target, subsystem=args.subsystem, live_schema=args.live_schema, output_path=args.output))

if __name__ == "__main__":
    main()
