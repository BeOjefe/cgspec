"""Shared scope policy: browser prototypes are implementation, not ordinary prose."""
from pathlib import PurePosixPath

REFERENCE_ASSETS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".ico",
    ".mp4", ".webm", ".mp3", ".wav", ".ogg", ".woff", ".woff2", ".ttf", ".otf",
}


def prototype_source(rel: str) -> bool:
    # Unknown suffixes can be loaded by a browser too. Only ordinary Markdown
    # notes are prose-exempt; even reference assets retain scope checks.
    return rel.startswith("docs/prototypes/") and PurePosixPath(rel).suffix.lower() != ".md"


def needs_tier(rel: str) -> bool:
    if rel.startswith(".cgspec-scratch/"):
        return False
    if not rel.startswith("docs/"):
        return True
    return prototype_source(rel)


def prototype_journey(rel: str) -> bool:
    parts = PurePosixPath(rel).parts
    return (len(parts) == 5 and parts[:2] == ("docs", "prototypes")
            and parts[3] == "journeys" and parts[4].endswith(".json"))


def live_prototype_source(rel: str) -> bool:
    return (prototype_source(rel) and not prototype_journey(rel)
            and PurePosixPath(rel).suffix.lower() not in REFERENCE_ASSETS
            and PurePosixPath(rel).name != ".gitkeep")
