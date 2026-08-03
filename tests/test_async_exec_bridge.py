import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


class TestAsyncExecBridgeSkeleton(unittest.TestCase):
    """The bridge dispatches long-running work, lets the agent stop, and wakes
    it when the work finishes. See
    docs/superpowers/specs/2026-08-03-async-resumable-execution-design.md"""

    IDX = "pi-extensions/async-exec-bridge/index.ts"
    PKG = "pi-extensions/async-exec-bridge/package.json"

    def test_package_is_esm_with_harness_root(self):
        pkg = read(self.PKG)
        self.assertIn('"type": "module"', pkg)
        self.assertIn("pi-harness", pkg)

    def test_index_exports_default_extension(self):
        c = read(self.IDX)
        self.assertIn("export default function", c)

    def test_listed_in_bridge_manifest(self):
        m = json.loads(read("pi-extensions/bridge-manifest.json"))
        names = [b["name"] for b in m["bridges"]]
        self.assertIn("async-exec-bridge", names)

    def test_run_directory_is_gitignored(self):
        """Job records and captured output are live state, not source. Without
        this every dispatch dirties `git status`."""
        self.assertIn(".pi/", read(".gitignore"))


class TestAsyncExecBridgeRestoreWiring(unittest.TestCase):
    def test_bridge_registered_and_managed(self):
        c = read("scripts/restore.py")
        self.assertIn('pi_extensions_root, "async-exec-bridge"', c)
        self.assertEqual(c.count('"async-exec-bridge"'), 3)
