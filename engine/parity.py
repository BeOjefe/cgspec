#!/usr/bin/env python3
"""Execute built-app state parity and walkthrough closure, failing closed on incomplete proof."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.request

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import browser
from _lib.common import CgspecError
from _lib.gitview import git
from _lib.parity_manifest import MANIFEST, digest, ui_paths, validate
import journey

LABELS = ('build_mode', 'data_source', 'authentication_method', 'mock_switch_state')


def diff_bytes(root, old, new, paths=None):
    args = ['git', '-c', 'core.quotepath=off', 'diff', '--binary', old, new]
    if paths: args += ['--', *paths]
    result = subprocess.run(args, cwd=root, capture_output=True)
    if result.returncode:
        raise CgspecError('cannot resolve exact binary diff for parity')
    return result.stdout


def local_file(root, rel):
    if not isinstance(rel, str) or Path(rel).is_absolute() or '..' in Path(rel).parts:
        raise CgspecError(f'expected project-relative file: {rel}')
    path = root / rel
    if any(p.is_symlink() for p in [path, *path.parents]) or not path.is_file():
        raise CgspecError(f'missing file or symlink: {rel}')
    return path


def command(value):
    if not isinstance(value, list) or not value or not all(isinstance(x, str) and x for x in value):
        raise CgspecError('app setup/build/serve commands must be non-empty argv lists')
    return value


@contextmanager
def served(root, app, output):
    """Build and serve inside the candidate worktree; stop the whole server process group."""
    process = None
    with (output / 'app.log').open('w') as log:
        try:
            for key in ('setup', 'build'):
                if key == 'setup' and key not in app:
                    continue
                subprocess.run(command(app.get(key)), cwd=root, stdout=log, stderr=log,
                               check=True, timeout=300)
            url = app.get('ready_url', '')
            if not url.startswith(('http://127.0.0.1:', 'http://localhost:')):
                raise CgspecError('app ready_url must be a loopback HTTP URL with a port')
            # Refuse a pre-existing server: its bytes cannot be attributed to this build.
            try:
                urllib.request.urlopen(url, timeout=1).close()
            except OSError:
                pass
            else:
                raise CgspecError('app port is already serving; cannot attribute proof to this build')
            process = subprocess.Popen(command(app.get('serve')), cwd=root, stdout=log, stderr=log,
                                       start_new_session=True)
            for _ in range(150):
                if process.poll() is not None:
                    raise CgspecError('built app server exited before readiness')
                try:
                    urllib.request.urlopen(url, timeout=1).close()
                    break
                except OSError:
                    time.sleep(.2)
            else:
                raise CgspecError('built app readiness timed out')
            yield url
        finally:
            if process is not None and process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()


def approval(root, entry, content, revision, diff_hash, registry=None):
    """Only a fresh approval for these exact bytes and this exact diff can accept drift."""
    expected = {'content_sha256': digest(content), 'revision': revision, 'diff_sha256': diff_hash}
    if not isinstance(entry, dict) or any(entry.get(k) != v for k, v in expected.items()):
        raise CgspecError('drift approval does not bind exact content, revision and diff')
    if not isinstance(entry.get('reviewer'), str) or not entry['reviewer'].strip():
        raise CgspecError('drift approval needs reviewer identity')
    try:
        when = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
        age = (datetime.now(timezone.utc) - when).total_seconds()
        if not 0 <= age <= 86400:
            raise ValueError('stale')
    except (KeyError, TypeError, ValueError):
        raise CgspecError('drift approval needs a fresh timezone-aware timestamp (24 hours)')
    # Reference a captured human approval; never turn a manifest label into approval.
    approvals = registry if registry is not None else json.loads(local_file(root, 'docs/_cgspec/07-state/approvals.json').read_text())
    source = next((x for x in approvals.get('approvals', []) if x.get('id') == entry.get('id')), None)
    if not source or any(source.get(k) != entry.get(k) for k in (*expected, 'reviewer', 'timestamp')):
        raise CgspecError('drift approval is not present with exact bindings in approvals.json')


def recorded_approval(root, binding, revision):
    registry = json.loads(local_file(root, 'docs/_cgspec/07-state/approvals.json').read_text())
    source = next((item for item in registry.get('approvals', []) if item.get('id') == binding.get('approval')), None)
    if not source or source.get('sha256') != binding.get('approval_sha256') or source.get('at') != binding.get('approved_at'):
        raise CgspecError('approval binding does not match the exact captured human approval')
    if binding.get('revision') != revision or not str(binding.get('reviewer', '')).strip():
        raise CgspecError('approval binding does not match exact revision and reviewer identity')
    try:
        when = datetime.fromisoformat(str(binding['approved_at']).replace('Z', '+00:00'))
        if when.tzinfo is None:
            raise ValueError('timezone missing')
    except (KeyError, TypeError, ValueError):
        raise CgspecError('approval binding needs a timezone-aware timestamp')
    if git(root, 'cat-file', '-e', f'{revision}^{{commit}}').returncode:
        raise CgspecError('approval revision is not a commit in this project')


def review(root, manifest, revision):
    binding = manifest['review']
    reviewed = binding['visual_revision']
    recorded_approval(root, binding, reviewed)
    if binding.get('builder') == binding.get('reviewer'):
        raise CgspecError('independent visual reviewer must differ from builder')
    content = {key: value for key, value in manifest.items() if key not in {'review', 'drift_approval'}}
    exists = git(root, 'merge-base', '--is-ancestor', reviewed, revision)
    changed = git(root, 'diff', '--quiet', reviewed, revision, '--', *manifest['covers'])
    reviewed_diff = diff_bytes(root, binding['base_revision'], reviewed, manifest['covers'])
    if exists.returncode or changed.returncode:
        raise CgspecError('covered application bytes changed after the bound visual and functional review')
    if binding.get('content_sha256') != digest(content) or binding.get('diff_sha256') != hashlib.sha256(reviewed_diff).hexdigest():
        raise CgspecError('visual review is not bound to exact manifest content and application diff')
    if binding.get('functional_revision') != reviewed:
        raise CgspecError('functional and visual review do not bind the same application revision')


def approved_baseline(root, screen, state_name, key, entry, revision):
    recorded_approval(root, entry, entry['revision'])
    path = local_file(root, entry['file'])
    if not path.resolve().is_relative_to((root / 'docs/prototypes/_baselines').resolve()):
        raise CgspecError('state baseline must be in baseline storage')
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    if sha != entry['sha256']:
        raise CgspecError(f'{state_name}: baseline hash mismatch')
    frozen = json.loads(local_file(root, 'docs/_cgspec/07-state/frozen.json').read_text())
    if not any(item.get('kind') == 'baseline' and item.get('path') == entry['file'] and item.get('sha256') == sha
               for item in frozen.get('entries', [])):
        raise CgspecError(f'{state_name}: baseline is not separately frozen at this hash')
    active = json.loads(local_file(root, 'docs/prototypes/_baselines/active.json').read_text())
    current = active.get('screens', {}).get(screen, {}).get('states', {}).get(state_name, {}).get(key)
    if not isinstance(current, dict) or any(current.get(field) != entry.get(field) for field in
            ('file', 'sha256', 'approval', 'approval_sha256', 'reviewer', 'approved_at', 'revision')):
        raise CgspecError(f'{state_name}: baseline is not the active approved {key} state baseline')
    return path


def artifact_labels(output, labels, revision):
    for path in output.iterdir():
        if path.suffix in {'.png', '.webm', '.log'}:
            path.with_name(path.name + '.json').write_text(json.dumps({**labels, 'revision': revision,
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}, indent=2))


def state_problems(result, run, state, manifest, output):
    problems = browser.proof_problems(run, result, output)
    drifted = False
    if problems:
        return problems, drifted
    for viewport in result['viewports']:
        controls = viewport.get('devControls', [])
        if controls and (manifest['build_mode'] == 'production' or manifest['data_source'] == 'real-backend'):
            problems.append(f'dev controls in production/real-backend proof: {controls}')
        if viewport.get('state') != state['name']:
            problems.append(f'{viewport["viewport"]}: wrong application state {viewport.get("state")!r}, expected {state["name"]!r}')
        for key in ('drift', 'darkDrift'):
            drift = viewport.get(key)
            if not isinstance(drift, dict) or drift.get('error') or not drift.get('totalPixels'):
                problems.append(f'{viewport["viewport"]}: incomplete {key} comparison')
            elif drift.get('differentDimensions') or drift.get('changedPixels'):
                drifted = True
    return problems, drifted


def run_state(root, state, manifest, output, url, revision, diff_hash, registry):
    data = journey.load(local_file(root, state['journey']), root)
    if not data['url'].startswith(url.rstrip('/') + '/') and data['url'] != url:
        raise CgspecError('built-app journey URL must use the provisioned server')
    if any('goto' in step and not str(step['goto']).startswith(url.rstrip('/') + '/') for step in data['steps']):
        raise CgspecError('journey navigation must stay on built app')
    if set(data['viewports']) != {'desktop', 'mobile'}:
        raise CgspecError('parity walkthrough must execute desktop and mobile')
    baselines = {key: str(approved_baseline(root, state['screen'], state['name'], key, entry,
                                            revision).resolve()) for key, entry in state['baselines'].items()}
    run = {'kind': 'audit', 'label': state['name'], 'url': data['url'], 'steps': data['steps'],
           'video': True, 'requiredOrigin': url, 'pixelTolerance': 0,
           'baselines': {vp: baselines[f'{vp}-light'] for vp in browser.AUDIT_VIEWPORTS},
           'darkBaselines': {vp: baselines[f'{vp}-dark'] for vp in browser.AUDIT_VIEWPORTS}}
    got = browser.run(root, [run], output, video=True)
    if got.get('blocked'):
        raise CgspecError(got['blocked'])
    result = browser.results_by_label(got).get(state['name'])
    problems, drifted = state_problems(result, run, state, manifest, output)
    content = {'manifest': {k: v for k, v in manifest.items() if k != 'drift_approval'}, 'state': state,
               'artifacts': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in output.glob(f'{state["name"]}-*.png')}}
    status = 'EXACT_MATCH'
    if drifted:
        approval(root, (registry or {}).get('approvals', [None])[-1], content, revision, diff_hash, registry)
        status = 'APPROVED_DRIFT'
    if manifest.get('two_account_claim'):
        from _lib.parity_auth import prove
        auth = prove(manifest.get('authorization'), url, revision)
        (output / f'{state["name"]}-authorization.json').write_text(json.dumps(auth, indent=2))
    return {'item': state['name'], 'verdict': 'FAIL' if problems else 'PASS',
            'detail': '; '.join(problems) if problems else status, 'revision': revision,
            **{k: manifest[k] for k in LABELS}, 'content_sha256': digest(content)}


def execute(root, base, output, approval_file=None):
    project = json.loads(local_file(root, 'docs/_cgspec/project.json').read_text())
    diff = diff_bytes(root, base, 'HEAD')
    changed = git(root, 'diff', '--name-only', '-z', '--no-renames', base, 'HEAD')
    if changed.returncode:
        raise CgspecError('cannot resolve actual diff for parity')
    paths = ui_paths(list(filter(None, changed.stdout.split('\0'))), project)
    if not paths:
        return [{'item': 'built-app parity', 'verdict': 'NOT_APPLICABLE', 'detail': 'no UI changes in actual diff'}]
    manifest = validate(json.loads(local_file(root, MANIFEST).read_text()), paths)
    revision = git(root, 'rev-parse', 'HEAD').stdout.strip()
    if git(root, 'status', '--porcelain', '--untracked-files=normal').stdout.strip():
        raise CgspecError('built-app proof requires a clean exact revision')
    registry = None
    if approval_file:
        approval_path = Path(approval_file).resolve()
        if approval_path.is_relative_to(root):
            raise CgspecError('drift approval file must be supplied outside candidate checkout')
        registry = json.loads(approval_path.read_text())
    output.mkdir(parents=True, exist_ok=True)
    labels = {k: manifest[k] for k in LABELS}
    diff_hash = hashlib.sha256(diff).hexdigest()
    review(root, manifest, revision)
    records = []
    with served(root, manifest.get('app', {}), output) as url:
        for state in manifest['states']:
            records.append(run_state(root, state, manifest, output, url, revision, diff_hash, registry))
            artifact_labels(output, labels, revision)
    artifact_labels(output, labels, revision)
    return records


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--base', required=True)
    parser.add_argument('--approval-file', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--json-out', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        records = execute(args.root.resolve(), args.base, args.out.resolve(), args.approval_file)
    except (CgspecError, OSError, ValueError, subprocess.SubprocessError) as exc:
        records = [{'item': 'built-app parity', 'verdict': 'FAIL', 'detail': str(exc)}]
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps({'schema': 1, 'records': records}, indent=2) + '\n')
    return 1 if any(r['verdict'] not in {'PASS', 'NOT_APPLICABLE'} for r in records) else 0


if __name__ == '__main__':
    sys.exit(main())
