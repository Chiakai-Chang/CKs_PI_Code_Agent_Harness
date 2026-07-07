import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_file(path):
    with open(os.path.join(ROOT, path), "r", encoding="utf-8") as f:
        return f.read()


def read_readme():
    return read_file("README.md")


class TestReadmeOnboarding(unittest.TestCase):
    def test_readme_has_quick_start_section(self):
        """README must have a quick-start section near top."""
        first_500_chars = read_readme()[:500]
        self.assertTrue(
            any(kw in first_500_chars for kw in ["3 分鐘", "3-Minute", "Quick Start", "快速開始"]),
            "README top 500 chars must contain a quick-start section",
        )

    def test_readme_has_trust_section(self):
        """README must have a trust checklist near top."""
        first_1500_chars = read_readme()[:1500]
        self.assertTrue(
            any(kw in first_1500_chars for kw in ["信任", "Trust", "MIT", "開源", "open-source"]),
            "README must have a trust checklist near top",
        )

    def test_readme_shows_one_command(self):
        """README must show a single git clone + install command near top."""
        first_1500_chars = read_readme()[:1500]
        self.assertIn("git clone", first_1500_chars, "README must show git clone command near top")
        self.assertTrue(
            "install.bat" in first_1500_chars or "install.sh" in first_1500_chars,
            "README must show install command near top",
        )


class TestInstallScripts(unittest.TestCase):
    def test_install_bat_has_trust_statement(self):
        content = read_file("install.bat")
        self.assertTrue(
            any(kw in content for kw in ["trust", "Trust", "MIT", "開源", "Source", "Source:"]),
            "install.bat must include a short trust/source statement",
        )

    def test_install_bat_has_progress_indicators(self):
        content = read_file("install.bat")
        self.assertIsNotNone(
            re.search(r"\[\d+/\d+\]", content), "install.bat should show progress markers"
        )

    def test_install_bat_has_confirmation_prompt(self):
        content = read_file("install.bat")
        self.assertTrue(
            "Continue?" in content or "繼續" in content,
            "install.bat must ask for confirmation",
        )

    def test_install_bat_elevation_quotes_path_and_pins_cwd(self):
        """Elevated relaunch must survive paths with spaces and not start in System32."""
        content = read_file("install.bat")
        if "RunAs" in content:
            self.assertIn("-WorkingDirectory", content,
                          "elevated relaunch must pin the working directory")
            self.assertIn('\\"%~dp0scripts\\setup.py\\"', content,
                          "elevated script path must be quoted for paths with spaces")

    def test_install_sh_has_trust_statement(self):
        content = read_file("install.sh")
        self.assertTrue(
            any(kw in content for kw in ["trust", "Trust", "MIT", "Source", "Source:"]),
            "install.sh must include a short trust/source statement",
        )

    def test_install_sh_has_confirmation_prompt(self):
        content = read_file("install.sh")
        self.assertTrue(
            "Continue?" in content or "continue" in content.lower(),
            "install.sh must ask for confirmation",
        )


class TestSetupScript(unittest.TestCase):
    def test_setup_py_supports_auto_mode(self):
        content = read_file("scripts/setup.py")
        self.assertIn("argparse", content, "setup.py should use argparse for --auto")
        self.assertIn("--auto", content, "setup.py must support --auto flag")

    def test_setup_py_wires_auto_mode_to_prompts(self):
        """--auto must actually suppress interactive prompts, not just parse."""
        content = read_file("scripts/setup.py")
        self.assertIn("def ask(", content, "setup.py must route prompts through ask()")
        self.assertIn("AUTO_MODE or not sys.stdin.isatty()", content,
                      "ask() must honor --auto and non-tty runs")

    def test_setup_py_has_llm_friendly_message(self):
        content = read_file("scripts/setup.py")
        self.assertTrue(
            any(kw in content for kw in [
                "No local LLM", "No LLM detected", "未偵測到本地 LLM",
                "install Ollama", "稍後", "skip",
            ]),
            "setup.py must guide user when no LLM detected",
        )

    def test_setup_py_does_not_require_python_on_path(self):
        """The interpreter runs the script; requiring 'python' breaks python3-only systems."""
        content = read_file("scripts/setup.py")
        self.assertNotIn('"python",', content.replace("'", '"'),
                         "setup.py must not require a 'python' binary on PATH")


class TestUninstallScript(unittest.TestCase):
    def test_uninstall_script_exists(self):
        self.assertTrue(
            os.path.isfile(os.path.join(ROOT, "scripts", "uninstall.py")),
            "scripts/uninstall.py must exist",
        )

    def test_uninstall_script_is_executable_style(self):
        content = read_file("scripts/uninstall.py")
        self.assertIn("if __name__", content, "uninstall.py must be runnable as script")
        self.assertTrue(
            "backup" in content.lower() or "restore" in content.lower(),
            "uninstall.py must mention backup/restore",
        )

    def test_uninstall_is_selective(self):
        """Uninstall must only remove harness-managed assets."""
        content = read_file("scripts/uninstall.py")
        self.assertIn("MANAGED_SKILLS", content)
        self.assertIn("MANAGED_BRIDGES", content)


class TestSharedFilesPlatformAgnostic(unittest.TestCase):
    def test_no_machine_specific_paths_in_shared_rules(self):
        """Shared rule/config files must not hardcode machine-specific paths."""
        shared_files = [
            "CLAUDE.md", ".cursorrules", ".agents/AGENTS.md",
            "pi-rules/AGENTS.md", "pi-config/settings.json.example",
            "package.json",
        ]
        pattern = re.compile(r"file:///[A-Za-z]:/|[A-Za-z]:/MyProject|[A-Za-z]:\\MyProject", re.IGNORECASE)
        for rel in shared_files:
            content = read_file(rel)
            self.assertIsNone(
                pattern.search(content),
                f"{rel} contains a machine-specific absolute path",
            )


if __name__ == "__main__":
    unittest.main()
