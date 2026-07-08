import json
import os
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_file(rel):
    with open(os.path.join(ROOT, rel), "r", encoding="utf-8") as f:
        return f.read()


class TestHarnessConfigPin(unittest.TestCase):
    def test_camofox_version_pinned(self):
        cfg = json.loads(read_file("pi-config/harness-config.json"))
        self.assertEqual(cfg.get("camofoxBrowserVersion"), "1.11.2",
                         "harness-config.json must pin camofoxBrowserVersion")


if __name__ == "__main__":
    unittest.main()
