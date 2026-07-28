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


if __name__ == "__main__":
    unittest.main()
