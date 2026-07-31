"""deep_research: subagent fan-out as a mechanism, not as advice.

`deep-research-guide` described decomposition, subagent fan-out and cited
synthesis while nothing implemented any of it — the model was asked to imagine
having subagents. This bridge spawns each sub-question as its own `pi --print`
process (Pi's documented subagent pattern) and returns only a digest.

Two measurements shaped it, and the tests pin both:
  * llama.cpp here runs `-np 1`, so concurrent requests SERIALIZE (measured: two
    parallel requests finished at 7.3s and 14.3s). Parallel fan-out buys nothing
    and multiplies wall time, hence sequential execution and a hard low cap.
  * A 42,999-char tool result was observed derailing this model mid-task, so the
    value is context isolation: children read the pages, the parent gets a
    bounded digest.
"""

import json
import os
import re
import shutil
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(ROOT, "pi-extensions", "deep-research-bridge", "research.ts")
IDX = os.path.join(ROOT, "pi-extensions", "deep-research-bridge", "index.ts")


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


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
    driver = os.path.join(ROOT, "tests", ".tmp_dr_driver.mjs")
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
class TestSubQuestionValidation(unittest.TestCase):
    def test_accepts_a_reasonable_set(self):
        out = run_js('process.stdout.write(JSON.stringify(m.validateSubQuestions(["a","b","c"])));')
        self.assertTrue(out["ok"])
        self.assertEqual(out["questions"], ["a", "b", "c"])

    def test_rejects_more_than_the_cap(self):
        """Sub-questions run sequentially; ten of them is an hour of wall time,
        not a thorough report."""
        out = run_js('process.stdout.write(JSON.stringify(m.validateSubQuestions(["a","b","c","d","e","f","g"])));')
        self.assertFalse(out["ok"])
        self.assertIn("sequentially", out["error"])

    def test_rejects_empty_and_non_array(self):
        for arg in ('[]', '"x"', 'null', '[" ", ""]'):
            out = run_js('process.stdout.write(JSON.stringify(m.validateSubQuestions(%s)));' % arg)
            self.assertFalse(out["ok"], arg)


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestChildOutputParsing(unittest.TestCase):
    def test_takes_only_the_last_assistant_message(self):
        """Earlier assistant messages are the child's tool-use narration. The
        whole point is that the parent does not inherit it."""
        lines = [
            json.dumps({"type": "message_end", "message": {"role": "assistant",
                        "content": [{"type": "text", "text": "narration"}]}}),
            json.dumps({"type": "message_end", "message": {"role": "assistant",
                        "content": [{"type": "text", "text": "FINAL finding"}]}}),
            "not json at all",
        ]
        out = run_js('process.stdout.write(JSON.stringify({t: m.parseChildOutput(%s)}));'
                     % json.dumps("\n".join(lines)))
        self.assertEqual(out["t"], "FINAL finding")

    def test_garbage_yields_empty_not_a_crash(self):
        out = run_js('process.stdout.write(JSON.stringify({t: m.parseChildOutput("garbage\\n{bad")}));')
        self.assertEqual(out["t"], "")


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestDeepResearchIsOptIn(unittest.TestCase):
    """Off by default, because the model picks it when it should not.

    Measured 2026-07-31 on one question: `deep_research` spent 44 minutes across
    four children and returned nothing usable, while plain web_search + web_open
    answered the same question in 8 minutes with named sources. The capability is
    real — it is the only thing keeping a 42,999-char page out of the parent
    context — but letting the model choose it costs 5x for a worse answer.

    Five of the seven defects found in the 2026-07-30/31 validation round came
    from this one bridge. Three are fixed; P1 (a stalled child's last message
    filed as a finding) and P3 (the cost model) are not.

    So: keep the code and the tests, take away the model's ability to reach for
    it. Flipping `enableDeepResearch` to true in pi-config/harness-config.json
    brings it back.
    """

    def _enabled_for(self, cfg_obj):
        """Run the real gate against a temp pi-config, so the DEFAULT is proven
        by execution rather than by reading the source."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "pi-config"))
            with open(os.path.join(tmp, "pi-config", "harness-config.json"), "w", encoding="utf-8") as f:
                json.dump(cfg_obj, f)
            root = tmp.replace("\\", "/")
            return run_js('process.stdout.write(JSON.stringify({on: m.deepResearchEnabled(%s)}));'
                          % json.dumps(root))["on"]

    def test_shipped_config_has_the_flag_off(self):
        cfg = json.loads(read("pi-config/harness-config.json"))
        self.assertIn("enableDeepResearch", cfg, "the flag must ship, not be an undocumented default")
        self.assertFalse(cfg["enableDeepResearch"], "default is off; see this class's docstring for why")

    def test_nothing_is_registered_when_the_flag_is_off(self):
        """The bridge must return BEFORE registering anything — not register a
        tool that refuses. A registered tool costs its description and
        guidelines in every turn whether or not it is ever called."""
        c = read("pi-extensions/deep-research-bridge/index.ts")
        gate = c.index("if (!deepResearchEnabled()) return;")
        first_register = c.index("pi.registerTool(")
        self.assertLess(gate, first_register, "the gate must precede every registration")

    def test_flag_true_enables_and_missing_key_disables(self):
        self.assertTrue(self._enabled_for({"enableDeepResearch": True}))
        self.assertFalse(self._enabled_for({"enableDeepResearch": False}))
        self.assertFalse(self._enabled_for({}), "an absent key must mean OFF")
        self.assertFalse(self._enabled_for({"enableDeepResearch": "yes"}),
                         "only a real boolean true opts in")

    def test_no_other_bridge_advertises_the_tool(self):
        """Guidance for a gated tool must live behind the same gate.

        Caught by dumping the real prompt with the flag off: `deep_research` was
        gone from the tool section, but stealth-web-bridge still told the model
        "For a question needing several separate things looked up, prefer
        deep_research". That is the mirror of a failure this repo already paid
        for — a guard once told the model `web_search` was not available while it
        was, and the model's own reasoning recorded the contradiction. Pointing
        it at a tool that does NOT exist is the same defect with the sign
        flipped.
        """
        import glob
        for idx in glob.glob(os.path.join(ROOT, "pi-extensions", "*", "index.ts")):
            name = os.path.basename(os.path.dirname(idx))
            if name == "deep-research-bridge":
                continue
            with open(idx, encoding="utf-8") as f:
                src = f.read()
            if name == "yes-hooks-bridge":
                # Knowing the NAME is required, not advertising. HARNESS_TOOLS
                # exists so the parser never tells the model a real tool does not
                # exist — observed live, the model's own reasoning recorded the
                # contradiction and it burned all three strikes. If the flag is
                # flipped on, the guard must still recognise the tool.
                self.assertIn("HARNESS_TOOLS", src)
                continue
            self.assertNotIn(
                "deep_research", src,
                f"{name} advertises deep_research, which is off by default — "
                "move that guidance into deep-research-bridge, behind the same gate",
            )

    def test_the_flag_is_read_the_way_every_other_bridge_reads_config(self):
        """taste-bridge once resolved the harness root as join(__dirname,
        '../..'), which lands on ~/.pi with no pi-config/, so its flag silently
        did nothing for every turn. Same mistake here would silently re-enable
        this."""
        c = read("pi-extensions/deep-research-bridge/research.ts")
        self.assertIn('pkg["pi-harness"]?.root', c)
        self.assertIn("harness-config.json", c)

    def test_default_is_off_when_the_key_is_missing(self):
        """An absent key must mean off. `!== false` (taste-bridge's idiom) would
        mean ON here, which is the opposite of what was decided."""
        c = read("pi-extensions/deep-research-bridge/research.ts")
        self.assertRegex(c, r"enableDeepResearch\s*===\s*true",
                         "must opt IN explicitly, not default to on when the key is absent")


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestChildOutputIsBounded(unittest.TestCase):
    """P7, 2026-07-31: a runaway child killed the PARENT.

        proc.stdout.on("data", (d) => out += d.toString());
        RangeError: Invalid string length

    The bridge accumulated a child's stdout into one unbounded string. A child
    that never stopped emitting eventually exceeded V8's maximum string length
    and threw inside the stream handler, taking the whole Pi process down 39
    minutes into a research call — not the child, the parent. The session log
    ends after a single turn.

    The two streams are trimmed from opposite ends, and that asymmetry is the
    point: parseChildOutput wants the LAST assistant message, while
    summarizeChildStderr wants the FIRST error, because banners come last and
    causes come first.
    """

    def test_stdout_keeps_the_tail(self):
        out = run_js(
            'process.stdout.write(JSON.stringify({t: m.appendBounded("AAAA", "BBBBCC", 6, "tail")}));')
        self.assertEqual(out["t"][-2:], "CC", "the final assistant message lives at the end")
        self.assertLessEqual(len(out["t"]), 6)

    def test_stderr_keeps_the_head(self):
        out = run_js(
            'process.stdout.write(JSON.stringify({t: m.appendBounded("ERR!", "xxxxxx", 6, "head")}));')
        self.assertTrue(out["t"].startswith("ERR!"), "the cause is the first thing printed")
        self.assertLessEqual(len(out["t"]), 6)

    def test_under_the_cap_nothing_is_lost(self):
        out = run_js('process.stdout.write(JSON.stringify({t: m.appendBounded("ab", "cd", 100, "tail")}));')
        self.assertEqual(out["t"], "abcd")

    def test_a_single_oversized_chunk_is_still_bounded(self):
        """The crash came from one enormous accumulation, so a single chunk
        larger than the cap must not slip through."""
        out = run_js('process.stdout.write(JSON.stringify({t: m.appendBounded("", "y".repeat(5000), 100, "tail")}));')
        self.assertLessEqual(len(out["t"]), 100)

    def test_the_bridge_uses_it_on_both_streams(self):
        idx = read("pi-extensions/deep-research-bridge/index.ts")
        self.assertNotIn('out += d.toString()', idx, "unbounded stdout accumulation is what crashed the parent")
        self.assertNotIn('err += d.toString()', idx, "stderr is unbounded too")
        self.assertIn("appendBounded", idx)


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestChildFailureDiagnostic(unittest.TestCase):
    """P2 from the 2026-07-30 validation: when a child fails, the parent is told
    nothing useful about why.

    The failure text was built as `err.slice(-300)` — the LAST 300 characters of
    the child's stderr. A child's stderr ends with whatever a bridge printed on
    the way up, so the digest carried:

        (failed after 900s — child agent exited null with no answer.
         [ecc-bridge] ECC Submodule Version: 2.0.0)

    Three of four sub-questions failed in that run and not one of them said why.
    Taking the tail is exactly backwards: banners come last, causes come first.
    """

    def test_bridge_banners_are_not_the_diagnostic(self):
        stderr = ("[ecc-bridge] ECC Submodule Version: 2.0.0\n"
                  "[stealth-web] backend ready\n")
        out = run_js('process.stdout.write(JSON.stringify({t: m.summarizeChildStderr(%s)}));'
                     % json.dumps(stderr))
        self.assertNotIn("ECC Submodule Version", out["t"],
                         "a startup banner is not a reason for failure")

    def test_a_real_error_survives_even_when_banners_follow_it(self):
        stderr = ("Error: connect ECONNREFUSED 127.0.0.1:8080\n"
                  "[ecc-bridge] ECC Submodule Version: 2.0.0\n")
        out = run_js('process.stdout.write(JSON.stringify({t: m.summarizeChildStderr(%s)}));'
                     % json.dumps(stderr))
        self.assertIn("ECONNREFUSED", out["t"], "the cause must not be crowded out by later noise")

    def test_empty_stderr_says_so_rather_than_nothing(self):
        out = run_js('process.stdout.write(JSON.stringify({t: m.summarizeChildStderr("")}));')
        self.assertTrue(out["t"], "an empty diagnostic is worse than 'no stderr'")

    def test_only_banners_reports_that_there_was_no_error_output(self):
        stderr = "[ecc-bridge] ECC Submodule Version: 2.0.0\n"
        out = run_js('process.stdout.write(JSON.stringify({t: m.summarizeChildStderr(%s)}));'
                     % json.dumps(stderr))
        self.assertTrue(out["t"])
        self.assertNotIn("[ecc-bridge]", out["t"])

    def test_output_is_bounded(self):
        out = run_js('process.stdout.write(JSON.stringify({t: m.summarizeChildStderr("E: " + "x".repeat(5000))}));')
        self.assertLessEqual(len(out["t"]), 400, "the parent must not inherit a wall of stderr")


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestDigest(unittest.TestCase):
    def test_reports_failures_instead_of_hiding_them(self):
        out = run_js("""
const d = m.buildDigest("Q", [
  {question: "s1", finding: "f1", ok: true, seconds: 3},
  {question: "s2", finding: "boom", ok: false, seconds: 9},
]);
process.stdout.write(JSON.stringify({d}));
""")
        self.assertIn("1/2 sub-questions", out["d"])
        self.assertIn("failed after 9s", out["d"])
        self.assertIn("unresolved", out["d"], "a failed sub-question must not be filled in from memory")

    def test_findings_are_clamped(self):
        out = run_js('process.stdout.write(JSON.stringify({n: m.clampFinding("x".repeat(9000)).length}));')
        self.assertLess(out["n"], 6200)


class TestRecursionGuard(unittest.TestCase):
    """Without this, one confused decomposition forks agents until the machine
    dies — each child would load the same bridge and could call the tool again."""

    def setUp(self):
        self.idx = read("pi-extensions/deep-research-bridge/index.ts")
        self.mod = read("pi-extensions/deep-research-bridge/research.ts")

    def test_marker_is_set_on_children(self):
        self.assertIn("CHILD_MARKER", self.mod)
        self.assertIn("[CHILD_MARKER]: \"1\"", self.idx)

    def test_tool_refuses_when_marker_present(self):
        self.assertIn("if (process.env[CHILD_MARKER])", self.idx)


class TestChildWriteBoundary(unittest.TestCase):
    """Children must not be able to change the machine they research from.

    Found 2026-07-30 in a real session. The question was pure research — "what
    is llama.cpp's Qwen3.5 MTP support?" — and the parent made exactly one tool
    call, `deep_research`. Inside its window a child modified
    `scripts/make-probe-fixture.py` and dropped a stray file in the repo root.
    Neither write appears anywhere in the parent's session log, because children
    run with `--no-session`.

    Three things stacked: cwd is the parent's cwd, so children stand in the
    repo; no tool restriction, so they hold the full built-in set; and no
    session, so there is no audit trail by construction. Recursion had been
    anticipated (CHILD_MARKER); write access had not.

    A denylist is used rather than a `--tools` allowlist on purpose. The harm is
    exactly "mutates the local machine", which is three names; an allowlist has
    to enumerate every research tool and silently reduces a child to nothing if
    one name drifts — and producing nothing is an already-observed failure mode
    of this bridge.
    """

    def setUp(self):
        self.idx = read("pi-extensions/deep-research-bridge/index.ts")

    def _excluded(self):
        m = re.search(r'"--exclude-tools"\s*,\s*"([^"]+)"', self.idx)
        return [t.strip() for t in m.group(1).split(",")] if m else []

    def test_children_cannot_write_edit_or_run_shell(self):
        excluded = self._excluded()
        self.assertTrue(excluded, "children must be spawned with --exclude-tools")
        for tool in ("bash", "edit", "write"):
            self.assertIn(tool, excluded, f"a research child must not hold `{tool}`")

    def test_research_tools_are_left_alone(self):
        """Negative control: blocking mutation must not disarm the research."""
        excluded = self._excluded()
        for tool in ("web_search", "web_open", "read", "grep", "find", "ls"):
            self.assertNotIn(tool, excluded, f"`{tool}` is read-only and must stay available")

    def test_the_reason_is_recorded_next_to_the_flag(self):
        """This flag looks removable to anyone who has not seen a child edit the
        repo. The incident has to be readable from the source."""
        self.assertRegex(self.idx, r"(?s)exclude-tools.{0,1200}?(cwd|repo|write)")


class TestSequentialByDesign(unittest.TestCase):
    def setUp(self):
        self.idx = read("pi-extensions/deep-research-bridge/index.ts")

    def test_awaits_each_child_in_a_loop(self):
        """Not Promise.all: with -np 1 the server serializes anyway, so parallel
        dispatch only removes the ability to report progress."""
        self.assertIn("for (let i = 0", self.idx)
        self.assertIn("await runChild(", self.idx)
        self.assertNotIn("Promise.all", self.idx)

    def test_streams_progress(self):
        self.assertIn("onUpdate?.(", self.idx)

    def test_children_are_isolated_sessions(self):
        for flag in ('"--print"', '"--mode", "json"', '"--no-session"', '"--append-system-prompt"'):
            self.assertIn(flag, self.idx)

    def test_child_has_a_timeout(self):
        self.assertIn("CHILD_TIMEOUT_MS", self.idx)


class TestRestoreWiring(unittest.TestCase):
    def test_bridge_registered_and_managed(self):
        c = read("scripts/restore.py")
        self.assertEqual(c.count('"deep-research-bridge"'), 3)

    def test_listed_in_bridge_manifest(self):
        with open(os.path.join(ROOT, "pi-extensions", "bridge-manifest.json"), encoding="utf-8") as f:
            names = {b["name"] for b in json.load(f)["bridges"]}
        self.assertIn("deep-research-bridge", names)

    def test_esm_bridge_avoids_require(self):
        self.assertNotIn("require(", read("pi-extensions/deep-research-bridge/index.ts"))


class TestCrossBridgeGuidanceIsCoherent(unittest.TestCase):
    """Two bridges each injecting confident guidance, with nothing checking the
    combination. stealth-web's guideline said to call web_search "for any task
    needing current or external information" — unconditional, and it swallowed
    every other route to the web. Observed twice: the model web_searched for a
    LOCAL skill file whose path it had just been given, and it web_searched
    instead of calling deep_research when told explicitly to call deep_research.
    """

    def test_web_search_guidance_is_scoped_not_absolute(self):
        c = read("pi-extensions/stealth-web-bridge/index.ts")
        self.assertNotIn("call web_search for any task needing current or external information", c)
        self.assertIn("results of in THIS conversation", c)

    def test_the_deferral_guidance_lives_with_the_tool_it_advertises(self):
        """This used to assert stealth-web told the model to prefer
        deep_research. That was right while deep_research was always on; once it
        became opt-in (default off, 2026-07-31) the same line started pointing
        the model at a tool that was no longer registered — verified by dumping
        the real prompt. The guidance moved into deep-research-bridge so it is
        gated with the tool. The incident it protects against is unchanged: the
        model web_searched instead of calling deep_research when told to."""
        dr = read("pi-extensions/deep-research-bridge/index.ts")
        self.assertIn("keeps the pages out of this context", dr)
        sw = read("pi-extensions/stealth-web-bridge/index.ts")
        self.assertNotIn("deep_research", sw)

    def test_web_search_says_not_to_search_for_local_files(self):
        c = read("pi-extensions/stealth-web-bridge/index.ts")
        self.assertIn("already on this machine", c)

    def test_deep_research_states_it_is_a_tool_not_a_skill(self):
        """Observed in the live run: the model's first thought was 'a skill
        called deep_research. I need to first find it in the skill catalog'."""
        c = read("pi-extensions/deep-research-bridge/index.ts")
        self.assertIn("is a TOOL, not a skill", c)


if __name__ == "__main__":
    unittest.main()
