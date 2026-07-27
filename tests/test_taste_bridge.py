import os
import re
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


class TestEsmBridgesDoNotUseRequire(unittest.TestCase):
    """ESM-declared bridges must resolve their own path via import.meta.url.

    Pi's own loader shims `require` for bridges — verified under Pi for both
    `"type": "module"` and CJS-declared packages, so require.resolve does work
    in production. The rule exists for testability: the only way to prove a
    handler actually runs is to import the installed copy in bare `node` and
    invoke it, and node gives an ESM-declared module no `require`. A bridge that
    uses it cannot be behaviourally tested — and since these handlers sit behind
    `try { } catch {}`, an untestable one fails by silently returning defaults,
    which is indistinguishable from working.

    (This test was originally written on the mistaken belief that require threw
    under Pi as well. It does not; the claim was proven in node, not in Pi. The
    rule is kept for the testability reason, which is real.)
    """

    def test_no_require_in_esm_bridges(self):
        import glob
        import json as _json
        offenders = []
        for pkg_path in glob.glob(os.path.join(ROOT, "pi-extensions", "*", "package.json")):
            with open(pkg_path, encoding="utf-8") as f:
                pkg = _json.load(f)
            if pkg.get("type") != "module":
                continue
            idx = os.path.join(os.path.dirname(pkg_path), "index.ts")
            if not os.path.exists(idx):
                continue
            with open(idx, encoding="utf-8") as f:
                body = "\n".join(
                    ln for ln in f.read().splitlines()
                    if not ln.lstrip().startswith(("//", "*", "/*"))
                )
            if re.search(r"\brequire\s*[.(]", body):
                offenders.append(os.path.basename(os.path.dirname(pkg_path)))
        self.assertEqual(
            offenders, [],
            'ESM bridges (package.json "type": "module") cannot use require; '
            "use fileURLToPath(import.meta.url). Offenders: %s" % offenders,
        )


class TestHarnessRootResolution(unittest.TestCase):
    """restore.py copies bridges to ~/.pi/agent/extensions/<name>/ and patches
    the harness root into package.json. Resolving the root as
    join(__dirname, "../..") lands on ~/.pi, which has no pi-config/ — so the
    config check silently never fired and `enableTasteBridge: false` (the
    shipped slim-mode default, documented in README) did nothing: GEMINI.md was
    injected into every single turn regardless."""

    def test_reads_pi_harness_root_from_package_json(self):
        c = read("pi-extensions/taste-bridge/index.ts")
        self.assertIn('pkg["pi-harness"]?.root', c)

    def test_all_bridges_resolve_root_via_package_json(self):
        """Every bridge that reads pi-config must resolve the root the same way;
        this is the check that would have caught taste-bridge."""
        import glob
        for idx in glob.glob(os.path.join(ROOT, "pi-extensions", "*", "index.ts")):
            with open(idx, encoding="utf-8") as f:
                c = f.read()
            if "pi-config" not in c:
                continue
            self.assertIn(
                'pi-harness', c,
                "%s reads pi-config but does not resolve the harness root from "
                "package.json — it will look in ~/.pi and silently find nothing"
                % os.path.relpath(idx, ROOT),
            )

    def test_status_line_respects_the_enable_flag(self):
        """A status line claiming 'active' while the injection is disabled is
        how a dead bridge passes for a working one."""
        c = read("pi-extensions/taste-bridge/index.ts")
        self.assertIn("tasteEnabled()", c)
        self.assertIn("if (!tasteEnabled()) return;", c)
        # both the status handler and the injection handler must be gated
        self.assertGreaterEqual(c.count("if (!tasteEnabled()) return;"), 2)


class TestRestoreWiring(unittest.TestCase):
    def test_bridge_registered_and_managed(self):
        c = read("scripts/restore.py")
        self.assertIn('pi_extensions_root, "taste-bridge"', c)
        self.assertEqual(c.count('"taste-bridge"'), 3)


if __name__ == "__main__":
    unittest.main()
