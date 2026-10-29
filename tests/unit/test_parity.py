"""Regression coverage for #29's closure bypasses."""
import copy
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
import unittest
from unittest.mock import patch
from tests.helpers import TempDir, git, git_project, write_json
from _lib.parity_manifest import validate, gate, MANIFEST, digest
from _lib.gitview import Change
from _lib.common import CgspecError
from _lib import browser
import parity


def manifest():
    binding = {'approval': 'A-20261029-abcd', 'approval_sha256': 'b' * 64,
               'reviewer': 'reviewer@example.test', 'approved_at': '2026-10-29T00:00:00Z',
               'revision': 'c' * 40}
    return {'schema': 1, 'covers': ['src/**'], 'build_mode': 'production', 'data_source': 'fixtures',
             'authentication_method': 'none', 'mock_switch_state': 'absent',
             'app': {'build': ['build-app'], 'serve': ['serve-app'], 'ready_url': 'http://127.0.0.1:9876'},
             'states': [{'name': 'invoice-v1', 'screen': 'invoice', 'route': '/invoices', 'data_set': 'invoice-v1',
                         'journey': 'docs/prototypes/invoice/journeys/v1.json',
                         'baselines': {f'{vp}-{theme}': {'file': f'docs/prototypes/_baselines/invoice-v1-{vp}-{theme}.png',
                                                       'sha256': 'a' * 64, **binding}
                                       for vp in ('desktop', 'mobile') for theme in ('light', 'dark')}}],
             'review': {**binding, 'builder': 'builder@example.test', 'base_revision': 'd' * 40,
                        'functional_revision': 'c' * 40, 'visual_revision': 'c' * 40,
                        'content_sha256': 'e' * 64, 'diff_sha256': 'f' * 64}}


class ParityTests(unittest.TestCase):
    def test_missing_and_nonmatching_manifest_block_actual_ui_diff(self):
        class View:
            def read_new(self, path):
                return self.raw
        view = View()
        for data in (None, {**manifest(), 'covers': ['other/**']}):
            view.raw = json.dumps(data).encode()
            self.assertTrue(gate(view, [Change('M', 'src/app.tsx')], {'profile': 'web-workspace'}))
        view.raw = json.dumps(manifest()).encode()
        self.assertEqual(gate(view, [Change('M', 'src/app.tsx')], {'profile': 'web-workspace'}), [])

    def test_every_state_requires_every_theme_and_viewport(self):
        data = manifest()
        validate(data, ['src/app.tsx'])
        for key in data['states'][0]['baselines']:
            broken = copy.deepcopy(data)
            del broken['states'][0]['baselines'][key]
            with self.assertRaises(CgspecError):
                validate(broken, ['src/app.tsx'])
        data['states'].append(copy.deepcopy(data['states'][0]))
        with self.assertRaises(CgspecError):
            validate(data, ['src/app.tsx'])

    def test_proof_rejects_runtime_and_console_errors_even_with_artifacts(self):
        run = {'kind': 'audit', 'label': 'x'}
        with TempDir() as root:
            with patch.object(browser, '_proved', return_value=True):
                got = {'viewports': [{'viewport': vp, 'errors': ['console error: broken']} for vp in ('desktop', 'mobile')]}
                self.assertIn('console error', '; '.join(browser.proof_problems(run, got, root)))

    def test_approval_exact_binding_identity_and_freshness(self):
        content = {'state': 'v1', 'pixels': 'hash'}
        entry = {'id': 'human-1', 'content_sha256': digest(content), 'revision': 'a' * 40,
                 'diff_sha256': 'b' * 64, 'reviewer': 'reviewer@example.test',
                 'timestamp': datetime.now(timezone.utc).isoformat()}
        with TempDir() as root:
            write_json(root / 'docs/_cgspec/07-state/approvals.json', {'approvals': [entry]})
            parity.approval(root, entry, content, 'a' * 40, 'b' * 64)
            for field, value in [('content_sha256', 'c' * 64), ('revision', 'c' * 40), ('diff_sha256', 'c' * 64),
                                 ('reviewer', ''), ('timestamp', (datetime.now(timezone.utc) - timedelta(days=2)).isoformat())]:
                with self.subTest(field=field), self.assertRaises(CgspecError):
                    parity.approval(root, {**entry, field: value}, content, 'a' * 40, 'b' * 64)

    def test_dev_switch_labels_cannot_claim_real_two_account_closure(self):
        data = manifest()
        data.update(two_account_claim=True, data_source='real-backend', authentication_method='dev-switch',
                    mock_switch_state='enabled', authorization={})
        with self.assertRaisesRegex(CgspecError, 'two-account'):
            validate(data, ['src/app.tsx'])


class ParityClosureTests(unittest.TestCase):
    PNG = b'\x89PNG\r\n\x1a\nproof'
    WEBM = b'\x1a\x45\xdf\xa3proof'

    def setUp(self):
        self.tmp = TempDir(); self.root = self.tmp.__enter__(); git_project(self.root)
        self.base = git(self.root, 'rev-parse', 'HEAD').stdout.strip()
        (self.root / 'src').mkdir(exist_ok=True); (self.root / 'src/app.tsx').write_text('export const app = 1;\n')
        journey_path = self.root / 'docs/prototypes/invoice/journeys/v1.json'
        journey_path.parent.mkdir(parents=True)
        write_json(journey_path, {'name': 'invoice-v1', 'url': 'http://127.0.0.1:9876/invoices',
                                  'viewports': ['desktop', 'mobile'],
                                  'steps': [{'state': 'invoice-v1'}, {'focus': 'customer'},
                                            {'screenshot': 'ready'}]})
        git(self.root, 'add', '-A'); git(self.root, 'commit', '-q', '-m', 'application revision')
        self.app_revision = git(self.root, 'rev-parse', 'HEAD').stdout.strip()
        approval = {'id': 'A-20261029-abcd', 'at': '2026-10-29T00:00:00+00:00',
                    'excerpt': 'approved exact invoice proof', 'sha256': 'b' * 64}
        write_json(self.root / 'docs/_cgspec/07-state/approvals.json', {'schema': 1, 'approvals': [approval]})
        bind = {'approval': approval['id'], 'approval_sha256': approval['sha256'],
                'reviewer': 'reviewer@example.test', 'approved_at': approval['at'],
                'revision': self.app_revision}
        baselines, active = {}, {'schema': 1, 'screens': {'invoice': {'states': {'invoice-v1': {'version': 1}}}}}
        frozen = json.loads((self.root / 'docs/_cgspec/07-state/frozen.json').read_text())
        for vp in ('desktop', 'mobile'):
            for theme in ('light', 'dark'):
                key = f'{vp}-{theme}'; rel = f'docs/prototypes/_baselines/invoice-v1-v1-{vp}{"-dark" if theme == "dark" else ""}.png'
                path = self.root / rel; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(self.PNG)
                entry = {'file': rel, 'sha256': hashlib.sha256(self.PNG).hexdigest(), **bind}
                baselines[key] = entry; active['screens']['invoice']['states']['invoice-v1'][key] = entry
                frozen['entries'].append({'path': rel, 'sha256': entry['sha256'], 'kind': 'baseline',
                                          'added': approval['at'], 'reason': 'approved invoice-v1 baseline'})
        write_json(self.root / 'docs/_cgspec/07-state/frozen.json', frozen)
        write_json(self.root / 'docs/prototypes/_baselines/active.json', active)
        self.data = {'schema': 1, 'covers': ['src/**'], 'build_mode': 'production', 'data_source': 'fixtures',
                     'authentication_method': 'none', 'mock_switch_state': 'absent',
                     'app': {'build': ['build-app'], 'serve': ['serve-app'], 'ready_url': 'http://127.0.0.1:9876'},
                     'states': [{'name': 'invoice-v1', 'screen': 'invoice', 'route': '/invoices',
                                 'data_set': 'invoice-v1', 'journey': journey_path.relative_to(self.root).as_posix(),
                                 'baselines': baselines}]}
        content_hash = digest(self.data)
        diff = git(self.root, 'diff', '--binary', self.base, self.app_revision, '--', 'src/**').stdout
        self.data['review'] = {**bind, 'builder': 'builder@example.test', 'base_revision': self.base,
                               'functional_revision': self.app_revision, 'visual_revision': self.app_revision,
                               'content_sha256': content_hash, 'diff_sha256': hashlib.sha256(diff.encode()).hexdigest()}
        write_json(self.root / MANIFEST, self.data)
        git(self.root, 'add', '-A'); git(self.root, 'commit', '-q', '-m', 'approved parity records')
        self.output = self.root.parent / f'{self.root.name}-proof'

    def tearDown(self):
        import shutil
        shutil.rmtree(self.output, ignore_errors=True); self.tmp.__exit__(None, None, None)

    def driver(self, state='invoice-v1', drift=0, video=True, controls=None):
        record_video = video
        def run(root, runs, output, video=False):
            output.mkdir(parents=True, exist_ok=True); results = []
            for item in runs:
                viewports = []
                for vp in ('desktop', 'mobile'):
                    prefix = f'{item["label"]}-{vp}'
                    for stale in output.glob(f'{prefix}*'):
                        if stale.is_file(): stale.unlink()
                    for suffix in ('.png', '-dark.png', '-ready.png'):
                        (output / f'{prefix}{suffix}').write_bytes(self.PNG)
                    if record_video: (output / f'{prefix}.webm').write_bytes(self.WEBM)
                    comp = {'changedPixels': drift, 'totalPixels': 100, 'differentDimensions': False}
                    viewports.append({'viewport': vp, 'state': state, 'errors': [], 'darkErrors': [],
                                      'devControls': controls or [], 'drift': comp, 'darkDrift': comp})
                results.append({'label': item['label'], 'viewports': viewports})
            return {'results': results}
        return run

    def execute(self, driver=None, approval_file=None):
        with patch.object(parity, 'served') as served, patch.object(browser, 'run', side_effect=driver or self.driver()):
            served.return_value.__enter__.return_value = 'http://127.0.0.1:9876'
            return parity.execute(self.root, self.base, self.output, approval_file)

    def test_valid_exact_match_and_wrong_state(self):
        self.assertEqual(self.execute()[0]['detail'], 'EXACT_MATCH')
        with self.assertRaisesRegex(CgspecError, 'wrong application state'):
            records = self.execute(self.driver(state='loading'))
            if records[0]['verdict'] == 'FAIL': raise CgspecError(records[0]['detail'])

    def test_missing_baseline_and_absent_interaction_recording_block(self):
        (self.root / self.data['states'][0]['baselines']['desktop-light']['file']).unlink()
        git(self.root, 'add', '-A'); git(self.root, 'commit', '-q', '-m', 'missing baseline')
        with self.assertRaisesRegex(CgspecError, 'missing file'):
            self.execute()
        git(self.root, 'checkout', 'HEAD^', '--', self.data['states'][0]['baselines']['desktop-light']['file'])
        git(self.root, 'add', '-A'); git(self.root, 'commit', '-q', '-m', 'restore baseline')
        records = self.execute(self.driver(video=False))
        self.assertEqual(records[0]['verdict'], 'FAIL'); self.assertIn('video', records[0]['detail'])

    def test_unapproved_and_approved_drift_are_distinct(self):
        with self.assertRaisesRegex(CgspecError, 'drift approval'):
            self.execute(self.driver(drift=2))
        # Exact external approval can accept this already-built revision without trusting candidate code.
        self.execute(self.driver())
        manifest_data = json.loads((self.root / MANIFEST).read_text())
        state = manifest_data['states'][0]
        artifacts = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.output.glob('invoice-v1-*.png')}
        content = {'manifest': {k: v for k, v in manifest_data.items() if k != 'drift_approval'},
                   'state': state, 'artifacts': artifacts}
        revision = git(self.root, 'rev-parse', 'HEAD').stdout.strip()
        diff = parity.diff_bytes(self.root, self.base, 'HEAD')
        approval = {'id': 'visual-review', 'content_sha256': digest(content), 'revision': revision,
                    'diff_sha256': hashlib.sha256(diff).hexdigest(), 'reviewer': 'visual@example.test',
                    'timestamp': datetime.now(timezone.utc).isoformat()}
        outside = self.root.parent / f'{self.root.name}-approval.json'; write_json(outside, {'approvals': [approval]})
        try:
            self.assertEqual(self.execute(self.driver(drift=2), outside)[0]['detail'], 'APPROVED_DRIFT')
        finally:
            outside.unlink(missing_ok=True)

    def test_detected_dev_controls_reject_real_or_production_claim(self):
        records = self.execute(self.driver(controls=['mock URL parameter', 'view-as-user']))
        self.assertEqual(records[0]['verdict'], 'FAIL'); self.assertIn('dev controls', records[0]['detail'])


@unittest.skipUnless(os.environ.get('CGSPEC_RUN_WEB_INTEGRATION') == '1',
                     'set CGSPEC_RUN_WEB_INTEGRATION=1 for real Chromium integration')
class ParityBrowserIntegrationTests(unittest.TestCase):
    def test_real_dom_detection_finds_hidden_switchers_mock_urls_and_console_errors(self):
        with TempDir() as root:
            page = root / 'page.html'
            page.write_text('''<!doctype html><html><body>
              <select hidden data-testid="view-as-user"><option>Other</option></select>
              <a href="/?mock_user=other">Mock account</a>
              <script>console.error("integration-console-error")</script>
              </body></html>''')
            output = root / 'shots'
            run = {'kind': 'audit', 'label': 'dev-controls', 'url': page.as_uri() + '?view_as=other',
                   'steps': [], 'video': False}
            result = browser.run(root, [run], output)
            self.assertNotIn('blocked', result, result)
            item = browser.results_by_label(result)['dev-controls']
            for viewport in item['viewports']:
                self.assertTrue(any('mock' in value.lower() or 'view-as' in value.lower()
                                    for value in viewport['devControls']), viewport)
                self.assertTrue(any('integration-console-error' in value for value in viewport['errors']), viewport)
