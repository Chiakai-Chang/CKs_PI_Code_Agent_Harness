import json
import os
import re
import shutil
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import sys as _sys
_sys.path.insert(0, os.path.join(ROOT, "tests"))
from _scratch import scratch  # per-process temp names; see tests/_scratch.py



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


class TestEmptySnapshotIsAnError(unittest.TestCase):
    """Measured in a real session: the first web_snapshot returned 4,648 chars,
    then six consecutive calls returned the literal string "(empty snapshot)" —
    as a plain SUCCESS result, with no reason and no next step. The model kept
    retrying the same dead tab. An empty page is a failure to report, not
    content to hand back."""

    IDX = "pi-extensions/stealth-web-bridge/index.ts"

    def setUp(self):
        self.src = read(self.IDX)

    def test_empty_snapshot_no_longer_returned_as_content(self):
        self.assertNotIn('text || "(empty snapshot)"', self.src)
        self.assertNotIn('truncateForTool(text || "(empty snapshot)"', self.src)

    def test_empty_snapshot_returns_tool_error(self):
        self.assertIn("if (!text) {", self.src)
        self.assertIn("empty snapshot", self.src)
        self.assertIn("toolError(", self.src)

    def test_distinguishes_dead_tab_from_blank_page(self):
        """The two need opposite next steps: re-open the URL vs act on the page.
        Conflating them is what allowed six identical retries."""
        self.assertIn("tabExists", self.src)
        self.assertIn("no longer exists", self.src)

    def test_tells_the_model_not_to_retry(self):
        self.assertIn("Do NOT call web_snapshot again", self.src)


def _node_major():
    if not shutil.which("node"):
        return 0
    try:
        out = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=30).stdout
    except Exception:
        return 0
    m = re.match(r"v(\d+)", out.strip())
    return int(m.group(1)) if m else 0


NODE_OK = _node_major() >= 22


class TestToolOutputTruncation(unittest.TestCase):
    """Pi truncates its own read tool at 2000 lines / 50KB. These web tools were
    returning up to 80,000 chars — measured across this machine's sessions,
    web_open results ran to a median of 9,319, p90 36,593, max 80,029 chars
    (~20K tokens in one tool result). A 42,999-char result from another tool was
    observed derailing this exact local model mid-task, so the size is a real
    failure mode, not a tidiness concern.

    truncate.ts is a separate module precisely so this test can execute it:
    index.ts imports `typebox`, which bare node cannot resolve.
    """

    MOD = "pi-extensions/stealth-web-bridge/truncate.ts"

    def _run(self, script):
        driver = scratch(".tmp_trunc_driver.mjs")
        url = "file:///" + os.path.join(ROOT, self.MOD).replace("\\", "/")
        with open(driver, "w", encoding="utf-8") as f:
            f.write('import { truncateForTool, humanSize, MAX_TOOL_BYTES, MAX_TOOL_LINES } from %s;\n%s'
                    % (json.dumps(url), script))
        try:
            p = subprocess.run(["node", driver], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", cwd=ROOT, timeout=120)
            if p.returncode != 0:
                raise AssertionError("node driver failed:\n%s\n%s" % (p.stdout, p.stderr))
            return json.loads(p.stdout)
        finally:
            if os.path.exists(driver):
                os.remove(driver)

    @unittest.skipUnless(NODE_OK, "node >= 22 required")
    def test_small_output_is_returned_unchanged(self):
        out = self._run(
            'const s = "hello world";'
            'process.stdout.write(JSON.stringify({same: truncateForTool(s, "t") === s}));')
        self.assertTrue(out["same"])

    @unittest.skipUnless(NODE_OK, "node >= 22 required")
    def test_large_output_is_capped_and_spilled_to_a_file(self):
        out = self._run("""
import { readFileSync } from "node:fs";
const big = Array.from({length: 5000}, (_, i) => "line " + i + " " + "x".repeat(60)).join("\\n");
const res = truncateForTool(big, "t");
const m = res.match(/saved to (\\S+) /);
process.stdout.write(JSON.stringify({
  inputBytes: Buffer.byteLength(big, "utf-8"),
  outputBytes: Buffer.byteLength(res, "utf-8"),
  hasNote: /Output truncated/.test(res),
  spillComplete: m ? readFileSync(m[1], "utf-8").length === big.length : false,
  noPartialLines: res.split("\\n").slice(0, -3).every(l => /^line \\d+ x+$/.test(l)),
}));
""")
        self.assertGreater(out["inputBytes"], 300000)
        self.assertLess(out["outputBytes"], 52000, "must land within Pi's own 50KB tool budget")
        self.assertTrue(out["hasNote"])
        self.assertTrue(out["spillComplete"], "the full text must remain reachable, not be discarded")
        self.assertTrue(out["noPartialLines"], "AX-tree output is line-oriented; never cut mid-line")

    @unittest.skipUnless(NODE_OK, "node >= 22 required")
    def test_budget_matches_pi_own_read_tool(self):
        out = self._run('process.stdout.write(JSON.stringify({lines: MAX_TOOL_LINES, bytes: MAX_TOOL_BYTES}));')
        self.assertEqual(out["lines"], 2000)
        self.assertEqual(out["bytes"], 50000)

    @unittest.skipUnless(NODE_OK, "node >= 22 required")
    def test_human_size_switches_units_at_the_real_boundaries(self):
        """1024 exactly is one kilobyte, not 1024 bytes. Three mutation
        survivors sat on these three comparisons: every `1024` could become
        `1025` and no test noticed, because every existing case was far from a
        boundary. The number appears in the truncation note the model reads."""
        out = self._run(
            "process.stdout.write(JSON.stringify({"
            "under: humanSize(1023), at: humanSize(1024), over: humanSize(1025),"
            "underMB: humanSize(1024 * 1024 - 1), atMB: humanSize(1024 * 1024)}));")
        self.assertEqual(out["under"], "1023B")
        self.assertEqual(out["at"], "1.0KB")
        self.assertEqual(out["over"], "1.0KB")
        self.assertEqual(out["underMB"], "1024.0KB")
        self.assertEqual(out["atMB"], "1.0MB")

    @unittest.skipUnless(NODE_OK, "node >= 22 required")
    def test_output_that_exactly_fills_a_budget_is_returned_whole(self):
        """`<=` and `<` differ only here, and `<` truncates output that fits —
        spilling a file and adding a note for nothing."""
        out = self._run(
            "const exactLines = Array.from({length: MAX_TOOL_LINES}, () => 'y').join(String.fromCharCode(10));"
            "const exactBytes = 'z'.repeat(MAX_TOOL_BYTES);"
            "process.stdout.write(JSON.stringify({"
            "linesUntouched: truncateForTool(exactLines, 't') === exactLines,"
            "bytesUntouched: truncateForTool(exactBytes, 't') === exactBytes,"
            "lineCount: exactLines.split(String.fromCharCode(10)).length,"
            "byteCount: Buffer.byteLength(exactBytes, 'utf-8')}));")
        self.assertEqual(out["lineCount"], 2000)
        self.assertEqual(out["byteCount"], 50000)
        self.assertTrue(out["linesUntouched"], "exactly MAX_TOOL_LINES was truncated")
        self.assertTrue(out["bytesUntouched"], "exactly MAX_TOOL_BYTES was truncated")

    @unittest.skipUnless(NODE_OK, "node >= 22 required")
    def test_exceeding_either_budget_alone_still_truncates(self):
        """`&&` with `||` returns output that blows one budget as long as it
        respects the other — which is how a 3000-line snapshot reaches the model
        whole. Both operands are covered, one per direction."""
        out = self._run(
            "const manyShortLines = Array.from({length: MAX_TOOL_LINES + 500}, () => 'y').join(String.fromCharCode(10));"
            "const oneHugeLine = 'z'.repeat(MAX_TOOL_BYTES + 5000);"
            "process.stdout.write(JSON.stringify({"
            "overLinesTruncated: truncateForTool(manyShortLines, 't') !== manyShortLines,"
            "overBytesTruncated: truncateForTool(oneHugeLine, 't') !== oneHugeLine,"
            "overLinesBytes: Buffer.byteLength(manyShortLines, 'utf-8')}));")
        self.assertLess(out["overLinesBytes"], 50000,
                        "the fixture must break ONE budget only, or it proves nothing")
        self.assertTrue(out["overLinesTruncated"], "too many lines, within the byte budget")
        self.assertTrue(out["overBytesTruncated"], "too many bytes, within the line budget")

    @unittest.skipUnless(NODE_OK, "node >= 22 required")
    def test_the_kept_lines_start_at_the_first_one(self):
        """`lines.slice(0, MAX_TOOL_LINES)` with `slice(1, …)` silently drops the
        first line of every truncated output. On an AX-tree snapshot that is the
        page's own title."""
        out = self._run(
            "const lines = Array.from({length: MAX_TOOL_LINES + 100}, (_, i) => 'L' + i);"
            "const res = truncateForTool(lines.join(String.fromCharCode(10)), 't');"
            "process.stdout.write(JSON.stringify({first: res.split(String.fromCharCode(10))[0]}));")
        self.assertEqual(out["first"], "L0", "the first line was dropped")

    @unittest.skipUnless(NODE_OK, "node >= 22 required")
    def test_the_newline_between_kept_lines_is_counted_once(self):
        """`byteLength(line) + 1` — the +1 is the newline that rejoins them.
        Counting 2 costs one line per thousand, and starting `used` at 1 costs
        another; both survived until a fixture sat on the boundary. 99 bytes plus
        a newline is 100, so the byte budget fits exactly 500 of them."""
        out = self._run(
            "const line = 'x'.repeat(99);"
            "const lines = Array.from({length: MAX_TOOL_LINES + 10}, () => line);"
            "const res = truncateForTool(lines.join(String.fromCharCode(10)), 't');"
            "const kept = res.split(String.fromCharCode(10)).filter(l => l === line).length;"
            "process.stdout.write(JSON.stringify({kept}));")
        self.assertEqual(out["kept"], 500,
                         "the byte budget fits exactly 500 lines of 100 bytes; "
                         "a different count means the per-line cost is wrong")

    def test_every_result_site_is_truncated(self):
        """A new tool that forgets to wrap its result reintroduces the problem."""
        c = read("pi-extensions/stealth-web-bridge/index.ts")
        sites = [ln for ln in c.splitlines()
                 if 'content: [{ type: "text"' in ln and "isError" not in ln]
        self.assertGreaterEqual(len(sites), 5)
        for ln in sites:
            self.assertIn("truncateForTool", ln,
                          "unbounded tool result: %s" % ln.strip()[:100])

    def test_restore_ships_the_module(self):
        """restore.py copies bridge directories wholesale; if it ever switched to
        copying index.ts alone, the import would break at load time."""
        c = read("scripts/restore.py")
        self.assertIn("copy_dir_contents", c)


if __name__ == "__main__":
    unittest.main()
