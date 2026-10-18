# 03-EXPERIENCE: Human Experience, Adaptive Spatial Zoning & 7-State Matrix

> **Stage 2 (Experience): UI/UX Architecture, Visual Design Tokens, Screen Lifecycles & Interactive Prototype**

---

## 1. Core Philosophy: Human Experience Precedes Physical Tech (Law 3)

The human experience defines *what* is built and *how* it feels to operate. Physical technical implementation (database schemas, foreign keys, backend languages, ORMs) is strictly forbidden until the spatial zoning, visual tokens, and interactive prototype are verified and approved by the human architect.

---

## 2. Adaptive Spatial Zoning (By Form-Factor Archetype)

Layout zoning is dynamically tailored to the product's primary form factor:

- **Archetype A: Desktop SaaS / Studio (Data-Dense Web):**
  - Zone 1: Shell Navigation & Context (Collapsible sidebar / Top app bar).
  - Zone 2: Command & Jump Lists (Centered command bar, shallow jump triads).
  - Zone 3: Primary Data Workspace (Data grid, master table, stream).
  - Zone 4: Contextual Inspection Drawer (Slide-over, detail pane).

- **Archetype B: Mobile Application (iOS / Android / PWA):**
  - Zone 1: Top App Bar (Title, back navigation, contextual action).
  - Zone 2: Primary Card Stream (Touch targets, vertical card stack).
  - Zone 3: Draggable Bottom Sheet (Contextual details, filters).
  - Zone 4: Bottom Navigation Bar / Floating Action Button.

- **Archetype C: Infinite Canvas / Node Graph (Spatial Tools):**
  - Zone 1: Zoomable Infinite Surface (Nodes, connections, canvas elements).
  - Zone 2: Floating Tool Dock (Creation, selection, wiring modes).
  - Zone 3: Floating HUD (Minimap, zoom controls, coordinate stats).
  - Zone 4: Floating Properties Inspector.

- **Archetype D: Single-Focus Flow / Wizard (Onboarding / Config):**
  - Zone 1: Minimal Brand Anchor & Progress Stepper.
  - Zone 2: Centered Hero Card (Active step, zero distraction).
  - Zone 3: Sticky Bottom Action Bar (Back / Continue / Save Draft).

- **Archetype E: Terminal UI / Developer CLI (TUI):**
  - Zone 1: Top Status Ribbon (Environment, branch, cluster stats).
  - Zone 2: Dual Split-Pane Workspace (Tree on left, active buffer on right).
  - Zone 3: Bottom Command / Hotkey Hint Bar.

---

## 3. Visual Design System Tokens & Anti-Slop Codex

### Forbidden AI Slop Tropes
- No purple-indigo gradients.
- No unstyled generic system fonts (must pair characterful typography with monospace metrics).
- No 3-column circle-icon marketing boxes.
- No centered fluffy cards with floating drop-shadows.
- No emojis used as functional UI icons.
- No missing operational states.

### High-Craft Aesthetic Direction
- Surface elevation layering (`#09090b` canvas -> `#121316` card -> `#18191e` active/hover).
- 1px hairline borders (`rgba(255, 255, 255, 0.08)`).
- Monospace font for tokens, IDs, and metrics (`JetBrains Mono`, `tabular-nums`).
- High information density (compact 36-40px table rows).
- Keyboard shortcuts on primary actions (`<kbd>Ctrl+K</kbd>`, `<kbd>[S]</kbd>`).

---

## 4. Protagonists & Functional Roles (Law 5)

CGSpec eliminates abstract fictional personas in favor of explicit functional roles:

1. **Organization Owner / Enterprise Admin:** Manages tenant policies, budgets, audit trails, and member invitations.
2. **Project Lead / Founding Engineer:** Configures repository mounts, runs councils, and validates vertical slices.
3. **Developer / Key Holder:** Consumes MCP keys, configures local CLI, runs debugging workflows.
4. **AI Agent Session:** Autonomous caller operating under granular permissions (`read | invoke | propose_edit`).

---

## 5. The 7-State Component & View Matrix

Every screen or interactive component must explicitly define and implement all 7 operational states:

1. **Populated (Default):** Standard active state rendering realistic domain data.
2. **Loading Skeleton:** Pulsing structural placeholders matching final geometry.
3. **Empty State:** Diagnostic illustration, clear explanation, and actionable primary CTA.
4. **Error State:** Explicit error code (e.g. `ERR_504`), diagnostic explanation, and retry action.
5. **Denied 403:** Permission explanation and role elevation request mechanism.
6. **Offline / Reconnecting:** Network resilience banner with cached state indication.
7. **Partial / Filtered:** Contextual zero-results helper with filter clear action.

---

## 6. Interactive Milestone Baseline Prototype

Prior to code scaffolding, the design team/agent generates a single-file, zero-build executable HTML prototype in `.cgspec/prototypes/`:
- Fully self-contained (HTML, CSS/Tailwind CDN, minimal vanilla JS).
- Built-in 5/7-state switcher bar at the top.
- Real domain data and interactive controls (search filter, inspection drawer, key generation modal).
- Tested and verified in a live headless/browser viewport.
