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

    def test_notifies_on_agent_settled(self):
        """agent_settled is the only signal that Pi will not continue on its
        own. No other bridge in this repo uses it."""
        c = read(self.IDX)
        self.assertIn('pi.on("agent_settled"', c)

    def test_notification_is_best_effort(self):
        """A failed notification must never affect job state."""
        c = read(self.IDX)
        self.assertIn("ctx.ui?.notify?.(", c)

    def test_settle_notification_is_decided_by_the_pure_module(self):
        """Which jobs to announce is real logic with three learned conditions
        (this session only, nothing still running, never twice). It lives in
        notify.ts where node --test can exercise it; index.ts only wires it.
        The behaviour itself is covered by notify.test.ts, not by matching
        strings here."""
        c = read(self.IDX)
        self.assertIn('from "./notify.ts"', c)
        body = c[c.index('pi.on("agent_settled"'):]
        self.assertIn("settleNotification(", body)
        self.assertIn("finishedThisSession", body)
        self.assertIn("alreadyNotified", body)

    def test_job_is_recorded_before_it_is_spawned(self):
        """If pi dies between spawn() and the write, a record written afterwards
        never exists — and the detached process is untrackable: bg_cancel cannot
        see it and reconcile cannot report it. Written first, the worst case is
        a null pid, recoverable from the job's own pid file."""
        c = read(self.IDX)
        body = c[c.index('name: "bg_start"'):]
        self.assertLess(body.index("writeJob("), body.index("startDetached("))

    def test_pruning_runs_after_reconcile(self):
        """Retention must never delete a record before it has been reconciled
        and, if it finished unseen, reported."""
        c = read(self.IDX)
        body = c[c.index('pi.on("session_start"'):]
        self.assertLess(body.index("reconcile("), body.index("selectPrunable("))

    def test_cancel_verifies_process_identity_before_killing(self):
        """A pid is not an identity. Killing on the number alone means killTree
        can take down an unrelated process, and its whole tree, that merely
        inherited a finished job's pid."""
        c = read(self.IDX)
        body = c[c.index('name: "bg_cancel"'):]
        self.assertLess(body.index("isSameProcess("), body.index("killTree("))

    def test_poll_trusts_the_recorded_exit_code_over_the_pid(self):
        """The polling loop uses the cheap existence check by design — a
        process-identity probe costs ~0.34s and cannot run every two seconds —
        so the wrapper's own .rc must be checked first, or a recycled pid keeps
        a finished job 'running' until the timeout."""
        c = read(self.IDX)
        body = c[c.index("const poll = setInterval("):]
        self.assertLess(body.index("readExitCode("), body.index("isAlive("))

    def test_reconcile_consults_the_recorded_exit_code(self):
        """A job can finish in the instant pi is killed: no handler runs, but
        the shell wrapper's .rc file is already on disk. Reporting that as
        'orphaned' discards the only evidence the crash left, and turns a clean
        success into a failure."""
        c = read(self.IDX)
        body = c[c.index('pi.on("session_start"'):]
        self.assertIn("readExitCode(", body)

    def test_pending_results_are_injected_through_before_agent_start(self):
        """session_start is typed ExtensionHandler<SessionStartEvent> with no
        result type — anything returned from it is discarded. before_agent_start
        is the only hook whose result carries a `message`."""
        c = read(self.IDX)
        self.assertIn('pi.on("before_agent_start"', c)
        start = c.index('pi.on("session_start"')
        body = c[start:c.index("pi.on(", start + 10)]
        self.assertNotIn("return { message", body)
