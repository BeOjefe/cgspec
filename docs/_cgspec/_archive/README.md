# Superseded & Historical Archives (`docs/_cgspec/_archive/`)

This directory preserves historical drafts, stashed prototypes, superseded ADRs, and obsolete baseline specs.

---

## 1. Zero Information Loss Invariant
In CGSpec, software specifications evolve monotonically. When a major architectural pivot occurs (e.g. Tier 3 `v1 -> v2` backend rewrite via `cgspec-pivot`), obsolete artifacts are never deleted—they are stashed here with full provenance.

---

## 2. Directory Structure
```
docs/_cgspec/_archive/
├── v1-legacy-baseline/     # Snapshot of legacy v0.1 spines before v0.2 migration
└── stash/                  # Stashed experimental UI wireframes and temporary branches
```
