# Component recipes

When no existing design system qualifies (method section 6b), prototypes and the real frontend assemble a small set of project components instead of inventing layout per screen. Each recipe lives in `docs/spines/03-EXPERIENCE.md` under `## Components` (or `docs/spines/03-EXPERIENCE/components.md` once it grows) and is implemented once in code.

## Recipe format

```markdown
### <Component>

Job: <one sentence: what the user does with it>
Anatomy: <parts, in order>
Tokens: <the token names it uses, from the token sheet>
States: default, hover, focus, active, disabled, loading, empty, error (only those that apply)
Test IDs: <data-testid values journeys rely on>
Do: <two or three rules>
Don't: <two or three rules>
```

## Starter set for a data-dense tool

Adapt names and rules to the register; delete what the product does not need.

### List row
Job: scan many items and open one. Anatomy: leading status mark, primary text, secondary metadata, trailing figure or action. Tokens: `size.row`, `color.text.primary|secondary`, `space.2|3`. States: default, hover, selected, focus. Do: one line per row at desktop; trailing figures right-aligned with tabular numbers. Don't: wrap rows in cards; put more than one primary action in a row.

### Table
Job: compare items across columns. Anatomy: sticky header, rows, optional footer total. Tokens: `size.row`, `color.surface.surface`, `border.hairline`. States: loading (skeleton rows), empty (message plus next action), sorted. Do: right-align numbers and their headers; truncate long text with a tooltip. Don't: zebra stripes and borders together; centre text columns.

### Side panel (detail)
Job: inspect one item without losing the list. Anatomy: header (title, status, close), body sections, sticky action bar. Do: keep the list visible on desktop; full screen on phone. Don't: open a modal for detail views.

### Tabs
Job: switch between views of the same thing. Do: 2–6 tabs, labels of one or two words, show counts when useful. Don't: use tabs for steps of a process.

### Button set
Job: act. Anatomy: one primary (accent), secondary (neutral), tertiary (text). Do: one primary per view; verbs as labels ("Assign technician"). Don't: two accent buttons side by side; icon-only buttons without a label or tooltip.

### Status pill
Job: show a state at a glance. Anatomy: dot or icon plus a word. Tokens: `color.status.*`. Do: word always present. Don't: colour alone; more than one pill per row.

### Empty state
Job: explain why nothing is here and offer the next step. Anatomy: one sentence, one action. Do: specific to the screen ("No urgent work orders right now."). Don't: large illustrations in a dense tool.

### Command palette (optional)
Job: reach any action by keyboard. Anatomy: input, grouped results, shortcut hints. Do: open with Ctrl/Cmd+K; show recent items first.
