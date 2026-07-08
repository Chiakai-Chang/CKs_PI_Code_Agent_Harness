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


class TestReconScript(unittest.TestCase):
    REL = "pi-skills/optional/camofox-stealth/recon.sh"

    def test_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(ROOT, self.REL)),
                        "recon.sh must exist")

    def test_posix_syntax_valid(self):
        r = subprocess.run(["sh", "-n", os.path.join(ROOT, self.REL)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, f"sh -n failed: {r.stderr}")

    def test_pins_version_and_port_and_pidfile(self):
        c = read_file(self.REL)
        self.assertIn("@askjo/camofox-browser@1.11.2", c)
        self.assertIn("9377", c)
        self.assertIn("recon.pid", c)
        self.assertNotIn(":8080", c)

    def test_has_functions(self):
        c = read_file(self.REL)
        for token in ["ensure", "is_blocked", "STEALTH_RECON_URL", "ENABLE_VNC"]:
            self.assertIn(token, c, f"recon.sh must reference {token}")

    def test_block_markers_present(self):
        c = read_file(self.REL)
        for marker in ["Just a moment", "cf-mitigated", "Enable JavaScript"]:
            self.assertIn(marker, c, f"recon.sh must detect '{marker}'")


if __name__ == "__main__":
    unittest.main()
