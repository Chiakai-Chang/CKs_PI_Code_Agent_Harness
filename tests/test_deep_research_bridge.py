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

    def test_web_search_defers_to_deep_research_for_multi_part_questions(self):
        c = read("pi-extensions/stealth-web-bridge/index.ts")
        self.assertIn("prefer deep_research", c)

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
