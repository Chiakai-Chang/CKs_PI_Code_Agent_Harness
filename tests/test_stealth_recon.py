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


class TestSkillMd(unittest.TestCase):
    REL = "pi-skills/optional/camofox-stealth/SKILL.md"

    def test_no_stale_api(self):
        c = read_file(self.REL)
        self.assertNotIn("3001", c, "must not reference the stale port 3001")
        self.assertNotIn("localhost:3001", c)
        # Current API drives navigation through a tab: /tabs/<id>/navigate.
        # Only the STALE root-level POST /navigate is forbidden.
        self.assertNotIn(":9377/navigate", c, "navigate must be under /tabs/<id>/, not root")

    def test_current_api_and_workflow(self):
        c = read_file(self.REL)
        self.assertIn("/tabs", c)
        self.assertIn("snapshot", c)
        self.assertIn("/tabs/$TID/navigate", c)
        self.assertIn("macro", c)
        self.assertIn("recon.sh ensure", c)
        self.assertIn("is_blocked", c)
        self.assertIn("findings.md", c)
        self.assertIn("9377", c)

    def test_selection_guidance_and_honesty(self):
        c = read_file(self.REL)
        self.assertIn("dev-browser", c, "must guide when to use dev-browser vs stealth")
        # honest fallback wording
        self.assertTrue("誠實" in c or "不編造" in c)

    def test_no_machine_paths(self):
        import re
        c = read_file(self.REL)
        self.assertIsNone(re.search(r"file:///[A-Za-z]:/|[A-Za-z]:/MyProject|:8080", c))


if __name__ == "__main__":
    unittest.main()
