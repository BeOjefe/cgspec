# Playbook 04: Model States & Build Evaluated Milestone Prototype

## Purpose
Guide the human architect and AI agent through Phase 4 and Phase 5 of the Experience Cycle: modeling proportional component states, building a single-file interactive HTML prototype (`prototype-v0.1.html`), and verifying the experience in a live browser across the project's target surface profile (Simple Website, Mobile iOS/Android, or Web/Desktop App).

---

## Operating Invariants

1. **Coexisting & Proportional States (Never Force Fake States on Simple Websites):**
   - Match the state matrix strictly to the **Surface Profile**:
     - **Profile A — Simple / Narrative Website (Landing page, portfolio, blog):** Model the **4 Narrative & Viewport States**: `Desktop Wide`, `Mobile Stack (375px)`, `Interactive Hover / Accordion Expanded`, and `Form Validation / Submitted` (if forms exist). Never force database states like `Denied 403` or `Offline` onto a static site.
     - **Profile B — Mobile App (iOS / Android):** Render inside an interactive mobile device frame (`390x844` iOS or `412x915` Android) and model the **7 Mobile States**: `Populated`, `Loading Skeleton`, `Empty`, `Error/Retry`, `OS Permission Prompt`, `Offline/Cached`, and **`Keyboard Up (Bottom 40% Occluded)`** (plus draggable bottom sheet detents: `Peek`, `Half`, `Full`).
     - **Profile C — Web / Desktop Workspace (SaaS, dashboard, editor):** Model the **7 Coexisting Operational States** at both screen and component level: `Populated`, `Loading Skeleton`, `Empty`, `Error`, `Denied 403`, `Offline`, and `Filtered Zero`.
2. **Single-File Zero-Build Deliverable:**
   - The milestone prototype must be a self-contained, zero-build HTML file placed in `docs/.cgspec/prototypes/prototype-v0.1.html`.
   - Use standard CDN links for utility CSS (Tailwind CSS) and geometric SVG icons (Lucide).
   - Require zero build step (`npm run dev` or Xcode/Gradle compilation) so the human architect can open and test the prototype instantaneously in any browser.
3. **Keyboard & Touch Ergonomics Contract:**
   - *Web / Desktop:* `Tab` / `Shift+Tab` sequential focus, `Escape` closes drawers/modals, `Cmd+K` / `Ctrl+K` command bar, visible focus rings.
   - *Mobile (iOS / Android):* Minimum `44x44pt` (iOS HIG) or `48x48dp` (Android M3) touch targets, primary actions anchored in the bottom thumb zone, zero hover-only interactions, and keyboard-avoiding scroll padding.

---

## Step-by-Step Procedure

### Step 4.1: Draft the Proportional State Matrix
Define what each major zone or section displays across the active Surface Profile's states:
- Write the matrix into `docs/03-EXPERIENCE.md` under `## 3. Coexisting Component State Matrix`.

### Step 4.2: Build the Prototype (`docs/.cgspec/prototypes/prototype-v0.1.html`)
Include a compact floating switcher toolbar at the top right tailored to the active Surface Profile:

#### For Profile A (Simple / Narrative Website):
```html
<div class="fixed top-2 right-2 z-50 flex items-center gap-1.5 p-1.5 bg-zinc-900 border border-zinc-700 rounded-lg shadow-xl text-xs font-mono text-zinc-300">
  <span class="px-2 py-0.5 text-zinc-400 font-bold">VIEW:</span>
  <button onclick="setViewport('desktop')" class="px-2 py-1 rounded bg-zinc-800">Desktop (1440px)</button>
  <button onclick="setViewport('mobile')" class="px-2 py-1 rounded hover:bg-zinc-700">Mobile (375px)</button>
  <button onclick="setState('interactive')" class="px-2 py-1 rounded hover:bg-zinc-700">Interactive Demo</button>
  <button onclick="setState('submitted')" class="px-2 py-1 rounded hover:bg-zinc-700">Form Submitted</button>
</div>
```

#### For Profile B (Mobile App — iOS / Android):
```html
<div class="fixed top-2 right-2 z-50 flex flex-wrap items-center gap-1.5 p-1.5 bg-zinc-900 border border-zinc-700 rounded-lg shadow-xl text-xs font-mono text-zinc-300">
  <span class="px-2 py-0.5 text-zinc-400 font-bold">MOBILE STATE:</span>
  <button onclick="setState('populated')" class="px-2 py-1 rounded bg-zinc-800">Populated</button>
  <button onclick="setState('sheet-half')" class="px-2 py-1 rounded hover:bg-zinc-700">Sheet (Half)</button>
  <button onclick="setState('keyboard-up')" class="px-2 py-1 rounded hover:bg-zinc-700">Keyboard Up</button>
  <button onclick="setState('loading')" class="px-2 py-1 rounded hover:bg-zinc-700">Loading</button>
  <button onclick="setState('empty')" class="px-2 py-1 rounded hover:bg-zinc-700">Empty</button>
  <button onclick="setState('permission')" class="px-2 py-1 rounded hover:bg-zinc-700">OS Permission</button>
  <button onclick="setState('offline')" class="px-2 py-1 rounded hover:bg-zinc-700">Offline</button>
</div>
```

#### For Profile C (Web / Desktop Workspace):
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

### Step 4.3: Verify in Live Browser
1. If browser automation tools are available (e.g. Chrome DevTools MCP):
   - Navigate to the prototype file and verify desktop (`1440x900`) and mobile (`390x844`) viewports.
   - Test state switcher buttons, keyboard traversal, or simulated mobile sheet/keyboard occlusion.
2. If running headless or in an isolated terminal:
   - Provide the exact local path and verification checklist so the human architect can open and test in their local browser.

### Step 4.4: Lock Baseline in Spine
- Update `docs/03-EXPERIENCE.md` with links to `docs/.cgspec/prototypes/prototype-v0.1.html`.
- Record milestone lock in `docs/.memlog.md`.
