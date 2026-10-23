"""Stopping to ask the user is a legal stop, not a failure.

Council finding (2026-10-23 agent-stewardship council, enforcement lens, finding 1), verified
against the engine before fixing: the contract tells the agent to stop and ask rather than build
on a guess that is costly to undo, but the stop check refused any stop while work was in flight.
The agent's only exits were `--done` (untrue: the work is not done), `--blocked` (records the
wait as a BLOCKED open issue, which is wrong for "waiting on your choice"), or two forced
"Not done yet" continuations that push it to keep going on the guess. The method told the agent
to ask; the engine punished it for asking.

`checkpoint --awaiting '<question>'` records the question and keeps the batch in flight. One
recorded question permits one stop, so it cannot become a standing bypass of the in-flight check.
"""

from __future__ import annotations

import json
import unittest

from tests.helpers import TempDir, hook, install, run_script, write_json

STATE = "docs/_cgspec/07-state"


class AwaitingUser(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        install(self.root)
        self.path = self.root / STATE / "checkpoint.json"

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def checkpoint(self, *args):
        return run_script("cgspec_hook.py", "checkpoint", "--root", str(self.root), *args)

    def read(self):
        return json.loads(self.path.read_text())

    def stop(self, active=False):
        return hook(self.root, "stop", {"hook_event_name": "Stop", "stop_hook_active": active}, "--tool", "claude")

    def start_work(self):
        done = self.checkpoint("--in-flight", "restyling the Files screen")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    # --- the regression ------------------------------------------------------------------------
    def test_stopping_to_ask_mid_batch_is_allowed(self):
        self.start_work()
        self.assertEqual(self.stop().returncode, 2, "precondition: in-flight work blocks a plain stop")
        asked = self.checkpoint("--awaiting", "Keep the current layout, or try the card grid?")
        self.assertEqual(asked.returncode, 0, asked.stdout + asked.stderr)
        result = self.stop()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("BLOCKED", result.stdout + result.stderr)

    def test_the_refusal_tells_the_agent_how_to_stop_and_ask(self):
        """An agent learns the exits from this message; one it is never shown is one it never uses."""
        self.start_work()
        self.assertIn("--awaiting", self.stop().stderr)

    def test_asking_keeps_the_work_in_flight_and_out_of_open_issues(self):
        """The batch is paused on a question, not finished and not failed."""
        self.start_work()
        self.checkpoint("--awaiting", "Which of the three palettes?")
        cp = self.read()
        self.assertEqual(cp["in_flight"], "restyling the Files screen")
        self.assertEqual(cp["awaiting_user"]["question"], "Which of the three palettes?")
        self.assertFalse(any("BLOCKED" in issue for issue in cp.get("open_issues", [])))

    # --- the bound -----------------------------------------------------------------------------
    def test_one_question_permits_one_stop(self):
        """Otherwise a single recorded question would silence the in-flight check forever."""
        self.start_work()
        self.checkpoint("--awaiting", "Dark or light first?")
        self.assertEqual(self.stop().returncode, 0)
        self.assertEqual(self.stop().returncode, 2, "a used question must not excuse a second stop")

    def test_the_question_survives_the_stop_for_the_next_session(self):
        """A user who leaves mid-question must find it waiting when anyone resumes."""
        self.start_work()
        self.checkpoint("--awaiting", "Dark or light first?")
        self.stop()
        pack = hook(self.root, "session-start", {"hook_event_name": "SessionStart"}, "--tool", "claude")
        self.assertIn("Dark or light first?", pack.stdout)

    def test_resuming_work_clears_the_question(self):
        self.start_work()
        self.checkpoint("--awaiting", "Dark or light first?")
        self.stop()
        self.checkpoint("--in-flight", "applying the dark palette")
        self.assertNotIn("awaiting_user", self.read())
        self.assertEqual(self.stop().returncode, 2, "resumed work is checked normally again")

    def test_finishing_clears_the_question(self):
        self.start_work()
        self.checkpoint("--awaiting", "Dark or light first?")
        self.checkpoint("--done")
        self.assertNotIn("awaiting_user", self.read())

    # --- what it does not excuse ---------------------------------------------------------------
    def test_a_question_does_not_excuse_doctor_errors(self):
        self.start_work()
        self.checkpoint("--awaiting", "Dark or light first?")
        (self.root / "docs/random.md").write_text("x\n")
        result = self.stop()
        self.assertEqual(result.returncode, 2)
        self.assertIn("doctor", result.stderr)

    def test_an_empty_question_is_refused(self):
        self.start_work()
        result = self.checkpoint("--awaiting", "   ")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("awaiting_user", self.read())

    def test_awaiting_conflicts_with_other_transitions(self):
        self.start_work()
        result = self.checkpoint("--awaiting", "q?", "--done")
        self.assertNotEqual(result.returncode, 0)

    def test_a_question_without_work_in_flight_is_recorded(self):
        """Asking is allowed with nothing in flight, and the question is still kept for a resume."""
        asked = self.checkpoint("--awaiting", "Which screen next?")
        self.assertEqual(asked.returncode, 0, asked.stdout + asked.stderr)
        self.assertEqual(self.read()["awaiting_user"]["question"], "Which screen next?")

    # --- final-challenge review round 1 (Opus 5.5, 2026-10-23) ---------------------------------
    def patch(self, data):
        return run_script("cgspec_hook.py", "checkpoint", "--root", str(self.root), "--update-file", "-",
                          stdin=json.dumps(data))

    def test_a_patch_that_changes_in_flight_clears_the_question(self):
        """M1: the contract recommends --update-file, so a patch is a transition too."""
        self.start_work()
        self.checkpoint("--awaiting", "Q1?")
        done = self.patch({"in_flight": "batch 2"})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertNotIn("awaiting_user", self.read())
        self.assertEqual(self.stop().returncode, 2, "an old question must not excuse a stop on new work")

    def test_awaiting_and_a_patch_setting_in_flight_conflict(self):
        self.start_work()
        result = run_script("cgspec_hook.py", "checkpoint", "--root", str(self.root), "--awaiting", "q?",
                            "--update-file", "-", stdin=json.dumps({"in_flight": "x"}))
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("awaiting_user", self.read())

    def test_a_refused_stop_does_not_use_up_the_question(self):
        """Mutation found by the reviewer: consuming on every stop passed all earlier tests."""
        self.start_work()
        self.checkpoint("--awaiting", "Dark or light first?")
        (self.root / "docs/random.md").write_text("x\n")
        self.assertEqual(self.stop().returncode, 2)
        self.assertIs(self.read()["awaiting_user"]["used"], False)
        (self.root / "docs/random.md").unlink()
        self.assertEqual(self.stop().returncode, 0, "the question still excuses the stop once doctor is clean")

    def test_blocked_clears_the_question(self):
        self.start_work()
        self.checkpoint("--awaiting", "Dark or light first?")
        self.stop()
        self.checkpoint("--blocked", "the API is down")
        self.assertNotIn("awaiting_user", self.read())

    def test_using_the_question_leaves_the_semantic_time_alone(self):
        """Bumping `updated` here would hide the stale-checkpoint check."""
        self.start_work()
        self.checkpoint("--awaiting", "Dark or light first?")
        before = self.read()["updated"]
        self.stop()
        self.assertEqual(self.read()["updated"], before)

    def test_antigravity_stop_allows_on_a_question(self):
        self.start_work()
        self.checkpoint("--awaiting", "Dark or light first?")
        result = hook(self.root, "stop", {"hook_event_name": "Stop"}, "--tool", "antigravity")
        self.assertEqual(json.loads(result.stdout.strip().splitlines()[0])["decision"], "allow")
        self.assertIs(self.read()["awaiting_user"]["used"], True)

    def test_an_asked_question_is_not_shown_as_still_waiting(self):
        """Minor 3: after the stop the user may already have answered."""
        self.start_work()
        self.checkpoint("--awaiting", "Dark or light first?")
        self.stop()
        pack = hook(self.root, "session-start", {"hook_event_name": "SessionStart"}, "--tool", "claude").stdout
        self.assertIn("last question asked", pack)
        self.assertNotIn("waiting on the user", pack)

    # --- delta review round 2 (Opus 5.5, 2026-10-23) --------------------------------------------
    def test_no_question_is_ever_parked_as_unanswered(self):
        """N1: on hosts without a stop hook nothing marks a question used, so a parked "UNANSWERED"
        entry would be false for every answered question. A false record is worse than none."""
        self.start_work()
        before = self.read().get("pending", [])
        self.checkpoint("--awaiting", "Dark or light first?")
        self.checkpoint("--done")  # answered in conversation, on a host with no stop check
        self.assertEqual(self.read().get("pending", []), before)
        self.start_work()
        self.checkpoint("--awaiting", "Which palette?")
        self.stop()
        self.checkpoint("--done")
        self.assertEqual(self.read().get("pending", []), before)

    def test_re_recording_an_unused_question_replaces_it_without_counting(self):
        """N2: rewording a question before any stop is one question, not two."""
        self.start_work()
        self.checkpoint("--awaiting", "Dark or light?")
        self.checkpoint("--awaiting", "Dark or light first?")
        asked = self.read()["awaiting_user"]
        self.assertEqual(asked["question"], "Dark or light first?")
        self.assertEqual(asked["count"], 1)
        self.assertEqual(self.read().get("pending", []), [])

    def test_repeating_the_same_in_flight_keeps_the_question(self):
        """N3: a patch or flag that restates the current batch is not a new batch."""
        self.start_work()
        self.checkpoint("--awaiting", "Dark or light first?")
        done = self.patch({"in_flight": "restyling the Files screen", "next_action": "apply the answer"})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.checkpoint("--in-flight", "restyling the Files screen")
        self.assertEqual(self.read()["awaiting_user"]["question"], "Dark or light first?")
        self.assertEqual(self.stop().returncode, 0, "the question must still excuse its stop")

    def test_questions_without_work_in_flight_are_not_counted(self):
        """N4: ordinary discovery questions are not a pattern worth flagging."""
        for n in range(3):
            self.checkpoint("--awaiting", f"Question {n}?")
            self.stop()
        pack = hook(self.root, "session-start", {"hook_event_name": "SessionStart"}, "--tool", "claude").stdout
        self.assertNotIn("questions asked during this batch", pack)

    def test_repeated_questions_in_one_batch_are_counted_and_visible(self):
        """Minor 2: asking before every stop cannot be prevented, but it must not be invisible."""
        self.start_work()
        for n in range(3):
            self.checkpoint("--awaiting", f"Question {n}?")
            self.stop()
        self.assertEqual(self.read()["awaiting_user"]["count"], 3)
        pack = hook(self.root, "session-start", {"hook_event_name": "SessionStart"}, "--tool", "claude").stdout
        self.assertIn("3 questions asked during this batch", pack)

    def test_hand_edited_awaiting_must_match_the_schema(self):
        cp = self.read()
        cp["in_flight"] = "work"
        cp["awaiting_user"] = {"question": ""}
        write_json(self.path, cp)
        self.assertNotEqual(self.checkpoint("--next", "x").returncode, 0,
                            "a malformed question record is preserved and refused, not silently trusted")


if __name__ == "__main__":
    unittest.main()
