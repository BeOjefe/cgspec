# CGSpec Engine Room (`docs/_cgspec/`)

This directory houses the internal tooling, deliberation logs, research compendiums, and historical archives that power the **Reformed CGSpec v0.2 Specification Engine**.

---

## Why the `_` Prefix?
- Standard dotfiles (`.cgspec/`) are hidden by default in `ls` and ignored by default in `ripgrep`, `git grep`, and IDE search engines.
- The underscore prefix (`_cgspec/`) ensures this directory is **100% visible and fully indexed** by development tools, while signaling its role as the engine room.

---

## Subdirectories

1. **[`01-script/`](./01-script/README.md):** Specification linting, deterministic AST codebase reverse-engineering, and memory log CLI tools.
2. **[`02-research/`](./02-research/README.md):** Deep technical research spikes, performance benchmarks, and architectural investigations (`RES-NNN-*.md`).
3. **[`03-council/`](./03-council/README.md):** Structured 3-agent adversarial debate deliberation transcripts (`COUNCIL-NNN-*/`).
4. **[`_archive/`](./_archive/README.md):** Stashed, superseded, or migrated documents preserving full provenance and historical audit trails.
