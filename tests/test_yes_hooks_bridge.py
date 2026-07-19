import os
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


class TestBridgeContract(unittest.TestCase):
    IDX = "pi-extensions/yes-hooks-bridge/index.ts"
    PKG = "pi-extensions/yes-hooks-bridge/package.json"

    def test_blocks_bash_via_pre_bash_guard(self):
        c = read(self.IDX)
        self.assertIn('event.toolName === "bash"', c)  # dispatched to bashGuard
        self.assertIn("pre-bash-guard.sh", c)
        self.assertIn("block: true", c)
        self.assertIn("r.status === 1", c)  # guard exits 1 on danger

    def test_fails_open_when_guard_absent(self):
        """A missing submodule/guard must NOT break every bash call."""
        c = read(self.IDX)
        self.assertIn("if (!existsSync(script)) return", c)

    def test_package_is_esm_with_harness_root(self):
        pkg = read(self.PKG)
        self.assertIn('"type": "module"', pkg)
        self.assertIn("pi-harness", pkg)


class TestContainmentGuard(unittest.TestCase):
    """The directory-containment guard blocks write/edit that escape the session
    cwd — fixes the observed '資料夾亂跳' failure (a run wrote into a sibling
    project and edited this harness itself). Contract-guard the wiring; the path
    decision logic is verified separately on real paths."""

    IDX = "pi-extensions/yes-hooks-bridge/index.ts"

    def test_guards_write_and_edit(self):
        c = read(self.IDX)
        self.assertIn('event.toolName === "write"', c)
        self.assertIn('event.toolName === "edit"', c)
        self.assertIn("containmentGuard", c)

    def test_uses_escape_check_and_blocks(self):
        c = read(self.IDX)
        # resolve target then reject paths that leave cwd
        for token in ("isAbsolute", "relative(cwd", 'rel.startsWith("..")'):
            self.assertIn(token, c)
        self.assertIn("block: true", c)
        self.assertIn("outside the project root", c)

    def test_fails_open_when_undecidable(self):
        """Missing path or cwd must NOT break every write/edit."""
        c = read(self.IDX)
        self.assertIn("typeof ctx.cwd", c)  # bail when cwd unknown


class TestRestoreWiring(unittest.TestCase):
    def test_bridge_registered_and_managed(self):
        c = read("scripts/restore.py")
        self.assertIn('pi_extensions_root, "yes-hooks-bridge"', c)
        # profile_extensions append + internal_bridge_names + delete loop
        self.assertEqual(c.count('"yes-hooks-bridge"'), 3)


class TestGuardBehavior(unittest.TestCase):
    """The guard the bridge relies on must actually block destructive commands
    and pass safe ones — the whole point of wiring it."""

    GUARD = os.path.join(ROOT, "external", "yes.md", "hooks", "pre-bash-guard.sh")

    def _exit(self, cmd):
        # guard prints UTF-8 (emoji/Chinese); force utf-8 so Windows cp950 default
        # doesn't UnicodeDecodeError in the reader thread.
        return subprocess.run(
            ["sh", self.GUARD, cmd],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        ).returncode

    @unittest.skipUnless(os.path.exists(GUARD), "yes.md submodule not initialized")
    def test_destructive_blocked(self):
        for cmd in ["rm -rf /", "git push --force origin main", "psql -c 'DROP TABLE users'"]:
            self.assertEqual(self._exit(cmd), 1, "must block: %s" % cmd)

    @unittest.skipUnless(os.path.exists(GUARD), "yes.md submodule not initialized")
    def test_safe_passed(self):
        for cmd in ["ls -la", "git status", "npm test", "git commit -m x"]:
            self.assertEqual(self._exit(cmd), 0, "must allow: %s" % cmd)


if __name__ == "__main__":
    unittest.main()
