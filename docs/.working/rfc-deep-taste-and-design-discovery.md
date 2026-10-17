# RFC: Re-founding `cgspec-ux` — The Deep Taste & Guided Design Discovery Protocol

> **Status:** Staging / Ideation (Draft)  
> **Target:** `skills/cgspec-ux/`  
> **Principle:** Design is abstract, contextual, and taste-driven. Autonomous models cannot substitute for human visual intent. The AI must act as a master design mentor, visual curator, and ergonomics interrogator before generating any UI.

---

## 1. The Core Problem: Why Static Design Prompts Fail

Most AI coding systems treat design as a mechanical prompt exercise:
- They impose a static layout ("dark mode dashboard with a sidebar and 4 metric cards").
- They treat anti-slop as a checklist of negative constraints (no purple gradients, no emojis).
- They jump straight from entity schemas to frontend components.

**The Reality:**
Design is fundamentally **abstract, contextual, and situational**:
- An engineering tool needs high-density monospace tables, keyboard shortcuts, and instant terminal feedback.
- A knowledge canvas needs direct-manipulation markdown, split editing, fluid typing typography, and calm daylight focus.
- A gateway monitor needs real-time telemetry, clear visual hierarchy, and alert triage.

A single archetype or static template cannot serve all situations.

---

## 2. The 4-Phase Guided Discovery Funnel

Rather than generating UI prematurely, the redesigned UX workflow operates as a guided collaborative dialogue between the Human Director and the AI Design Architect:

### Phase A: Ergonomic Intent & Direct Manipulation (Post-OOUX)
- Takes the domain nouns from `02-OOUX.md`.
- Interrogates how the human actually touches and manipulates those nouns:
  - *Are you editing markdown in-place with instant inline WYSIWYG (like Notion/Craft), split-screen code + preview (like Obsidian/VSCode), or reading-first with a dedicated edit modal?*
  - *Is the primary interaction mouse-driven, drag-and-drop, keyboard-first with `Cmd+K` command palettes, or spatial node-canvas?*
- Translates abstract data objects into tactile interaction verbs.

### Phase B: Curated Visual Reference Hunting & External Cross-Pollination
- The AI does not guess in a vacuum; it acts as a design scout:
  - Suggests **3 to 5 real-world reference products** across both direct competitors and cross-industry analogues (e.g. for a document editor: Google Docs, Notion, Bear, Ulysses; for an infrastructure dashboard: Cloudflare, Tailscale, Datadog; for developer tools: Linear, Raycast, GitHub).
  - Guides the user to examine live examples, share screenshots, or inspect visual patterns (e.g., Mobbin, UX Pilot, Curated.design).
  - Prompts the user: *"Look at how Linear handles split navigation vs how Cloudflare does shallow jump-lists. Which pacing feels right for your product?"*

### Phase C: Micro-Step Ergonomic Interview (Non-Overwhelming)
- The AI never dumps 20 design questions at once.
- Uses `ask_question` with structured, concrete options and clear recommendations:
  1. **Visual Atmosphere & Canvas Tone:** Luminous Daylight, Technical Blueprint, Atmospheric Obsidian Atelier, or Warm Architectural Bone?
  2. **Information Density & Rhythm:** Spacious editorial layout vs dense data-dense workstation?
  3. **Navigation Topology:** Collapsible vertical rail, horizontal application bar, or pure command bar?
  4. **Direct Action Ergonomics:** Inline row actions, right-side sliding inspector drawer, or focused full-page view?

### Phase D: Multi-Variant Aesthetic Prototyping & Anti-Slop Enforcement
- Once references and ergonomic decisions are locked into `docs/.memlog.md`:
  - The AI generates 2-3 distinct visual directions as single-file HTML prototypes (with full 7-state switchers).
  - The human tests them interactively in a real browser, clicks buttons, and picks the winning soul.
  - Zero AI Slop is enforced across all variants (no purple glows, no centered bouncy cards, no unstyled default sans, no fake stats).
