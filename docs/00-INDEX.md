# CGSpec v0.2 candidate — documentation index

The `claude/design-craft` branch is an implementation candidate. [METHOD-v0.2.md](METHOD-v0.2.md) is the current method specification; [the repository README](../README.md) records implementation status and limits. The `0.2.0` marker does not mean a release has been published.

## Current implementation

| Area | Entry | Status |
| --- | --- | --- |
| Method and design path | [METHOD-v0.2.md](METHOD-v0.2.md) | Specification; some tools remain unbuilt |
| Agent operating contract | [CONTRACT.md](../engine/CONTRACT.md) | Candidate |
| Engine state and hook formats | [FORMATS.md](../engine/FORMATS.md) | Candidate |
| Install, doctor and ledger | [engine/](../engine/) | Implemented; full suite passing at latest checkpoint |
| Source ingestion and v0.1 adoption | [engine/](../engine/) | Implemented; independent safety review open |
| Browser journeys, visual audit, prototype bundling, impact map | [engine/](../engine/) | Implemented; browser-backed and agent-driven review open |
| Workflow skills | [skills/](../skills/) | Nine v0.2 skills plus pivot alias; runtime rehearsal pending |
| Team roles | [agents/](../agents/) | Eight definitions; runtime rehearsal pending |
| Project templates | [templates/](../templates/) | Candidate; CortexGate upgrade rehearsal pending |

## Historical v0.1 records

The [five spines](spines/README.md), [ADRs](adr/README.md), [research notes](_cgspec/02-research/README.md), [council notes](_cgspec/03-council/README.md), [old ledger](_memlog.md) and [changelog](../CHANGELOG.md) document earlier CGSpec work. Their old status labels, absolute `file://` links, and tool claims are historical evidence, **not v0.2 implementation or current approval**. Use the v0.2 specification and current engine for new work. Git history retains the earlier scripts removed from this candidate; the only v0.2 script source is `engine/`.
