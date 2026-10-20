# CGSpec contributor entry
Created: unknown · Last edited: 2026-10-20T17:48:52Z

This repository develops CGSpec v0.2. Read [current implementation status](docs/STATUS.md), then the relevant parts of [the method specification](docs/METHOD-v0.2.md), [engine formats](engine/FORMATS.md) and [the short contract](engine/CONTRACT.md).

In this workspace, `/home/ojefe/Documents/Project/cgspec` is the development checkout; `cgspec-next` is a duplicate, not a second development stream. On another machine, use the checkout opened by the user. Work on feature branches and land changes through PRs; never write directly to main or change Git configuration. Leave CortexGate and other consumer projects untouched unless their upgrade is explicitly authorized.

This plugin source tree is not an installed CGSpec consumer project. Do not install over it to silence consumer-layout errors from doctor. Validate the source with its tests and plugin validator, and run consumer doctor and governance checks in disposable installed projects. Record source revision, checks and limitations; never treat the main-origin workflow as the engine suite.

The current method and skills define new work. The documentation index identifies v0.1 history; historical Accepted labels are not current v0.2 approval. ADR-006 records this repository's current governance decision, with credential isolation still pending. Preserve historical evidence and other sessions' work. Add regression tests for substantive defects. The user leads goals and taste; the agent carries the method.
