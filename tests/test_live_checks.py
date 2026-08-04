"""The two live checks (e2e, lifecycle) need pi, an installed bridge and a
model server. A hosted CI runner has none of those, so they skip there.

A check that always skips is worth nothing, which is exactly the risk of putting
them in CI. These tests are what stops that: they RUN both scripts for real
against a closed port and assert the skip path behaves — so the part of the
check that CI can execute is genuinely executed, and the escape hatch that makes
a skip impossible is proven to work.
"""

import os
import shutil
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKS = [
    "pi-extensions/async-exec-bridge/e2e-check.sh",
    "pi-extensions/async-exec-bridge/lifecycle-check.sh",
]
# Port 1 is reserved and never listening, so the preflight cannot reach a server.
DEAD_BASE = "http://127.0.0.1:1"


def bash():
    return shutil.which("bash")


def run(script, env_extra, timeout=120):
    env = dict(os.environ)
    env.update(env_extra)
    return subprocess.run(
        [bash(), script],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


@unittest.skipIf(bash() is None, "bash is not available")
class TestLiveChecksSkipCleanly(unittest.TestCase):
    def test_scripts_are_executable_shell(self):
        for rel in CHECKS + ["pi-extensions/async-exec-bridge/live-preflight.sh"]:
            path = os.path.join(ROOT, rel)
            self.assertTrue(os.path.isfile(path), "%s is missing" % rel)
            proc = subprocess.run([bash(), "-n", path], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, "%s is not valid shell: %s" % (rel, proc.stderr))

    def test_skips_with_exit_zero_when_no_model_server(self):
        """CI must stay green without a model, but must say why it skipped —
        a silent pass and a real pass would otherwise look identical."""
        for rel in CHECKS:
            with self.subTest(check=rel):
                proc = run(rel, {"ASYNC_EXEC_API_BASE": DEAD_BASE})
                self.assertEqual(
                    proc.returncode, 0,
                    "%s should skip, not fail:\n%s\n%s" % (rel, proc.stdout, proc.stderr),
                )
                self.assertIn("SKIP:", proc.stdout, "the skip must be stated, not silent")

    def test_require_live_turns_a_skip_into_a_failure(self):
        """The escape hatch for anyone who meant to run it for real — a
        developer locally, or a self-hosted runner that does have a model.
        Without this, forgetting to start the server looks like success."""
        for rel in CHECKS:
            with self.subTest(check=rel):
                proc = run(rel, {"ASYNC_EXEC_API_BASE": DEAD_BASE, "ASYNC_EXEC_REQUIRE_LIVE": "1"})
                self.assertEqual(
                    proc.returncode, 1,
                    "%s must fail when skipping is forbidden:\n%s" % (rel, proc.stdout),
                )
                self.assertIn("FAIL:", proc.stdout)
                self.assertNotIn("SKIP:", proc.stdout)

    def test_skip_names_the_missing_precondition(self):
        for rel in CHECKS:
            with self.subTest(check=rel):
                proc = run(rel, {"ASYNC_EXEC_API_BASE": DEAD_BASE})
                self.assertRegex(
                    proc.stdout,
                    r"SKIP: (pi is not on PATH|the bridge is not installed|no model server reachable)",
                    "the skip reason must be specific enough to act on",
                )
