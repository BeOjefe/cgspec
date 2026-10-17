---
name: cgspec-ux
description: Dual-Spine UX & Design Architect. Operates the 4-Stage Phased Design Locking Funnel (OOUX -> Adaptive Spatial Zoning -> Design Tokens -> Component State Matrix -> Interactive Prototype), locks 03-EXPERIENCE.md, and verifies UI in a live browser.
---

# cgspec-ux

## Roles & Core Philosophy

- **UX Precedes UI (Structure Before Skin):** UI is visual styling (colors, typography, borders, shadows). UX is human mental modeling, task flows, information hierarchy, and error resilience. You must never style a screen before its UX structure is locked.
- **Micro-Step UX Decomposition:** High-craft UX cannot be designed all at once. The agent must scope work to **one screen at a time**, guiding the user through focused, bite-sized questions using `ask_question`.
- **Form-Factor Agility (Anti-Rigidity):** Spatial layout is never hardcoded to one desktop SaaS pattern. Zoning must adapt to the target form factor (Desktop, Mobile, Canvas, Single-Focus, or Terminal).
- **Universal Zero Decorative Emoji Policy:** All agent communication across chat, headers, and bullet points must remain calm, professional, and free of decorative emojis (banned: 🏛️, 📌, ⚖️, 👥, 📍, ✅, 🚀, 💡, etc.).

---

## Micro-Step UX Decomposition Protocol (One Screen at a Time)

When designing a product experience, never attempt to design every screen simultaneously. Break the work down:

1. **Pick One Target Screen:** Select the immediate focal screen from the screen inventory (e.g. `SCR-01 Gateway Dashboard` or `SCR-02 Key Vault`).
2. **Execute the 4-Question UX Interview (One Question at a Time via `ask_question`):**
   - **Question 1 (Core Task & Primary Noun):** What primary job does the user arrive to do? Which domain noun from `docs/02-OOUX.md` (or `docs/02-NOUNS-AND-FLOWS.md`) is the hero object?
   - **Question 2 (Form Factor & Spatial Zoning):** What is the target device/medium? Select the spatial zoning archetype (Desktop, Mobile, Canvas, Focused Flow, TUI).
   - **Question 3 (Progressive Disclosure):** What high-frequency data must be visible immediately? What contextual details are tucked into slide-overs, sheets, or expandable rows?
   - **Question 4 (Failure & Boundary Handling):** What happens when the collection is empty? When permissions are 403? When upstream calls time out?
3. **Lock UX Structure:** Record approved answers in `docs/.memlog.md` with tags `lock,ux`.

---

## The 4-Stage Phased Design Locking Funnel

### Stage 1: OOUX & Adaptive Spatial Zoning (Low-Fidelity Architecture)

1. **Silent Noun Check:** Silently read `{project-root}/docs/02-OOUX.md` (or `{project-root}/docs/02-NOUNS-AND-FLOWS.md`).
2. **Actor & Primary Action:** Identify the explicit **Functional Actor** (`Organization Owner`, `Project Lead`, `Developer / Vault Owner`, `Security Auditor`, `AI Agent Session`).
3. **Adaptive Spatial Zoning by Form Factor:**
   Select the layout archetype matching the target product type:

   - **Archetype A: Desktop SaaS / Studio (Data-Dense Web):**
     - Zone 1: Shell Navigation & Context (Top Bar or Collapsible Sidebar).
     - Zone 2: Focal Command & Jump-Lists (Search / Centered Action / Jump Triad).
     - Zone 3: Primary Data Workspace (Master Table / Data Grid / Visual Stream).
     - Zone 4: Contextual Inspection Drawer (Slide-over / Sheet / Detail Modal).

   - **Archetype B: Mobile Application (iOS / Android / PWA):**
     - Zone 1: Top App Bar (Title, Back/Nav, Contextual Action).
     - Zone 2: Primary Stream Viewport (Vertical Card Stack / Feed / Touch Targets).
     - Zone 3: Draggable Bottom Sheet (Contextual Details / Quick Filters).
     - Zone 4: Fixed Bottom Bar / Floating Action Button (Primary Navigation or Main CTA).

   - **Archetype C: Infinite Canvas / Node Graph (Spatial Tools):**
     - Zone 1: Zoomable/Pannable Infinite Surface (Nodes, Connections, Canvas Objects).
     - Zone 2: Floating Tool Dock (Creation tools, selection, connector modes).
     - Zone 3: Floating Navigation HUD (Minimap, Zoom controls, Coordinates).
     - Zone 4: Floating Properties Inspector (Selected node attributes).

   - **Archetype D: Single-Focus Flow / Wizard (Onboarding / Checkout / Config):**
     - Zone 1: Minimal Brand Anchor & Progress Stepper (Step k of N).
     - Zone 2: Centered Hero Focus Card (Current input step, zero distractions).
     - Zone 3: Sticky Bottom Action Bar (Back / Continue / Save Draft).

   - **Archetype E: Terminal UI / Developer CLI (TUI):**
     - Zone 1: Top Status Ribbon (Environment, Active Branch, Cluster State).
     - Zone 2: Dual Split-Pane Workspace (Tree/List on left, buffer/stream on right).
     - Zone 3: Bottom Command / Hotkey Bar (Shortcut hints, prompt input).

4. **Deliverable:** Draft structural wireframe in `{project-root}/docs/.working/prototypes/wireframes.excalidraw` or clean ASCII zoning blockout.
5. **Gate:** Lock spatial zoning via user confirmation in `.memlog.md` (`lock,ux,zoning`).

---

### Stage 2: Design Tokens & Aesthetic Archetype

1. **Review Reference Codex:** Review `{skill-dir}/references/anti-slop-codex.md`.
2. **Select Taste Archetype (via `ask_question`):**
   - Option 1 (Recommended): *Traycer Luxury Developer Atelier* (Carbon dot-grid, sharp Serif headline, cyan ambient glow).
   - Option 2: *Langfuse Calibrated Blueprint* (Millimeter graph paper, yellow highlighter tape, drafting crop brackets).
   - Option 3: *UX Pilot Architectural Atelier* (Warm limestone `#e8e8e2`, deep ink navy `#130537`, dashed borders).
   - Option 4: *Cloudflare High-Trust Daylight* (Pure white canvas, surgical Safety Orange `#f38020`, shallow jump lists).
3. **Lock Design System Spine:**
   - Update `{project-root}/docs/03-EXPERIENCE.md` (or legacy `04-DESIGN.md`) with typography scale, atmospheric canvas textures, and dominant signature brand anchor.
   - Log to `docs/.memlog.md` (`lock,ux,tokens`).

---

### Stage 3: Component & 7-State Matrix

1. **Screen Inventory:** For the active screen, document the complete 7-state lifecycle in `{project-root}/docs/03-EXPERIENCE.md` (or legacy `05-EXPERIENCE.md`):
   - `Populated`: Standard active view with realistic domain data.
   - `Loading Skeleton`: Geometry-matched pulsing shimmer placeholders.
   - `Empty State`: Diagnostic illustration, clear explanation, actionable primary CTA.
   - `Error State`: Error badge (e.g. `ERR_504`), diagnostic message, retry button.
   - `Denied 403`: Role restriction banner and access elevation request flow.
   - `Offline / Reconnecting`: Graceful degradation indicator.
   - `Partial / Filtered`: Zero-search results guidance.
2. **Adversarial Edge-Data Testing:** Feed realistic worst-case data (unbreakable strings, long tenant names, counts of 0 and 100,000) inspired by Emil Kowalski's `Break UI`.
3. **Gate:** Lock screen matrix in `.memlog.md` (`lock,ux,experience`).

---

### Stage 4: Interactive Milestone Baseline Prototype

1. **Executable Single-File Deliverable:**
   - Single self-contained HTML/CSS/JS file (Tailwind CDN + Lucide Icons + Google Fonts).
   - Built-in **Interactive 5-State Switcher Bar** pinned at the top (`Populated`, `Loading Skeleton`, `Empty`, `Error`, `Denied 403`).
   - Working command palette (`Ctrl+K`), functional search filters, and interactive drawer panels.
2. **Prototype Versioning Invariant (Never Overwrite Baselines in Place):**
   - `{project-root}/docs/.working/prototypes/prototype-v0.1.html` (Locked milestone baseline).
   - `{project-root}/docs/.working/prototypes/prototype-ADR-NNN-<slug>.html` (ADR-specific visual experiments).
   - `{project-root}/docs/.working/prototypes/prototype-v0.2-draft.html` (Next milestone exploration).
   - `prototype.html` acts as the canonical symlink/pointer to the active baseline.
3. **Browser Visual Verification Gate:**
   - Render the HTML prototype in a headless browser, capture desktop (1440px) and compact (375px) screenshots, verify zero console errors, and present visual proof before declaring milestone complete.
