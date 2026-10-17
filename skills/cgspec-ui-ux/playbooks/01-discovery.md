# Playbook 01: Ingest Locked Intent & Select the Focal Screen

## Purpose
Guide the human architect and AI agent through Phase 1 of the Experience Cycle: ingesting the locked Stage 1 Intent (`01-INTENT.md`) and ORCA domain nouns (`02-OOUX.md`), selecting the primary journey slice / focal screen, and establishing the tactile design brief without re-interviewing the user from scratch.

---

## Operating Invariants

1. **Ingest, Never Re-Interview:**
   - The user already defined their persona, core problem statement, anti-goals, and Day-in-the-Life walkthrough in `docs/01-INTENT.md`, and the domain objects/relationships in `docs/02-OOUX.md`.
   - Never force the user to re-explain their project from scratch. Ingest the locked spines directly as ground truth.
2. **Select the Focal Screen (The Workhorse Canvas):**
   - Do NOT default automatically to a passive dashboard or metrics overview.
   - Select the single screen from the Day-in-the-Life walkthrough that represents the highest intersection of:
     - **Daily Frequency:** Used dozens of times per work session.
     - **Core Product Value:** Where the primary domain nouns are created, viewed, or edited.
     - **Design Uncertainty:** Where spatial placement and tactile mechanics are least obvious.
3. **Anchor & Explore Dialogue:**
   - Do NOT ask open-ended void questions ("What should it look like?").
   - Do NOT trap the user with mechanical multiple-choice questionnaires for ambiguous taste.
   - State a concrete, informed baseline hypothesis grounded in the locked `01-INTENT.md` walkthrough and ask 1 focused calibration question.
4. **Anti-Jargon Law:**
   - Describe physical human interactions in everyday language before introducing design terms.
   - Never drop naked product names ("Typora-style", "Linear-like") without unpacking the concrete physical behavior hands perform.
5. **Immediate Disk Persistence (Law 11):**
   - Record the selected focal screen and journey slice to `docs/design/brief.md` (or update `docs/03-EXPERIENCE.md`) and log to `docs/.memlog.md` in the current turn before speaking.

---

## Step-by-Step Procedure

### Step 1.1: Ingest Locked Stage 1 Spines
Silently read:
- `docs/01-INTENT.md`: Target persona, core mission, Day-in-the-Life walkthrough steps, and strict anti-goals.
- `docs/02-OOUX.md`: Primary domain nouns, relationships, and Calls-to-Action (CTAs).

### Step 1.2: Select the Focal Screen
Identify which specific screen hosts the core work loop from the Day-in-the-Life walkthrough:
- Example: In a note-taking system, the focal screen is the **In-Place Editorial Workspace**, not the global settings or a passive dashboard.
- Example: In an API security gateway, the focal screen is the **Virtual Key Builder & Tool Attenuation Vault**, not the billing overview.

### Step 1.3: Define the Tactile Scope & Boundaries
Extract from `01-INTENT.md`:
- **The In-Scope Workflow:** Exactly which step of the walkthrough is being visualized in this screen.
- **The Anti-Goals:** Verify that all out-of-scope ideas remain safely parked in `docs/00-INBOX.md` (`Future Backlog v0.2+`).

---

## Deliverables & Disk Updates
- Create or update `docs/design/brief.md` (using `templates/design-brief.md`).
- Log milestone entry to `docs/.memlog.md` (e.g. `### [M-NNN] Selected Focal Screen <Screen Name> from Locked v0.1 Intent`).
