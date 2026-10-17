# RFC: Re-founding `cgspec-ux` — The Deep Taste & Guided Design Discovery Protocol

> **Status:** Staging / Ideation (Active Working Draft)  
> **Target:** `skills/cgspec-ux/`  
> **First Principle:** In the age of AI coding, generating code is fast and trivial. Real product value lives in **human ergonomics, visual taste, and direct manipulation**. Design cannot be one-shotted. The AI must act as a visual scout, design curator, and ergonomics interrogator over a multi-day discovery dialogue before any component is scaffolded.

---

## 1. The Core Problem: Why Prompt-Based UI Always Fails

Most AI coding systems treat design as a mechanical prompt exercise:
- They impose a static, repetitive layout ("dark mode dashboard with a sidebar and 4 metric cards").
- They treat anti-slop as a checklist of negative constraints (no purple gradients, no emojis).
- They jump straight from entity schemas to frontend code without understanding how human hands touch the screen.

**The Reality:**
Design is fundamentally **abstract, contextual, and situational**:
- An engineering tool needs high-density monospace tables, keyboard shortcuts, and instant terminal feedback.
- A knowledge canvas needs direct-manipulation markdown, split editing, fluid typing typography, and calm daylight focus.
- An infrastructure gateway needs real-time telemetry, clear visual hierarchy, and alert triage.

A single archetype or static template cannot serve all situations.

---

## 2. The 5-Phase Guided Design Discovery Funnel

Rather than generating UI prematurely, the redesigned UX workflow operates as a guided collaborative dialogue between the Human Director and the AI Design Architect:

### Phase 1: Tactile Ergonomics & Direct Manipulation (Post-OOUX)
- Takes the domain nouns from `02-OOUX.md`.
- Interrogates how the human actually touches, edits, and navigates those nouns:
  - *Are you editing markdown in-place with instant inline WYSIWYG (like Notion/Craft), split-screen code + preview (like Obsidian/VSCode), or reading-first with a dedicated edit modal?*
  - *Is the primary interaction mouse-driven, drag-and-drop, keyboard-first with `Cmd+K` command palettes, or spatial node-canvas?*
- **Strict Separation of Structure vs. Cosmetics:** At this stage, colors, themes, and palettes are strictly off-limits. We focus 100% on spatial layout, information architecture, and direct manipulation workflows.
  - *Exception:* If the user expresses an unsolicited visual spark (e.g. "I love this neon orange accent"), immediately capture it to `docs/.memlog.md` with tags `spark,taste` so it is not lost, but keep the main dialogue anchored on ergonomics.

### Phase 2: Proactive Visual Reference Scouting & In-Artifact Media Curation
- The AI does not guess in a vacuum; it acts as a visual scout:
  - Proactively suggests **3 to 5 real-world reference products** across direct competitors and cross-industry analogues (e.g., Notion, Obsidian, Bear, Linear, Raycast, Cloudflare, VS Code).
  - Proactively shares live links, design library anchors (Mobbin, UX Pilot, Curated.design), and renders visual screenshots directly inside Antigravity Artifacts.
  - **Visual & Precise Words on Visuals:** Every visual exemplar is paired with precise anatomical design vocabulary:
    - *"Notice Obsidian's collapsible file tree with sticky header vs Bear's 3-column typographic flow vs Linear's split-view inspection drawer."*

### Phase 3: Motion & Animation Vocabulary Helper (The Gemini Multimodal Bridge)
- Users often have an intuitive visual feel for an animation (e.g. how a drawer slides, how a modal morphs) but lack the CSS/JS technical terminology.
- The AI helps the user name and specify the exact motion physics:
  - Identifies standard animation patterns: FLIP layout transitions, spring physics, accordion drawers, morphing dialogs, staggered fades, inertia scrolling.
  - **Gemini Video Bridge Protocol:** If the user records a screen video or finds a video clip of an interaction they love:
    - The user can upload the video to `gemini.google.com` (leveraging native video reasoning) to extract the exact CSS transition properties, easing curve (`cubic-bezier(...)`), and duration.
    - The user brings that exact specification back to the agent to lock into `docs/03-EXPERIENCE.md`.

### Phase 4: Micro-Step Ergonomic Interview (Non-Overwhelming)
- The AI never dumps 20 design questions at once.
- Uses `ask_question` with structured, concrete options and clear recommendations:
  1. **Primary Workspace Modality:** Direct inline editing vs split raw/preview vs modal drawer?
  2. **Information Density & Rhythm:** Spacious editorial layout vs dense data-dense workstation?
  3. **Navigation Topology:** Collapsible vertical rail, horizontal application bar, or pure command bar?
  4. **Direct Action Ergonomics:** Inline row actions, right-side sliding inspector drawer, or focused full-page view?
- At each step, the AI checks in: *"Does this capture how you want it to feel, or did we miss an edge case?"*

### Phase 5: Multi-Variant Interactive Prototyping & Anti-Slop Enforcement
- Once references and ergonomic decisions are locked into `docs/.memlog.md`:
  - The AI generates 2-3 distinct visual directions as single-file HTML prototypes (with full 7-state switchers).
  - The human tests them interactively in a real browser, clicks buttons, and picks the winning soul.
  - Zero AI Slop is enforced across all variants (no purple glows, no centered bouncy cards, no unstyled default sans, no fake stats).

---

## 3. Pacing Philosophy: Design is Deep, Code is Trivial

- Designing a high-craft product is not a 10-minute prompt. It may take **1, 2, or 5 days of deep collaborative dialogue**, visual reference scouting, and ergonomic prototyping.
- This investment is deeply necessary: once the mental model and interactive prototype are locked, downstream code scaffolding is 100% deterministic and takes mere hours.
