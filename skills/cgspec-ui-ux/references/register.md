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

## Example (invoice tracker for solo freelancers)

> Calm and exact, like a good accountant's ledger rather than a startup dashboard. Users open it for a minute between client work to see what is owed and act on what is late, mostly on a laptop. It borrows the dense, quiet tables of the first reference and the confident single figure of the third. It must never feel like a marketing site or a toy.
>
> - Density: dense tool (14px body, 4px unit, 36px rows)
> - Type: one neo-grotesque for everything, tabular figures for amounts
> - Stance: light primary, dark later
> - Mood: composed
> - Accent: deep green, only for the primary action and paid status
> - Signature element: the overdue total set large in the top-left of every screen, with days overdue as a thin bar under each row
> - Avoid: gradient hero, card grid dashboard, playful illustrations
> - Deliberate choices: none
