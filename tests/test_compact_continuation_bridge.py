import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


class TestCompactContinuationBridgeContract(unittest.TestCase):
    """Pi's compact() unconditionally aborts the current agent operation, and
    for "manual"/"threshold" reasons willRetry is always false (dist/core/
    agent-session.js's own comment: "NO auto-retry (user continues
    manually)") — only "overflow" auto-retries. Reported live: "pi 在 compact
    過後會自動停止". This bridge hooks session_compact and queues a
    continuation follow-up whenever Pi itself won't auto-retry."""

    IDX = "pi-extensions/compact-continuation-bridge/index.ts"
    PKG = "pi-extensions/compact-continuation-bridge/package.json"

    def test_hooks_session_compact(self):
        c = read(self.IDX)
        self.assertIn('pi.on("session_compact"', c)

    def test_skips_when_pi_already_retries(self):
        """willRetry is only true for overflow recovery, which Pi's own
        engine already retries — must not double up with our own follow-up."""
        c = read(self.IDX)
        self.assertIn("if (event.willRetry) return;", c)

    def test_sends_followup_that_triggers_a_turn(self):
        c = read(self.IDX)
        self.assertIn("pi.sendMessage(", c)
        self.assertIn('deliverAs: "followUp"', c)
        self.assertIn("triggerTurn: true", c)

    def test_package_is_esm_with_harness_root(self):
        pkg = read(self.PKG)
        self.assertIn('"type": "module"', pkg)
        self.assertIn("pi-harness", pkg)


class TestRestoreWiring(unittest.TestCase):
    def test_bridge_registered_and_managed(self):
        c = read("scripts/restore.py")
        self.assertIn('pi_extensions_root, "compact-continuation-bridge"', c)
        # profile_extensions append + internal_bridge_names + delete loop
        self.assertEqual(c.count('"compact-continuation-bridge"'), 3)


if __name__ == "__main__":
    unittest.main()
