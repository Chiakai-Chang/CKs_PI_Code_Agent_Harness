import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


class TestBridgeContract(unittest.TestCase):
    IDX = "pi-extensions/stealth-web-bridge/index.ts"
    PKG = "pi-extensions/stealth-web-bridge/package.json"

    def test_registers_both_first_class_tools(self):
        c = read(self.IDX)
        self.assertIn('name: "web_search"', c)
        self.assertIn('name: "web_open"', c)
        self.assertIn("registerTool", c)

    def test_search_uses_ddg_html_not_blocked_macros(self):
        c = read(self.IDX)
        self.assertIn("html.duckduckgo.com/html/?q=", c)
        # The macros are broken/blocked; the bridge must not drive search through them.
        self.assertNotIn("@duckduckgo_search", c)
        self.assertNotIn("@google_search", c)

    def test_utf8_safe_json_body(self):
        """node fetch sends proper UTF-8; guard against a regression to shell/curl."""
        c = read(self.IDX)
        self.assertIn("JSON.stringify", c)
        self.assertIn("encodeURIComponent", c)

    def test_block_detection_present(self):
        c = read(self.IDX)
        self.assertIn("BLOCK_MARKERS", c)
        self.assertIn("detected unusual traffic", c)

    def test_prompt_snippet_makes_tool_visible(self):
        """promptSnippet is what surfaces the tool in the system prompt tool list."""
        c = read(self.IDX)
        self.assertIn("promptSnippet", c)

    def test_package_is_esm_with_harness_root_placeholder(self):
        pkg = read(self.PKG)
        self.assertIn('"type": "module"', pkg)
        self.assertIn("pi-harness", pkg)


class TestRestoreWiring(unittest.TestCase):
    R = "scripts/restore.py"

    def test_bridge_registered_and_managed(self):
        c = read(self.R)
        # profile_extensions append, cleanup-preserve list, and delete list must
        # all name the bridge, or restore would half-install or never refresh it.
        self.assertIn('pi_extensions_root, "stealth-web-bridge"', c)
        # profile_extensions append + internal_bridge_names + delete loop
        self.assertEqual(c.count('"stealth-web-bridge"'), 3)


if __name__ == "__main__":
    unittest.main()
