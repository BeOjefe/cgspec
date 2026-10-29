"""Supersession must preserve approval, pair identity and executable replacement proof."""
from __future__ import annotations

import copy
import json
import unittest
from unittest.mock import patch

from tests.integration import test_test_evolution as evolution
from tests.helpers import approve, git, write_json
from _lib import ci_gate, commit_gate, run_supersession, runs
from _lib.gitview import View


class SupersessionIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = evolution.TestEvolutionIntegrationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.root = self.fixture.root
        self.old_pair = self.fixture.record['_file']
        self.fixture._commit_record()
        write_json(self.root / 'docs/slices/SLICE-001-feature.start.json', {'outcomes': [{'id': 'OUT-one'}]})
        (self.root / 'docs/criteria.md').write_text('Keep required behavior\n')
        self.old = runs.freeze_run(self.root, 'Old architecture', 'T2', ['docs/criteria.md'], ['tests/check.py'], [],
                                   run_id='R-20261029-0001', slice_id='SLICE-001', outcomes=['OUT-one'],
                                   proof_paths=[self.old_pair])
        self.commit('freeze old active run')
        source = self.fixture.test_file.read_text().replace('tests/check.py', 'tests/new.py')
        (self.root / 'tests/new.py').write_text(source)
        (self.root / 'src/fixed.txt').unlink()
        self.commit('replacement red')
        red = git(self.root, 'rev-parse', 'HEAD').stdout.strip()
        (self.root / 'src/fixed.txt').write_text('fixed\n')
        self.commit('replacement green')
        self.new_pair = 'docs/_cgspec/06-evidence/tests/replacement.json'
        pair = {k: v for k, v in self.fixture.record.items() if k != '_file'}
        pair.update(schema=1, test_file='tests/new.py', selector='tests/new.py', test_id='tests/new.py::test_original',
                    command=['python3', 'tests/new.py', '{report}'], failed_at=red, recorded='2026-10-29T00:00:00Z')
        write_json(self.root / self.new_pair, pair)
        approval = approve(self.root, 'approve supersession R-20261029-0001 to R-20261029-0002')
        self.new = runs.freeze_run(self.root, 'New architecture', 'T2', ['docs/criteria.md'], ['tests/new.py'], [],
                                   run_id='R-20261029-0002', slice_id='SLICE-001', outcomes=['OUT-one'],
                                   proof_paths=[self.new_pair], supersession={
            'replaces': self.old['run_id'], 'reason': 'replace architecture', 'approval_ref': approval,
            'links': {'agreements': [{'old': 'docs/criteria.md', 'new': 'docs/criteria.md'}],
                      'outcomes': [{'old': 'OUT-one', 'new': 'OUT-one'}],
                      'tests': [{'old': 'tests/check.py', 'new': 'tests/new.py'}],
                      'proofs': [{'old': self.old_pair, 'new': self.new_pair}]}})

    def commit(self, message):
        git(self.root, 'add', '-A')
        git(self.root, 'commit', '-q', '-m', message)

    def retire(self):
        runs.supersede_run(self.root, self.old['run_id'], self.new['run_id'])
        self.commit('approved transition')

    def test_retirement_replays_replacement_and_allows_removed_historical_test(self):
        self.retire()
        self.fixture.test_file.unlink()
        self.commit('remove superseded test')
        self.assertTrue(ci_gate._proof_superseded(self.root, self.old_pair))
        project = json.loads((self.root / 'docs/_cgspec/project.json').read_text())
        self.assertEqual(commit_gate._test_pairs(View.commit(self.root, 'HEAD'), [],
                         {'tier': 'T2', 'slice': 'SLICE-001'}, project['path_classes'], project), [])
        with patch.object(ci_gate, 'prove_failed', return_value='replacement still fails') as replay:
            self.assertFalse(ci_gate._proof_superseded(self.root, self.old_pair))
            self.assertEqual(replay.call_args.args[1]['_file'], self.new_pair)

    def test_new_terminal_run_cannot_manufacture_transition(self):
        # Move the frozen old run to another path so it is newly introduced terminal history.
        old_path = self.root / f"docs/_cgspec/05-runs/{self.old['run_id']}/run.json"
        runs.supersede_run(self.root, self.old['run_id'], self.new['run_id'])
        terminal = json.loads(old_path.read_text())
        terminal['run_id'] = 'R-20261029-0003'
        terminal_path = self.root / 'docs/_cgspec/05-runs/R-20261029-0003/run.json'
        write_json(terminal_path, terminal)
        git(self.root, 'add', '-A')
        self.assertTrue(any('newly added runs must start active' in e for e in runs.check_run_commit(View.staged(self.root))))
        self.commit('fabricated terminal run')
        # A freshly added terminal run has no validated transition, even if links exist.
        self.new['supersession']['replaces'] = terminal['run_id']
        write_json(self.root / f"docs/_cgspec/05-runs/{self.new['run_id']}/run.json", self.new)
        self.commit('point at fabricated old run')
        self.assertFalse(ci_gate._proof_superseded(self.root, self.old_pair))

    def test_self_nonpair_and_legacy_replacement_links_fail_closed(self):
        for target in (self.old_pair, 'docs/criteria.md'):
            new = copy.deepcopy(self.new)
            new['supersession']['links']['proofs'][0]['new'] = target
            self.assertTrue(run_supersession.proof_link_errors(self.old, new, lambda p: (self.root / p).read_bytes()))
        pair = json.loads((self.root / self.new_pair).read_text())
        pair.pop('test_semantics')
        write_json(self.root / self.new_pair, pair)
        self.assertTrue(any('fresh semantic proof' in e for e in run_supersession.proof_link_errors(
            self.old, self.new, lambda p: (self.root / p).read_bytes())))

    def test_omitted_and_empty_outcomes_cannot_retire_required_outcome(self):
        for inventory in (None, []):
            old = copy.deepcopy(self.old)
            if inventory is None:
                old.pop('outcomes')
            else:
                old['outcomes'] = inventory
            errors = run_supersession.outcome_errors(old, lambda p: (self.root / p).read_bytes(),
                          ['docs/slices/SLICE-001-feature.start.json'])
            self.assertTrue(errors)
        data = runs.freeze_run(self.root, 'Unknown inventory', 'T1', [], [], [], run_id='R-20261029-0004')
        self.assertNotIn('outcomes', data)

    def test_proof_links_must_follow_frozen_run_test_mapping(self):
        new = copy.deepcopy(self.new)
        new['supersession']['links']['tests'][0]['new'] = 'tests/some-other.py'
        self.assertTrue(any('frozen old/new test mapping' in e for e in run_supersession.proof_link_errors(
            self.old, new, lambda p: (self.root / p).read_bytes())))
        old = copy.deepcopy(self.old)
        old['tests'] = [{'path': 'tests/some-other.py'}]
        self.assertTrue(any('match the old run' in e for e in run_supersession.proof_link_errors(
            old, self.new, lambda p: (self.root / p).read_bytes())))

    def test_malformed_links_return_errors(self):
        for links in (None, [None], {}, 'bad', [{'old': self.old_pair, 'new': []}],
                      [{'old': self.old_pair, 'new': {}}]):
            new = copy.deepcopy(self.new)
            new['supersession']['links']['proofs'] = links
            self.assertTrue(run_supersession.proof_link_errors(self.old, new, lambda _: None))

    def test_unapproved_transition_cannot_retire_proof(self):
        self.retire()
        replacement = self.root / f"docs/_cgspec/05-runs/{self.new['run_id']}/run.json"
        data = json.loads(replacement.read_text())
        data['supersession']['approval']['ref'] = 'missing'
        write_json(replacement, data)
        self.commit('tamper approval')
        self.assertFalse(ci_gate._proof_superseded(self.root, self.old_pair))
