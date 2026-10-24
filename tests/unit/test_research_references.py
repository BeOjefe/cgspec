"""Local-only third-party reference imports under docs/_cgspec/02-research/.

Two failure modes these guard against:

1. A third-party tree gets committed. The imports carry other authors and licences, so
   vendoring one into CGSpec is a distribution decision, not a side effect of `git add`.
2. A tree appears and nobody writes down what it is. An undocumented directory full of
   another project's `SKILL.md` and `AGENTS.md` is worse than no directory: the next agent
   cannot tell reference material from CGSpec's own source, and may read it as instructions.

The directories are untracked by design, so the presence checks skip when they are absent
(a fresh clone, or CI). The "never tracked" check does not skip: it is the one that matters
and it is meaningful everywhere.
"""

from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RESEARCH = Path("docs/_cgspec/02-research")
INVENTORY = RESEARCH / "README.md"
QUEUE = RESEARCH / "RESEARCH-QUEUE.md"


def tracked_under(rel: Path) -> list[str]:
    done = subprocess.run(["git", "ls-files", "-z", "--", str(rel)],
                          cwd=REPO, capture_output=True, text=True, check=True)
    return [p for p in done.stdout.split("\0") if p]


def inventoried_names() -> set[str]:
    """Directory names the inventory table names, as `Name/` in the first column."""
    text = (REPO / INVENTORY).read_text(encoding="utf-8")
    return set(re.findall(r"^\|\s*`([^`/]+)/`\s*\|", text, re.M))


class ReferencesAreNeverCommitted(unittest.TestCase):
    def test_no_inventoried_import_is_tracked(self):
        names = inventoried_names()
        self.assertTrue(names, f"{INVENTORY} lists no imports; the table format changed")
        for name in sorted(names):
            with self.subTest(name):
                tracked = tracked_under(RESEARCH / name)
                self.assertEqual(tracked, [], f"{name} is tracked by Git; third-party reference "
                                              "material must stay local to the working copy")

    def test_only_markdown_is_tracked_in_the_research_directory(self):
        """A reference tree committed under a name the inventory does not list would slip past
        the check above, so bound what may live here at all."""
        unexpected = [p for p in tracked_under(RESEARCH) if not p.endswith(".md")]
        self.assertEqual(unexpected, [], "only research documents belong in "
                                         f"{RESEARCH}; found non-Markdown tracked files")


class InventoryMatchesTheWorkingCopy(unittest.TestCase):
    def setUp(self):
        self.root = REPO / RESEARCH
        self.present = {p.name for p in self.root.iterdir()
                        if p.is_dir() and not p.name.startswith(".")}
        if not self.present:
            self.skipTest("no local reference imports in this working copy")

    def test_every_present_directory_is_documented(self):
        missing = sorted(self.present - inventoried_names())
        self.assertEqual(missing, [], f"undocumented directories in {RESEARCH}: {missing}. "
                                      f"Add a row to {INVENTORY} saying what each one is, where "
                                      "it came from, and why it is here.")

    def test_each_documented_directory_records_a_source(self):
        """A row without a source cannot be re-downloaded if the working copy is cleaned."""
        text = (REPO / INVENTORY).read_text(encoding="utf-8")
        for name in sorted(self.present & inventoried_names()):
            with self.subTest(name):
                row = next(line for line in text.splitlines()
                           if line.startswith(f"| `{name}/`"))
                self.assertRegex(row, r"https?://|`[0-9a-f]{40}`|anthropics/",
                                 f"the {name} row names no recoverable source")


class QueueStatesQuestionsNotFindings(unittest.TestCase):
    """The queue is read by agents looking for work; a half-written entry invites invention."""

    def setUp(self):
        self.text = (REPO / QUEUE).read_text(encoding="utf-8")
        self.items = re.findall(r"^## (QUEUE-\d{3}) — (.+)$", self.text, re.M)

    def test_queue_has_items_with_unique_ids(self):
        ids = [i for i, _ in self.items]
        self.assertTrue(ids, f"{QUEUE} declares no QUEUE-NNN items")
        self.assertCountEqual(ids, set(ids), "duplicate QUEUE-NNN ids")

    def test_every_item_names_a_source_and_a_finish_condition(self):
        blocks = re.split(r"^## QUEUE-\d{3} — ", self.text, flags=re.M)[1:]
        for (item_id, _), block in zip(self.items, blocks):
            with self.subTest(item_id):
                self.assertRegex(block, r"\*\*Source:\*\*.*https?://",
                                 "no source URL, so the spike cannot be started")
                self.assertIn("What finishes this spike", block,
                              "no finish condition, so the spike cannot be closed")

    def test_no_queued_item_is_also_a_concluded_spike(self):
        """A RES file means a conclusion; leaving the queue entry behind double-counts it."""
        for item_id, title in self.items:
            with self.subTest(item_id):
                slug = re.sub(r"[^a-z0-9]+", "-", title.split(":")[0].casefold()).strip("-")
                clashes = [p.name for p in (REPO / RESEARCH).glob("RES-*.md")
                           if slug and slug in p.name]
                self.assertEqual(clashes, [], f"{item_id} is queued but {clashes} exists")


if __name__ == "__main__":
    unittest.main()
