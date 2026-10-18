# ADR-004: Arbitrary Multi-Service Topologies, Virtual Mounting & Contract-First Interface Decoupling

- **Status:** Accepted
- **Date:** 2026-10-16
- **Context:** Real-world enterprise systems do not adhere to simplistic "one frontend, one backend" binaries. Modern engineering architectures routinely consist of $N$ microservice repositories (e.g. `services/auth`, `services/order-matching`, `services/payments`, `workers/market-data`, `workers/airflow`, `apps/web-dashboard`).
- **Decision:**
  1. **Zero Binary Assumptions:** CGSpec strictly supports $N$-tier polyrepo ecosystems through Mode B (Polyrepo Hub `<project>-blueprint`) and Mode C (Service Satellite Repositories).
  2. **Virtual Mounting Engine:** Repositories are mounted under user-defined virtual path prefixes (e.g. `services/*`, `workers/*`, `apps/*`), preserving independent git histories, branches, and codebases.
  3. **Contract-First Decoupling:** When Service A depends on Service B, the shared interface (REST endpoint, gRPC protobuf, or Kafka event payload) is defined in the central blueprint first (`CG-Core`). Dependent teams implement against mock adapters immediately without blocking on service deployments.
- **Consequences:**
  - Independent team velocity: microservices and frontends deploy on decoupled release cycles.
  - Zero cross-service git pollution: database migrations and service code stay strictly in their respective repositories.
