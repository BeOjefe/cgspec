# Craft method

Load at layer 3 (wireframes), 5 (token sheet) and 6 (high fidelity). The bans in `visual_audit.py` stop the worst output; this file is how you make good output. Each rule says what to decide, how to decide it, and how the critique rubric (`critique-rubric.md`) will check it. Copy the pattern of a reference, never its paint.

## 1. One focal point per screen

Before laying out a screen, write one sentence: "On this screen the user mainly needs to ___." The element that answers it gets the largest size or strongest contrast on the screen; nothing else competes at that level.

- A dashboard is not "everything at once". Pick the one number or list the user acts on (for a maintenance tool: which open work orders are urgent and how late they are).
- Secondary actions sit visibly lower: smaller, quieter colour, or behind a menu.
- Check: squint or blur the screenshot. The focal point is still the first thing you see.

## 2. Hierarchy in at least three levels, readable in greyscale

Distinguish levels with size, weight and colour tier together, not colour alone.

| Level | Typical use | Signals |
| --- | --- | --- |
| 1 | Screen title, focal figure | Largest size in the scale, heavier weight |
| 2 | Section heads, row primary text | Body size or one step up, medium weight, primary text colour |
| 3 | Metadata, labels, timestamps | One step down, regular weight, secondary text colour |
| 4 (optional) | Hints, disabled | Smallest step, tertiary colour |

- Never more than about five distinct font sizes on one screen.
- Check: convert the screenshot to greyscale; the levels are still distinct.

## 3. A type scale chosen for the density

Choose the base size and ratio from the register's density (see `register.md`), then name every size by role.

| Density | Base body | Ratio | Line height (body / display) | Typical use |
| --- | --- | --- | --- | --- |
| Dense tool | 13–14px | 1.125–1.2 | 1.45 / 1.15 | Tables, admin, finance, dev tools |
| Balanced app | 15–16px | 1.2–1.25 | 1.5 / 1.2 | Most product apps |
| Editorial | 17–19px | 1.25–1.333 | 1.6 / 1.1 | Reading, marketing, docs |

- Display sizes (above 28px) get slightly negative tracking (-0.01 to -0.02em); small caps labels get positive tracking (+0.04 to +0.08em).
- Numbers that line up (amounts, dates, IDs) use `font-variant-numeric: tabular-nums`.
- One family is enough; a second family needs a job (numbers, display) written in the register.
- Check: every rendered font size is a step of the scale (`visual_audit.py` type-scale check).

## 4. One spacing unit and a rhythm

- Pick a base unit (4px for dense tools, 8px otherwise). Every padding, margin and gap is a multiple.
- Related things sit closer than unrelated things: inside a group use 1–2 units, between groups 3–6 units. That difference is what makes groups readable without boxes.
- Prefer spacing and alignment over borders and cards to show grouping. Add a border or surface only when spacing alone cannot separate.
- Check: spacing values sit on the base grid (`visual_audit.py` spacing check); groups are visible with borders hidden.

## 5. One alignment grid

- Decide the column structure per breakpoint (for example 12 columns desktop, 4 phone) and the left edge every text block aligns to.
- Left-align text by default; centre only short, standalone content (empty states, a single call to action).
- Numbers in tables align right; their headers align with them.
- Check: draw vertical lines at the main edges of the screenshot; most elements touch one of a few lines.

## 6. Surfaces you can tell apart

Define two to four surface levels and use them consistently.

| Role | Light stance | Dark stance |
| --- | --- | --- |
| canvas | The page | The page |
| surface | Panels, table background | One step lighter than canvas |
| raised | Popovers, menus, active row | One more step lighter |
| overlay | Modals, behind a scrim | Highest |

- Separate levels by tone first, then a hairline border, and shadow last (shadows read as floating; use them for things that do float).
- Adjacent levels need a visible but quiet difference (roughly 3–6% lightness apart).
- Check: in the screenshot you can name each surface's level.

## 7. Colour roles, one accent with one job

- Neutrals carry the interface: 3 text tiers (primary, secondary, tertiary) and the surface levels.
- One accent hue, used for the primary action and the current selection. If it appears on more than about 10% of the screen, it stops meaning anything.
- Status colours (success, warning, danger, info) are for status only, never decoration; each pairs with an icon or word so colour is not the only signal.
- Contrast: body text at least 4.5:1, large text and meaningful icons at least 3:1, focus rings at least 3:1 against both neighbours.
- A choice the warnings flag (purple accent, cream and serif) is fine when the register records it as deliberate, with the reason.
- Check: `visual_audit.py` contrast and accent-count checks; rubric item 5.

## 8. Density that fits the content

- Set row height, control height and base unit from the register, not per screen.
- Dense tool: 32–40px rows, 28–32px controls on desktop; touch targets still 44px on phone (rows can stay compact while their tap area grows).
- Show real-looking data in realistic amounts (dozens of records, long names, zero, negative, very old dates). A layout that only works with three tidy rows is not done.
- Check: rubric item 4; layouts survive long text and empty data.

## 9. The signature element

Every product gets one recognisable detail, chosen at layer 0–1 and written in the register: a distinctive way of showing the key number, a characteristic table treatment, a precise use of the accent, an unusual but fitting typeface for figures. One, used consistently, beats five scattered flourishes.

- It must serve the focal point or the main task, not decorate.
- Check: rubric item 6; you can point to it on every main screen.

## 10. States are designed, not left over

For each screen design: loading, empty (with the next action), error (with what to do), populated, partial/filtered, and long-content. An empty state is a chance to teach the next step, not a grey box.

## Order of work at layer 6

1. Apply tokens to one key screen completely; review it against the rubric before touching others.
2. Fix hierarchy and spacing before colour; fix colour before effects.
3. Only then roll out to the remaining screens, reusing the component recipes (`components.md`).
