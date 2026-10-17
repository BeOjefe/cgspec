# 05-EXPERIENCE: Human Experience, Protagonists & Interaction Flows

## 1. Protagonists & Personas

CGSpec eliminates abstract personas in favor of explicit functional protagonists interacting with AI agents:

1. **Founding Engineer / Solo Creator:** Moves fast, needs rigor without friction, shifts between high-level PRD vision and vertical slice implementation.
2. **Staff Architect / Tech Lead:** Oversees multiple repositories, conducts peer debate councils for architectural decisions, ensures ADR consistency and strict modularity.
3. **AI Coding Assistant (Agent / Pair Programmer):** Operates under AGENTS.md laws, derives specifications non-linearly, runs doctor invariant checks, and never jumps to code before UI/UX approval.

---

## 2. Interaction Journeys

### Journey 1: Greenfield Discovery & Specification Lock
1. **Initiation:** Agent or human initializes CGSpec vault via `cgspec-init`.
2. **Intent & PRD:** Problem space, target audience, and Day-in-the-Life journey defined in `01-PRD.md`.
3. **Domain Mental Model:** Nouns and permissions defined in `02-NOUNS-AND-FLOWS.md` (Sophia Prater OOUX).
4. **Experience & UI/UX:** Spatial zoning, design tokens, 7-state matrix, and interactive single-file prototype approved by human before architecture or coding starts.
5. **Architectural Lock:** Physical DDL, Ports & Adapters, and ADRs recorded.
6. **Slice Delivery:** Atomic vertical slices verified via tests and browser automation.

### Journey 2: Brownfield Codebase Ingestion
1. **Harvest:** Agent runs `cgspec ingest` to harvest routes, ASTs, and database models.
2. **Distillation:** Manifest generated in `.working/brownfield-manifest.json` and business nouns extracted into `02-NOUNS-AND-FLOWS.md`.
3. **Baseline Freeze:** `ADR-000` locks the legacy baseline.
4. **Forward Slicing:** New capabilities developed using CGSpec's strict vertical slice methodology.

---

## 3. The 7-State Component & View Matrix

Every interface generated or governed by CGSpec adheres to the 7-State lifecycle:

1. **Populated:** Standard operational view displaying realistic domain data.
2. **Loading Skeleton:** Pulsing structural placeholders matching final geometry.
3. **Empty State:** Clean explanatory illustration with direct call-to-action to create first item.
4. **Error State:** Explicit error code, diagnostic explanation, and retry action.
5. **Denied 403:** Permission explanation and role elevation request mechanism.
6. **Offline / Reconnecting:** Network resilience banner with cached state indication.
7. **Partial / Filtered:** Contextual zero-results helper with filter clear action.
