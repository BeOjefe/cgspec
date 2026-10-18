# Interactive HTML Prototypes & Wireframes (`docs/prototypes/`)

This directory contains standalone, zero-build, interactive HTML prototypes and wireframes developed during **Stage 2 (Spatial UI & Experience Design)**.

---

## 1. Zero-Build Architecture
Prototypes in this directory are 100% self-contained single-file HTML documents. They run directly in any web browser without requiring a Node.js build step, bundler, or local server.
- Uses Tailwind CSS CDN for tactical design tokens.
- Uses SVG / Lucide Icons via script or inline geometric SVGs.
- Uses minimal vanilla JavaScript for interaction, state switching, and mock data filtering.

---

## 2. 7-State Matrix Requirement
Every prototype must provide an interactive State Switcher bar (at the top of the viewport) demonstrating all required lifecycle states:
1. `Populated` (Default happy path)
2. `Empty` (Zero items, informative onboarding CTA)
3. `Loading` (Tactile skeleton loaders matching layout)
4. `Error` (Graceful retry trigger and diagnostic context)
5. `Partial` (Degraded connectivity or truncated data stream)
6. `Denied` (403 forbidden state with remediation path)
7. `Stale` (Expired cache or sync warning badge)

---

## 3. Anti-AI-Slop Deterministic Gate
Before being accepted into milestone delivery, prototypes must pass the deterministic anti-slop gate (`visual_audit.py` exit code `0`).
