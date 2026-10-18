# Playbook 04: Model States & Build Evaluated Milestone Prototype

## Purpose
Guide Phase 5 of the Experience Cycle: modeling the required lifecycle states for the active **Surface Profile** (`Profile A..D` in [`SKILL.md`](../SKILL.md)), building the zero-build single-file HTML prototype (`docs/.cgspec/05-prototype/prototype-v0.1.html`), and verifying it via `visual_audit.py` + headless browser screenshots.

---

## Step-by-Step Procedure

### Step 4.1: Draft the Proportional State Matrix (`docs/03-EXPERIENCE.md`)
Model the required states from [`SKILL.md` Section 2.1](../SKILL.md) at both screen and component level (never force database auth/offline states onto a static Profile A website).

### Step 4.2: Build `prototype-v0.1.html` (Dual-Target Save)
Write a self-contained single-file HTML prototype (Tailwind CSS + geometric SVG icons, zero build step) to both `<appDataDir>/brain/<conversation-id>/prototype-v0.1.html` (`UserFacing: true`) and `docs/.cgspec/05-prototype/prototype-v0.1.html`, including a compact top-right state switcher matching the active Surface Profile:

#### Profile A (Simple / Narrative Website — 4 States):
```html
<div class="fixed top-2 right-2 z-50 flex items-center gap-1.5 p-1.5 bg-zinc-900 border border-zinc-700 rounded-lg text-xs font-mono text-zinc-300">
  <button onclick="setViewport('desktop')" class="px-2 py-1 rounded bg-zinc-800">Desktop (1440px)</button>
  <button onclick="setViewport('mobile')" class="px-2 py-1 rounded hover:bg-zinc-700">Mobile (375px)</button>
  <button onclick="setState('interactive')" class="px-2 py-1 rounded hover:bg-zinc-700">Hover/Expanded</button>
  <button onclick="setState('submitted')" class="px-2 py-1 rounded hover:bg-zinc-700">Form Validation</button>
</div>
```

#### Profile B (Mobile App iOS / Android — 7 States):
```html
<div class="fixed top-2 right-2 z-50 flex flex-wrap items-center gap-1.5 p-1.5 bg-zinc-900 border border-zinc-700 rounded-lg text-xs font-mono text-zinc-300">
  <button onclick="setState('populated')" class="px-2 py-1 rounded bg-zinc-800">Populated</button>
  <button onclick="setState('sheet-half')" class="px-2 py-1 rounded hover:bg-zinc-700">Sheet (Half)</button>
  <button onclick="setState('keyboard-up')" class="px-2 py-1 rounded hover:bg-zinc-700">Keyboard Up</button>
  <button onclick="setState('loading')" class="px-2 py-1 rounded hover:bg-zinc-700">Skeleton</button>
  <button onclick="setState('empty')" class="px-2 py-1 rounded hover:bg-zinc-700">Empty</button>
  <button onclick="setState('permission')" class="px-2 py-1 rounded hover:bg-zinc-700">OS Permission</button>
  <button onclick="setState('offline')" class="px-2 py-1 rounded hover:bg-zinc-700">Offline</button>
</div>
```

#### Profile C (Web / Desktop Workspace — 7 States + Role Simulator):
```html
<div class="fixed top-2 right-2 z-50 flex items-center gap-1.5 p-1.5 bg-zinc-900 border border-zinc-700 rounded-lg text-xs font-mono text-zinc-300">
  <button onclick="setState('populated')" class="px-2 py-1 rounded bg-zinc-800">Populated</button>
  <button onclick="setState('loading')" class="px-2 py-1 rounded hover:bg-zinc-700">Skeleton</button>
  <button onclick="setState('empty')" class="px-2 py-1 rounded hover:bg-zinc-700">Empty</button>
  <button onclick="setState('error')" class="px-2 py-1 rounded hover:bg-zinc-700">Error</button>
  <button onclick="setState('denied')" class="px-2 py-1 rounded hover:bg-zinc-700">Denied 403</button>
  <button onclick="setState('offline')" class="px-2 py-1 rounded hover:bg-zinc-700">Offline</button>
</div>
```

### Step 4.3: Run Closed-Loop Visual Audit & Lock Baseline
1. Run `python3 docs/.cgspec/01-script/visual_audit.py docs/.cgspec/05-prototype/prototype-v0.1.html --screenshot-dir /tmp/cgspec-shots`.
2. Inspect captured desktop (`1440x900`) and compact (`375x812`) screenshots via `view_file` against [`references/quality-rubric.md`](../references/quality-rubric.md).
3. Update `docs/03-EXPERIENCE.md` and `docs/.memlog.md` once the user approves the prototype.
