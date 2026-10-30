"""Spec section 2 as data: the only definition of where things live and which statuses exist.

doctor.py checks projects against this; install.py and the templates are built from it.
"""

from __future__ import annotations

GUI_PROFILES = {"website", "web-workspace", "mobile", "small"}

SPINES = ["01-INTENT", "02-OOUX", "03-EXPERIENCE", "04-ARCHITECTURE", "05-DELIVERY"]

# Spine needed once any part of the product has reached this stage (spec 4).
SPINE_REQUIRED_FROM = {
    "01-INTENT": "design",
    "02-OOUX": "design",
    "03-EXPERIENCE": "architecture",
    "04-ARCHITECTURE": "milestones",
    "05-DELIVERY": "coding",
}
STAGES = ["brainstorming", "design", "architecture", "milestones", "coding", "testing", "cicd", "follow-up"]

EMPTY_MARKER = "<!-- cgspec:empty -->"
# A spine counts as written only with at least this many words of real content.
MIN_SPINE_WORDS = 12
PLACEHOLDER_LINE = r"^[-*\s]*(tbd|tbc|todo|wip|n/?a|none( yet)?|\.{3,}|-+|lorem ipsum.*|to be (defined|done|decided|written).*)[.!\s]*$"
INDEX_BEGIN = "<!-- cgspec:index:begin -->"
INDEX_END = "<!-- cgspec:index:end -->"

REQUIRED_FILES = [
    "AGENTS.md",
    "CLAUDE.md",
    "docs/00-INDEX.md",
    "docs/00-INBOX.md",
    "docs/_memlog.md",
    "docs/_cgspec/project.json",
    "docs/_cgspec/01-engine/manifest.json",
    "docs/_cgspec/04-checks/manifest.json",
    "docs/_cgspec/07-state/frozen.json",
    "docs/_cgspec/07-state/tier.json",
    "docs/_cgspec/07-state/checkpoint.json",
]
REQUIRED_DIRS = [
    "docs/spines",
    "docs/adrs",
    "docs/slices",
    "docs/_cgspec/01-engine",
    "docs/_cgspec/02-research",
    "docs/_cgspec/03-councils",
    "docs/_cgspec/04-checks",
    "docs/_cgspec/05-runs",
    "docs/_cgspec/06-evidence",
    "docs/_cgspec/07-state",
]
GUI_DIRS = ["docs/prototypes", "docs/prototypes/_snapshots", "docs/prototypes/_vision"]

# Everything allowed directly inside docs/ and docs/_cgspec/; anything else is an error.
ALLOWED_IN_DOCS = {
    "00-INDEX.md", "00-INBOX.md", "00-REGISTRY.md", "_memlog.md", ".memlog.lock",
    "spines", "adrs", "slices", "prototypes", "_cgspec",
}
ALLOWED_IN_CGSPEC = {
    "project.json", "capabilities.json", "01-engine", "02-research", "03-councils", "04-checks",
    "05-runs", "06-evidence", "07-state", "_archive",
}
ALLOWED_STATE_FILES = {
    "checkpoint.json": "checkpoint",
    "budget.json": "budget",
    "frozen.json": "frozen",
    "tier.json": "tier",
    "quota.json": "quota",
    "legacy-baseline.json": "legacy-baseline",
    "approvals.json": "approvals",
    "stop-retries.json": None,
    "hook-heartbeats": None,  # process-specific receipts; authenticated by session-check, not JSON Schema
}

DECISION_STATUSES = ["Draft", "Proposed", "Approved", "Delegated", "Rejected", "Superseded", "Imported"]
SLICE_STATUSES = ["Draft", "Approved", "In progress", "Done", "Blocked"]
VERDICTS = ["PASS", "FAIL", "PARTIAL", "BLOCKED", "NOT_APPLICABLE"]

ADR_NAME = r"^ADR-(\d{3}|draft)-[a-z0-9][a-z0-9-]*\.md$"
SLICE_NAME = r"^SLICE-(\d{3}|draft)-[a-z0-9][a-z0-9-]*\.md$"
RES_NAME = r"^RES-\d{3}-[a-z0-9][a-z0-9-]*\.md$"
COUNCIL_NAME = r"^COUNCIL-\d{3}-[a-z0-9][a-z0-9-]*$"
RUN_NAME = r"^R-\d{8}-[0-9a-f]{4}$"

# Compared case-insensitively. Executable bit or a "#!" first line also marks a script.
SCRIPT_SUFFIXES = {
    ".py", ".pyw", ".ipynb", ".js", ".mjs", ".cjs", ".ts", ".mts", ".cts", ".sh", ".bash", ".zsh",
    ".fish", ".ps1", ".psm1", ".bat", ".cmd", ".rb", ".pl", ".php", ".lua", ".r", ".jl", ".go", ".rs",
}
# Browser code allowed in prototype screen folders and the vision board, unless it uses Node.
PROTOTYPE_ASSET_SUFFIXES = {".js", ".mjs", ".ts", ".tsx", ".jsx"}
# Grey prototypes are plain browser pages (layers 0-4; layers 5-7 live in the real frontend),
# so their code may only load relative paths or full URLs. Anything else counts as a script.
IMPORT_SPECIFIER = r"""(?:\bimport\s*(?:[\w*{}\s,]+\s*from\s*)?|\bexport\s*[\w*{}\s,]+\s*from\s*)(['"`])([^'"`]*)\1"""
DYNAMIC_IMPORT = r"\bimport\s*\("
LITERAL_CALL_ARG = r"""^\s*(['"`])([^'"`$]*)\1\s*\)"""
NODE_GLOBALS = r"\brequire\s*\(|\bprocess\b\s*\.|\b(Bun|Deno)\s*\.|globalThis\s*\[|__dirname|__filename"
BROWSER_SPECIFIER = r"^(\.{1,2}/|/|https?://)"

# Outside docs/, scripts are expected under the code and tests path classes; these are also fine.
CONFIG_GLOBS = ["*.config.*", "**/*.config.*", ".github/**", ".husky/**", "**/.*rc.*", "**/.*rc",
                "**/conftest.py", "**/setup.py", "**/noxfile.py", "**/manage.py"]
SKIP_WALK = {".git", "node_modules", ".cgspec-scratch", ".venv", "venv", "__pycache__", "dist", "build",
             ".next", ".nuxt", ".svelte-kit", "target", "vendor", ".tox", ".mypy_cache", ".pytest_cache"}

# The description line each spine template carries; a spine holding only this is empty.
SPINE_TEMPLATE_TEXT = {
    "01-INTENT": "Why this exists, for whom, goal type, anti-goals, v0.1 scope.",
    "02-OOUX": "OOUX nouns with attributes, relations, hierarchy and permissions.",
    "03-EXPERIENCE": "Tasks, screens, flows, design layer status per screen (or API/CLI behavior when headless).",
    "04-ARCHITECTURE": "System context, containers, components, data model, contracts, budgets, threat model; links to ADRs.",
    "05-DELIVERY": "Slices in order, CI/CD, releases, runbooks, observation.",
}
