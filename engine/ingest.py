#!/usr/bin/env python3
"""Evidence-first, partial source inventory; never an approved baseline.

Default: JSON to stdout, no writes. --output atomically replaces an explicitly
chosen manifest. --registry accepts a JSON array (or {"repositories": [...]}) of
{id, path}; relative repo paths resolve beside the registry. Missing satellites
are reported unavailable, never created. Exit 0: selected parsers ran without
known omissions; 2: partial/unavailable coverage or invalid input; 1: output I/O
failure. Even exit 0 is NOT complete architecture or behavioral discovery.
Python uses AST for selected syntactic candidates. SQL uses a limited DDL
heuristic. Other languages are explicitly unsupported, not silently parsed.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

MAX_FILE_BYTES = 1024 * 1024
IGNORE_DIRS = {'.git', '.hg', '.svn', 'node_modules', 'vendor', '.venv', 'venv',
               '__pycache__', 'target', 'dist', 'build', '.next', '.turbo',
               '.gemini', '.cgspec', '_cgspec', 'docs', 'templates', 'archive',
               'coverage', 'outputs', 'generated'}
SOURCE_SUFFIXES = {'.py', '.sql', '.js', '.ts', '.jsx', '.tsx', '.go', '.rs',
                   '.java', '.rb', '.php', '.cs', '.cpp', '.c', '.prisma', '.kt',
                   '.swift', '.sh', '.vue', '.svelte'}
METHODS = {'get', 'post', 'put', 'delete', 'patch', 'head', 'options', 'route'}


def validate_paths(target, subsystem=None, live_schema=None):
    root = Path(target).resolve(strict=True)
    if not root.is_dir():
        raise ValueError('target must be an existing directory')
    scan = (root / subsystem).resolve(strict=True) if subsystem else root
    if not scan.is_relative_to(root) or not scan.is_dir():
        raise ValueError('subsystem must be an existing directory within target')
    schema = (root / live_schema).resolve(strict=True) if live_schema else None
    if schema and (not schema.is_relative_to(root) or not schema.is_file()):
        raise ValueError('live schema must be an existing file within target')
    return root, scan, schema


def python_candidates(content, source):
    tree = ast.parse(content, filename=source)
    models, endpoints = [], []
    unresolved = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            bases = [b.id if isinstance(b, ast.Name) else b.attr
                     for b in node.bases if isinstance(b, (ast.Name, ast.Attribute))]
            if set(bases) & {'Model', 'BaseModel', 'Base', 'Document', 'Entity'}:
                fields = []
                for item in node.body:
                    targets = ([item.target] if isinstance(item, ast.AnnAssign)
                               else item.targets if isinstance(item, ast.Assign) else [])
                    fields.extend(t.id for t in targets if isinstance(t, ast.Name))
                models.append({'name': node.name, 'fields': fields, 'line': node.lineno,
                               'source_file': source, 'evidence': 'python_ast_candidate'})
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                if not (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute)
                        and dec.func.attr.lower() in METHODS):
                    continue
                path = dec.args[0] if dec.args else next(
                    (k.value for k in dec.keywords if k.arg in {'path', 'rule'}), None)
                if not (isinstance(path, ast.Constant) and isinstance(path.value, str)):
                    unresolved += 1
                    continue
                methods = [dec.func.attr.upper()]
                if dec.func.attr.lower() == 'route':
                    methods = ['UNSPECIFIED']
                    for k in dec.keywords:
                        if k.arg == 'methods':
                            try:
                                values = ast.literal_eval(k.value)
                                if isinstance(values, (list, tuple)) and all(isinstance(v, str) for v in values):
                                    methods = [v.upper() for v in values]
                            except (ValueError, TypeError):
                                unresolved += 1
                endpoints.append({'methods': methods, 'path': path.value,
                                  'handler': node.name, 'line': dec.lineno,
                                  'source_file': source, 'evidence': 'python_ast_candidate',
                                  'limitations': 'Receiver identity, router prefixes and runtime registration unresolved'})
    return {'models': models, 'endpoints': endpoints, 'unresolved_patterns': unresolved}


# Remove comments and literal strings before DDL matching; preserve quoted SQL
# identifiers. Dollar quoting is deliberately unsupported (no partial guessing).
SQL_TOKEN = re.compile(r"--[^\n]*|/\*[\s\S]*?\*/|'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|`(?:``|[^`])*`")
IDENT = r'(?:"(?:""|[^"])+"|`(?:``|[^`])+`|[A-Za-z_][\w$]*)'
QUALIFIED = IDENT + r'(?:\s*\.\s*' + IDENT + r')*'
TABLE = re.compile(r'\bCREATE\s+(?:TEMPORARY\s+|TEMP\s+|UNLOGGED\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(' + QUALIFIED + r')\s*\(', re.I)


def sql_candidates(content, source):
    if re.search(r'\$(?:[A-Za-z_][\w]*)?\$', content) or '[' in content:
        return {'database_tables': [], 'unsupported_reason': 'Dollar-quoted bodies or bracket identifiers require a dialect parser'}
    issue = sql_comment_issue(content)
    if issue:
        return {'database_tables': [], 'unsupported_reason': issue}
    clean = SQL_TOKEN.sub(lambda m: m.group() if m.group().startswith(('"', '`'))
                         else ''.join('\n' if c == '\n' else ' ' for c in m.group()), content)
    tables = []
    quoted_spans = [(m.start(), m.end()) for m in SQL_TOKEN.finditer(content)
                    if m.group().startswith(('\"', '`'))]
    for match in TABLE.finditer(clean):
        if any(start <= match.start() < end for start, end in quoted_spans):
            continue
        depth, end = 1, match.end()
        quote = None
        while end < len(clean) and depth:
            char = clean[end]
            if quote:
                if char == quote:
                    quote = None
            elif char in {'"', '`'}:
                quote = char
            elif char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
            end += 1
        if depth:
            return {'database_tables': tables, 'unsupported_reason': 'Unclosed CREATE TABLE body'}
        name = re.sub(r'\s*\.\s*', '.', match.group(1))
        tables.append({'table_name': name, 'source_file': source,
                       'line': clean.count('\n', 0, match.start()) + 1,
                       'evidence': 'sql_ddl_heuristic',
                       'limitations': 'Table-name candidates only; columns, constraints and dialect semantics not inferred'})
    return {'database_tables': tables}


def sql_comment_issue(content):
    """Reject comment syntax this intentionally small SQL lexer cannot parse safely."""
    i, depth, quote, line = 0, 0, None, False
    while i < len(content):
        pair = content[i:i + 2]
        char = content[i]
        if line:
            line = char != '\n'
        elif quote:
            if char == quote:
                if content[i + 1:i + 2] == quote:
                    i += 1
                else:
                    quote = None
        elif depth:
            if pair == '/*':
                return 'Nested SQL block comments require a dialect parser'
            if pair == '*/':
                depth = 0
                i += 1
        elif pair == '--':
            line = True
            i += 1
        elif pair == '/*':
            depth = 1
            i += 1
        elif char in ("'", '"', '`'):
            quote = char
        i += 1
    return 'Unclosed SQL block comment' if depth else None


def git_evidence(root):
    def git(*args):
        return subprocess.run(['git', '-c', 'core.fsmonitor=false', '-C', str(root), *args], capture_output=True,
                              text=True, timeout=10, env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'})
    try:
        top = git('rev-parse', '--show-toplevel')
        if top.returncode or Path(top.stdout.strip()).resolve() != root:
            return {'status': 'not_repository_root'}
        head = git('rev-parse', '--verify', 'HEAD')
        status = git('status', '--porcelain=v1', '--untracked-files=normal')
        return {'status': 'observed' if status.returncode == 0 else 'unavailable',
                'revision': head.stdout.strip() if head.returncode == 0 else None,
                'working_tree_porcelain': status.stdout.splitlines(),
                'limitation': 'Working tree may change during scan; no atomic repository snapshot'}
    except (OSError, subprocess.TimeoutExpired):
        return {'status': 'unavailable'}


def collect_candidates(root, scan, result):
    candidates = set()
    def walk_error(exc):
        result['issues'].append({'reason': 'Directory unreadable', 'error': type(exc).__name__})
    for base, dirs, files in os.walk(scan, followlinks=False, onerror=walk_error):
        for name in dirs:
            if name not in IGNORE_DIRS and Path(base, name).is_symlink():
                result['issues'].append({'path': str(Path(base, name).relative_to(root)),
                                         'reason': 'symlink directory skipped'})
        dirs[:] = sorted(d for d in dirs if d not in IGNORE_DIRS and not Path(base, d).is_symlink())
        for name in sorted(files):
            path = Path(base, name)
            if path.suffix.lower() in SOURCE_SUFFIXES:
                candidates.add(path)
    return candidates


def inspect_source(path, root, schema, output, result):
    rel = str(path.relative_to(root))
    source = {'path': rel}
    result['sources'].append(source)
    try:
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            source.update(status='skipped', reason='symlink or containment violation')
            return
        if output and path.resolve() == output:
            source.update(status='skipped', reason='explicit output excluded')
            return
        if path.stat().st_size > MAX_FILE_BYTES:
            source.update(status='skipped', reason='file exceeds 1 MiB limit')
            return
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, 'O_NOFOLLOW', 0))
        with os.fdopen(fd, 'rb') as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                source.update(status='skipped', reason='not a regular file')
                return
            data = handle.read(MAX_FILE_BYTES + 1)
        if len(data) > MAX_FILE_BYTES:
            source.update(status='skipped', reason='file grew beyond 1 MiB limit')
            return
        source.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        content = data.decode('utf-8')
        if path.suffix.lower() == '.py':
            evidence = python_candidates(content, rel)
            source['parser'] = 'python_ast_selected_patterns'
            if evidence.get('unresolved_patterns'):
                result['issues'].append({'path': rel, 'reason': 'dynamic Python patterns unresolved'})
        elif path.suffix.lower() == '.sql' or path == schema:
            evidence = sql_candidates(content, rel)
            source['parser'] = 'sql_ddl_heuristic'
        else:
            source.update(status='unsupported', reason='No validated parser for this language; file inventory only')
            return
        for key in ('models', 'endpoints', 'database_tables'):
            result[key].extend(evidence.get(key, []))
        source['status'] = 'unsupported' if evidence.get('unsupported_reason') else 'parsed'
        if evidence.get('unsupported_reason'):
            source['reason'] = evidence['unsupported_reason']
    except (OSError, UnicodeError, SyntaxError, ValueError, RecursionError) as exc:
        source.update(status='invalid', reason=type(exc).__name__)


def snapshot(root, scan, schema=None, output=None):
    result = {'project_root': str(root), 'scan_root': str(scan), 'approval': 'unreviewed',
              'coverage': 'partial', 'status': 'observed', 'git': git_evidence(root),
              'limitations': ['Selected syntax only; not a dependency, deployment, behavior or domain inventory',
                              'Excluded directory names: ' + ', '.join(sorted(IGNORE_DIRS)),
                              'No runtime discovery; inferred candidates need human/agent review'],
              'models': [], 'endpoints': [], 'database_tables': [], 'sources': [], 'issues': []}
    candidates = collect_candidates(root, scan, result)
    if schema:
        candidates.add(schema)
    for path in sorted(candidates):
        inspect_source(path, root, schema, output, result)
    result['source_counts'] = {key: sum(s.get('status') == key for s in result['sources'])
                               for key in ('parsed', 'invalid', 'unsupported', 'skipped')}
    result['source_counts']['total'] = len(result['sources'])
    if not result['sources']:
        result['issues'].append({'reason': 'No recognized source files found'})
    result['has_known_omissions'] = (bool(result['issues']) or any(
        s.get('status') != 'parsed' for s in result['sources']))
    return result


def write_manifest(manifest, output=None):
    text = json.dumps(manifest, indent=2, ensure_ascii=False) + '\n'
    if output is None:
        sys.stdout.write(text)
        return
    # Parent must exist: output is explicit, but never create a target tree.
    temp = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=output.parent,
                                         prefix='.cgspec-ingest-', delete=False) as handle:
            temp = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, output)
    finally:
        if temp and temp.exists():
            temp.unlink()


def registry_snapshot(args, output, manifest):
    if args.target_path or args.subsystem or args.live_schema:
        raise ValueError('registry cannot combine with target/subsystem/live-schema')
    registry = Path(args.registry).resolve(strict=True)
    if output == registry:
        raise ValueError('output cannot overwrite registry')
    entries = json.loads(registry.read_text(encoding='utf-8'))
    if isinstance(entries, dict):
        entries = entries.get('repositories')
    if not isinstance(entries, list) or not entries:
        raise ValueError('registry requires a nonempty repositories array')
    ids = set()
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get('id'), str) or not entry['id'].strip() or not isinstance(entry.get('path'), str) or not entry['path'].strip():
            raise ValueError('each repository needs nonempty string id and path')
        if entry['id'] in ids:
            raise ValueError('repository ids must be unique')
        ids.add(entry['id'])
    repositories = {}
    for entry in entries:
        target = registry.parent / entry['path']
        try:
            root, scan, schema = validate_paths(target)
        except (OSError, ValueError):
            repositories[entry['id']] = {'status': 'unavailable', 'path': str(target),
                                          'coverage': 'partial', 'approval': 'unreviewed'}
            continue
        if output and output.is_relative_to(root):
            raise ValueError('federation output must be outside satellite repositories')
        repositories[entry['id']] = snapshot(root, scan, schema, output)
    manifest['repositories'] = repositories
    return any(r.get('has_known_omissions', True) for r in repositories.values())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target_path', nargs='?')
    parser.add_argument('--subsystem')
    parser.add_argument('--live-schema')
    parser.add_argument('--registry', help='JSON repositories [{id,path}], relative paths beside registry')
    parser.add_argument('--output', help='Explicit JSON output; parent must already exist')
    args = parser.parse_args(argv)
    try:
        output = Path(args.output).absolute() if args.output else None
        if output and (output.is_symlink() or not output.parent.is_dir() or output.is_dir()):
            raise ValueError('output must be a regular file path with an existing parent, not a symlink')
        if output:
            output = output.resolve()
        manifest = {'schema_version': '2.0', 'observed_at': datetime.now(timezone.utc).isoformat(),
                    'approval': 'unreviewed', 'coverage': 'partial'}
        if args.registry:
            partial = registry_snapshot(args, output, manifest)
        else:
            root, scan, schema = validate_paths(args.target_path or '.', args.subsystem, args.live_schema)
            if output and (output == schema or output.suffix.lower() in SOURCE_SUFFIXES):
                raise ValueError('output must not overwrite source or live schema')
            manifest.update(snapshot(root, scan, schema, output))
            partial = manifest['has_known_omissions']
    except (OSError, ValueError, TypeError) as exc:
        print(f'Invalid inventory input: {exc}', file=sys.stderr)
        return 2
    try:
        write_manifest(manifest, output)
    except OSError as exc:
        print(f'Cannot write inventory: {exc}', file=sys.stderr)
        return 1
    return 2 if partial else 0


if __name__ == '__main__':
    sys.exit(main())
