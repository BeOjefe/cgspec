import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[2] / 'engine/ingest.py'
spec = importlib.util.spec_from_file_location('inventory_ingest', SCRIPT)
ingest = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ingest)


class IngestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / 'repo'
        self.repo.mkdir()

    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = ingest.main(list(map(str, args)))
        return code, json.loads(out.getvalue()) if out.getvalue() else None, err.getvalue()

    def test_default_read_only_ast_candidates_no_invented_dynamic_path(self):
        (self.repo / 'app.py').write_text('''# @app.get('/comment')
s = "@app.get('/string')"
@app.get(path='/real')
async def real(): pass
@router.get(PREFIX)
def dynamic(): pass
class Item(BaseModel):
    name: str
''')
        before = sorted(p.relative_to(self.repo) for p in self.repo.rglob('*'))
        code, data, _ = self.run_cli(self.repo)
        self.assertEqual(code, 2)
        self.assertEqual([e['path'] for e in data['endpoints']], ['/real'])
        self.assertEqual(data['models'][0]['fields'], ['name'])
        self.assertEqual(data['approval'], 'unreviewed')
        self.assertEqual(len(data['sources'][0]['sha256']), 64)
        self.assertEqual(before, sorted(p.relative_to(self.repo) for p in self.repo.rglob('*')))

    def test_unsupported_js_does_not_invent_commented_or_string_route(self):
        (self.repo / 'app.js').write_text('// app.get("/ghost", fn);\nconst s = "router.post(\'/fake\', fn)";')
        code, data, _ = self.run_cli(self.repo)
        self.assertEqual(code, 2)
        self.assertEqual(data['endpoints'], [])
        self.assertEqual(data['source_counts']['unsupported'], 1)

    def test_schema_qualified_sql_and_nested_parentheses(self):
        (self.repo / 'schema.sql').write_text('''-- CREATE TABLE ghost (id int);
SELECT 'CREATE TABLE fake (id int);';
SELECT "CREATE TABLE quoted_fake (id int)";
CREATE TABLE IF NOT EXISTS "public"."users" (id integer, amount decimal(10,2));
CREATE TABLE app.orders (id int);
''')
        code, data, _ = self.run_cli(self.repo, '--live-schema', 'schema.sql')
        self.assertEqual(code, 0)
        self.assertEqual([t['table_name'] for t in data['database_tables']], ['"public"."users"', 'app.orders'])
        self.assertEqual(data['source_counts']['total'], 1)
        self.assertEqual(data['coverage'], 'partial')

    def test_nested_sql_comment_never_invents_a_table(self):
        (self.repo / 'schema.sql').write_text('''/* outer
  /* inner */
  CREATE TABLE ghost (id int);
*/
CREATE TABLE real (id int);
''')
        code, data, _ = self.run_cli(self.repo)
        self.assertEqual(code, 2)
        self.assertNotIn('ghost', [t['table_name'] for t in data['database_tables']])
        self.assertTrue(data['has_known_omissions'])

    def test_unclosed_sql_quotes_and_mysql_comments_are_not_candidates(self):
        for content in ("SELECT 'unfinished\nCREATE TABLE ghost (id int);\n",
                        'SELECT "unfinished\nCREATE TABLE ghost (id int);\n',
                        '# CREATE TABLE ghost (id int);\n'):
            with self.subTest(content=content):
                (self.repo / 'schema.sql').write_text(content)
                code, data, _ = self.run_cli(self.repo)
                self.assertEqual(code, 2)
                self.assertEqual(data['database_tables'], [])
                self.assertEqual(data['source_counts']['unsupported'], 1)

    def test_backslash_escaped_sql_literal_does_not_invent_table(self):
        (self.repo / 'schema.sql').write_text(r"SELECT E'\' CREATE TABLE ghost(id int); \'';" + '\n')
        code, data, _ = self.run_cli(self.repo)
        self.assertEqual(code, 2)
        self.assertEqual(data['database_tables'], [])
        self.assertEqual(data['source_counts']['unsupported'], 1)

    def test_git_inventory_does_not_execute_fsmonitor(self):
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        (self.repo / 'app.py').write_text('x = 1')
        marker = self.base / 'executed'
        hook = self.base / 'monitor.sh'
        hook.write_text(f'#!/bin/sh\ntouch "{marker}"\n')
        hook.chmod(0o755)
        subprocess.run(['git', '-C', str(self.repo), 'config', 'core.fsmonitor', str(hook)], check=True)
        self.run_cli(self.repo)
        self.assertFalse(marker.exists())

    def test_named_pipe_never_blocks_inventory(self):
        if not hasattr(os, 'mkfifo'):
            self.skipTest('FIFO unavailable')
        os.mkfifo(self.repo / 'pipe.py')
        proc = subprocess.run(['python3', str(SCRIPT), str(self.repo)], capture_output=True,
                              text=True, timeout=2)
        self.assertEqual(proc.returncode, 2)
        data = json.loads(proc.stdout)
        self.assertEqual(data['source_counts']['skipped'], 1)

    def test_named_pipe_registry_is_rejected_without_blocking(self):
        if not hasattr(os, 'mkfifo'):
            self.skipTest('FIFO unavailable')
        pipe = self.base / 'registry.json'
        os.mkfifo(pipe)
        proc = subprocess.run(['python3', str(SCRIPT), '--registry', str(pipe)],
                              capture_output=True, text=True, timeout=2)
        self.assertEqual(proc.returncode, 2)

    def test_named_pipe_output_is_preserved(self):
        if not hasattr(os, 'mkfifo'):
            self.skipTest('FIFO unavailable')
        (self.repo / 'app.py').write_text('x = 1\n')
        pipe = self.base / 'output.json'
        os.mkfifo(pipe)
        code, _, _ = self.run_cli(self.repo, '--output', pipe)
        self.assertEqual(code, 2)
        self.assertTrue(pipe.is_fifo())

    def test_output_cannot_replace_recognized_infrastructure_source(self):
        (self.repo / 'app.py').write_text('x = 1\n')
        for name in ('Dockerfile', 'main.tf', 'package.json'):
            with self.subTest(name=name):
                source = self.repo / name
                source.write_text('original\n')
                code, _, _ = self.run_cli(self.repo, '--output', source)
                self.assertEqual(code, 2)
                self.assertEqual(source.read_text(), 'original\n')

    def test_output_cannot_replace_unrelated_json_config(self):
        (self.repo / 'app.py').write_text('x = 1\n')
        config = self.repo / 'settings.json'
        config.write_text('{"secret": "keep"}\n')
        code, _, _ = self.run_cli(self.repo, '--output', config)
        self.assertEqual(code, 2)
        self.assertEqual(config.read_text(), '{"secret": "keep"}\n')

    def test_output_created_during_scan_is_never_replaced(self):
        (self.repo / 'app.py').write_text('x = 1\n')
        output = self.base / 'inventory.json'
        actual_snapshot = ingest.snapshot

        def intervening_snapshot(*args):
            output.write_text('{"secret": "later"}\n')
            return actual_snapshot(*args)

        with patch.object(ingest, 'snapshot', side_effect=intervening_snapshot):
            code, _, _ = self.run_cli(self.repo, '--output', output)
        self.assertEqual(code, 2)
        self.assertEqual(output.read_text(), '{"secret": "later"}\n')

    def test_existing_manifest_changed_during_scan_is_preserved(self):
        (self.repo / 'app.py').write_text('x = 1\n')
        output = self.base / 'inventory.json'
        output.write_text('{"schema_version":"2.0","approval":"unreviewed"}\n')
        actual_snapshot = ingest.snapshot

        def intervening_snapshot(*args):
            output.write_text('{"schema_version":"2.0","approval":"unreviewed","new":true}\n')
            return actual_snapshot(*args)

        with patch.object(ingest, 'snapshot', side_effect=intervening_snapshot):
            code, _, _ = self.run_cli(self.repo, '--output', output)
        self.assertEqual(code, 2)
        self.assertIn('"new":true', output.read_text())

    def test_infrastructure_files_are_explicit_unsupported_coverage(self):
        (self.repo / 'app.py').write_text('x = 1\n')
        (self.repo / 'Dockerfile').write_text('FROM scratch\n')
        (self.repo / 'main.tf').write_text('resource "x" "y" {}\n')
        code, data, _ = self.run_cli(self.repo)
        self.assertEqual(code, 2)
        self.assertEqual(data['source_counts']['unsupported'], 2)
        self.assertTrue(data['has_known_omissions'])

    def test_invalid_target_preserves_stale_output(self):
        output = self.base / 'old.json'
        output.write_text('old')
        for args in [(self.base / 'missing',), (self.repo, '--subsystem', '../'),
                     (self.repo, '--subsystem', 'missing'),
                     (self.repo, '--live-schema', 'missing.sql')]:
            code, data, _ = self.run_cli(*args, '--output', output)
            self.assertEqual(code, 2)
            self.assertIsNone(data)
            self.assertEqual(output.read_text(), 'old')
        self.assertFalse((self.base / 'missing').exists())

    def test_live_schema_cannot_escape(self):
        (self.base / 'external.sql').write_text('CREATE TABLE x (id int);')
        code, _, _ = self.run_cli(self.repo, '--live-schema', '../external.sql')
        self.assertEqual(code, 2)

    def test_invalid_python_and_unsupported_sql_explicit(self):
        (self.repo / 'bad.py').write_text('class :')
        (self.repo / 'body.sql').write_text('DO $$ BEGIN CREATE TABLE x(id int); END $$;')
        code, data, _ = self.run_cli(self.repo)
        self.assertEqual(code, 2)
        self.assertEqual(data['source_counts']['invalid'], 1)
        self.assertEqual(data['source_counts']['unsupported'], 1)

    def test_size_exclusions_and_symlink_escape(self):
        (self.repo / 'huge.py').write_bytes(b' ' * (ingest.MAX_FILE_BYTES + 1))
        outside = self.base / 'outside.py'
        outside.write_text("@app.get('/escape')\ndef f(): pass")
        (self.repo / 'link.py').symlink_to(outside)
        for folder in ('docs', 'templates', 'vendor', 'node_modules'):
            (self.repo / folder).mkdir()
            (self.repo / folder / 'bad.py').write_text('invalid ?')
        code, data, _ = self.run_cli(self.repo)
        self.assertEqual(code, 2)
        self.assertEqual(data['source_counts']['total'], 2)
        self.assertEqual(data['source_counts']['skipped'], 2)
        self.assertEqual(data['endpoints'], [])

    def test_federation_uses_ids_and_reports_missing_without_satellite_writes(self):
        (self.repo / 'ok.py').write_text('x = 1')
        registry = self.base / 'registry.json'
        registry.write_text(json.dumps({'repositories': [{'id': 'api', 'path': 'repo'}, {'id': 'web', 'path': 'missing'}]}))
        output = self.base / 'central.json'
        code, _, _ = self.run_cli('--registry', registry, '--output', output)
        self.assertEqual(code, 2)
        data = json.loads(output.read_text())
        self.assertEqual(set(data['repositories']), {'api', 'web'})
        self.assertEqual(data['repositories']['web']['status'], 'unavailable')
        self.assertFalse((self.base / 'missing').exists())
        self.assertEqual([p.name for p in self.repo.iterdir()], ['ok.py'])
        self.assertEqual(list(self.base.glob('.cgspec-ingest-*')), [])

    def test_invalid_registry_preserves_output_and_rejects_satellite_output(self):
        registry = self.base / 'registry.json'
        registry.write_text(json.dumps([{'id': 'same', 'path': 'repo'}, {'id': 'same', 'path': 'repo'}]))
        output = self.base / 'old.json'
        output.write_text('old')
        self.assertEqual(self.run_cli('--registry', registry, '--output', output)[0], 2)
        self.assertEqual(output.read_text(), 'old')
        registry.write_text(json.dumps([{'id': 'api', 'path': 'repo'}]))
        self.assertEqual(self.run_cli('--registry', registry, '--output', self.repo / 'manifest.json')[0], 2)
        self.assertFalse((self.repo / 'manifest.json').exists())

    def test_git_root_vs_nested_directory(self):
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        (self.repo / 'a.py').write_text('x = 1')
        _, data, _ = self.run_cli(self.repo)
        self.assertEqual(data['git']['status'], 'observed')
        self.assertIsNone(data['git']['revision'])
        self.assertTrue(data['git']['working_tree_porcelain'])
        child = self.repo / 'child'
        child.mkdir()
        (child / 'b.py').write_text('y = 2')
        self.assertEqual(self.run_cli(child)[1]['git']['status'], 'not_repository_root')

    def test_no_sources_not_silent_success_and_source_overwrite_rejected(self):
        self.assertEqual(self.run_cli(self.repo)[0], 2)
        source = self.repo / 'a.py'
        source.write_text('x = 1')
        self.assertEqual(self.run_cli(self.repo, '--output', source)[0], 2)
        self.assertEqual(source.read_text(), 'x = 1')


if __name__ == '__main__':
    unittest.main()
