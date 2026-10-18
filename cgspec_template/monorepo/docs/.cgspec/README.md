# CGSpec Engine Internal Subsystem (`docs/.cgspec/`)

This directory is the dedicated engine room for the **Reformed CGSpec v0.2 Specification-Driven SDLC Methodology**. It centralizes all executable scripts, research spikes, debate council logs, ADR records, interactive HTML prototypes, slice contracts, and deprecated stashes inside `docs/.cgspec/` to ensure **zero root workspace pollution**.

---

## 1. Directory Structure & Numbering Invariant

All engine directories use strictly singular, zero-padded nouns for stable terminal sorting and deterministic script discovery:

```
docs/.cgspec/
├── README.md               # This specification guide
├── 01-script/              # Deterministic verification and ingestion tools
├── 02-research/            # Deep technical spikes, benchmarks, and citations (RES-NNN)
├── 03-council/             # Supervised 3-Agent Peer Debate Council session transcripts
├── 04-adr/                 # Irreversible Architecture Decision Records (ADR-NNN)
├── 05-prototype/           # Single-file interactive HTML wireframes & prototypes (scr01..scr05)
├── 06-slice/               # Bounded vertical slice implementation contracts (SLICE-NNN)
└── .archive/               # Design Stash Protocol (superseded prototypes and specs)
```

> **Invariant:** Never create a `.working/` directory. Never create pluralized directory names (e.g. `scripts/` or `prototypes/` inside `.cgspec/`). All engine artifacts must reside in these exact 7 subpaths.

---

## 2. Subsystem Responsibilities

### `01-script/` — Deterministic Quality & Ingestion Tools
- **`doctor.py`:** The primary integrity hook. Verifies Law 3 spine sequence (00..05), ADR index parity, sequential memlog milestones, and enforces a strict Unicode emoji ban across documentation and code.
- **`visual_audit.py`:** Automated Phase A wireframe and prototype auditor. Runs Checks 1–22 (syntax, stationary toggles, phantom DOM IDs, tabular numerals, and anti-slop checks: gradient text, unprompted neon glow, stock shadcn signatures, and the 2026 cream-serif-sage default trap).
- **`ingest.py`:** Deterministic AST codebase ingestion engine for legacy/brownfield codebases. Parses routes, ORM models, and database DDL across Python, TypeScript/JavaScript, Go, and SQL without requiring LLM inference.

### `02-research/` — Technical Spikes & Research Registry (`RES-NNN`)
- Deep investigative records for trade-offs, benchmarks, UI libraries, or technical discoveries before drafting ADRs or code.
- Naming convention: `RES-NNN-<slug>.md` (e.g. `RES-001-ui-frameworks-benchmark.md`).
- Must be registered in `docs/00-INDEX.md` under Section 5.

### `03-council/` — Supervised Peer Debate Transcripts
- Complete, verbatim transcripts of the 3-Agent Peer Debate Council (`cgspec-council`) evaluating contested architectural or security trade-offs.
- Naming convention: `COUNCIL-NNN-<topic>.md`.

### `04-adr/` — Architecture Decision Records (`ADR-NNN`)
- The immutable, irreversible technical constitution of the project.
- Every ADR documents: Context, Decision, Invariants, and Consequences.
- Naming convention: `ADR-NNN-<slug>.md`.
- Status (`[Accepted]`, `[Superseded by ADR-XXX]`) must be kept in 100% sync with `docs/00-INDEX.md` Section 4.

### `05-prototype/` — Interactive Single-File HTML Prototypes
- Self-contained, runnable HTML/Tailwind/Lucide prototypes for each focal screen declared in `03-EXPERIENCE.md`.
- Naming convention: `scr01-wireframe-v1.html` .. `scr01-wireframe-vN.html` (monotonic version increment: $v(N+1) = \max + 1$).
- Must feature a 7-State Switcher (`Populated`, `Skeleton`, `Empty`, `Error`, `Denied 403`, `Offline`, `Filtered Zero`).
- `index.html` in this folder serves as the local development hub.

### `06-slice/` — Bounded Vertical Slice Contracts (`SLICE-NNN`)
- Pre-coding specifications for each atomic vertical slice cutting through UI, Ports/Adapters, domain logic, database, and automated tests.
- Naming convention: `SLICE-NNN-<slug>.md`.
- Must specify: Target OOUX Nouns, In-Scope Files, Port Interfaces, Mock Adapters, and Test Acceptance Criteria.

### `.archive/` — Design Stash Protocol
- When user feedback, scope pivots, or architectural council debates supersede a wireframe or specification, the file is **never deleted**.
- It is stashed here with a monotonic timestamped prefix:
  `YYYYMMDD-HHMMSS-<stage>-<target>-v<N>-<reason>.ext`
  Example: `20261018-084500-stage2-scr01-wireframe-v10-user-rejected-card-box.html`.
- Preserves a clean historical audit trail that matches Git commit SHAs.
