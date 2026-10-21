"""Shared scope policy: browser prototypes are implementation, not ordinary prose."""
from pathlib import PurePosixPath

from .layout import PROTOTYPE_ASSET_SUFFIXES, SCRIPT_SUFFIXES

PROTOTYPE_SOURCES = PROTOTYPE_ASSET_SUFFIXES | {
    ".html", ".htm", ".css", ".scss", ".sass", ".less", ".svg", ".json",
    ".vue", ".svelte",
}


def prototype_source(rel: str) -> bool:
    return rel.startswith("docs/prototypes/") and PurePosixPath(rel).suffix.lower() in PROTOTYPE_SOURCES


def needs_tier(rel: str) -> bool:
    if rel.startswith(".cgspec-scratch/"):
        return False
    if not rel.startswith("docs/"):
        return True
    return prototype_source(rel) or PurePosixPath(rel).suffix.lower() in SCRIPT_SUFFIXES


def live_prototype_source(rel: str) -> bool:
    # Generated frozen snapshots and historical copies still need scope, but
    # do not need new behavior tests merely because they preserve old bytes.
    parts = PurePosixPath(rel).parts
    return prototype_source(rel) and not ({"_archive", "_snapshots"} & set(parts))
