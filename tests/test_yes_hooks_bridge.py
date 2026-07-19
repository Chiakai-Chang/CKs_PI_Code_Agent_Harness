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
        self.assertIn('event.toolName !== "bash"', c)
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
        return subprocess.run(["sh", self.GUARD, cmd], capture_output=True, text=True).returncode

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
