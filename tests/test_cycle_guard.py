"""A loop that cycles through queries never repeats itself consecutively.

Measured 2026-08-05, one run of a market-survey brief:

    web_search calls: 598   distinct queries: 43
      44x  台灣 智慧門鈴 品牌 價格 通路 momo PChome 2025 2026
      44x  台灣 智慧門鈴 價格 2025 2026 Ring Eufy Tapo 品牌 通路
      44x  台灣 智慧門鈴 品牌 價格 Ring Eufy Tapo 2025 2026 通路
      44x  台灣 智慧門鈴 價格 2025 2026 通路 momo 品牌 通路

Twenty-five minutes, then a timeout. `yes-hooks-bridge`'s repeat-call guard was
silent throughout, and its own comment says why:

    // Consecutive only: any different call resets the count, so edit/test/edit/
    // test cycles — identical `bash` calls separated by real work — are untouched.

Every call differed from the one before it, so the counter reset 598 times. The
guard sees AAAA and cannot see ABCABCABC.

A window would not have caught this either: 43 distinct queries spread across any
reasonable window leave each signature appearing once or twice. What does hold is
that an identical search query returns identical results — issuing it a sixth
time cannot produce information the first five did not. So the count is per
signature, for the whole session, and only for tools where that reasoning holds.
`bash` and `edit` repeat legitimately: the file changed in between.
"""

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

MOD = os.path.join(ROOT, "pi-extensions", "yes-hooks-bridge", "loop-detect.ts")


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


def run_js(script):
    driver = scratch(".tmp_cycle_driver.mjs")
    url = "file:///" + MOD.replace("\\", "/")
    with open(driver, "w", encoding="utf-8") as f:
        f.write("import * as m from %s;\n%s" % (json.dumps(url), script))
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
class TestCyclingSearches(unittest.TestCase):
    def test_a_three_query_cycle_is_caught(self):
        """The shape the existing guard is blind to."""
        out = run_js("""
        const d = new m.CycleDetector();
        const q = ["alpha", "beta", "gamma"];
        let blockedAt = -1;
        for (let i = 0; i < 30; i++) {
          const r = d.check("web_search", { query: q[i % 3] });
          if (r && blockedAt < 0) blockedAt = i;
        }
        process.stdout.write(JSON.stringify({ blockedAt }));
        """)
        self.assertGreater(out["blockedAt"], 0, "a cycling search loop must eventually be stopped")
        self.assertLess(out["blockedAt"], 30, "and stopped well before the run gives up")

    def test_the_reason_tells_it_what_to_do_instead(self):
        """`web_search` returns addresses now. Repeating the query is the wrong
        move; opening one of the results is the right one."""
        out = run_js("""
        const d = new m.CycleDetector();
        let reason = "";
        for (let i = 0; i < 12; i++) {
          const r = d.check("web_search", { query: "same" });
          if (r) { reason = r.reason; break; }
        }
        process.stdout.write(JSON.stringify({ reason }));
        """)
        self.assertRegex(out["reason"], r"(?i)web_open|open")

    def test_a_long_cycle_is_still_bounded(self):
        """43 distinct queries was the real shape. Each one still gets its own
        budget, so the ceiling is distinct x limit rather than unbounded."""
        out = run_js("""
        const d = new m.CycleDetector();
        let calls = 0, blocked = 0;
        for (let round = 0; round < 44; round++) {
          for (let q = 0; q < 43; q++) {
            calls++;
            if (d.check("web_search", { query: "q" + q })) blocked++;
          }
        }
        process.stdout.write(JSON.stringify({ calls, blocked }));
        """)
        self.assertGreater(out["blocked"], 0)
        allowed = out["calls"] - out["blocked"]
        self.assertLess(allowed, 300, "598 real searches must not be reachable again")


@unittest.skipUnless(NODE_OK, "node >= 22 required")
@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheBoundaryIsExactlyWhereItSays(unittest.TestCase):
    """Added 2026-08-08 from the mutation sweep, not from a suspicion.

    Three separate mutations survived here at once and they are all the same
    boundary: `SAME_QUERY_LIMIT = 5` shifted to 6, the `?? 0` default shifted to
    1, and `count <= LIMIT` narrowed to `<`. Every existing test loops well past
    the limit and asserts that something was blocked, so any of those three
    changes the exact firing point and none of them changes the answer.

    A repeat guard that fires one call early is a guard that refuses work the
    user asked for; one call late is one more wasted call. The number is the
    behaviour, so the test has to name it."""

    def test_the_fifth_identical_query_is_allowed_and_the_sixth_is_not(self):
        out = run_js("""
        const d = new m.CycleDetector();
        const verdicts = [];
        for (let i = 1; i <= 6; i++) {
          verdicts.push(d.check("web_search", { query: "same" }) ? "BLOCKED" : "allowed");
        }
        process.stdout.write(JSON.stringify({ verdicts, limit: m.SAME_QUERY_LIMIT }));
        """)
        self.assertEqual(out["limit"], 5)
        self.assertEqual(out["verdicts"],
                         ["allowed", "allowed", "allowed", "allowed", "allowed", "BLOCKED"])

    def test_the_refusal_actually_carries_block_true(self):
        """`block: true` in the returned object survived the sweep: every test
        here checks that `check()` returned something truthy, and a refusal with
        `block: false` is still an object. Pi reads the field, so that guard
        would keep counting, keep explaining itself, and stop blocking."""
        out = run_js("""
        const d = new m.CycleDetector();
        let r = null;
        for (let i = 0; i < 8; i++) r = d.check("web_search", { query: "same" }) || r;
        process.stdout.write(JSON.stringify({ block: r && r.block }));
        """)
        self.assertIs(out["block"], True)


class TestLegitimateRepetitionIsUntouched(unittest.TestCase):
    """The existing guard's comment is right about this and must stay right."""

    def test_bash_may_repeat_because_the_file_changed(self):
        out = run_js("""
        const d = new m.CycleDetector();
        let blocked = 0;
        for (let i = 0; i < 40; i++) if (d.check("bash", { command: "npm test" })) blocked++;
        process.stdout.write(JSON.stringify({ blocked }));
        """)
        self.assertEqual(out["blocked"], 0, "edit/test cycles must not be interrupted")

    def test_edit_and_write_may_repeat(self):
        for tool in ("edit", "write", "read"):
            with self.subTest(tool=tool):
                out = run_js("""
                const d = new m.CycleDetector();
                let blocked = 0;
                for (let i = 0; i < 40; i++) if (d.check(%s, { path: "a.ts" })) blocked++;
                process.stdout.write(JSON.stringify({ blocked }));
                """ % json.dumps(tool))
                self.assertEqual(out["blocked"], 0)

    def test_different_queries_are_not_a_loop(self):
        """Exploring is not looping. Twenty distinct searches must all run."""
        out = run_js("""
        const d = new m.CycleDetector();
        let blocked = 0;
        for (let i = 0; i < 20; i++) if (d.check("web_search", { query: "topic " + i })) blocked++;
        process.stdout.write(JSON.stringify({ blocked }));
        """)
        self.assertEqual(out["blocked"], 0)

    def test_reset_clears_the_tally_for_a_new_session(self):
        out = run_js("""
        const d = new m.CycleDetector();
        for (let i = 0; i < 12; i++) d.check("web_search", { query: "x" });
        d.reset();
        process.stdout.write(JSON.stringify({ afterReset: d.check("web_search", { query: "x" }) }));
        """)
        self.assertIsNone(out["afterReset"])

    def test_unserializable_input_fails_open(self):
        out = run_js("""
        const d = new m.CycleDetector();
        const a = {}; a.self = a;
        process.stdout.write(JSON.stringify({ r: d.check("web_search", a) }));
        """)
        self.assertIsNone(out["r"], "a call it cannot fingerprint must not be blocked")


if __name__ == "__main__":
    unittest.main()
