# The Anti-Slop Frontend & UX Codex (Design-Taste Invariants)
> Derived from Garry Tan's `gstack`, `bmad-ux`, Anthropic Frontend Aesthetics Guardrails, and `tasteskill.dev`.

---

## 1. The 10 Forbidden "AI Slop" Tropes (Strict Negative Constraints)

When left unguided, AI models converge toward statistical averages ("AI Slop"). The following patterns are strictly forbidden:

1. **No Purple/Indigo Gradient Blobs:** Never use `#6366f1` / `#8b5cf6` radial gradients, blurred background spheres, or rainbow mesh hero glow.
2. **No Default Generic Sans-Serif:** Never use unstyled `Inter`, `Arial`, or system-ui fallback without intentional character or curated display/monospace pairings.
3. **No Symmetrical 3-Column Feature Grids:** Never generate the cliché 3 cards in a row with an icon centered in a colored circle + bold heading + two lines of generic text.
4. **No Centered Everything:** Avoid lazy `text-center` across headers, body paragraphs, and cards. Align with purposeful asymmetry, strong left-aligned gutters, and structural grids.
5. **No Toy-Like Bubbly Radii:** Professional software does not use `rounded-2xl` or `rounded-3xl` (16px–24px) on compact cards or buttons. Use precise `rounded-md` (6px) or `rounded-lg` (8px), or crisp sharp borders (`rounded-none` / `rounded-sm`).
6. **No Low-Density Fluffy Padding:** Never pad containers with `p-10` or `p-12` when displaying only 3 words of content. Optimize for high information density, clear visual rhythm, and scannability.
7. **No Vague Buzzword Marketing Jargon:** Never use placeholder phrases like *"Unlock the power of AI"*, *"Revolutionize your workflow"*, or *"Seamlessly integrate everything"*. Use explicit domain terminology, actual technical metrics, and precise functional verbs.
8. **No Emojis as UI Icons:** Never use emojis (🚀, 💡, 🔥, ✨) as structural icons in navigation, buttons, or card headers. Use clean, geometric SVG primitives (e.g. Lucide Icons).
9. **No Missing UI Edge States:** Every screen must support the full 7-state lifecycle: `Loading Skeleton`, `Empty State`, `Error Banner`, `Populated View`, `Partial / Filtered`, `Offline Mode`, and `Denied 403`.
10. **No Blurry Disembodied Drop Shadows:** Avoid heavy `shadow-2xl` floating cards without physical grounding. Prioritize 1px hairline borders (`border-white/10` or `border-zinc-800`) over blurry blur-radius shadows.

---

## 2. The 8 High-Craft Invariants (Strict Positive Standards)

1. **Surface Elevation & Tonal Depth:**
   - In Dark Mode: Canvas `#09090b` $\to$ Panel `#111215` $\to$ Card `#18191e` $\to$ Hover `#22242b`, bound by 1px hairline borders (`border-white/10` or `border-zinc-800`).
   - In Light Mode: Canvas `#f8f9fa` $\to$ Panel `#ffffff` $\to$ Subtle divider `#e4e4e7` $\to$ Dark text `#09090b`.
2. **Characterful Typography Hierarchy:**
   - Pair an expressive display/grotesque font (e.g. *Geist*, *Plus Jakarta Sans*, *Syne*, *Fraunces*) with high-legibility body type.
   - Use dedicated monospace fonts (*JetBrains Mono*, *Geist Mono*, *Fira Code*) for all metrics, IDs, hashes, ports, tokens, and technical labels.
   - Enforce `tabular-nums` on all numbers, latencies, dates, and currency values to prevent layout jitter.
3. **High Information Density & Keyboard First:**
   - Integrate keyboard shortcut indicators (`<kbd class="px-1.5 py-0.5 text-[10px] font-mono bg-zinc-800 border border-zinc-700 rounded">⌘K</kbd>`).
   - Maintain dense table row heights (36px–40px) with explicit column widths, hover elevation, and sticky table headers.
4. **Authentic Domain Data & Functional Metrics:**
   - Always populate prototypes with realistic data: realistic usernames, ISO timestamps (`2026-10-16 14:22:01 UTC`), status badges (`Active`, `Degraded`, `Syncing`), and real units (`24ms`, `99.98%`, `1.4 GB/s`).
5. **Asymmetry & Intentional Composition:**
   - Use master-detail split views, collapsable contextual sidebars, and tabbed inspection sheets rather than uniform repeating tiles.
6. **Built-In 7-State Switcher Toolbar:**
   - Every prototype must feature a compact state switcher bar (e.g. floating pill or top banner) allowing immediate toggling between:
     - `Populated View` (Default)
     - `Loading Skeletons`
     - `Empty State` (with actionable CTA)
     - `Error / Failed State` (with retry button and error code)
     - `Denied / 403 Forbidden` (with permission request trigger)
7. **Semantic Status Tokens:**
   - `Success / Healthy`: Emerald (`text-emerald-400 bg-emerald-500/10 border-emerald-500/20`)
   - `Warning / Degraded`: Amber (`text-amber-400 bg-amber-500/10 border-amber-500/20`)
   - `Critical / Error`: Rose (`text-rose-400 bg-rose-500/10 border-rose-500/20`)
   - `Neutral / Idle`: Zinc (`text-zinc-400 bg-zinc-800 border-zinc-700`)
8. **Zero Build Dependency Portable HTML:**
   - Prototypes in `docs/.working/prototypes/` must be 100% self-contained single HTML files runnable directly in any browser without requiring `npm install` or bundlers (using Tailwind CDN + Lucide Icons script).

---

## 3. The 4 Breakthrough Taste Archetypes (Beyond the Dark Dashboard Trap)

1. **The "Traycer Luxury Developer Atelier" (Dark Luxury & Cybernetic Precision):**
   - Canvas: Dark `#0a0b0e` with a tactile carbon dot-grid texture (`background-image: radial-gradient(rgba(255, 255, 255, 0.08) 1px, transparent 1px); background-size: 20px 20px;`).
   - Typographic Juxtaposition: Sharp literary Serif display headline (*Newsreader*, *Fraunces*, *Instrument Serif*) paired with neutral sans body and *JetBrains Mono* metrics.
   - Accents: Ethereal cyan/teal ambient backlight (`rgba(6, 182, 212, 0.15)` blurred at `60px`).
   - Hero: Realistic multi-pane IDE / terminal viewport.

2. **The "Langfuse Calibrated Blueprint" (Precision Engineering Lab):**
   - Canvas: Millimeter graph paper drafting grid (`background-image: linear-gradient(to right, rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.04) 1px, transparent 1px); background-size: 24px 24px;`).
   - Signature Accent: Fluorescent highlighter tape marker blocks (`#facc15` / `#ffff55` with black text) behind key terms.
   - Drafting Geometry: Corner crop brackets `[ ┌ ... ┐ ]` around hero panels.
   - Hardware Keycaps: Embedded shortcut keycaps inside buttons (`Start free [S]`, `Documentation [D]`).

3. **The "UX Pilot Architectural Atelier" (Tactile Brutalist Draftsman):**
   - Canvas: Warm tactile limestone/bone surface (`#e8e8e2`) paired with deep ink-navy typography (`#130537`).
   - Typographic Authority: Architectural all-caps grotesque (*Everett*, *Syne*, *Cabinet Grotesk*) with ink traps.
   - Drafting Details: Dashed blueprint dividers (`border-dashed border-[#130537]`) and coordinate registration pills (`(-1)`, `(0)`, `(1)`).
   - Pigment Framing: Soft pastel architectural framing mats (lavender `#BCB3F2`, putty `#DDDBCD`, sage `#CDDCDD`).

4. **The "Cloudflare High-Trust Daylight Infrastructure" (Luminous Institutional Grade):**
   - Canvas: Crisp daylight confidence (`#ffffff` canvas, `#f9fafb` sidebar, `#f3f4f6` hover).
   - Brand Anchor: Surgical Safety Orange (`#f38020`) as a bold focal mark.
   - Anti-4-Box Navigation: Replace generic 4-box metric strips with the "Shallow Jump-List Triad" (`Domains >`, `Workers >`, `Recents >`).

