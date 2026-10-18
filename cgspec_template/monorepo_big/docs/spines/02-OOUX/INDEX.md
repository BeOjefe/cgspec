# 02-OOUX: Domain Mental Model & Object Matrix (Sprouted Spine)

- **Status:** `[Drafting]`
- **Framework:** `Sophia Prater ORCA Domain Modeling`

---

## Sprouted Domain Sub-Modules

1. **[`nouns/`](./nouns/):** Modular specifications for each primary domain noun:
   - `NOUN-01-WORKSPACE.md`: Multi-root directory workspace lifecycle, pinning, and folder scopes.
   - `NOUN-02-VIRTUAL-KEY.md`: Attenuated token generation, TTL expiration, and rate-limiting.
   - `NOUN-03-PERSONAL-VAULT.md`: Cryptographic envelope encryption and DEK erasure.
2. **[`PERMISSIONS-MATRIX.md`](./PERMISSIONS-MATRIX.md):** The complete cross-product of all domain nouns against the 6 granular permissions (`read | invoke | propose_edit | write | share | admin`).
3. **[`RELATIONSHIPS-GRAPH.md`](./RELATIONSHIPS-GRAPH.md):** Cardinality, ownership, and inheritance hierarchy among domain objects.
