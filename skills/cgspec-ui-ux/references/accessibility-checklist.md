# Accessibility & Ergonomics Checklist (WCAG AA & Power-User Standards)

## Visual & Contrast
- [ ] **Body Text Contrast:** Minimum 4.5:1 contrast ratio against the immediate surface background.
- [ ] **Large Text & Headings:** Minimum 3.0:1 contrast ratio for text >= 18px bold or 24px regular.
- [ ] **UI Components & Hairlines:** Minimum 3.0:1 contrast for borders indicating actionable boundaries.
- [ ] **Color Blindness Independence:** Information (errors, statuses, links) is never conveyed by color alone; always paired with an icon, label, or textual indicator.

## Keyboard & Traversal
- [ ] **Sequential Navigation:** Logical tab order (`tabindex="0"` for interactive custom elements, `-1` for programmatic focus).
- [ ] **Visible Focus Rings:** Every focused control has an unmistakable focus indicator (e.g. `ring-2 ring-blue-500 ring-offset-2`).
- [ ] **Zero Keyboard Traps:** Focus can always be moved away using standard directional keys, `Tab`, or `Escape`.
- [ ] **Modal / Drawer Focus Trap:** When a modal is open, focus is trapped inside until dismissed via `Escape` or a close button, returning focus to the triggering element.
- [ ] **Global Command Bar:** Accessible from anywhere via `Cmd+K` (Mac) or `Ctrl+K` (Linux/Windows).

## Touch & Hit Targets
- [ ] **Minimum Hit Size:** Minimum 36x36px (desktop/compact) or 44x44px (touch/mobile) for clickable buttons and icon toggles.
- [ ] **Sufficient Padding:** Inline icons have generous hitboxes extending beyond the visible icon glyph.

## Semantics & Screen Readers
- [ ] **Landmarks:** Screen organized with semantic tags (`<header>`, `<nav>`, `<main>`, `<aside>`, `<footer>`).
- [ ] **Icon Buttons:** Every icon-only button contains an `aria-label` or hidden screen-reader text (`sr-only`).
- [ ] **Live Regions:** Dynamic status changes (e.g. "Saved to disk", "Indexing 24 files") use `aria-live="polite"`.
