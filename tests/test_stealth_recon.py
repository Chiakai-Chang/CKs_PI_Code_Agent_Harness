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

    def test_wrapper_version_read_from_config(self):
        """Wrapper version is single-sourced from harness-config.json
        (camofoxBrowserVersion), read relative to the script, with a hardcoded
        fallback so recon never hard-breaks if the config is unreadable."""
        c = read_file(self.REL)
        self.assertIn("camofoxBrowserVersion", c)
        self.assertIn("harness-config.json", c)
        self.assertIn('CAMOFOX_VER="1.11.2"', c, "must keep a safe hardcoded fallback")

    def test_pins_playwright_core_engine(self):
        """The wrapper's ^1.58.0 range resolves to playwright-core 1.61+, which
        sends a viewport.isMobile field the Camoufox juggler rejects, breaking
        every tab. Pin playwright-core to the camoufox-js-tested 1.53.x via an
        npm override so a fresh install stays compatible."""
        c = read_file(self.REL)
        self.assertIn("playwright-core", c)
        self.assertIn("1.53.1", c)
        self.assertIn("overrides", c,
                      "must install with an npm override, not bare npx-latest")

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
        # Search goes through the DuckDuckGo HTML endpoint at tab-create time, NOT
        # the navigate macros: @duckduckgo_search does not exist in the pinned
        # server and @google_search hits Google's /sorry bot wall.
        self.assertIn("html.duckduckgo.com", c)
        # Non-ASCII queries must ride a file payload, not inline `curl -d`, or the
        # Windows shell mangles UTF-8 into U+FFFD replacement chars.
        self.assertIn("--data-binary", c)
        self.assertIn("recon.sh", c)
        self.assertIn("ensure", c)
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


class TestRule(unittest.TestCase):
    REL = "pi-rules/stealth-recon.md"

    def test_exists_and_bounded(self):
        c = read_file(self.REL)
        self.assertIn("findings.md", c)
        self.assertIn("參考不照抄", c)
        self.assertIn("camofox-stealth", c)
        # bounded: mentions a cap so trivial tasks aren't dragged
        self.assertTrue("上限" in c or "瑣碎" in c)


class TestSetupPrefetch(unittest.TestCase):
    REL = "scripts/setup.py"

    def test_prefetch_present_and_optional(self):
        c = read_file(self.REL)
        self.assertIn("camofoxBrowserVersion", c, "setup must read pinned version")
        self.assertIn("@askjo/camofox-browser", c)
        # opt-in via ask() default "n" — must not force download
        self.assertIn("prefetch", c.lower())

    def test_prefetch_routes_through_recon_install(self):
        """Prefetch must use recon.sh install (pins playwright-core + runs the
        gated engine postinstall), not a bare `npm install -g` that leaves the
        engine cache empty and playwright-core floating to a broken version."""
        c = read_file(self.REL)
        self.assertIn("recon.sh", c)
        self.assertRegex(c, r'recon\.sh[^\n]*install|"install"')
        self.assertNotIn("npm install -g @askjo", c,
                         "bare global npm install reintroduces the engine-gating bug")

    def test_prefetch_uses_ask_not_raw_input(self):
        # the prefetch prompt must degrade in --auto/non-tty (uses ask(), not input())
        c = read_file(self.REL)
        idx = c.lower().find("prefetch")
        window = c[max(0, idx - 400): idx + 400]
        self.assertIn("ask(", window, "prefetch prompt must use ask() for --auto safety")


class TestDocs(unittest.TestCase):
    def test_readme_lists_stealth_recon(self):
        c = read_file("README.md")
        self.assertIn("camofox", c.lower())
        self.assertIn("stealth", c.lower())

    def test_rationale_mentions_pin_and_update(self):
        c = read_file("pi-skills/optional/camofox-stealth/RATIONALE.md")
        self.assertIn("1.11.2", c)
        self.assertTrue("釘版" in c or "更新" in c)

    def test_uninstall_notes_user_data(self):
        c = read_file("scripts/uninstall.py")
        self.assertIn(".camofox", c)


class TestReconBlockDetection(unittest.TestCase):
    REL = "pi-skills/optional/camofox-stealth/recon.sh"

    def _rc(self, content):
        import tempfile
        fd, p = tempfile.mkstemp()
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        try:
            return subprocess.run(
                ["sh", os.path.join(ROOT, self.REL), "is_blocked", p],
                capture_output=True, text=True,
            ).returncode
        finally:
            os.remove(p)

    def test_blocked_challenge_returns_0(self):
        self.assertEqual(self._rc("<title>Just a moment...</title>" + ("x " * 100)), 0)

    def test_google_sorry_page_returns_0(self):
        # Google's /sorry bot wall is wordy (passes the low-word-count heuristic)
        # and carries no Cloudflare markers, so it must be caught by its own text.
        page = ("Our systems have detected unusual traffic from your computer "
                "network. This page checks to see if it's really you and not a "
                "robot. " * 5)
        self.assertEqual(self._rc(page), 0)

    def test_clean_page_returns_nonzero(self):
        self.assertNotEqual(self._rc("This is a normal article. " * 50), 0)

    def test_missing_file_returns_nonzero(self):
        rc = subprocess.run(
            ["sh", os.path.join(ROOT, self.REL), "is_blocked", "/no/such/file/xyz"],
            capture_output=True, text=True,
        ).returncode
        self.assertNotEqual(rc, 0)


class TestReconFirstRun(unittest.TestCase):
    REL = "pi-skills/optional/camofox-stealth/recon.sh"

    def test_first_run_notice_and_longer_timeout(self):
        c = read_file(self.REL)
        # First-run auto-install must be announced and given a longer wait so the
        # ~300MB Camoufox download does not falsely time out on the normal path.
        self.assertIn(".recon-initialized", c)
        self.assertIn("300MB", c)
        self.assertIn("STEALTH_RECON_FIRST_RUN_TIMEOUT", c)
        self.assertIn("wait_timeout", c)


if __name__ == "__main__":
    unittest.main()
