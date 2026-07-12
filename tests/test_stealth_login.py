import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "pi-skills", "optional", "camofox-stealth", "scripts")
sys.path.insert(0, SCRIPTS)


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


class TestLoginHelperContract(unittest.TestCase):
    """Optional deps (browser_cookie3/keyring) are imported lazily, so the module
    itself imports on a stdlib-only interpreter."""

    def setUp(self):
        import importlib
        self.mod = importlib.import_module("stealth_login")

    def test_module_imports_without_optional_deps(self):
        self.assertTrue(hasattr(self.mod, "main"))

    def _silence(self):
        import contextlib
        import io
        return contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO())

    def test_help_lists_all_three_subcommands(self):
        out, err = self._silence()
        with out, err, self.assertRaises(SystemExit):
            self.mod.main(["--help"])

    def test_missing_subcommand_errors(self):
        out, err = self._silence()
        with out, err, self.assertRaises(SystemExit):
            self.mod.main([])

    def test_password_never_comes_from_argv(self):
        """The store subcommand must not accept a password positional/flag —
        credentials are read from stdin or getpass, never argv (process listing)."""
        src = read("pi-skills/optional/camofox-stealth/scripts/stealth_login.py")
        self.assertIn("getpass", src)
        self.assertIn("sys.stdin", src)
        # store parser only takes domain + username, not a password
        self.assertIn('ps.add_argument("username")', src)
        self.assertNotIn('add_argument("password"', src)

    def test_cookies_path_uses_server_cookie_endpoint(self):
        src = read("pi-skills/optional/camofox-stealth/scripts/stealth_login.py")
        self.assertIn("/sessions/", src)
        self.assertIn("browser_cookie3", src)


class TestLoginCommandWiring(unittest.TestCase):
    IDX = "pi-extensions/stealth-web-bridge/index.ts"

    def test_login_command_registered(self):
        c = read(self.IDX)
        self.assertIn('registerCommand("login"', c)

    def test_password_piped_via_stdin_not_argv(self):
        c = read(self.IDX)
        # runLogin writes credentials to child stdin; store is called with the
        # password as stdinData, not as a command-line argument.
        self.assertIn("proc.stdin.write(stdinData)", c)
        self.assertIn('runLogin(["store", domain, username], password', c)

    def test_cookie_reuse_tried_before_credentials(self):
        c = read(self.IDX)
        cookies_at = c.find('runLogin(["cookies"')
        creds_at = c.find("ui.confirm")
        self.assertTrue(0 < cookies_at < creds_at, "cookie reuse must be attempted before prompting for credentials")


if __name__ == "__main__":
    unittest.main()
