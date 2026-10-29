"""Merge-resilient proof seals use real SSH signatures and disposable Git histories."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from tests.helpers import TempDir, git, git_project, write_json
from _lib.gitview import View
from _lib.proof_seals import canonical, digest, historical_pair_error, mapping_errors, record_errors, signer_policy_errors
from _lib.proof_commands import create_mapping, create_seal


@unittest.skipUnless(shutil.which("ssh-keygen"), "ssh-keygen unavailable")
class ProofSealTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.root = self._tmp.__enter__()
        git_project(self.root)
        self.keys = Path(tempfile.mkdtemp(prefix="cgspec-signing-"))
        self.addCleanup(shutil.rmtree, self.keys, True)
        self.private = self.keys / "ci"
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(self.private)], check=True)
        public = self.private.with_suffix(".pub").read_text().strip()
        project_path = self.root / "docs/_cgspec/project.json"
        project = json.loads(project_path.read_text())
        project["proof_signers"] = [{"identity": "ci@example", "public_key": public,
                                     "provider": "github", "workflow": "cgspec-proof.yml@main"}]
        write_json(project_path, project)
        git(self.root, "add", str(project_path))
        git(self.root, "commit", "-q", "-m", "trusted proof signer policy")
        self.base = git(self.root, "rev-parse", "HEAD").stdout.strip()
        (self.root / "tests/login.test.ts").parent.mkdir(exist_ok=True)
        (self.root / "tests/login.test.ts").write_text("test('login', () => {});\n")
        (self.root / "src/login/form.ts").write_text("export const f = 2;\n")
        self.pair_path = "docs/_cgspec/06-evidence/tests/login.json"
        self.pair = {"schema": 1, "test_id": "login", "test_file": "tests/login.test.ts",
                     "command": ["true"], "failed_at": "f" * 40, "passed_at": None,
                     "covers": ["src/login/form.ts"], "slice": "SLICE-001",
                     "recorded": "2026-10-29T00:00:00Z"}
        write_json(self.root / self.pair_path, self.pair)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "reviewed candidate")
        self.reviewed = git(self.root, "rev-parse", "HEAD").stdout.strip()
        self.seal_path = "docs/_cgspec/06-evidence/seals/login.json"
        self.seal = self._seal()
        write_json(self.root / self.seal_path, self.seal)
        git(self.root, "add", self.seal_path)
        git(self.root, "commit", "-q", "-m", "trusted pre-merge seal")
        self.branch = git(self.root, "branch", "--show-current").stdout.strip()

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def _sign(self, record):
        record["attestation"]["signature"] = ""
        with tempfile.NamedTemporaryFile(dir=self.keys, prefix="payload-", delete=False) as handle:
            handle.write(canonical(record))
            payload = Path(handle.name)
        subprocess.run(["ssh-keygen", "-Y", "sign", "-q", "-f", str(self.private),
                        "-n", "cgspec-proof", str(payload)], check=True)
        record["attestation"]["signature"] = payload.with_suffix(".sig").read_text()
        return record

    def _attestation(self):
        return {"identity": "ci@example", "provider": "github", "workflow": "cgspec-proof.yml@main",
                "run_id": "run-42", "signed_at": "2026-10-29T00:00:00Z", "signature": ""}

    def _seal(self):
        pair_raw = (self.root / self.pair_path).read_bytes()
        content = {path: hashlib.sha256((self.root / path).read_bytes()).hexdigest()
                   for path in ("src/login/form.ts", "tests/login.test.ts", "docs/_cgspec/project.json")}
        phase = lambda revision, result: {
            "revision": revision, "result": result, "detail_sha256": "a" * 64,
            "runner_id": "unit", "runner_hash": "b" * 64, "environment_hash": "c" * 64,
            "test_sha256": content["tests/login.test.ts"]}
        record = {"schema": 1, "seal_id": "SEAL-login", "test_pair": self.pair_path,
                  "test_pair_sha256": digest(pair_raw), "test_id": "login", "outcomes": ["OUT-login"],
                  "reviewed_base": self.base, "reviewed_head": self.reviewed,
                  "red": phase("f" * 40, "ASSERTION_FAILED"),
                  "green": phase(self.reviewed, "PASS"), "content": content,
                  "review": {"reviewer": "independent-reviewer", "revision": self.reviewed,
                             "record_sha256": "d" * 64}, "attestation": self._attestation()}
        return self._sign(record)

    def _integrate(self, change_source=False):
        git(self.root, "checkout", "-q", "-b", "integrated", self.base)
        git(self.root, "merge", "--squash", "-q", self.branch)
        if change_source:
            (self.root / "src/login/form.ts").write_text("export const f = 3;\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "integrated candidate")
        return git(self.root, "rev-parse", "HEAD").stdout.strip()

    def _revalidation_seal(self, integrated):
        seal = json.loads(json.dumps(self.seal))
        seal.update(seal_id="SEAL-login-revalidation", reviewed_head=integrated)
        seal["review"]["revision"] = integrated
        seal["green"]["revision"] = integrated
        seal["content"]["src/login/form.ts"] = hashlib.sha256(
            (self.root / "src/login/form.ts").read_bytes()).hexdigest()
        self._sign(seal)
        path = self.root / "docs/_cgspec/06-evidence/seals/login-revalidation.json"
        write_json(path, seal)
        git(self.root, "add", str(path))
        git(self.root, "commit", "-q", "-m", "revalidate integrated difference")
        return path.relative_to(self.root).as_posix()

    def _mapping(self, integrated, strategy="squash", difference=None):
        seal_raw = (self.root / self.seal_path).read_bytes()
        record = {"schema": 1, "map_id": "MAP-login", "seal": self.seal_path,
                  "seal_sha256": digest(seal_raw), "strategy": strategy,
                  "integrated_revision": integrated, "pull_request": "github:43",
                  "differences": [difference] if difference else [], "mapped_at": "2026-10-29T00:00:00Z",
                  "attestation": self._attestation()}
        return self._sign(record)

    def _commit_mapping(self, mapping):
        path = self.root / "docs/_cgspec/06-evidence/integrations/login.json"
        write_json(path, mapping)
        git(self.root, "add", str(path))
        git(self.root, "commit", "-q", "-m", "map trusted proof")
        return git(self.root, "rev-parse", "HEAD").stdout.strip()

    def test_valid_squash_and_unavailable_red_object(self):
        from _lib.ci_gate import prove_failed
        integrated = self._integrate()
        head = self._commit_mapping(self._mapping(integrated))
        view = View.commit(self.root, head)
        self.assertIsNone(historical_pair_error(view, self.pair_path, self.pair))
        self.assertEqual(record_errors(view, view.changes()), [])
        sealed_pair = dict(self.pair, _file=self.pair_path)
        self.assertIsNone(prove_failed(self.root, sealed_pair))

    def test_valid_rebase_mapping(self):
        integrated = self._integrate()
        mapping = self._mapping(integrated, strategy="rebase")
        project = json.loads((self.root / "docs/_cgspec/project.json").read_text())
        self.assertEqual(mapping_errors(self.root, mapping, (self.root / self.seal_path).read_bytes(), project), [])

    def test_merge_and_merge_queue_strategies_are_explicit(self):
        integrated = self._integrate()
        project = json.loads((self.root / "docs/_cgspec/project.json").read_text())
        for strategy in ("merge", "merge-queue"):
            with self.subTest(strategy=strategy):
                mapping = self._mapping(integrated, strategy=strategy)
                self.assertEqual(mapping_errors(self.root, mapping, (self.root / self.seal_path).read_bytes(), project), [])

    def test_changed_content_without_revalidation_fails(self):
        integrated = self._integrate(change_source=True)
        mapping = self._mapping(integrated)
        project = json.loads((self.root / "docs/_cgspec/project.json").read_text())
        errors = mapping_errors(self.root, mapping, (self.root / self.seal_path).read_bytes(), project)
        self.assertTrue(any("without an exact mapping" in error for error in errors), errors)

    def test_changed_content_with_signed_revalidation_passes(self):
        integrated = self._integrate(change_source=True)
        revalidation = self._revalidation_seal(integrated)
        sealed_hash = self.seal["content"]["src/login/form.ts"]
        integrated_hash = hashlib.sha256((self.root / "src/login/form.ts").read_bytes()).hexdigest()
        difference = {"path": "src/login/form.ts", "sealed_sha256": sealed_hash,
                      "integrated_sha256": integrated_hash, "revalidation": revalidation}
        mapping = self._mapping(integrated, difference=difference)
        project = json.loads((self.root / "docs/_cgspec/project.json").read_text())
        self.assertEqual(mapping_errors(self.root, mapping, (self.root / self.seal_path).read_bytes(), project), [])

    def test_missing_and_untrusted_attestation_fail_closed(self):
        integrated = self._integrate()
        mapping = self._mapping(integrated)
        mapping["attestation"]["signature"] = ""
        project = json.loads((self.root / "docs/_cgspec/project.json").read_text())
        self.assertTrue(mapping_errors(self.root, mapping, (self.root / self.seal_path).read_bytes(), project))
        mapping = self._mapping(integrated)
        mapping["attestation"]["identity"] = "rogue@example"
        self.assertTrue(any("not uniquely trusted" in error for error in
                            mapping_errors(self.root, mapping, (self.root / self.seal_path).read_bytes(), project)))

    def test_signed_seal_cannot_misstate_test_identity_or_red_revision(self):
        integrated = self._integrate()
        project = json.loads((self.root / "docs/_cgspec/project.json").read_text())
        for field, value, expected in (("test_id", "other", "test_id"),
                                       ("red", dict(self.seal["red"], revision="e" * 40), "failed_at")):
            with self.subTest(field=field):
                seal = json.loads(json.dumps(self.seal))
                seal[field] = value
                self._sign(seal)
                raw = (json.dumps(seal, indent=2, sort_keys=True) + "\n").encode()
                mapping = self._mapping(integrated)
                mapping["seal_sha256"] = digest(raw)
                self._sign(mapping)
                errors = mapping_errors(self.root, mapping, raw, project)
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_original_seal_and_mapping_are_immutable(self):
        integrated = self._integrate()
        head = self._commit_mapping(self._mapping(integrated))
        path = self.root / "docs/_cgspec/06-evidence/integrations/login.json"
        data = json.loads(path.read_text())
        data["pull_request"] = "rewritten"
        write_json(path, data)
        git(self.root, "add", str(path))
        view = View.staged(self.root)
        self.assertTrue(any("immutable" in reason for reason in record_errors(view, view.changes())))

    def test_signer_policy_cannot_bootstrap_itself_in_ci(self):
        errors = signer_policy_errors(View.commit(self.root, self.base))
        self.assertTrue(any("protected baseline" in error for error in errors), errors)

    def test_trusted_cli_creates_seal_and_mapping(self):
        artifacts = self.keys / "artifacts"
        artifacts.mkdir()
        fingerprints = {"runner": "b" * 64, "environment": "c" * 64, "inputs": {}}
        red = {"revision": "f" * 40, "result": "ASSERTION_FAILED", "runner_id": "unit",
               "proof_file": self.pair_path, "test_id": "login", "candidate_revision": self.reviewed,
               "test_sha256": self.seal["content"]["tests/login.test.ts"], "fingerprints": fingerprints}
        green = dict(red, revision=self.reviewed, result="PASS")
        review = {"schema": 1, "check": "independent-review", "revision": self.reviewed,
                  "verdict": "PASS", "ran_at": "2026-10-29T00:00:00Z", "ran_by": "reviewer"}
        for name, value in (("red", red), ("green", green), ("review", review)):
            write_json(artifacts / f"{name}.json", value)
        output = artifacts / "seal.json"
        common = {"identity": "ci@example", "provider": "github", "workflow": "cgspec-proof.yml@main",
                  "run_id": "run-43", "signing_key": str(self.private), "output": str(output)}
        args = Namespace(pair=str(self.root / self.pair_path), red=str(artifacts / "red.json"),
                         green=str(artifacts / "green.json"), review=str(artifacts / "review.json"),
                         outcomes="OUT-login", seal_id="SEAL-cli", pair_path=self.pair_path,
                         base=self.base, **common)
        create_seal(self.root, args)
        generated, generated_raw = json.loads(output.read_text()), output.read_bytes()
        project = json.loads((self.root / "docs/_cgspec/project.json").read_text())
        from _lib.proof_seals import seal_errors
        self.assertEqual(seal_errors(generated, project), [])
        integrated = self._integrate()
        mapped = artifacts / "map.json"
        map_args = Namespace(seal=str(output), seal_path="docs/_cgspec/06-evidence/seals/cli.json",
                             map_id="MAP-cli", strategy="squash", integrated_revision=integrated,
                             pull_request="github:43", revalidation={}, output=str(mapped), **{
                                 key: value for key, value in common.items() if key != "output"})
        create_mapping(self.root, map_args)
        self.assertEqual(mapping_errors(self.root, json.loads(mapped.read_text()), generated_raw, project), [])


if __name__ == "__main__":
    unittest.main()
