"""Every schema accepts a realistic valid document and rejects the defects we care about."""

from __future__ import annotations

import copy
import unittest

from tests import helpers  # noqa: F401  (sets sys.path)
from _lib.schema import validate_named

H64 = "a" * 64
NOW = "2026-10-18T21:40:00Z"

VALID = {
    "project": {
        "schema": 1, "cgspec_version": "0.2.0", "profile": "web-workspace", "topology": "single",
        "path_classes": {"schema": ["db/**"], "api": ["src/api/**"], "auth": ["src/auth/**"],
                         "deps": ["package.json"], "code": ["src/**"], "tests": ["tests/**"], "docs": ["docs/**"]},
        "tools": ["claude", "git", "ci"],
    },
    "tier": {"schema": 1, "active": {"id": "T-20261018-0c1d", "tier": "T0", "reason": "fix typo",
                                      "files": ["src/a.ts"], "created": NOW}},
    "start": {"schema": 1, "slice": "SLICE-004", "version": 1, "status": "Draft", "goal": "A member can sign in",
              "outcomes": [{"id": "OUT-login", "statement": "Valid sign-in reaches the workspace", "covers": ["src/login/**"],
                            "accept": ["Valid credentials succeed"], "reject": ["Invalid credentials fail"],
                            "evaluation": {"method": "Exercise the real API", "requires_real": True,
                                           "data_source": "real_backend", "proof": ["logs"]},
                            "development": {"uses_mocks": False, "data_source": "real_backend"}}],
              "exclusions": [], "constraints": [], "design": {"required": False, "target": None, "states": []},
              "prerequisites": [], "approval": None, "prior_approvals": [],
              "readiness": {"definition_hash": "", "mocks_allowed": False, "ran_at": None, "checks": []},
              "active_outcomes": [], "drafted_at": NOW, "drafted_ns": 1, "updated": NOW},
    "run": {"schema": 1, "run_id": "R-20261018-77be", "tier": "T2", "goal": "login screen",
            "criteria": [{"path": "docs/_cgspec/05-runs/R-20261018-77be/criteria.md", "sha256": H64}],
            "tests": [{"path": "tests/login.test.ts", "sha256": H64}],
            "units": [{"id": "u1", "owner": "builder-1", "allowed_paths": ["src/login/**"], "status": "todo"}],
            "frozen_at": NOW, "approval": {"source": "message-hook", "ref": "inbox#42", "at": NOW}},
    "frozen": {"schema": 1, "entries": [{"path": "docs/prototypes/_snapshots/home-v1.html", "sha256": H64,
                                          "kind": "snapshot", "added": NOW, "reason": "layer 3 locked"}]},
    "checks-manifest": {"schema": 1, "checks": [{"id": "CHK-001", "path": "docs/_cgspec/04-checks/no_raw_hex.py",
                                                 "sha256": H64, "command": ["python3", "{path}"], "applies_to": ["src/**"],
                                                 "approval": {"source": "commit-trailer", "ref": "abc1234", "at": NOW},
                                                 "added": NOW}]},
    "checkpoint": {"schema": 1, "updated": NOW, "goal": "v0.1", "stages": {"web": "design"},
                   "next_action": "lock layer 3", "in_flight": None, "wakeup": None},
    "budget": {"schema": 1, "task": "SLICE-004", "limits": {"helpers": 3, "review_rounds": 3, "research_passes": 2},
               "used": {"helpers": 0, "review_rounds": 1, "research_passes": 0}},
    "quota": {"schema": 1, "read_at": NOW, "source": "claude-statusline",
              "five_hour": {"used_pct": 40.5}, "weekly": {"used_pct": 12}},
    "test-pair": {"schema": 1, "test_id": "tests/login.test.ts::rejects_empty", "test_file": "tests/login.test.ts",
                  "command": ["npx", "vitest", "run"], "failed_at": "abc1234", "passed_at": None,
                  "covers": ["src/login/form.ts"], "slice": "SLICE-004", "recorded": NOW},
    "evidence": {"schema": 1, "check": "doctor", "revision": "abc1234", "verdict": "PASS", "ran_at": NOW, "ran_by": "ci"},
    "legacy-baseline": {"schema": 1, "created": NOW, "files": {"src/old.js": {"sha256": H64, "lines": 900}}},
}

# (schema, mutation description, function producing an invalid doc)
INVALID = [
    ("project", "unknown profile", lambda d: d.update(profile="desktop")),
    ("project", "missing path class", lambda d: d["path_classes"].pop("auth")),
    ("project", "bad version", lambda d: d.update(cgspec_version="2.0")),
    ("tier", "unknown tier", lambda d: d["active"].update(tier="T4")),
    ("tier", "old sequential id", lambda d: d["active"].update(id="T-001")),
    ("tier", "extra key", lambda d: d["active"].update(skip_gates=True)),
    ("start", "acceptance example missing", lambda d: d["outcomes"][0].update(accept=[])),
    ("start", "unknown lifecycle state", lambda d: d.update(status="Complete")),
    ("run", "T0 run", lambda d: d.update(tier="T0")),
    ("run", "short hash", lambda d: d["criteria"][0].update(sha256="abc")),
    ("run", "agent-invented approval source", lambda d: d["approval"].update(source="agent")),
    ("run", "too many review rounds", lambda d: d["units"][0].update(review_rounds=4)),
    ("frozen", "unknown kind", lambda d: d["entries"][0].update(kind="whatever")),
    ("checks-manifest", "check outside 04-checks", lambda d: d["checks"][0].update(path="docs/gen.py")),
    ("checks-manifest", "missing approval", lambda d: d["checks"][0].pop("approval")),
    ("checkpoint", "unknown stage", lambda d: d["stages"].update(web="polish")),
    ("budget", "negative count", lambda d: d["used"].update(helpers=-1)),
    ("quota", "pct over 100", lambda d: d["five_hour"].update(used_pct=120)),
    ("test-pair", "no covered files", lambda d: d.update(covers=[])),
    ("test-pair", "non-sha revision", lambda d: d.update(failed_at="yesterday")),
    ("evidence", "made-up verdict", lambda d: d.update(verdict="LGTM")),
    ("legacy-baseline", "negative lines", lambda d: d["files"]["src/old.js"].update(lines=-1)),
]


class SchemaTests(unittest.TestCase):
    def test_valid_documents_pass(self):
        for name, doc in VALID.items():
            with self.subTest(schema=name):
                self.assertEqual(validate_named(doc, name), [])

    def test_invalid_documents_fail(self):
        for name, label, mutate in INVALID:
            with self.subTest(schema=name, defect=label):
                doc = copy.deepcopy(VALID[name])
                mutate(doc)
                self.assertNotEqual(validate_named(doc, name), [], f"{name}: {label} was accepted")

    def test_null_tier_is_valid(self):
        self.assertEqual(validate_named({"schema": 1, "active": None}, "tier"), [])

    def test_bool_is_not_integer(self):
        doc = copy.deepcopy(VALID["budget"])
        doc["used"]["helpers"] = True
        self.assertNotEqual(validate_named(doc, "budget"), [])


if __name__ == "__main__":
    unittest.main()
