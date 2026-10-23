# CGSpec v0.2 documentation index
Created: unknown · Last edited: 2026-10-22T21:26:35Z

[METHOD-v0.2.md](METHOD-v0.2.md) is the current specification. [STATUS.md](STATUS.md) is the single implementation-status reference. The `0.2.0` marker does not mean a release has been published.

## Current implementation

| Area | Entry | Status |
| --- | --- | --- |
| Method and design path | [METHOD-v0.2.md](METHOD-v0.2.md) | Specification; some tools remain unbuilt |
| Agent operating contract | [CONTRACT.md](../engine/CONTRACT.md) | Candidate |
| Engine state and hook formats | [FORMATS.md](../engine/FORMATS.md) | Candidate |
| Install, doctor and ledger | [engine/](../engine/) | Implemented; validation must cite the tested revision and skipped checks |
| Source ingestion and v0.1 adoption | [engine/](../engine/) | Implemented; independent safety review open |
| Browser journeys, visual audit, prototype bundling, impact map | [engine/](../engine/) | Implemented; browser-backed and agent-driven review open |
| Workflow skills | [skills/](../skills/) | Nine v0.2 skills plus pivot alias; runtime rehearsal pending |
| Team roles | [agents/](../agents/) | Eight definitions; runtime rehearsal pending |
| Project templates | [templates/](../templates/) | Candidate; CortexGate upgrade rehearsal pending |
| Current research | [02-research/](_cgspec/02-research/README.md) | [RES-005](_cgspec/02-research/RES-005-anthropic-design-plugin-structure-and-skills.md) design plugin and [RES-006](_cgspec/02-research/RES-006-scroll-craft-skill-standard-and-verification.md) scroll-craft concluded 2026-10-22; queued spikes in [RESEARCH-QUEUE.md](_cgspec/02-research/RESEARCH-QUEUE.md) |

## Historical v0.1 records

The [five spines](spines/README.md), [earlier ADRs](adr/README.md), [research notes](_cgspec/02-research/README.md), [council notes](_cgspec/03-council/README.md), [old ledger](_memlog.md) and [changelog](../CHANGELOG.md) preserve earlier work. ADR-001 through ADR-005 are v0.1 history: their status labels, paths, tool and product-specific guarantees do not establish current v0.2 behavior. [ADR-006](adr/ADR-006-main-branch-governance.md) is the current repository-specific governance decision; it is not a default imposed on consumer projects. Use the v0.2 specification and current engine for new work. Git history retains the earlier scripts; the only v0.2 script source is `engine/`.
