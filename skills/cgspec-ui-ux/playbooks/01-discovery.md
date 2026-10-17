# Playbook 01: Ingest Locked Intent & Select the Focal Screen

## Purpose
Guide Phase 1 of the Experience Cycle: ingesting the locked Stage 1 Intent (`01-INTENT.md`) and ORCA domain nouns (`02-OOUX.md`), selecting the single focal screen (`SCR-01`) with the highest value and uncertainty, and writing `docs/design/brief.md` without re-interviewing the user from scratch.

---

## Step-by-Step Procedure

### Step 1.1: Ingest Locked Stage 1 Spines
Read `docs/01-INTENT.md` (functional actors, mission, Day-in-the-Life walkthrough, anti-goals) and `docs/02-OOUX.md` (domain nouns, relationships, permissions, attributes). Never ask the user to repeat facts already locked in Stage 1.

### Step 1.2: Select the Focal Screen (`SCR-01`)
Do not default automatically to a passive metrics dashboard. Select the single screen from the Day-in-the-Life walkthrough at the intersection of:
1. **Daily Frequency:** Used repeatedly during a normal session.
2. **Core Product Value:** Where primary domain nouns are created, viewed, or manipulated.
3. **Design Uncertainty:** Where spatial placement and tactile mechanics are least obvious.

### Step 1.3: Draft `docs/design/brief.md`
Using [`templates/design-brief.md`](../templates/design-brief.md), record:
- Target functional actors and active **Surface Profile** (`Profile A..D` in [`SKILL.md`](../SKILL.md)).
- The in-scope workflow step for `SCR-01` (keeping other screens scheduled as `SCR-02..N` placeholders).
- Log the focal screen selection to `docs/.memlog.md`.
