# 03-EXPERIENCE: Surface Profile, Spatial Topology & Design Tokens

- **Status:** `[Drafting]`
- **Target Surface Profile:** `[Profile C: Web Workspace | Profile A: Simple Website | Profile B: Mobile App | Profile D: CLI/TUI]`
- **Prototypes:** `docs/.cgspec/05-prototype/`

---

## 1. Selected Surface Profile & Spatial Zoning
*(Calibrated from RES-001 and RES-004)*

For **Profile C: Web Workspace**:
- **Zone 1: Top Unified Header:** Breadcrumbs, global search (<kbd>Cmd+K</kbd>), active workspace badge.
- **Zone 2: Left Multi-Root Explorer Rail:** Collapsible tree navigation, folder filters, activity icons.
- **Zone 3: Center Fluid Work Canvas:** Primary reading, writing, editing, or analytical workspace.
- **Zone 4: Right Context Inspector Drawer:** Metadata, action history, AI copilot, or permission toggles.

---

## 2. Design Tokens & Anti-Slop Calibrations
*(Derived from RES-002, RES-003, and RES-004)*

- **Base Canvas:** Deep tonal black (`#09090b` or `#0b0d13`). Zero muddy purple gradients.
- **Card Surface:** `#121316` with 1px hairline border (`border-white/10` or `border-zinc-800`).
- **Typography:**
  - Headings & UI: Crisp Sans (Geist / Inter / system font).
  - Metrics, Timestamps, Hashes, Latencies: Monospace with `tabular-nums` (`font-mono font-variant-numeric: tabular-nums`).
- **Motion Physics:** Damped springs (`cubic-bezier(0.16, 1, 0.3, 1)` for 150ms micro-interactions). Zero disembodied floating blobs.

---

## 3. Required 7-State Matrix
Every screen prototype must implement the interactive state switcher:
1. `Populated` (Default working view with realistic sample data)
2. `Skeleton` (Pulsing loading skeleton matching exact layout geometry)
3. `Empty` (Zero items found, clear call-to-action button)
4. `Error` (Graceful failure card with retry action)
5. `Denied 403` (Crisp permission-denied gate with request access CTA)
6. `Offline` (Network disconnected indicator)
7. `Filtered Zero` (Search query returned 0 matches with clear-filter CTA)
