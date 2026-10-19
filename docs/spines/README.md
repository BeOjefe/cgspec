# Living Core Spines (`docs/spines/`)

This directory houses the **5 Living Core Spines** of the specification, organized strictly according to **Law 3 Purity (Intent -> Domain -> Experience -> Architecture -> Delivery)**.

---

## The 5 Spines

1. **[`01-INTENT.md`](./01-INTENT.md) (Stage 1 — Intent & Vision):**
   Product purpose, target actors, anti-goals, boundary invariants, and human day-in-the-life workflows.
2. **[`02-OOUX.md`](./02-OOUX.md) (Stage 1 — Domain Mental Model):**
   Sophia Prater Object-Oriented UX (ORCA) object model, domain nouns, attributes, nested relationships, and the 6-permission matrix (`read, invoke, propose_edit, write, share, admin`).
3. **[`03-EXPERIENCE.md`](./03-EXPERIENCE.md) (Stage 2 — Spatial UI & Interaction):**
   Target Surface Profile (`Profile A..D`), 4-zone spatial viewport shell, tactile design tokens, and the 7-state UI matrix (`Populated, Empty, Loading, Error, Partial, Denied, Stale`).
4. **[`04-ARCHITECTURE.md`](./04-ARCHITECTURE.md) (Stage 3 — Physical Systems & Interfaces):**
   Hexagonal Ports & Adapters, physical database schemas, cryptographic envelopes, and multi-service deployment topologies.
5. **[`05-DELIVERY.md`](./05-DELIVERY.md) (Stage 4 — Slices & Verification):**
   Monotonic milestone roadmap, bounded vertical slice registry, deterministic verification gates, and automated test criteria.

---

## Law 3 Invariant
Software must never jump to physical code or database schemas until intent (`01-INTENT`), domain mental models (`02-OOUX`), and interactive HTML wireframes (`03-EXPERIENCE`) are validated and locked.
