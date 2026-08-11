"""Restating the goal mid-run, because nothing in this harness ever did.

The owner's question on 2026-08-09: "跑到第 18 步還記得:我原本到底要完成什麼?"
Checked, and the answer was no. Every goal-bearing injection in this harness is
registered on `before_agent_start`, which the installed type declares as "Fired
after user submits prompt but before agent loop" — once per USER MESSAGE. The
owner's own session 019fe60f was 1 user message and 16 assistant turns.

These tests are about the trigger, not the wording. The threshold and the cap are
the whole design: a reminder that fires on a two-call exchange is noise, and one
that fires every turn is wallpaper the model learns to skip — this repo has
measured that outcome three separate times.

The failing case that matters most is the last class: a restatement that quotes a
request the user has already moved on from. That is worse than silence, so a
cycle boundary must clear the previous cycle's goal.
"""

import io
import tempfile
import json
import os
import re
import shutil
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(ROOT, "pi-extensions", "task-shape-bridge", "goal-restate.ts")
INDEX = os.path.join(ROOT, "pi-extensions", "task-shape-bridge", "index.ts")


def _node_major():
    if not shutil.which("node"):
        return 0
    try:
        out = subprocess.run(["node", "--version"], capture_output=True,
                             text=True, timeout=30).stdout
    except Exception:
        return 0
    m = re.match(r"v(\d+)", out.strip())
    return int(m.group(1)) if m else 0


NODE_OK = _node_major() >= 22


def run_js(script):
    driver = os.path.join(ROOT, "tests", ".tmp_restate_driver.mjs")
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


def drive(prompt, multi_step, results):
    """Run a cycle and return the text emitted after each tool result.

    `results` is a list of isError booleans, one per tool result.
    """
    return run_js(
        "const r = new m.GoalRestate();\n"
        "r.begin(%s, %s);\n"
        "const out = %s.map(e => r.afterToolResult(e));\n"
        "process.stdout.write(JSON.stringify(out));"
        % (json.dumps(prompt), json.dumps(multi_step), json.dumps(results))
    )


GOAL = "研究三個競品的定價、整理成表格、然後寫一份建議書"


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTrigger(unittest.TestCase):
    def test_silent_below_the_threshold(self):
        """A short exchange is never interrupted.

        Median tool calls per real user-prompt cycle on this machine is 2
        (219 cycles measured 2026-08-09). Firing there would make the common
        case the noisy one."""
        out = drive(GOAL, True, [False] * 11)
        self.assertEqual([o for o in out if o], [],
                         "fired before the threshold: %r" % out)

    def test_fires_exactly_at_the_threshold(self):
        out = drive(GOAL, True, [False] * 12)
        fired = [i for i, o in enumerate(out) if o]
        self.assertEqual(fired, [11],
                         "expected one firing on the 12th result, got %r" % fired)

    def test_capped_per_cycle(self):
        """Rarity is the design. 100 calls buys two restatements, not eight."""
        out = drive(GOAL, True, [False] * 100)
        self.assertEqual(len([o for o in out if o]), 2,
                         "cap not honoured: %d firings" % len([o for o in out if o]))

    def test_counter_resets_after_firing(self):
        """The second restatement is another 12 calls away, not the next one."""
        out = drive(GOAL, True, [False] * 24)
        fired = [i for i, o in enumerate(out) if o]
        self.assertEqual(fired, [11, 23], "spacing wrong: %r" % fired)

    def test_errors_do_not_count(self):
        """A refused or failed call is not progress.

        Counting it would interrupt the run least able to use a reminder as
        anything but noise."""
        out = drive(GOAL, True, [True] * 12)
        self.assertEqual([o for o in out if o], [],
                         "errors advanced the counter: %r" % out)

    def test_single_step_never_arms(self):
        """A single-step request cannot drift from itself."""
        out = drive("看一下 README 寫了什麼", False, [False] * 40)
        self.assertEqual([o for o in out if o], [],
                         "armed on a single-step request: %r" % out)

    def test_empty_prompt_never_arms(self):
        out = drive("", True, [False] * 40)
        self.assertEqual([o for o in out if o], [])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestContent(unittest.TestCase):
    def test_quotes_the_actual_request(self):
        out = drive(GOAL, True, [False] * 12)
        text = [o for o in out if o][0]
        self.assertIn(GOAL, text,
                      "the restatement does not contain the request it restates")

    def test_reports_the_step_count(self):
        """How far in it is, is the part the model cannot observe itself."""
        out = drive(GOAL, True, [False] * 12)
        self.assertIn("12", [o for o in out if o][0])

    def test_counts_results_not_calls(self):
        """Session 019fe72a fired on the 12th result while the model had issued
        14 calls — turns emit tool calls in batches. A message whose job is to be
        the reliable account of where the run is must not contain a number the
        model can see is wrong."""
        text = [o for o in drive(GOAL, True, [False] * 12) if o][0]
        self.assertIn("工具結果", text)
        self.assertNotIn("呼叫了 12 次工具", text)

    def test_labelled_so_it_is_not_read_as_tool_output(self):
        out = drive(GOAL, True, [False] * 12)
        self.assertIn("[task-shape]", [o for o in out if o][0])

    def test_long_prompts_are_marked_as_truncated(self):
        """A silently clipped goal reads as a complete one.

        A model acting on half a request is the failure this file exists to
        prevent, so truncation has to be visible."""
        long_goal = "研究" + ("競品定價與功能差異," * 200)
        short = run_js("process.stdout.write(JSON.stringify(m.shorten(%s)));"
                       % json.dumps(long_goal))
        self.assertLessEqual(len(short), 420)
        self.assertIn("截斷", short)

    def test_short_prompts_are_not_marked(self):
        short = run_js("process.stdout.write(JSON.stringify(m.shorten(%s)));"
                       % json.dumps(GOAL))
        self.assertEqual(short, GOAL)
        self.assertNotIn("截斷", short)

    def test_a_prompt_of_exactly_the_limit_is_left_alone(self):
        """The boundary itself. `<=` vs `<` here is one character and marks an
        untruncated request as truncated; the mutation sweep survived the flip
        until this test existed."""
        exact = "研" * 40
        out = run_js("process.stdout.write(JSON.stringify(m.shorten(%s, 40)));"
                     % json.dumps(exact))
        self.assertEqual(out, exact)

    def test_truncation_keeps_the_head_from_the_first_character(self):
        """Dropping the first character is invisible in a length check and
        changes what the model is told it was asked for."""
        long_goal = "首要目標是" + ("競品定價與功能差異," * 200)
        out = run_js("process.stdout.write(JSON.stringify(m.shorten(%s)));"
                     % json.dumps(long_goal))
        self.assertTrue(out.startswith("首要目標是"), "head lost: %r" % out[:20])

    def test_truncation_keeps_exactly_max_goal_chars(self):
        """Pins the constant. Without this, 400 -> 401 changes the payload and
        no test notices."""
        long_goal = "目標" * 500
        out, limit = run_js(
            "process.stdout.write(JSON.stringify([m.shorten(%s), m.MAX_GOAL_CHARS]));"
            % json.dumps(long_goal))
        head = out.split(" …(原文更長")[0]
        self.assertEqual(len(head), limit)
        self.assertEqual(limit, 400)


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestCycleBoundary(unittest.TestCase):
    """The class this module is most dangerous without.

    A restatement quoting a request the user has already moved on from actively
    pushes the model back to stale work. Silence beats it."""

    def test_new_cycle_replaces_the_goal(self):
        out = run_js(
            "const r = new m.GoalRestate();\n"
            "r.begin('第一個請求:研究並整理並撰寫報告', true);\n"
            "for (let i = 0; i < 11; i++) r.afterToolResult(false);\n"
            "r.begin('第二個請求:改成研究並比較並列出風險', true);\n"
            "const out = [];\n"
            "for (let i = 0; i < 12; i++) out.push(r.afterToolResult(false));\n"
            "process.stdout.write(JSON.stringify(out.filter(Boolean)));")
        self.assertEqual(len(out), 1, "expected one firing in the new cycle")
        self.assertIn("第二個請求", out[0])
        self.assertNotIn("第一個請求", out[0],
                         "restated the previous cycle's goal")

    def test_new_cycle_resets_the_counter(self):
        """11 calls carried over must not make the 1st call of the next cycle fire."""
        out = run_js(
            "const r = new m.GoalRestate();\n"
            "r.begin('研究並整理並撰寫', true);\n"
            "for (let i = 0; i < 11; i++) r.afterToolResult(false);\n"
            "r.begin('研究並整理並撰寫', true);\n"
            "process.stdout.write(JSON.stringify(r.afterToolResult(false)));")
        self.assertIsNone(out, "counter survived the cycle boundary")

    def test_new_cycle_restores_the_budget(self):
        """A conversation is not one request. Spending the cap in cycle 1 must
        not silence cycle 2 — the same defect the routing note shipped with and
        was measured costing two of three user turns in session 019fd29d.

        24 calls rather than 12, so a budget that came back only half restored
        fails here instead of passing."""
        out = run_js(
            "const r = new m.GoalRestate();\n"
            "r.begin('研究並整理並撰寫', true);\n"
            "for (let i = 0; i < 100; i++) r.afterToolResult(false);\n"
            "r.begin('研究並整理並撰寫', true);\n"
            "const out = [];\n"
            "for (let i = 0; i < 24; i++) out.push(r.afterToolResult(false));\n"
            "process.stdout.write(JSON.stringify(out.filter(Boolean).length));")
        self.assertEqual(out, 2)

    def test_new_cycle_gives_the_full_run_up(self):
        """After a boundary the next firing is 12 calls away, not 11.

        A counter that restarts at 1 shortens every cycle after the first by one
        call and nothing else in this file can see it."""
        out = run_js(
            "const r = new m.GoalRestate();\n"
            "r.begin('研究並整理並撰寫', true);\n"
            "for (let i = 0; i < 7; i++) r.afterToolResult(false);\n"
            "r.begin('研究並整理並撰寫', true);\n"
            "const out = [];\n"
            "for (let i = 0; i < 12; i++) out.push(r.afterToolResult(false));\n"
            "process.stdout.write(JSON.stringify(out.map(Boolean)));")
        self.assertEqual(out, [False] * 11 + [True],
                         "firing landed on the wrong call: %r" % out)

    def test_reset_disarms(self):
        out = run_js(
            "const r = new m.GoalRestate();\n"
            "r.begin('研究並整理並撰寫', true);\n"
            "r.reset();\n"
            "const out = [];\n"
            "for (let i = 0; i < 40; i++) out.push(r.afterToolResult(false));\n"
            "process.stdout.write(JSON.stringify(out.filter(Boolean)));")
        self.assertEqual(out, [])


class TestWiring(unittest.TestCase):
    """A pure module nobody calls is the defect this repo ships most often.

    `handlers-that-never-run`: an undeclared variable in a bridge handler passed
    774 tests, three checks and a byte-identical install."""

    def setUp(self):
        with open(INDEX, encoding="utf-8") as f:
            self.src = f.read()

    def test_bridge_imports_and_constructs_it(self):
        self.assertIn("goal-restate.ts", self.src)
        self.assertIn("new GoalRestate(", self.src)

    def test_armed_on_every_prompt_cycle(self):
        self.assertIn("restate.begin(", self.src)

    def test_delivered_through_the_tool_result_channel(self):
        """The only channel measured to reach the model mid-run."""
        self.assertIn("restate.afterToolResult(", self.src)
        self.assertRegex(self.src, r"content:\s*\[\.\.\.existing")

    def test_the_routing_note_still_shares_the_channel(self):
        """Both riders return from one handler. An early return on the first
        would starve the second in silence."""
        handler = self.src.split('pi.on("tool_result"')[1]
        self.assertIn("blocks.push", handler)
        self.assertIn("restate.afterToolResult", handler)

    def test_session_start_resets(self):
        self.assertIn("restate.reset()", self.src)



class TestCalibrationIsSuppliedNotHardcoded(unittest.TestCase):
    """T-A2. 12 and 2 were measured against one model on one day. Left as
    constants they swap models in silence — no error, just a reminder that
    arrives too late or too often.

    These drive the class with injected values, so a wiring that ignored its
    arguments would show up here. The class must also still work with none,
    because an unreadable config has to mean "use the shipped value"."""

    def cycle(self, args, results):
        return run_js(
            "const r = new m.GoalRestate(%s);\n" % args +
            "r.begin('先研究 A,再比較 B,最後整理成表', true);\n"
            "const out = %s.map(e => r.afterToolResult(e));\n" % json.dumps(results) +
            "process.stdout.write(JSON.stringify(out.map(t => t === null ? null : 'R')));")

    def test_a_lower_threshold_restates_sooner(self):
        out = self.cycle("3, 1", [False] * 6)
        self.assertEqual(out, [None, None, "R", None, None, None])

    def test_the_cap_is_the_supplied_one(self):
        out = self.cycle("2, 2", [False] * 6)
        self.assertEqual(out.count("R"), 2)

    def test_no_arguments_keeps_the_shipped_calibration(self):
        out = self.cycle("", [False] * 13)
        self.assertEqual(out.index("R"), 11, "shipped threshold is 12 results")

    def bridge(self, script):
        driver = os.path.join(ROOT, "tests", ".tmp_calibrated_driver.mjs")
        # calibration.ts, not index.ts: the bridge entry point opens with
        # `require.resolve`, which exists only under Pi's shim, so importing it
        # from node dies before the first assertion.
        url = "file:///" + os.path.join(
            ROOT, "pi-extensions", "task-shape-bridge", "calibration.ts").replace("\\", "/")
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

    def calibrated(self, root, key, fallback):
        return self.bridge("process.stdout.write(JSON.stringify("
                           "m.calibrated(%s, %s, %s)));"
                           % (json.dumps(root), json.dumps(key), fallback))

    def test_the_reader_returns_what_the_config_says(self):
        """Driven, not read. The shipped value and the fallback are both real
        numbers, so a reader that ignored the file entirely would still look
        right to a test that only checked the shipped case."""
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        os.makedirs(os.path.join(tmp, "pi-config"))
        with open(os.path.join(tmp, "pi-config", "harness-config.json"),
                  "w", encoding="utf-8") as f:
            json.dump({"goalRestateThreshold": 3}, f)
        self.assertEqual(self.calibrated(tmp, "goalRestateThreshold", 99), 3)

    def test_a_missing_config_keeps_the_shipped_value(self):
        self.assertEqual(self.calibrated(os.path.join(ROOT, "no-such-dir"),
                                         "goalRestateThreshold", 99), 99)

    def test_a_value_that_is_not_a_positive_integer_is_ignored(self):
        """A config that says "12", or 0, or true, must not be obeyed. Zero is
        the dangerous one: it would restate after every single tool result."""
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        os.makedirs(os.path.join(tmp, "pi-config"))
        for bad in ["12", 0, -1, True, 2.5, None]:
            with self.subTest(bad=bad):
                with open(os.path.join(tmp, "pi-config", "harness-config.json"),
                          "w", encoding="utf-8") as f:
                    json.dump({"goalRestateThreshold": bad}, f)
                self.assertEqual(
                    self.calibrated(tmp, "goalRestateThreshold", 99), 99)

    def test_the_bridge_passes_both_numbers_to_the_class(self):
        src = io.open(os.path.join(ROOT, "pi-extensions", "task-shape-bridge",
                                   "index.ts"), encoding="utf-8").read()
        call = src.split("new GoalRestate(", 1)[1].split(");", 1)[0]
        self.assertIn("goalRestateThreshold", call)
        self.assertIn("goalRestateMax", call)


if __name__ == "__main__":
    unittest.main()
