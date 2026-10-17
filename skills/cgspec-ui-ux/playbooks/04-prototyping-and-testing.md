# Playbook 04: Model States & Build Evaluated Milestone Prototype

## Purpose
Guide the human architect and AI agent through Phase 4 and Phase 5 of the Experience Cycle: modeling coexisting component states, building a single-file interactive HTML prototype (`prototype-v0.1.html`), and verifying the experience in a live browser.

---

## Operating Invariants

1. **Coexisting States Over Rigid Screen Replacements:**
   - Real-world applications do not swap the entire screen for an empty or error state.
   - States coexist at both screen level and component level: a populated document editor may contain an offline indicator banner, a failing backlink indexer widget, and an empty comments drawer.
   - Design each component to handle its individual operational lifecycle.
2. **Single-File Zero-Build Deliverable:**
   - The milestone prototype must be a self-contained, zero-build HTML file placed in `docs/.working/prototypes/prototype-v0.1.html`.
   - Use standard CDN links for utility CSS (e.g. Tailwind CSS) and icons (Lucide or inline SVG).
   - Require zero build step (`npm run dev` or bundler) so the human architect or reviewer can open it instantly in any web browser.
3. **Built-in Interactive State Switcher:**
   - The prototype must include a floating state switcher bar fixed at the top of the viewport.
   - The switcher allows the reviewer to toggle instantaneously between:
     1. `Populated` (Default with realistic, non-lorem-ipsum data, long names, edge characters)
     2. `Loading Skeleton` (Shimmer pulse animation on tables and cards)
     3. `Empty State` (Helpful onboarding CTA and explanation)
     4. `Error State` (Actionable retry trigger, non-technical failure explanation)
     5. `Denied 403` (Clear permission boundary notice and escalation path)
     6. `Offline Mode` (Cached data with tactile offline indicator badge)
     7. `Filtered Zero` (Clear search query and 1-click filter reset)
4. **Keyboard Accessibility Contract:**
   - Tab and Shift+Tab must navigate interactive elements in logical visual order.
   - Modals and drawers must close on `Escape`.
   - Global command bar must open on `Cmd+K` or `Ctrl+K`.
   - Focus rings must be prominently visible (`outline-none ring-2 ring-primary`).

---

## Step-by-Step Procedure

### Step 4.1: Draft the Coexisting State Matrix
Define what each major screen zone displays across all operational states:
- Write the matrix into `docs/03-EXPERIENCE.md` under `## 3. Coexisting Component State Matrix`.

### Step 4.2: Build the Prototype
1. Implement `docs/.working/prototypes/prototype-v0.1.html`.
2. Include the state switcher toolbar:
```html
<div class="fixed top-2 right-2 z-50 flex items-center gap-1.5 p-1.5 bg-zinc-900 border border-zinc-700 rounded-lg shadow-xl text-xs font-mono text-zinc-300">
  <span class="px-2 py-0.5 text-zinc-400 font-bold">STATE:</span>
  <button onclick="setState('populated')" class="px-2 py-1 rounded bg-zinc-800 hover:bg-zinc-700">Populated</button>
  <button onclick="setState('loading')" class="px-2 py-1 rounded hover:bg-zinc-700">Loading</button>
  <button onclick="setState('empty')" class="px-2 py-1 rounded hover:bg-zinc-700">Empty</button>
  <button onclick="setState('error')" class="px-2 py-1 rounded hover:bg-zinc-700">Error</button>
  <button onclick="setState('denied')" class="px-2 py-1 rounded hover:bg-zinc-700">Denied</button>
  <button onclick="setState('offline')" class="px-2 py-1 rounded hover:bg-zinc-700">Offline</button>
</div>
```
3. Test realistic data: real file names, realistic Markdown text, boundary strings (e.g. 80-character titles).

### Step 4.3: Verify in Live Browser
1. If browser automation tools are available (e.g. Chrome DevTools MCP):
   - Navigate to the prototype file.
   - Capture desktop (1440x900) and compact viewports.
   - Test state switcher buttons and keyboard hotkeys.
   - Audit color contrast and focus visibility.
2. If running headless or in an isolated terminal:
   - Provide the exact local path and verification checklist so the human architect can open and test in their local browser.

### Step 4.4: Lock Baseline in Spine
- Update `docs/03-EXPERIENCE.md` with links to `docs/.working/prototypes/prototype-v0.1.html`.
- Record milestone lock in `docs/.memlog.md`.
