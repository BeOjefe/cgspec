# Register (layer 5a)

The register is the product's visual direction in one short paragraph plus a few fields. Lock it right after the user reacts to references (layer 0–1), before wireframes, because layout and look depend on each other: a 13px dense tool and an 18px editorial page need different wireframes. The full token sheet (layer 5b) still comes after layer 4 is locked; it must follow the register.

Write it in `docs/spines/03-EXPERIENCE.md` under `## Register`, show it to the user, and lock it with their approval. Changing it later reopens layer 3 on every screen.

## Template

```markdown
## Register

Status: Proposed | Locked (approval A-...)

<One paragraph, 3-5 sentences: who uses it, in what situation, how it should feel, and what it should never feel like. Name the references it draws from and what each contributes.>

- Density: dense tool | balanced app | editorial  (base body size, base spacing unit, row height)
- Type: <family or families and why; which one sets numbers>
- Stance: light | dark | both (which is primary)
- Mood: <one word>
- Accent: <one hue and its single job>
- Signature element: <the one recognisable detail and where it appears>
- Avoid: <two or three things this product must not look like>
- Deliberate choices: <each choice a generic-look warning flags, with the reason; for example "purple accent: existing brand colour since 2024">
```

## Rules

- Each field must trace to a reference the user reacted to, or to a stated user need. "Looks modern" is not a reason.
- One accent, one signature element. If you want two, you have not chosen yet.
- A deliberate choice listed here turns the matching `visual_audit.py` look warning into an accepted note; nothing else silences it. Do not use `cgspec-allow` comments for choices the user has not seen.
- The register is a starting point, not paint: the bans in RES-004 are defaults to challenge with a reason, not laws. Avoiding every cliché at once produces a new cliché.

## Example (maintenance work orders for building managers)

> Steady and legible, like a well-run control room rather than a consumer app. Building managers check it between site visits to see what is urgent and who is on it, on a laptop at the desk and a phone on site. It borrows the dense, sortable lists of the first reference and the strong single status band of the second. It must never feel playful or decorative.
>
> - Density: dense tool (14px body, 4px unit, 36px rows)
> - Type: one humanist sans for text, tabular figures for times and counts
> - Stance: light primary, dark later
> - Mood: steady
> - Accent: a single deep blue, only for the primary action and the current selection
> - Signature element: an urgency band down the left edge of each row whose length shows hours past the response target
> - Avoid: card-grid dashboard, gradient headers, illustrations
> - Deliberate choices: none
