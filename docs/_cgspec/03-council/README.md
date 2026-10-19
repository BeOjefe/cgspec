# Council Deliberations & Debate Logs (`docs/_cgspec/03-council/`)

This directory houses the structured transcripts and deliberations produced by the **Stage 3 Supervised 3-Agent Peer Debate Council** (`cgspec-council`).

---

## 1. When is Council Invoked?
Council is invoked when an architectural, security, data-model, or UX trade-off is contested and requires adversarial debate before drafting an ADR.

---

## 2. Directory Structure per Session
Each council debate session lives in its own dedicated directory:
```
docs/_cgspec/03-council/COUNCIL-NNN-<slug>/
├── 00-topic.md             # Locked question, context, stakes, and target invariant
├── round-01.md             # Initial independent arguments from 3 debaters
├── round-02.md             # Cross-rebuttal and stress-testing
├── round-03.md             # Synthesis and concessions
└── summary.md              # Final consensus and drafted ADR proposal
```

---

## 3. Main Chat Insulation
Debater arguments and raw deliberation transcripts remain strictly on disk inside this directory. Only the final executive consensus summary and proposed `ADR-NNN` are surfaced to the human architect.
