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

    def test_interaction_tools_registered(self):
        """The agent must be able to drive pages, not just read them."""
        c = read(self.IDX)
        for name in ("web_click", "web_type", "web_scroll", "web_press"):
            self.assertIn('name: "%s"' % name, c)

    def test_capability_parity_tools_registered(self):
        """Ported from the upstream OpenClaw plugin (plugin.ts): re-snapshot,
        visual screenshot, page-context JS."""
        c = read(self.IDX)
        for name in ("web_snapshot", "web_screenshot", "web_evaluate"):
            self.assertIn('name: "%s"' % name, c)

    def test_screenshot_returns_image_content(self):
        c = read(self.IDX)
        self.assertIn('type: "image" as const', c)

    def test_backend_start_resolves_real_shell(self):
        """spawn('sh') ENOENTs on Windows where Git's sh is not on the Node
        process PATH — the backend then never cold-starts. Must resolve a real
        shell (harness shellPath / Git-Bash path), not rely on bare 'sh'."""
        c = read(self.IDX)
        self.assertIn("function findShell", c)
        self.assertIn("spawn(findShell()", c)
        self.assertIn("shellPath", c)
        # the only remaining literal spawn("sh"…) is inside an explanatory comment
        self.assertNotIn('spawn("sh", [', c)

    def test_interaction_acts_on_tracked_current_tab(self):
        c = read(self.IDX)
        # web_search / web_open record the tab so interaction tools need no tabId
        self.assertIn("lastTabId = tabId", c)
        self.assertIn("actAndSnapshot", c)

    def test_action_returns_fresh_snapshot(self):
        """After an action the page changed — the tool must return the new state
        so multi-step flows can continue."""
        c = read(self.IDX)
        self.assertIn("readSnapshot(tabId)", c)

    def test_optional_tabid_override_for_multitab(self):
        """Current tab is the default, but an explicit tabId must be accepted so
        multi-tab work (keep search open while reading a result) is possible."""
        c = read(self.IDX)
        self.assertIn("TAB_PARAM", c)
        self.assertIn("function currentTab", c)
        # tabId is surfaced back to the model so it can target a specific tab
        self.assertIn("tabId }", c)  # details include tabId
        self.assertIn("[tab ${tabId}", c)  # and it's shown in the snapshot text

    def test_package_is_esm_with_harness_root_placeholder(self):
        pkg = read(self.PKG)
        self.assertIn('"type": "module"', pkg)
        self.assertIn("pi-harness", pkg)


class TestProactiveCompactGuard(unittest.TestCase):
    """Pi's own auto-compaction threshold check only runs *between* whole agent
    turns (verified against the installed @earendil-works/pi-coding-agent engine),
    never between individual tool round-trips within one turn. A single web_*
    call can return up to ~20K tokens (camofox server caps snapshots at 80,000
    chars), so a turn chaining a few large page fetches can jump straight past
    the hard ctx-size limit with no intervening checkpoint — the observed
    "request (268581 tokens) exceeds the available context size (262144)" 400.
    This guard checks ctx.getContextUsage() after a turn that used a web_* tool
    and proactively calls ctx.compact() before that wall is hit.

    Hooked at turn_end, not tool_result (regression, found 2026-07-22 from a
    real "pi stops after compact" report): ctx.compact() unconditionally
    aborts the current agent operation first (dist/core/agent-session.js).
    Calling it from tool_result fires mid-turn, cutting off work that hadn't
    finished yet with no auto-resume. turn_end fires after the turn (and all
    its tool calls) already completed naturally, matching Pi's own official
    trigger-compact.ts example."""

    IDX = "pi-extensions/stealth-web-bridge/index.ts"

    def test_hooks_turn_end_scoped_to_web_tools(self):
        c = read(self.IDX)
        self.assertIn('pi.on("turn_end"', c)
        self.assertIn('r.toolName.startsWith("web_")', c)
        self.assertNotIn('pi.on("tool_result"', c)

    def test_checks_context_usage_and_compacts(self):
        c = read(self.IDX)
        self.assertIn("getContextUsage", c)
        self.assertIn("ctx.compact?.(", c)
        self.assertIn("PROACTIVE_COMPACT_PERCENT", c)

    def test_avoids_stacking_duplicate_compacts(self):
        """Must not fire ctx.compact() again while one is already in flight."""
        c = read(self.IDX)
        self.assertIn("proactiveCompactInFlight", c)
        self.assertIn("onComplete", c)
        self.assertIn("onError", c)


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
