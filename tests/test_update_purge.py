import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_file(rel):
    with open(os.path.join(ROOT, rel), "r", encoding="utf-8") as f:
        return f.read()


class TestSetupUpdateMode(unittest.TestCase):
    def test_update_in_choices(self):
        c = read_file("scripts/setup.py")
        self.assertIn('choices=["full", "model", "restore", "update"]', c)

    def test_menu_has_option_4(self):
        c = read_file("scripts/setup.py")
        self.assertIn("[4] 更新", c)
        self.assertIn('if ans == "4": return "update"', c)

    def test_run_update_flow(self):
        c = read_file("scripts/setup.py")
        self.assertIn("def run_update", c)
        i = c.find("def run_update")
        blk = c[i:i + 800]
        self.assertIn("git pull --recurse-submodules", blk)
        self.assertIn("restore.py", blk)
        self.assertIn("pi update --all", blk)

    def test_update_dispatched(self):
        c = read_file("scripts/setup.py")
        self.assertIn('if mode == "update":', c)
        self.assertIn("run_update()", c)


class TestUpdateEntryScripts(unittest.TestCase):
    def test_update_bat(self):
        c = read_file("update.bat")
        self.assertIn("--mode update", c)
        self.assertIn("chcp 65001", c)

    def test_update_sh(self):
        c = read_file("update.sh")
        self.assertIn("--mode update", c)

    def test_no_machine_paths(self):
        import re
        for f in ("update.bat", "update.sh"):
            self.assertIsNone(
                re.search(r"[A-Za-z]:/MyProject|file:///", read_file(f)),
                f"{f} must not contain machine-specific paths",
            )


class TestUninstallPurge(unittest.TestCase):
    REL = "scripts/uninstall.py"

    def test_argparse_and_flag(self):
        c = read_file(self.REL)
        self.assertIn("import argparse", c)
        self.assertIn('"--purge"', c)

    def test_purge_targets(self):
        c = read_file(self.REL)
        self.assertIn(".camofox", c)
        self.assertIn("agent.backup", c)

    def test_scope_fixed(self):
        c = read_file(self.REL)
        self.assertIn("@earendil-works/pi-coding-agent", c)
        self.assertNotIn("@mariozechner", c)

    def test_ask_helper_nontty_safe(self):
        c = read_file(self.REL)
        self.assertIn("def ask", c)
        self.assertIn("isatty", c)


class TestReadmeUpdatePurge(unittest.TestCase):
    def test_readme_mentions_update_and_uninstall(self):
        c = read_file("README.md")
        self.assertIn("update.bat", c)
        self.assertIn("--mode update", c)
        self.assertIn("--purge", c)


if __name__ == "__main__":
    unittest.main()
