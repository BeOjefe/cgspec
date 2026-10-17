# CGSpec Experience Quality Rubric

This rubric evaluates user experience and interface design across 5 uncompromising craft dimensions:

---

## 1. Spatial Hierarchy & Density (Weight: 25%)
- **Score 5 (Exemplary):** Visual zoning is immediately legible. Core task canvas commands visual focus. Navigational rails and context drawers stay secondary until summoned. Density is tailored to the persona (compact for developers, balanced for productivity).
- **Score 3 (Acceptable):** Screen has clear zones, but borders or card paddings feel slightly inconsistent. Minor awkward wrapping on long strings.
- **Score 1 (Failing):** AI Slop layout. Giant disembodied floating cards, equal visual weight on everything, empty whitespace voids, or mangled wrapped tables.

---

## 2. Tactile Ergonomics & Motion (Weight: 25%)
- **Score 5 (Exemplary):** Zero modal friction. In-place manipulation feels natural. Cursor placement preserves context. Transitions are snappy (100-150ms cubic-bezier), layout never jumps vertically during state changes or inline expansion.
- **Score 3 (Acceptable):** Functional editing, but requires occasional redundant clicks or has minor layout shifts on load.
- **Score 1 (Failing):** Rigid edit/save modal dialogs interrupting thought flow. Jarring full-page refreshes or jerky layout jumping.

---

## 3. Typographic Discipline & Token Craft (Weight: 20%)
- **Score 5 (Exemplary):** Coherent typographic scale (max 3 font families). Monospace paired with `tabular-nums` for all metrics, codes, hashes, and timestamps. Exactly 1 surgical brand anchor color. Tonal elevation with 1px hairlines.
- **Score 3 (Acceptable):** Legible typography, but occasional inconsistent font weights or secondary accent color conflicts.
- **Score 1 (Failing):** Unstyled default browser fonts, generic purple-indigo gradients, emojis used as interface icons, uncalibrated high-saturation rainbows.

---

## 4. Operational State Completeness (Weight: 15%)
- **Score 5 (Exemplary):** All 7 operational states modeled cleanly at component level. Loading skeletons prevent layout shift. Empty states provide clear next actions. Errors are human-friendly with actionable retries.
- **Score 3 (Acceptable):** Populated and loading states well-handled, but empty or error states look like generic placeholders.
- **Score 1 (Failing):** Happy-path only. White screens on fetch errors, infinite spinners, missing 403 handling.

---

## 5. Keyboard Flow & Accessibility (Weight: 15%)
- **Score 5 (Exemplary):** Complete end-to-end task execution reachable via keyboard. Visible, high-contrast focus rings. WCAG AA contrast (minimum 4.5:1 for body text). `Cmd+K` command search. Proper ARIA landmarks.
- **Score 3 (Acceptable):** Tab navigation works, but focus rings are subtle or a few drawer interactions require mouse clicks.
- **Score 1 (Failing):** Keyboard trap, invisible focus indicators, low-contrast washed-out gray text on gray backgrounds.
