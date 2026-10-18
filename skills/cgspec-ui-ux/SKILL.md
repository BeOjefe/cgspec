---
name: cgspec-ui-ux
description: Design or revise a product experience from real references through task flows, grey behavior prototypes, and the real frontend; handles responsive and mobile evidence explicitly.
---

# Design the experience

Read the [agent contract](../../engine/CONTRACT.md) and [method section 6](../../docs/METHOD-v2.md). Start from the user's goal and current locked layers in `docs/spines/03-EXPERIENCE.md`. The AI finds up to six contrasting real references, with links, screenshots and captions in `docs/prototypes/_vision/`; the user reacts in their own words or marks images. Name effects and motion the user points to. If reference access is unavailable, state the gap and proceed with evidence already present. Do not ask the user to research or write the brief.

Advance only the layer affected: 0 references and shared words; 1 actor tasks; 2 screens and flows; 3 grey shell and wireframes with zone IDs; 4 clickable grey behavior, states and test IDs; 5 one real token sheet; 6 real frontend screens with mocked typed data; 7 motion in that frontend. Layers 0–4 are disposable. Lock layer 4 before building 5–7; approved journeys carry into the real app. A small tweak inside locked zones and tokens is applied directly. A changed flow, zone or token reopens only dependent layers and baselines; show impact before consequential redesign.

An existing design system is an option only when its installable typed components, machine-readable tokens and permissive license are verified. Explain how its exact version and checks will be used. If none qualifies, derive project tokens from references with provenance. Avoid imposing a universal visual style or treating generic-look warnings as user taste decisions.

For each screen, test the actual behavior in a browser when available, including responsive states and keyboard/accessibility paths; inspect screenshots separately. For native mobile, distinguish browser simulation, simulator and device evidence. Use `visual_audit.py`, `journey.py` and the bundler only if those tools exist in the installed engine. Missing browser or unbuilt tools mean PARTIAL or BLOCKED for that check, never PASS. Record revision and evidence before locking or presenting completion.
