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


class TestAsyncExecBridgeTools(unittest.TestCase):
    IDX = "pi-extensions/async-exec-bridge/index.ts"

    def test_registers_the_three_tools(self):
        """Pi's registerTool takes one object with a `name` field. Asserting on a
        `registerTool("bg_start"` call shape would pin an API that does not
        exist."""
        c = read(self.IDX)
        for tool in ("bg_start", "bg_status", "bg_cancel"):
            self.assertIn(f'name: "{tool}"', c)

    def test_bg_start_declares_its_parameters(self):
        """A tool without a TypeBox `parameters` schema cannot receive arguments,
        so the model would have no way to say what to run."""
        c = read(self.IDX)
        self.assertIn("parameters: Type.Object(", c)
        self.assertIn("cmd:", c)

    def test_dispatch_runs_preflight_before_spawning(self):
        c = read(self.IDX)
        self.assertLess(c.index("preflight("), c.index("startDetached("))

    def test_result_is_written_before_the_wake_attempt(self):
        """Waking can fail and be retried; state cannot. Anchored inside wake()
        because the file header quotes pi.sendMessage in prose, which a
        whole-file index would match first."""
        c = read(self.IDX)
        body = c[c.index("function wake("):]
        self.assertLess(body.index("writeJob("), body.index("pi.sendMessage("))

    def test_pending_results_are_injected_through_before_agent_start(self):
        """session_start is typed ExtensionHandler<SessionStartEvent> with no
        result type — anything returned from it is discarded. before_agent_start
        is the only hook whose result carries a `message`."""
        c = read(self.IDX)
        self.assertIn('pi.on("before_agent_start"', c)
        start = c.index('pi.on("session_start"')
        body = c[start:c.index("pi.on(", start + 10)]
        self.assertNotIn("return { message", body)
