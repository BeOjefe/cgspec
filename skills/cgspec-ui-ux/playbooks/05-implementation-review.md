# Playbook 05: Implementation Review & Fidelity Audit

## Purpose
Guide the human architect and AI agent through the final verification stage of the Experience Cycle: auditing the implemented production frontend against the approved prototype (`docs/.cgspec/05-prototype/prototype-v0.1.html`) and the specification in `docs/03-EXPERIENCE.md`.

---

## Operating Invariants

1. **Verify Against the Spec, Not Memory:**
   - Always compare the live production code or UI build directly against the approved prototype and `docs/03-EXPERIENCE.md`.
2. **Audit Beyond the Happy Path:**
   - Production bugs frequently lurk in non-happy states: missing loading skeletons, unhandled network disconnects, awkward word-wrapping on long names.
   - Test all 7 operational states in the live implementation.
3. **Ergonomic & Performance Audit:**
   - Measure keyboard flow: Can a user complete the core loop without touching the mouse?
   - Check layout stability: Does the UI jump vertically when entering edit mode or when data loads?
4. **Structured Deviation Logging:**
   - Any visual or functional regression must be classified and logged:
     - **Critical Fidelity Deviation:** Broken state, missing focus ring, layout shift, or inaccessible control (must fix before slice closes).
     - **Cosmetic Calibration:** Minor spacing or color variation (can be polished or accepted).
5. **Disk Update:**
   - Record audit results in `docs/design/reviews/` or append an audit note to `docs/.memlog.md`.

---

## Step-by-Step Procedure

### Step 5.1: Visual & Spatial Alignment Check
1. Open the running production frontend and the approved prototype side-by-side.
2. Verify zone dimensions:
   - Header height matches approved spec.
   - Rails and drawers collapse and expand cleanly.
   - Text does not wrap awkwardly across common screen sizes.

### Step 5.2: State Matrix Audit
Verify each component's behavior:
- [ ] Populated state displays realistic density and proper font hierarchy.
- [ ] Loading skeleton animates without layout jumping.
- [ ] Empty state provides an actionable trigger (not a dead end).
- [ ] Error state provides a human explanation and retry button.
- [ ] 403 / Denied state clearly explains permission boundaries.
- [ ] Offline indicator informs the user without blocking local read access.

### Step 5.3: Keyboard & Interaction Walkthrough
- [ ] `Tab` moves focus sequentially through interactive controls.
- [ ] Active element has a visible, high-contrast focus indicator.
- [ ] `Escape` dismisses drawers, modals, and open dropdowns.
- [ ] Primary shortcut (`Cmd+K` or designated action) fires reliably.

### Step 5.4: Sign-Off or Remediation
- If deviations exist, create remediation tasks for the active slice in `docs/05-DELIVERY.md`.
- Once verified, mark Tier 2 Design validation complete in `docs/00-INDEX.md` and log to `docs/.memlog.md`.
