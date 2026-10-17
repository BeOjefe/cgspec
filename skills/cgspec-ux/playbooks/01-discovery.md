# Playbook 01: Establish the Design Brief & Map the Journey

## Purpose
Guide the human architect and AI agent through Phase 1 of the Experience Cycle: understanding who the user is, what job they are trying to accomplish, the real-world usage scenario, and selecting the focal screen for initial design.

---

## Operating Invariants

1. **Understand Before Drawing:** Never jump into layout boxes, visual themes, or component code until the user's primary task and usage context are crystal clear.
2. **Anchor & Explore Dialogue:**
   - Do NOT ask open-ended, void questions ("What do you want it to look like?").
   - Do NOT trap the user with mechanical multiple-choice questionnaires for ambiguous taste.
   - Instead, state a concrete, informed baseline hypothesis ("Based on your goal of long-form writing, here is an initial assumption...") and ask 1-2 focused, high-leverage questions to calibrate.
3. **Plain Physical Language:** Describe physical human interactions in everyday language before introducing technical jargon.
4. **Anti-Jargon Law:** If referencing any existing product or pattern, explain the exact mechanical behavior in plain English. Never drop naked names ("Typora-style", "Notion-like") without unpacking what hands actually do.
5. **Immediate Disk Persistence (Law 11):** Record every validated insight, user preference, and anti-goal to disk (`docs/design/brief.md` or `docs/03-EXPERIENCE.md`, plus `docs/.memlog.md`) in the current turn before speaking.

---

## Step-by-Step Procedure

### Step 1.1: Define the Job and Situation
Elicit and document:
- **Primary Persona:** Who is sitting in front of the screen? (e.g. "Software engineer documenting architectural decisions", "Operations lead managing API credentials").
- **Core Job-to-be-Done:** What specific outcome are they trying to reach?
- **Current Friction / Frustration:** What interrupts them or feels painful in existing tools?
- **Strict Anti-Goals:** What is explicitly out of scope for v0.1? (Record in `docs/00-INBOX.md` under `Future Backlog (v0.2+)`).

### Step 1.2: Map the Day-in-the-Life Walkthrough
Walk through a real, end-to-end scenario step-by-step:
1. **Entry Point:** Where does the user start? What triggers them to open this screen?
2. **First Action:** What is the first thing they see, touch, or type?
3. **Core Work Loop:** How do they create, edit, search, or inspect data?
4. **Feedback & Confidence:** How does the system confirm success without annoying popups?
5. **Recovery & Edge Cases:** What happens when an input is invalid, network drops, or permission is missing?

### Step 1.3: Select the Focal Screen
Do NOT default automatically to a dashboard or metrics strip.
Identify the single screen that represents the highest intersection of:
- **Daily Frequency:** Used dozens of times per session.
- **Core Product Value:** Where the actual work happens.
- **Design Uncertainty:** Where interaction mechanics are least obvious.

---

## Deliverables & Disk Updates
- Create or update `docs/design/brief.md` (using `templates/design-brief.md`).
- Log milestone entry to `docs/.memlog.md` (e.g. `### [M-NNN] Locked Phase 1 Design Brief for <Screen>`).
