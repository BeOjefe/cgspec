# 04-ARCHITECTURE: Physical Topology, Schemas & Port/Adapter Interfaces

- **Status:** `[Locked in 03 — Awaiting Stage 3 Council]`
- **Pre-requisite:** Stage 2 UI/UX validation must be complete before physical schemas are locked.

---

## 1. Physical Topology & Deployment Architecture
- **Runtime Environment:** [e.g. Node.js 22 LTS / Python 3.12 / Go 1.23]
- **Storage Subsystem:** [e.g. SQLite / PostgreSQL / Local Encrypted Files]
- **API Boundary:** [e.g. Hexagonal Ports & Adapters / REST / JSON-RPC / gRPC]

---

## 2. Relational Schemas & Physical Data Models
*(Compiled directly from 02-OOUX domain nouns and validated UI fields)*

```sql
-- DDL Schemas mapped to domain nouns
CREATE TABLE IF NOT EXISTS primary_nouns (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

---

## 3. Ports & Adapters (Hexagonal Boundaries)
UI components must never import databases or cryptographic primitives directly:
- **Port:** `PrimaryNounRepositoryPort` (Interface)
- **Adapter A:** `SqlitePrimaryNounAdapter` (Production implementation)
- **Adapter B:** `MockPrimaryNounAdapter` (In-memory testing implementation)
