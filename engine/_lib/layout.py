"""Spec section 2 as data: the only definition of where things live and which statuses exist.

doctor.py checks projects against this; install.py and the templates are built from it.
"""

from __future__ import annotations

GUI_PROFILES = {"website", "web-workspace", "mobile", "small"}

SPINES = ["01-INTENT", "02-DOMAIN", "03-EXPERIENCE", "04-ARCHITECTURE", "05-DELIVERY"]

# Spine needed once any part of the product has reached this stage (spec 4).
SPINE_REQUIRED_FROM = {
    "01-INTENT": "design",
    "02-DOMAIN": "design",
    "03-EXPERIENCE": "architecture",
    "04-ARCHITECTURE": "milestones",
    "05-DELIVERY": "coding",
}
STAGES = ["brainstorming", "design", "architecture", "milestones", "coding", "testing", "cicd", "follow-up"]

EMPTY_MARKER = "<!-- cgspec:empty -->"
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
    "spines", "adrs", "slices", "prototypes", "_cgspec", "METHOD-v2.md",
}
ALLOWED_IN_CGSPEC = {
    "project.json", "01-engine", "02-research", "03-councils", "04-checks",
    "05-runs", "06-evidence", "07-state", "_archive",
}
ALLOWED_STATE_FILES = {
    "checkpoint.json": "checkpoint",
    "budget.json": "budget",
    "frozen.json": "frozen",
    "tier.json": "tier",
    "quota.json": "quota",
    "legacy-baseline.json": "legacy-baseline",
    "stop-retries.json": None,
}

DECISION_STATUSES = ["Draft", "Proposed", "Approved", "Delegated", "Rejected", "Superseded", "Imported"]
SLICE_STATUSES = ["Draft", "Approved", "In progress", "Done", "Blocked"]
VERDICTS = ["PASS", "FAIL", "PARTIAL", "BLOCKED", "NOT_APPLICABLE"]

ADR_NAME = r"^ADR-(\d{3}|draft)-[a-z0-9][a-z0-9-]*\.md$"
SLICE_NAME = r"^SLICE-(\d{3}|draft)-[a-z0-9][a-z0-9-]*\.md$"
RES_NAME = r"^RES-\d{3}-[a-z0-9][a-z0-9-]*\.md$"
COUNCIL_NAME = r"^COUNCIL-\d{3}-[a-z0-9][a-z0-9-]*$"
RUN_NAME = r"^R-\d{8}-[0-9a-f]{4}$"

SCRIPT_SUFFIXES = {".py", ".js", ".mjs", ".cjs", ".ts", ".sh", ".bash", ".ps1", ".rb"}
