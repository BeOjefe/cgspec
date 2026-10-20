# From references to measured values

Use after the user has reacted to references (layer 0) and again when building the token sheet (layer 5b). The goal is numbers with a source, so the token sheet is derived, not invented. Copy the pattern, never the paint: measure proportions and relationships, then choose your own values in that spirit.

## Worksheet (one per reference the user liked)

Save as `docs/prototypes/_vision/<ref-slug>.md` next to the screenshot.

```markdown
# <Reference name>

Source: <URL>, captured <date>, screenshot <file>
User reaction: "<their words>"
What we take from it: <one sentence: the pattern, not the look>

| Property | Measured | How measured |
| --- | --- | --- |
| Body text size / line height | 14px / 20px | browser devtools on <element> |
| Display size of the focal figure | 32px | devtools |
| Size steps seen | 12, 13, 14, 16, 20, 32 | devtools, 6 elements |
| Base spacing unit | 4px | paddings 8/12/16/24 |
| Row height (lists, tables) | 36px | devtools |
| Corner radius | 6px controls, 8px panels | devtools |
| Surface levels | 3: #FAFAF9, #FFFFFF, #F4F4F2 | eyedropper |
| Text tiers | #1C1C1A, #5E5E58, #8C8C84 | eyedropper |
| Accent and its job | one hue, primary button and selection only | observation |
| Signature detail | <what makes it recognisable> | observation |
```

Measure with the browser's devtools when the reference is a live page; with an eyedropper and a pixel ruler on screenshots otherwise. Write "estimated" next to any value read from a compressed image. If a reference cannot be opened, say so; do not fill values from memory.

## Turning several worksheets into decisions

1. Put the measured values of all liked references side by side.
2. For each property, write the range and which reference sets each end.
3. Choose the project's value inside the user's preferred range and record why in the register or token sheet (`"$description"` field).
4. Anything you take directly from one reference (a signature-like detail) must be adapted, not copied; note the adaptation.
