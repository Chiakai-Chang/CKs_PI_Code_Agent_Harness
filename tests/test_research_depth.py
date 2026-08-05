"""Breadth without depth, and a session that leaves nothing behind.

Measured 2026-08-05, Pi session 019fd29d-4e18-7970-835b-87b2d2ae46cc — a real
research request from the harness owner, three turns, run to completion:

    tool calls   40  =  38 web_search  +  2 web_open  +  0 write/edit
    distinct query signatures: 40      max repeat: 1

Three separate readings of the same run:

  * `max repeat: 1` — every query differed, so `loop-detect.ts` was right to stay
    silent. This is not the loop that cycles. It is a third shape: many distinct
    questions, one round, nothing read in full.

  * `2 web_open / 38 web_search` — the conclusions were assembled from search
    result snippets. Snippets are written to earn a click, not to be quoted.

  * `0 write/edit` — the working directory D:\\tmp\\pi-test held nothing but
    `.git` afterwards. The whole investigation existed only in context: not
    reviewable, not resumable, and no claim traceable to where it came from.

Blocking `web_search` is the only lever that reaches this. There is no event for
"about to answer", and a note cannot compete with momentum: the task-shape router
delivered a correct routing note on the first search of that very session, and
37 searches followed it.

The gates therefore refuse a search — but only a search that is already past the
point of usefulness, and never in a way that can trap the run. A gate ignored
three times steps aside for the rest of the session (`retired`), because the
scar this repo carries from GateGuard is a gate nobody had run denying the first
bash command of every session.
"""

import json
import os
import re
import shutil
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(ROOT, "pi-extensions", "yes-hooks-bridge", "research-depth.ts")


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
    driver = os.path.join(ROOT, "tests", ".tmp_depth_driver.mjs")
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
class TestDepthGate(unittest.TestCase):
    """Searching without ever reading is the failure. Reading clears it."""

    def test_searching_without_opening_anything_is_eventually_refused(self):
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        let blockedAt = -1;
        for (let i = 0; i < 30; i++) {
          const r = g.check("web_search", { query: "q" + i });
          if (r && blockedAt < 0) blockedAt = i;
        }
        process.stdout.write(JSON.stringify({ blockedAt }));
        """)
        self.assertGreater(out["blockedAt"], 0, "a run that never reads must be stopped")
        self.assertLess(out["blockedAt"], 12,
                        "and stopped early — the real run wasted 29 more searches after this point")

    def test_the_reason_names_the_next_action(self):
        """`web_search` returns real addresses now (the readability fix). Before
        that it returned none, and demanding a page open would have been cruel."""
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        let reason = "";
        for (let i = 0; i < 20; i++) {
          const r = g.check("web_search", { query: "q" + i });
          if (r) { reason = r.reason; break; }
        }
        process.stdout.write(JSON.stringify({ reason }));
        """)
        self.assertRegex(out["reason"], r"web_open")

    def test_reading_one_page_clears_it(self):
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        for (let i = 0; i < 3; i++) g.check("web_search", { query: "q" + i });
        g.check("web_open", { url: "https://example.com/a" });
        let blocked = 0;
        for (let i = 0; i < 6; i++) if (g.check("web_search", { query: "later" + i })) blocked++;
        process.stdout.write(JSON.stringify({ blocked }));
        """)
        self.assertEqual(out["blocked"], 0, "a run that reads is doing the right thing")

    def test_the_real_session_would_have_been_stopped_29_searches_earlier(self):
        """Replay of 019fd29d: 38 searches, then the only two opens."""
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        let firstBlock = -1;
        for (let i = 0; i < 38; i++) {
          if (g.check("web_search", { query: "distinct " + i }) && firstBlock < 0) firstBlock = i;
        }
        process.stdout.write(JSON.stringify({ firstBlock }));
        """)
        self.assertGreater(out["firstBlock"], 0)
        self.assertLess(out["firstBlock"], 38 - 20,
                        "the point of the gate is to arrive long before the run gave up")


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestArtifactGate(unittest.TestCase):
    """A session that writes nothing cannot be reviewed, resumed, or sourced."""

    def test_a_long_search_run_that_writes_nothing_is_refused(self):
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        g.check("web_open", { url: "https://example.com/read" });  // depth gate satisfied
        let reason = "";
        for (let i = 0; i < 40; i++) {
          const r = g.check("web_search", { query: "q" + i });
          if (r) { reason = r.reason; break; }
        }
        process.stdout.write(JSON.stringify({ reason }));
        """)
        self.assertTrue(out["reason"], "writing nothing across a long run must be refused")
        self.assertRegex(out["reason"], r"(?i)write|file|\.md")

    def test_writing_a_file_clears_it(self):
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        g.check("web_open", { url: "https://example.com/read" });
        g.check("write", { path: "findings.md" });
        let blocked = 0;
        for (let i = 0; i < 40; i++) if (g.check("web_search", { query: "q" + i })) blocked++;
        process.stdout.write(JSON.stringify({ blocked }));
        """)
        self.assertEqual(out["blocked"], 0)


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestCitationGate(unittest.TestCase):
    """Pages read, report written, and no way to tell where any of it came from.

    Measured 2026-08-05, three runs of the market-survey scenario with both other
    gates installed:

        run1   8 searches   11 pages opened   report.md 3788 chars   0 URLs
        run2   6 searches    6 pages opened   report.md 4295 chars   0 URLs
        run3   9 searches    9 pages opened   findings.md 3482 chars 0 URLs

    Depth was fine. Artifacts were fine. Every file was substantial and none of
    them cited anything. What URLs did appear turned up only in the chat reply,
    and one of those was invented (a shopee.tw search endpoint assembled from a
    pattern).

    All three runs read `research-task-routing`, whose findings table carries a
    mandatory `Source` column, and two also read `planning-with-files`. The skill
    loaded, was read, and the instruction inside it was skipped three times out
    of three. Changing the shape of the instruction — from a sentence to a table
    column with a blank cell — had already been tried; this is that same
    instruction losing again.

    A file with no sources is the polished version of the failure this whole
    round is about: it survives the session and still cannot be checked.
    """

    def test_a_substantial_report_that_cites_nothing_is_refused(self):
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        g.check("web_open", { url: "https://a.example/one" });
        g.check("web_open", { url: "https://b.example/two" });
        const r = g.check("write", { path: "report.md", content: "x".repeat(3800) });
        process.stdout.write(JSON.stringify({ blocked: !!r, reason: r ? r.reason : "" }));
        """)
        self.assertTrue(out["blocked"])

    def test_the_reason_hands_back_the_addresses_it_read(self):
        """Naming the pages is the point. `research-task-routing` already asks for
        a Source column in words and was ignored three times out of three."""
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        g.check("web_open", { url: "https://a.example/one" });
        g.check("web_open", { url: "https://b.example/two" });
        const r = g.check("write", { path: "report.md", content: "x".repeat(3800) });
        process.stdout.write(JSON.stringify({ reason: r ? r.reason : "" }));
        """)
        self.assertIn("https://a.example/one", out["reason"])
        self.assertIn("https://b.example/two", out["reason"])

    def test_a_report_that_cites_its_sources_passes(self):
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        g.check("web_open", { url: "https://a.example/one" });
        g.check("web_open", { url: "https://b.example/two" });
        const body = "finding\\n".repeat(400) + "source: https://a.example/one";
        const r = g.check("write", { path: "report.md", content: body });
        process.stdout.write(JSON.stringify({ blocked: !!r }));
        """)
        self.assertFalse(out["blocked"])

    def test_an_edit_is_judged_on_its_new_text(self):
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        g.check("web_open", { url: "https://a.example/one" });
        g.check("web_open", { url: "https://b.example/two" });
        const r = g.check("edit", { path: "report.md",
                                    edits: [{ newText: "y".repeat(3800) }] });
        process.stdout.write(JSON.stringify({ blocked: !!r }));
        """)
        self.assertTrue(out["blocked"])

    def test_a_plan_written_before_any_reading_is_untouched(self):
        """task_plan.md comes first, legitimately, and has nothing to cite yet."""
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        const r = g.check("write", { path: "task_plan.md", content: "p".repeat(3800) });
        process.stdout.write(JSON.stringify({ blocked: !!r }));
        """)
        self.assertFalse(out["blocked"])

    def test_a_short_note_is_untouched(self):
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        g.check("web_open", { url: "https://a.example/one" });
        g.check("web_open", { url: "https://b.example/two" });
        const r = g.check("write", { path: "progress.md", content: "phase 1 done" });
        process.stdout.write(JSON.stringify({ blocked: !!r }));
        """)
        self.assertFalse(out["blocked"])

    def test_it_gives_up_rather_than_block_every_write(self):
        """A run that will not cite must still be able to finish."""
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        g.check("web_open", { url: "https://a.example/one" });
        g.check("web_open", { url: "https://b.example/two" });
        let blocks = 0, allowed = 0;
        for (let i = 0; i < 20; i++) {
          if (g.check("write", { path: "r.md", content: "x".repeat(3800) })) blocks++;
          else allowed++;
        }
        process.stdout.write(JSON.stringify({ blocks, allowed }));
        """)
        self.assertGreater(out["blocks"], 0)
        self.assertGreater(out["allowed"], 0, "a run must always be able to finish writing")

    def test_a_blocked_write_still_counts_as_having_written(self):
        """Otherwise the artifact gate punishes a run for the citation gate's
        refusal — two guards in the same module must not deadlock each other."""
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        g.check("web_open", { url: "https://a.example/one" });
        g.check("web_open", { url: "https://b.example/two" });
        g.check("write", { path: "r.md", content: "x".repeat(3800) });
        process.stdout.write(JSON.stringify({ writes: g.stats().writes }));
        """)
        self.assertGreaterEqual(out["writes"], 1)


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestItCannotTrapTheRun(unittest.TestCase):
    """The GateGuard scar: a gate nobody had run denied the first bash command of
    every session. A gate that cannot be satisfied must step aside."""

    def test_a_gate_ignored_three_times_steps_aside(self):
        """If `web_open` is failing — the site blocks it, the page 404s — the run
        can neither search nor read. It must not be stuck there forever."""
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        let blocks = 0, allowedAfter = 0;
        for (let i = 0; i < 200; i++) {
          if (g.check("web_search", { query: "q" + i })) blocks++;
          else if (blocks > 0) allowedAfter++;
        }
        process.stdout.write(JSON.stringify({ blocks, allowedAfter }));
        """)
        self.assertGreater(out["allowedAfter"], 0, "the run must be able to continue")
        self.assertLessEqual(out["blocks"], 8, "and must not be nagged indefinitely")


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestOrdinaryWorkIsUntouched(unittest.TestCase):
    """Thresholds are generous on purpose: a normal lookup must never see this."""

    def test_a_short_lookup_is_never_touched(self):
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        let blocked = 0;
        for (let i = 0; i < 5; i++) if (g.check("web_search", { query: "q" + i })) blocked++;
        process.stdout.write(JSON.stringify({ blocked }));
        """)
        self.assertEqual(out["blocked"], 0)

    def test_other_tools_are_not_searches(self):
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        let blocked = 0;
        for (const t of ["bash", "read", "grep", "ls", "edit", "write"])
          for (let i = 0; i < 50; i++) if (g.check(t, { x: i })) blocked++;
        process.stdout.write(JSON.stringify({ blocked }));
        """)
        self.assertEqual(out["blocked"], 0, "only web_search is gated")

    def test_reset_clears_the_session(self):
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        for (let i = 0; i < 30; i++) g.check("web_search", { query: "q" + i });
        g.reset();
        let blocked = 0;
        for (let i = 0; i < 5; i++) if (g.check("web_search", { query: "fresh" + i })) blocked++;
        process.stdout.write(JSON.stringify({ blocked }));
        """)
        self.assertEqual(out["blocked"], 0)

    def test_unserializable_input_fails_open(self):
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        const a = {}; a.self = a;
        let threw = false;
        try { for (let i = 0; i < 20; i++) g.check("web_search", a); } catch { threw = true; }
        process.stdout.write(JSON.stringify({ threw }));
        """)
        self.assertFalse(out["threw"], "a guard must never break the turn")


if __name__ == "__main__":
    unittest.main()
