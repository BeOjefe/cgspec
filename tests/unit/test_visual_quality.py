"""The design checks must follow a project's declared choices, not file-name guesses."""

from __future__ import annotations

import json
import unittest

from tests.helpers import TempDir
from _lib import visual_quality as quality


class VisualQualityTests(unittest.TestCase):
    def test_tokens_are_loaded_only_from_declared_path(self):
        with TempDir() as root:
            (root / "tokens.dtcg.json").write_text(json.dumps({"font": {"size": {
                "base": {"$value": "99px"}}}}))
            (root / "actual.json").write_text(json.dumps({"font": {"size": {
                "base": {"$value": "14px"}}}, "space": {"unit": {"$value": "4px"}}}))
            self.assertFalse(quality.find_tokens(root, {}).get("sizes"))
            self.assertEqual(quality.find_tokens(root, {"design_tokens": "actual.json"})["sizes"], [14.0])
            self.assertEqual(quality.find_tokens(root, {"design_tokens": "actual.json"})["unit"], 4.0)

    def test_declared_status_hues_do_not_trip_generic_limit(self):
        with TempDir() as root:
            sheet = {"color": {"accent": {"default": {"$value": "#8139c7"}}, "status": {
                "success": {"$value": "#16803a"}, "warning": {"$value": "#bc740c"},
                "danger": {"$value": "#bc362b"}, "info": {"$value": "#1768b5"}}}}
            (root / "actual.json").write_text(json.dumps(sheet))
            tokens = quality.find_tokens(root, {"design_tokens": "actual.json"})
            hues = {str(h): 1 for h in tokens["hues"]}
            vp = {"viewport": "desktop", "quality": {"hues": hues}}
            self.assertFalse(any("W-ACCENTS" in item for item in quality.analyse(vp, tokens)[1]))
            hues["300"] = 1
            self.assertTrue(any("W-ACCENTS" in item for item in quality.analyse(vp, tokens)[1]))

    def test_unparsed_color_tokens_do_not_claim_hues_are_outside_sheet(self):
        with TempDir() as root:
            (root / "tokens.json").write_text(json.dumps({"color": {
                "brand": {"$value": "{palette.brand}"}}}))
            tokens = quality.find_tokens(root, {"design_tokens": "tokens.json"})
            self.assertIn("W-TOKEN-COLOR-UNPARSED", tokens["issue"])
            self.assertNotIn("hues", tokens)
            viewport = {"viewport": "desktop", "quality": {"hues": {
                "30": 1, "90": 1, "150": 1, "270": 1}}}
            self.assertFalse(any("W-ACCENTS" in w for w in quality.analyse(viewport, tokens)[1]))

    def test_fallback_type_limit_matches_per_screen_craft_rule(self):
        viewport = {"viewport": "desktop", "quality": {"sizes": {
            str(i): 1 for i in range(12, 18)}}}
        self.assertTrue(any("W-TYPE-SCALE" in w for w in quality.analyse(viewport, {})[1]))

    def test_deliberate_requires_locked_exact_tokens(self):
        with TempDir() as root:
            spine = root / "docs/spines/03-EXPERIENCE.md"
            spine.parent.mkdir(parents=True)
            spine.write_text("# Experience\n\n## Register\nStatus: Proposed\n"
                             "- Deliberate choices: purple, cream-serif\n"
                             "- Deliberate reason purple: brand\n"
                             "- Deliberate reason cream-serif: references\n")
            self.assertEqual(quality.deliberate(root), set())
            spine.write_text(spine.read_text().replace("Proposed", "Locked"))
            self.assertEqual(quality.deliberate(root), {"purple", "cream-serif"})
            spine.write_text(spine.read_text().replace("- Deliberate reason cream-serif: references\n", ""))
            self.assertEqual(quality.deliberate(root), set())
            spine.write_text("# Experience\n\n## Register\nStatus: Locked\n"
                             "- Deliberate choices: avoid purple, no serif, hero story\n")
            self.assertEqual(quality.deliberate(root), set())


if __name__ == "__main__":
    unittest.main()
