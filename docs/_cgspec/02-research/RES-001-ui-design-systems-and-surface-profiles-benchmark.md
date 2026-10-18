# RES-001: UI Frameworks, Design Systems & Adaptive Surface Profiles Benchmark

> **CGSpec Technical Spike & Architecture Research Compendium**  
> **Status:** `CONCLUDED (GUIDING STAGE 2 SURFACE PROFILES)`  
> **Author:** Antigravity Architect & BeOjefe Engineering  
> **Date:** October 2026  
> **Target Spines:** [`docs/03-EXPERIENCE.md`](file:///home/ojefe/Documents/Project/cgspec/docs/03-EXPERIENCE.md), [`skills/cgspec-ui-ux/SKILL.md`](file:///home/ojefe/Documents/Project/cgspec/skills/cgspec-ui-ux/SKILL.md)  
> **Related Decisions:** [`ADR-001`](file:///home/ojefe/Documents/Project/cgspec/docs/adr/ADR-001-first-principles-spec-driven-sdlc-architecture.md), [`ADR-004`](file:///home/ojefe/Documents/Project/cgspec/docs/adr/ADR-004-arbitrary-multi-service-topologies-and-virtual-mounting.md)

---

## 1. Problem Statement & Research Objective

In modern multi-agent and human-agent engineering, UI architecture often defaults to either:
1. **Ad-hoc component assembly (AI Vibe-Coding):** LLMs randomly pulling Tailwind utility classes, resulting in unstyled, generic, or fragmented interfaces without cohesive design tokens.
2. **Framework lock-in:** Forcing a single opinionated UI library across all project surfaces regardless of the target platform (e.g. attempting to use mobile-centric Material Design 3 for an enterprise data workspace, or using heavyweight React-only libraries for a simple CLI or lightweight mobile web tool).

The objective of this research spike is to:
- Conduct an exhaustive comparative analysis of the primary design systems and UI framework archetypes (Material Design 3 vs. Apple iOS HIG vs. shadcn/ui vs. Ant Design vs. Mantine vs. IBM Carbon vs. Penpot).
- Map each framework archetype to CGSpec's **4 Canonical Surface Profiles** (`Profile A: Simple Web`, `Profile B: Mobile App`, `Profile C: Web Workspace/SaaS`, `Profile D: CLI/TUI`).
- Provide deterministic evaluation criteria for AI agents operating in **Stage 2 (UI/UX Compilation)** so they select the correct design foundation systematically rather than guessing.

---

## 2. Comprehensive Framework Benchmark Matrix

| System / Framework | Best For | Licensing & Governance | Key Strengths | Critical Weaknesses & Trade-Offs | Bundle & Runtime Overhead |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Material Design 3 (M3 / M3 Expressive)** | Android native apps, Google ecosystem, cross-platform Flutter/Compose | Free, Open Source (Apache 2.0) | Dynamic color extraction (`monet`), expressive physics-based motion tokens, first-class Jetpack Compose & Flutter tooling | Distinctly "Google-esque" visual identity if uncustomized; rounded pill shapes can feel toy-like on enterprise SaaS; high DOM nesting | Heavy on web (M3 Web Components); zero overhead in native Android |
| **Apple iOS HIG / SwiftUI** | Native iPhone, iPad, macOS, watchOS, visionOS | Proprietary developer guidelines; SwiftUI/UIKit bundled with OS | Unmatched tactile fidelity, standard platform native feel, zero runtime friction for iOS users, strict accessible contrast | Closed Apple ecosystem; cannot be run natively on Web or Android without cross-platform shims (e.g. Cupertino in Flutter) | Zero external bundle overhead (built directly into Apple OS runtimes) |
| **shadcn/ui (Radix + Tailwind)** | Modern Next.js, React, Astro SaaS dashboards and web workspaces | MIT (100% Free & Open Source) | **Code ownership model:** components are copied directly into the repo, eliminating upstream npm version lock-in; unstyled accessible Radix primitives + Tailwind styling; extreme token flexibility | You own and maintain the component code; requires Tailwind build pipeline; React-ecosystem centric (though ported to Svelte/Vue) | Extremely lightweight (tree-shaken Radix primitives + compiled utility CSS) |
| **Ant Design (antd)** | Enterprise back-offices, heavy data tables, complex operational tools | MIT (Alibaba Open Source) | Massive out-of-the-box component inventory (data tables with pivot sorting, nested tree-selects, complex form builders); enterprise i18n | Rigid opinionated visual style (feels corporate/bureaucratic); heavy CSS-in-JS bundle footprint; difficult to radically re-theme | Heavy (~1.2MB uncompressed; noticeable cold-start latency) |
| **Mantine / Chakra UI** | Rapid SaaS MVPs, developer-first React applications | MIT (Free & Open Source) | Superb DX, rich hooks library (`@mantine/hooks`), built-in dark mode and focus management without extra boilerplate | Slower adoption outside React; tight coupling to runtime theme providers | Moderate (~150KB–300KB runtime bundle) |
| **IBM Carbon Design System** | Data-dense scientific tools, multi-tenant enterprise telemetry, analytics | Apache 2.0 (IBM Open Source) | Industry-leading data visualization color palettes, strict WCAG AAA compliance, robust grid systems for high data density | Steep learning curve; rigid visual grammar; challenging for rapid prototypes | Moderate to heavy (enterprise-grade modular packages) |
| **Shopify Polaris** | E-commerce merchant tools, operational workflows, inventory admin | MIT (Shopify Open Source) | Hyper-optimized for operational clarity, merchant workflows, and high-trust transaction interfaces | Highly tailored to merchant metaphors; less suitable for consumer social or developer tooling | Moderate |
| **Penpot (Open-Source Design Platform)** | Collaborative open-source UI design, design token handoff | AGPLv3 (Free, Open Source, Self-Hostable) | Native SVG/CSS engine (not proprietary vectors like Figma); standards-based design tokens; team self-hosting without cloud lock-in | Smaller plugin and UI kit ecosystem compared to Figma Community | Web application (browser-based) |

---

## 3. Mapping Frameworks to CGSpec's 4 Adaptive Surface Profiles

CGSpec's Law 10 requires every project to declare its primary **Surface Profile** in `docs/03-EXPERIENCE.md`. Autonomous AI agents must select their UI implementation adapter according to this exact mapping:

### Profile A: Simple Public Website / Marketing Landing Pages
- **Target Experience:** Fast load times, high visual impact, SEO optimization, smooth storytelling animations.
- **Recommended Architecture:**
  - **Utility-First + Tailwind:** Tailwind CSS with lightweight headless components (DaisyUI, Flowbite, or custom semantic HTML).
  - **Headless UI Primitives:** Radix UI or Headless UI for accessible modals, dialogs, and mobile disclosure menus.
  - **Anti-Pattern to Avoid:** Do NOT pull heavy enterprise suites like Ant Design or Carbon into a landing page.

### Profile B: Mobile Native Applications (iOS & Android)
- **Target Experience:** 120Hz gesture response, platform ergonomics, system navigation gestures, tactile haptics.
- **Recommended Architecture:**
  - **Native iOS:** Apple Human Interface Guidelines via SwiftUI / UIKit.
  - **Native Android:** Material Design 3 via Jetpack Compose.
  - **Cross-Platform:** Flutter (rendering native Cupertino or Material 3 components) or React Native paired with **Tamagui** / **NativeWind** (Tailwind for mobile).
  - **Anti-Pattern to Avoid:** Avoid webviews with fake iOS/Material CSS headers that fail to respect native gesture navigation, safe areas, and dynamic island cutouts.

### Profile C: Web Workspaces, SaaS Dashboards & Complex Developer Consoles
- **Target Experience:** High information density, multi-pane spatial zoning, resizable columns, keyboard shortcuts (`Ctrl+K`), rich table filters.
- **Recommended Architecture:**
  - **The Modern Standard:** **`shadcn/ui` (Radix Primitives + Tailwind CSS)**.
    - *Why:* You own the code in `src/components/ui/`. No third-party package breaking changes. Unstyled primitives guarantee complete accessibility (WAI-ARIA compliance) while allowing full custom styling (e.g. Zinc tonal elevations, 1px hairlines).
  - **High-Density Enterprise Alternative:** **IBM Carbon** or **Ant Design** (only when pre-built multi-column virtualized data tables, pivot grids, and complex tree selectors are mandatory and engineering resources are constrained).
  - **Anti-Pattern to Avoid:** Generic Material Design 3 on desktop SaaS dashboards (results in excessive padding, large touch targets on desktop mouse viewports, and inefficient information density).

### Profile D: CLI / TUI Developer Tools
- **Target Experience:** Zero latency, terminal ergonomics, ANSI color compatibility, non-blocking asynchronous event loops.
- **Recommended Architecture:**
  - **Go:** Bubbletea (Charmbracelet) or Lip Gloss.
  - **Python:** Rich / Textual.
  - **Node.js / Rust:** Ink (React in terminal) or Ratatui (Rust).

---

## 4. Figma Community Kits & Open-Source Asset Workflows

When drafting Stage 2 design tokens and visual prototypes:
1. **Figma Community Libraries:** Official, free UI kits exist for Material 3, iOS 18 HIG, shadcn/ui, Ant Design, and Carbon.
2. **Penpot Integration:** For teams committed to 100% open-source pipelines without proprietary cloud dependencies, Penpot allows direct CSS Grid and Flexbox alignment, generating live CSS properties directly readable by CGSpec AST tools (`visual_audit.py`).

---

## 5. Architectural Verdict & Handoff to CGSpec Spines

1. **For CGSpec Prototypes (`.cgspec/prototypes/`):**
   - Standardize on **Tailwind CSS + Pure Inline SVG + Vanilla JS** for single-file, zero-build prototypes.
   - Enforce **shadcn/ui design tokens** (Zinc/Slate scales, 1px hairlines `border-zinc-200` / `border-white/10`, monospace `JetBrains Mono` for tabular data).
2. **For Production Production Slices (`docs/slices/SLICE-NNN.md`):**
   - If Web Workspace/SaaS: Recommend `shadcn/ui` (Radix + Tailwind).
   - If Mobile: Recommend SwiftUI for iOS, Jetpack Compose for Android.
   - If Multi-Platform: Recommend Flutter or React Native + NativeWind.
3. **Registry Status:** Recorded as `RES-001` in `docs/00-INDEX.md`. Future ADRs on UI stacks must cite this research record.

---

## 6. Primary References, Benchmark Sources & Citations

1. **Figma Community UI Kits & Design Token Libraries:**
   - [Figma Community UI Kits Index](https://www.figma.com/community/ui-kits)
   - [Figma Design System Examples & Case Studies](https://www.figma.com/resource-library/design-system-examples/)
   - [UI Things: Curated Free Figma UI Kits](https://uithings.com/free-figma-ui-kits)
2. **Platform-Native Titan Guidelines:**
   - [Google Material Design 3 (M3 / Expressive Motion Guidelines)](https://m3.material.io/)
   - [Apple Human Interface Guidelines (HIG / SwiftUI Architecture)](https://developer.apple.com/design/human-interface-guidelines/)
3. **Open-Source Web & Enterprise Framework Comparisons:**
   - [Reddit Frontend Architecture: UI Frameworks Beyond MUI (Community Benchmark)](https://www.reddit.com/r/Frontend/comments/vr3ino/what_ui_frameworks_other_than_mui_would_you/)
   - [ThemeWagon: Comparing Best Open-Source UI Component Libraries](https://themewagon.com/blog/comparing-best-open-source-ui-libraries/)
   - [GreatFrontend: Top Open-Source Design Systems by Leading Tech Companies](https://www.greatfrontend.com/blog/top-open-source-design-systems-by-tech-companies-you-can-use-right-away)
4. **Mobile & Cross-Platform Framework Performance:**
   - [Purchasely Mobile Engineering: Native vs Cross-Platform UI Benchmark](https://www.purchasely.com/blog/mobile-app-frameworks)
5. **Open-Source Collaborative Design Alternatives:**
   - [Penpot Open-Source Standards-Based Design Platform](https://penpot.app/)

