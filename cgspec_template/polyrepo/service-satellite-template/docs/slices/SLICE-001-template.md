# SLICE-001: [Title of First Vertical Slice]

- **Status:** `[Queued]`
- **Target OOUX Nouns:** `[PrimaryNounA]`
- **Pre-requisites:** `03-EXPERIENCE.md` validated, `ADR-001` accepted.

---

## 1. Scope & Bounded File Manifest
- **In-Scope Production Files:**
  - `src/domain/primary_noun.ts`
  - `src/ports/primary_noun_repository.port.ts`
  - `src/adapters/sqlite_primary_noun_adapter.ts`
  - `src/ui/components/PrimaryNounCard.tsx`
- **In-Scope Test Files:**
  - `tests/unit/primary_noun.test.ts`
  - `tests/e2e/primary_noun_flow.spec.ts`

---

## 2. Port & Adapter Interfaces
Define the decoupled Port interface before implementation:

```typescript
export interface PrimaryNounRepositoryPort {
  findById(id: string): Promise<PrimaryNoun | null>;
  save(noun: PrimaryNoun): Promise<void>;
  list(filter: Record<string, unknown>): Promise<PrimaryNoun[]>;
}
```

---

## 3. Test Acceptance Criteria & Verification Gates
1. Unit tests pass with 100% coverage on domain logic.
2. End-to-end integration test passes against mock adapter.
3. UI passes `visual_audit.py` across 7 states.
