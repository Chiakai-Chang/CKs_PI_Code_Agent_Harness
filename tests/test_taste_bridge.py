import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


class TestTasteBridgeContract(unittest.TestCase):
    IDX = "pi-extensions/taste-bridge/index.ts"
    PKG = "pi-extensions/taste-bridge/package.json"

    def test_preserves_event_system_prompt(self):
        c = read(self.IDX)
        self.assertIn("before_agent_start", c)
        self.assertIn("event.systemPrompt", c)
        self.assertIn('(event.systemPrompt ?? "")', c)

    def test_package_is_esm_with_harness_root(self):
        pkg = read(self.PKG)
        self.assertIn('"type": "module"', pkg)
        self.assertIn("pi-harness", pkg)


class TestRestoreWiring(unittest.TestCase):
    def test_bridge_registered_and_managed(self):
        c = read("scripts/restore.py")
        self.assertIn('pi_extensions_root, "taste-bridge"', c)
        self.assertEqual(c.count('"taste-bridge"'), 3)


if __name__ == "__main__":
    unittest.main()
