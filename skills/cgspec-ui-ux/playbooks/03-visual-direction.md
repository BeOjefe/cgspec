# Playbook 03: Develop Visual Direction & Positive Quality Rules

## Purpose
Guide the human architect and AI agent through Phase 3 and Phase 4 of the Experience Cycle: translating human aesthetic taste into concrete typography, density, surface elevation, brand anchors, and positive quality standards.

---

## Operating Invariants

1. **Positive Standards Over Pure Negation:**
   - Anti-slop bans ("no purple gradients", "no floating cards") prevent mistakes, but they do NOT automatically produce great design.
   - Design must be driven by positive requirements: clear visual hierarchy, appropriate density, harmonious typography, legible contrast, and tactile feedback.
2. **Translate Pacing into Physical Tokens:**
   - Listen to the user's emotional and physical vocabulary ("feels like a quiet notebook", "feels like an industrial control cockpit", "clean daylight confidence").
   - Convert these feelings into concrete CSS variables, font selections, and spacing units.
3. **Typographic Discipline:**
   - Never use default unstyled browser fonts.
   - Use tabular figures (`tabular-nums`) and monospace font for all IDs, metrics, timestamps, and hashes.
   - Limit the system to 1 primary body sans, 1 monospace utility font, and optionally 1 display serif/grotesque if warranted by brand identity.
4. **Surgical Brand Anchor (The 1-Color Rule):**
   - Pick exactly ONE signature brand accent (e.g. Safety Orange `#f38020`, Blueprint Amber `#facc15`, Terminal Cyan `#06b6d4`).
   - Reserve this accent for primary actions, critical badges, and focus anchors. Never create an unfocused rainbow of conflicting neon accents.
5. **Hairline Surface Elevation:**
   - Differentiate cards and panels through tonal surface background shifts and 1px hairline borders (`border-white/10` or `#e5e7eb`), never heavy disembodied drop shadows.

---

## Density & Surface Calibration

| Mode | Hit / Row Height | Body / Display Scale | Spacing Unit | Target Surface & Use Case |
| :--- | :--- | :--- | :--- | :--- |
| **Narrative / Marketing Website** | 44px - 52px CTAs | 16px - 18px body / 40px - 64px hero | 32px - 80px section rhythm | Landing pages, portfolios, blogs, product launch pages |
| **Mobile Touch (iOS / Android)** | **44pt (iOS) / 48dp (Android) min** | 15px - 17px (SF Pro / Roboto scale) | 12px - 20px thumb-friendly | Native iOS, Android, React Native, Flutter, mobile web |
| **Cozy / Editorial Workspace** | 44px - 48px | 15px - 16px | 16px - 24px | Long-form writing, document reading, consumer web apps |
| **Balanced / Standard SaaS** | 38px - 42px | 14px | 12px - 16px | Standard SaaS dashboards, settings, workspace navigation |
| **Compact / High-Density** | 32px - 36px | 12px - 13px | 8px - 12px | Desktop developer tools, terminals, data tables, key vaults |

---

## Deliverables & Disk Updates
- Record tokens and styling rules in `docs/spines/03-EXPERIENCE.md` under `## 2. Design Tokens & Visual Direction`.
- If testing two aesthetic directions, render comparative HTML cards in an Artifact with identical layout and dummy data.
- Append agreed visual choices to `.memlog.md`.
