"""The third guard with the same bash-shaped hole, and the one that mattered most.

`research-depth.ts` counted writes from `write` and `edit` only. Two gates run
on that count:

  * The artifact gate refuses further searching when nothing has been written.
    A run that writes with bash keeps being refused for work it has done.
  * The citation gate refuses a substantial file carrying no address. A report
    written with a heredoc was never seen at all — and that gate is the one
    guard measured to change behaviour in this harness, taking addresses in
    files from 0/0/0 to 10/15/0.

Not hypothetical: the clean advancer rerun shows the model writing its
deliverable as `cat > ".../output.md" << 'EOF'`.

Two things this deliberately does NOT copy from the C.A.S.E. fix. That one
refuses shell writes to status.txt outright and never parses content, because
the protocol already demands the write tool there. Here there is no such
alternative — writing a file with bash outside a C.A.S.E. task is ordinary work
— so content is parsed where it can be, and where it cannot the bytes are
counted as unchecked rather than quietly treated as clean.

And scratch writes do not count toward the artifact gate. Crediting
`echo x > /tmp/f` would let a run satisfy "leave something behind" by touching a
temp file, which is the gate weakening itself.
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
    driver = os.path.join(ROOT, "tests", ".tmp_rdbash_driver.mjs")
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


HEREDOC = "cat > report.md << 'EOF'\n%s\nEOF" % ("finding without any address. " * 40)
HEREDOC_SOURCED = "cat > report.md << 'EOF'\n%s\nEOF" % (
    ("finding — https://a.example/one\n" * 40))


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheArtifactGateStopsMisfiring(unittest.TestCase):
    def test_a_heredoc_counts_as_a_write(self):
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        g.check("bash", { command: %s });
        process.stdout.write(JSON.stringify(g.stats()));
        """ % json.dumps(HEREDOC))
        self.assertEqual(out["writes"], 1)

    def test_a_run_that_wrote_with_bash_is_not_refused_for_writing_nothing(self):
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        g.check("web_open", { url: "https://a.example/one" });
        g.check("bash", { command: %s });
        let blocked = 0;
        for (let i = 0; i < 40; i++) if (g.check("web_search", { query: "q" + i })) blocked++;
        process.stdout.write(JSON.stringify({ blocked }));
        """ % json.dumps(HEREDOC_SOURCED))
        self.assertEqual(out["blocked"], 0)

    def test_a_scratch_write_earns_no_credit(self):
        """Otherwise "leave something behind" is satisfied by touching /tmp."""
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        g.check("bash", { command: "echo x > /tmp/scratch.txt" });
        process.stdout.write(JSON.stringify(g.stats()));
        """)
        self.assertEqual(out["writes"], 0)

    def test_reading_is_not_writing(self):
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        for (const c of ["cat notes.md", "ls -la .", "grep -r x ."])
          g.check("bash", { command: c });
        process.stdout.write(JSON.stringify(g.stats()));
        """)
        self.assertEqual(out["writes"], 0)


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheCitationGateSeesHeredocs(unittest.TestCase):
    def test_a_sourceless_report_written_with_bash_is_refused(self):
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        g.check("web_open", { url: "https://a.example/one" });
        g.check("web_open", { url: "https://b.example/two" });
        const r = g.check("bash", { command: %s });
        process.stdout.write(JSON.stringify({ blocked: !!r, reason: r ? r.reason : "" }));
        """ % json.dumps(HEREDOC))
        self.assertTrue(out["blocked"])
        self.assertIn("https://a.example/one", out["reason"])

    def test_a_sourced_report_written_with_bash_passes(self):
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        g.check("web_open", { url: "https://a.example/one" });
        g.check("web_open", { url: "https://b.example/two" });
        const r = g.check("bash", { command: %s });
        process.stdout.write(JSON.stringify({ blocked: !!r }));
        """ % json.dumps(HEREDOC_SOURCED))
        self.assertFalse(out["blocked"])

    def test_a_printf_literal_is_content_too(self):
        body = "conclusion without sources. " * 40
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        g.check("web_open", { url: "https://a.example/one" });
        g.check("web_open", { url: "https://b.example/two" });
        const r = g.check("bash", { command: %s });
        process.stdout.write(JSON.stringify({ blocked: !!r }));
        """ % json.dumps('printf "%s" > report.md' % body))
        self.assertTrue(out["blocked"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestWhatItCannotSeeIsVisible(unittest.TestCase):
    """Partial coverage is honest only when the gap is on the report."""

    def test_an_unextractable_write_counts_but_is_not_judged(self):
        """`cat a > b` names its target and hides its content.

        The first version of this test used `sed -i`, which the extractor does
        not recognise as a write at all — so it asserted a count that could
        never happen and failed for a reason unrelated to what it was checking.
        `sed -i` staying invisible is a real gap and is recorded in the retro,
        not papered over here.
        """
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        g.check("web_open", { url: "https://a.example/one" });
        g.check("web_open", { url: "https://b.example/two" });
        const r = g.check("bash", { command: "cat draft.md > report.md" });
        const s = g.stats();
        process.stdout.write(JSON.stringify({ blocked: !!r, writes: s.writes,
                                              unchecked: s.uncheckedWrites }));
        """)
        self.assertFalse(out["blocked"], "it cannot read the content, so it must not judge it")
        self.assertEqual(out["writes"], 1)
        self.assertEqual(out["unchecked"], 1)

    def test_an_extractable_write_is_not_counted_as_unchecked(self):
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        g.check("bash", { command: %s });
        process.stdout.write(JSON.stringify(g.stats()));
        """ % json.dumps(HEREDOC_SOURCED))
        self.assertEqual(out["uncheckedWrites"], 0)


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestExistingBehaviourIsUnchanged(unittest.TestCase):
    """The write/edit path was measured working; it must not shift."""

    def test_the_write_tool_still_refuses_a_sourceless_report(self):
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        g.check("web_open", { url: "https://a.example/one" });
        g.check("web_open", { url: "https://b.example/two" });
        const r = g.check("write", { path: "r.md", content: "x".repeat(3800) });
        process.stdout.write(JSON.stringify({ blocked: !!r }));
        """)
        self.assertTrue(out["blocked"])

    def test_the_depth_gate_is_untouched(self):
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        let blockedAt = -1;
        for (let i = 0; i < 20; i++) {
          const r = g.check("web_search", { query: "q" + i });
          if (r && blockedAt < 0) blockedAt = i;
        }
        process.stdout.write(JSON.stringify({ blockedAt }));
        """)
        self.assertEqual(out["blockedAt"], 8)

    def test_unserializable_input_does_not_throw(self):
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        const a = {}; a.self = a;
        let threw = false;
        try { g.check("bash", a); } catch { threw = true; }
        process.stdout.write(JSON.stringify({ threw }));
        """)
        self.assertFalse(out["threw"])

@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestInPlaceEditsCountButAreNotJudged(unittest.TestCase):
    """Task_013. `research-depth` imports writeTargets from bash-containment, so
    the new forms arrive here for free — and "for free" is exactly the kind of
    claim this repo does not accept without running it.

    The two halves have to land differently. The output gate must SEE the write,
    or a run that produced its report with `sed -i` looks like a run that
    produced nothing. The citation gate must NOT judge it, because no content
    can be extracted from an in-place edit and a gate that judges what it cannot
    read is a gate reporting on its own guesses."""

    IN_PLACE = "sed -i 's/TODO/done/' report.md"

    def test_it_is_counted_as_a_write(self):
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        g.check("bash", { command: %s });
        process.stdout.write(JSON.stringify(g.stats()));
        """ % json.dumps(self.IN_PLACE))
        self.assertEqual(out["writes"], 1)

    def test_the_content_is_recorded_as_unchecked_rather_than_judged(self):
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        g.check("web_open", { url: "https://a.example/one" });
        g.check("web_open", { url: "https://b.example/two" });
        const r = g.check("bash", { command: %s });
        process.stdout.write(JSON.stringify({ blocked: !!r, stats: g.stats() }));
        """ % json.dumps(self.IN_PLACE))
        self.assertFalse(out["blocked"], "nothing was read, so nothing may be judged")
        self.assertEqual(out["stats"]["uncheckedWrites"], 1)

    def test_a_read_only_sed_is_not_a_write_at_all(self):
        out = run_js("""
        const g = new m.ResearchDepthGuard();
        g.check("bash", { command: "sed -n '1,5p' report.md" });
        process.stdout.write(JSON.stringify(g.stats()));
        """)
        self.assertEqual(out["writes"], 0)
        self.assertEqual(out["uncheckedWrites"], 0)


if __name__ == "__main__":
    unittest.main()
