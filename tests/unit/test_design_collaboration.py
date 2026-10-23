"""Guards for the human-AI collaboration rules in the contract and design guidance.

These check that known contradictions stay removed and that required rules stay
present. They do not prove an agent follows the guidance; behavioural trials do.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def section(text, heading):
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    if not match:
        raise AssertionError(f"missing section: {heading}")
    return match.group(1)


class PushBackContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = read("engine/CONTRACT.md")
        self.push = section(self.contract, "Push back when the work is at risk").lower()

    def test_contract_names_the_pushback_triggers(self):
        for trigger in ("before", "concretely", "did not read", "architecture", "environment"):
            self.assertIn(trigger, self.push)

    def test_contract_limits_blocking_and_records_overrides(self):
        self.assertIn("accepted-risk", self.push)
        self.assertIn("memlog", self.push)
        self.assertIn("once", self.push)

    def test_contract_checks_understanding_before_consequential_approval(self):
        self.assertIn("understood", self.push)

    def test_quick_agreement_does_not_skip_the_understanding_check(self):
        agreement = next(line for line in self.contract.splitlines()
                         if line.startswith("- Ordinary agreement"))
        self.assertIn("hard-to-undo", agreement)
        self.assertIn("understanding check", agreement)
        method = read("docs/METHOD-v0.2.md")
        clear = next(line for line in method.splitlines()
                     if line.startswith("- Clear feedback is applied"))
        self.assertIn("understanding check", clear)

    def test_method_states_who_carries_the_definition(self):
        """Was test_method_states_the_human_job. That framing is what the 2026-10-23 stewardship
        council replaced: push-back and the read-before-consequential-approval rule stay, but the
        definition, records and reconciliation belong to the agent."""
        collab = section(read("docs/METHOD-v0.2.md"), "1. Collaboration contract").lower()
        self.assertIn("push back", collab)
        self.assertIn("read what you approve", collab)
        self.assertIn("never asked to reconcile", collab)


class StewardshipContractTests(unittest.TestCase):
    """2026-10-23 agent-stewardship council (Gemini 3.8, human-collaboration and enforcement lenses).

    The method promised that the agent absorbs changes of mind, while the contract called
    architecture, documentation and reconciling a change of direction "the user's real job" and
    listed changing direction as grounds for pushback. Both cannot hold. These pin the resolution:
    the agent owns definition and reconciliation; push-back targets actions, never the person.
    """

    def setUp(self):
        self.push = section(read("engine/CONTRACT.md"), "Push back when the work is at risk")
        self.method = read("docs/METHOD-v0.2.md")
        self.collab = section(self.method, "1. Collaboration contract")

    def test_the_blame_framing_is_gone(self):
        for text in (self.push, self.collab):
            lowered = text.lower()
            self.assertNotIn("real job", lowered)
            self.assertNotIn("human job", lowered)
            self.assertNotIn("your part is the definition", lowered)
            self.assertNotIn("change direction without saying", lowered)

    def test_the_agent_owns_reconciliation(self):
        lowered = self.push.lower()
        self.assertIn("none of that is the user's job", lowered)
        self.assertIn("never fault them", lowered)
        self.assertIn("do not ask the user to reconcile", lowered)

    def test_new_thoughts_are_applied_or_parked_without_interrogation(self):
        self.assertIn("`pending`", self.push)
        self.assertIn('do not ask "is there more coming?"', self.push.lower())
        self.assertNotIn("ask whether more is coming", self.method)

    def test_the_method_no_longer_claims_every_message_is_triaged(self):
        """The inbox hook captures text; nothing records a disposition, and most hosts have no hook."""
        self.assertNotIn("Every message is triaged", self.method)
        self.assertIn("Capture is not triage", self.method)

    def test_stopping_to_ask_has_a_legal_path(self):
        self.assertIn("checkpoint --awaiting", self.push)


class DesignGuidanceTests(unittest.TestCase):
    def setUp(self):
        self.skill = read("skills/cgspec-ui-ux/SKILL.md")
        self.method_design = section(read("docs/METHOD-v0.2.md"), "6. Design path")

    def test_no_fixed_variation_count_or_mechanical_pacing(self):
        for text in (self.skill, self.method_design):
            self.assertNotRegex(text, r"3[-–]5 (quick|deliberately)")
            self.assertNotIn("one screen at a time", text)
            self.assertNotIn("Never build several layers", text)

    def test_change_is_classified_before_work(self):
        for kind in ("behavior", "layout", "appearance", "content", "motion"):
            self.assertIn(kind, self.skill.lower())

    def test_artifact_is_chosen_by_the_open_question(self):
        lowered = self.skill.lower()
        for artifact in ("journey", "state diagram", "wireframe", "side-by-side", "clickable"):
            self.assertIn(artifact, lowered)

    def test_screens_carry_a_data_inventory_against_the_object_model(self):
        self.assertIn("data inventory", self.skill.lower())
        self.assertIn("02-OOUX.md", self.skill)

    def test_decisions_survive_an_interruption(self):
        lowered = self.skill.lower()
        self.assertIn("delegated", lowered)
        self.assertIn("open-question", lowered)
        self.assertIn("without the user pasting", lowered)
        # The session pack surfaces checkpoint `pending`, not ledger bodies.
        self.assertIn("`pending`", self.skill)
        self.assertIn("checkpoint --update-file", self.skill)
        recovery = read("engine/_lib/recovery_pack.py")
        self.assertIn('"pending"', recovery)

    def test_design_skill_has_pushback_examples(self):
        self.assertIn("push back", self.skill.lower())


class BehaviorCoverageTests(unittest.TestCase):
    def test_coverage_requires_named_states_and_concurrency_cases(self):
        text = read("skills/cgspec-ui-ux/references/behavior-coverage.md").lower()
        for phrase in ("named state", "repeated", "stale", "exact version", "executed", "specified"):
            self.assertIn(phrase, text)


class ForgePushBackTests(unittest.TestCase):
    def test_forge_stops_build_requests_without_a_minimum_definition(self):
        text = read("skills/cgspec-forge/SKILL.md").lower()
        self.assertIn("just build", text)
        self.assertIn("minimum definition", text)


if __name__ == "__main__":
    unittest.main()
