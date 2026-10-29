"""Outcome-based closure and independent review (issue #28)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from tests.helpers import TempDir, git, git_project, make_ready_start, make_slice, run_script
from _lib.common import EXIT_BLOCK


class ClosureTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git_project(self.root)
        make_slice(self.root)
        make_ready_start(self.root, with_git_plan=False)
        self.commit("agreed slice")

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def commit(self, message: str) -> str:
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "--allow-empty", "-m", message)
        return self.rev()

    def rev(self) -> str:
        return git(self.root, "rev-parse", "--short", "HEAD").stdout.strip()

    def evidence(self, name: str, *, verdict="PASS", claim="integration", data_source="real_backend",
                 covers=("OUT-work",), revision=None, ran_by="verifier", ran_at="2026-10-29T10:00:00Z", **extra) -> str:
        rec = {"schema": 1, "check": name, "revision": revision or self.rev(), "verdict": verdict, "state": "Fresh",
               "claim": claim, "data_source": data_source, "covers": list(covers), "details": "ran",
               "ran_at": ran_at, "ran_by": ran_by, **extra}
        path = self.root / f"docs/_cgspec/06-evidence/closure-test/{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rec))
        return path.relative_to(self.root).as_posix()

    def review(self, name="final-review", **extra) -> str:
        fields = dict(claim="review", data_source="unknown", ran_by="reviewer-agent", reviewer="reviewer-agent",
                      builder="builder-agent", reviewer_model="other-model", inspected=["git diff main...HEAD"], findings=[])
        fields.update(extra)
        return self.evidence(name, **fields)

    def close(self, action="check", *extra):
        return run_script("cgspec_hook.py", "close", action, "--slice", "SLICE-001", "--root", str(self.root), *extra)

    def blocked(self, needle: str):
        result = self.close()
        self.assertEqual(result.returncode, EXIT_BLOCK, result.stdout + result.stderr)
        self.assertIn(needle, result.stdout)
        return result.stdout

    def test_valid_completion_and_checklist(self):
        proof = self.evidence("signin-real")
        self.review()
        result = self.close()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        sheet = self.close("checklist", "--pr", "https://example.test/pull/9")
        self.assertEqual(sheet.returncode, 0, sheet.stdout + sheet.stderr)
        text = (self.root / "docs/_cgspec/06-evidence/closure/SLICE-001.md").read_text()
        self.assertIn("## OUT-work", text)
        self.assertIn(proof, text)
        self.assertIn("https://example.test/pull/9", text)
        self.assertIn("- [ ] Confirm: The declared check passes", text)

    def test_missing_proof_blocks(self):
        self.review()
        self.blocked("OUT-work: no passing evidence")

    def test_failed_and_blocked_proof_block(self):
        self.review()
        self.evidence("signin-real", verdict="FAIL")
        self.assertIn("is FAIL", self.blocked("OUT-work"))
        self.evidence("signin-real", verdict="BLOCKED", ran_at="2026-10-29T11:00:00Z")
        self.assertIn("is BLOCKED", self.blocked("OUT-work"))

    def test_later_pass_supersedes_earlier_failure(self):
        self.evidence("signin-real", verdict="FAIL")
        self.evidence("signin-real", ran_at="2026-10-29T11:00:00Z")
        self.review()
        self.assertEqual(self.close().returncode, 0)

    def test_mock_only_integration_claims_cannot_close(self):
        self.review()
        for source in ("fixture", "static", "unknown"):
            self.evidence("signin-real", data_source=source)
            self.assertIn("requires real-environment integration proof", self.blocked("OUT-work"))
        self.evidence("signin-real", claim="visual")
        self.assertIn("requires real-environment integration proof", self.blocked("OUT-work"))

    def test_builder_cannot_run_its_own_real_proof(self):
        self.evidence("signin-real", ran_by="builder-agent")
        self.review()
        self.assertIn("someone other than the builder", self.blocked("OUT-work"))

    def test_stale_evidence_cannot_close_later_changes(self):
        self.evidence("signin-real")
        self.review()
        self.assertEqual(self.close().returncode, 0)
        (self.root / "src/login/form.ts").write_text("export const f = 2;\n")
        self.commit("later change")
        out = self.blocked("no passing evidence for the current revision")
        self.assertIn("stale:", out)
        self.assertIn("no current independent review", out)

    def test_uncommitted_change_invalidates_evidence(self):
        self.evidence("signin-real")
        self.review()
        (self.root / "src/login/form.ts").write_text("export const f = 3;\n")
        self.blocked("no passing evidence")

    def test_bookkeeping_commits_do_not_invalidate(self):
        self.evidence("signin-real")
        self.review()
        self.commit("record evidence")
        self.assertEqual(self.close().returncode, 0)

    def test_review_must_be_independent_and_inspect_artifacts(self):
        self.evidence("signin-real")
        self.review(reviewer="builder-agent")
        self.assertIn("is the builder", self.blocked("no current independent review"))
        self.review(same_model_review=True)
        self.assertIn("declares same-model review", self.blocked("independent review"))
        self.review(inspected=[], reviewer_model="")
        out = self.blocked("independent review")
        self.assertIn("lists no inspected diff", out)
        self.assertIn("lacks reviewer_model", out)

    def test_unresolved_findings_block_until_resolved(self):
        self.evidence("signin-real")
        self.review(findings=[{"id": "F1", "severity": "major", "status": "open"}])
        self.assertIn("unresolved finding F1", self.blocked("review"))
        self.review(findings=[{"id": "F1", "severity": "major", "status": "resolved"}])
        self.blocked("unresolved finding F1")  # resolved without a recorded resolution still blocks
        self.review(findings=[{"id": "F1", "severity": "major", "status": "resolved", "resolution": "fixed in abc"}])
        self.assertEqual(self.close().returncode, 0)

    def test_review_must_cover_every_active_outcome(self):
        self.evidence("signin-real")
        self.review(covers=["OUT-other"])
        self.blocked("covering every active outcome")

    def test_run_completion_requires_closure_but_history_stays_readable(self):
        crit = self.root / "docs/_cgspec/05-runs/crit.md"
        crit.parent.mkdir(parents=True, exist_ok=True)
        crit.write_text("criteria\n")
        test = self.root / "tests/test_x.py"
        test.parent.mkdir(exist_ok=True)
        test.write_text("def test_x():\n    assert True\n")
        base = ("cgspec_hook.py", "run", "--root", str(self.root))
        frozen = run_script(*base, "freeze", "--goal", "Close the login slice", "--criteria", crit.relative_to(self.root).as_posix(),
                            "--tests", "tests/test_x.py", "--slice", "SLICE-001", "--run-id", "R-20261029-0001",
                            "--units", "[]")
        self.assertEqual(frozen.returncode, 0, frozen.stdout + frozen.stderr)
        run_json = self.root / "docs/_cgspec/05-runs/R-20261029-0001/run.json"
        self.assertEqual(json.loads(run_json.read_text())["closure"], "required")
        refused = run_script(*base, "complete", "R-20261029-0001")
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("cannot complete run", refused.stdout + refused.stderr)
        self.commit("freeze run and tests")
        self.evidence("signin-real")
        self.review()
        done = run_script(*base, "complete", "R-20261029-0001")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        # A historical run without the closure marker completes as before.
        legacy = json.loads(run_json.read_text())
        legacy.pop("closure")
        legacy.update(status="active", completed_at=None, run_id="R-20261029-0002")
        target = self.root / "docs/_cgspec/05-runs/R-20261029-0002/run.json"
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps(legacy))
        (self.root / "docs/_cgspec/05-runs/R-20261029-0001/run.json").unlink()
        self.assertEqual(run_script(*base, "complete", "R-20261029-0002").returncode, 0)


if __name__ == "__main__":
    unittest.main()
