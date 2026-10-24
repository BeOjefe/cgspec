"""bundle_prototype.py (spec 6 versions, spec 8 frozen): self-contained, frozen milestone snapshots."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import stat
import unittest

from tests.helpers import TempDir, approve, doctor, git_project, run_script

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")


def bundle(root, *args):
    return run_script("bundle_prototype.py", *args, "--root", str(root))


class BundleTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.root = r = self._tmp.__enter__()
        git_project(r)
        src = r / "docs/prototypes/invoice"
        (src / "img").mkdir(parents=True)
        (src / "index.html").write_text(
            '<!doctype html><html><head><link rel="stylesheet" href="style.css"></head>'
            '<body><img src="img/dot.png" alt="dot"><script src="app.js"></script></body></html>')
        (src / "style.css").write_text("body { color: #333; }\n")
        (src / "app.js").write_text("document.body.dataset.ready = '1';\n")
        (src / "img/dot.png").write_bytes(PNG)

    def tearDown(self):
        # Only snapshots are made read-only by these tests. Walking the whole
        # repository also enters .git before an in-loop skip can exclude it.
        for p in (self.root / "docs/prototypes/_snapshots").glob("*"):
            if p.is_file() and not p.is_symlink():
                os.chmod(p, 0o644)
        self._tmp.__exit__(None, None, None)

    def cut(self, *extra):
        return bundle(self.root, "invoice", "--layer", "2", "--approval", approve(self.root, "approved, lock layer 2"), *extra)

    def frozen(self):
        return json.loads((self.root / "docs/_cgspec/07-state/frozen.json").read_text())["entries"]

    def test_cut_is_self_contained_frozen_and_recorded(self):
        result = self.cut()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        snap = self.root / "docs/prototypes/_snapshots/invoice-v1.html"
        html = snap.read_text()
        self.assertIn("body { color: #333; }", html)
        self.assertIn("document.body.dataset.ready", html)
        self.assertIn("data:image/png;base64,", html)
        self.assertNotIn('href="style.css"', html)
        self.assertNotIn('src="app.js"', html)
        self.assertFalse(snap.stat().st_mode & stat.S_IWUSR)
        entry = [e for e in self.frozen() if e["path"].endswith("invoice-v1.html")]
        self.assertEqual(len(entry), 1)
        self.assertEqual(entry[0]["kind"], "snapshot")
        self.assertEqual(entry[0]["sha256"], hashlib.sha256(snap.read_bytes()).hexdigest())
        self.assertIn("layer 2", entry[0]["reason"])
        self.assertIn("invoice v1", (self.root / "docs/_memlog.md").read_text())
        self.assertEqual(doctor(self.root).returncode, 0, doctor(self.root).stdout)

    def test_next_cut_is_v2_and_v1_untouched(self):
        self.cut()
        v1 = (self.root / "docs/prototypes/_snapshots/invoice-v1.html").read_bytes()
        (self.root / "docs/prototypes/invoice/style.css").write_text("body { color: #111; }\n")
        self.assertEqual(self.cut().returncode, 0)
        self.assertEqual((self.root / "docs/prototypes/_snapshots/invoice-v1.html").read_bytes(), v1)
        self.assertIn("#111", (self.root / "docs/prototypes/_snapshots/invoice-v2.html").read_text())
        self.assertEqual(len([e for e in self.frozen() if "invoice-v" in e["path"]]), 2)

    def test_fake_approval_refused_and_nothing_written(self):
        result = bundle(self.root, "invoice", "--layer", "2", "--approval", "A-20261019-deadbeef")
        self.assertEqual(result.returncode, 1)
        self.assertFalse((self.root / "docs/prototypes/_snapshots/invoice-v1.html").exists())

    def test_remote_resource_refused(self):
        (self.root / "docs/prototypes/invoice/index.html").write_text(
            '<html><head><script src="https://cdn.example.com/x.js"></script></head></html>')
        result = self.cut()
        self.assertEqual(result.returncode, 1)
        self.assertIn("cdn.example.com", result.stdout + result.stderr)
        self.assertFalse((self.root / "docs/prototypes/_snapshots/invoice-v1.html").exists())

    def test_missing_local_file_and_escape_refused(self):
        (self.root / "docs/prototypes/invoice/index.html").write_text('<html><script src="../../secret.js"></script></html>')
        self.assertEqual(self.cut().returncode, 1)
        (self.root / "docs/prototypes/invoice/index.html").write_text('<html><script src="gone.js"></script></html>')
        result = self.cut()
        self.assertEqual(result.returncode, 1)
        self.assertIn("gone.js", result.stdout + result.stderr)

    def test_unknown_screen_and_bad_layer(self):
        self.assertEqual(bundle(self.root, "nope", "--layer", "2", "--approval", approve(self.root, "approved")).returncode, 1)
        self.assertNotEqual(bundle(self.root, "invoice", "--layer", "9", "--approval", "x").returncode, 0)


if __name__ == "__main__":
    unittest.main()
