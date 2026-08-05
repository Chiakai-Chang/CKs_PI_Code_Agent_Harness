"""Deciding whether a request is multi-step, cheaply and before any tool runs.

Measured baseline (scripts/measure-triggers.py, local model, isolated sessions,
neutral cwd, repeats=3):

    debug-methodology         2/3   67%
    multi-step-methodology    0/3    0%

The 21 methodology skills are all in the system prompt with their descriptions —
verified by dumping it. Debugging fires because the request lands in
systematic-debugging's vocabulary; a market survey lands in nobody's, because
those descriptions are written for software work and live in submodules we do
not edit.

So the routing has to happen on our side, and it has to be cheap: this runs at
the top of every turn, before the model is called, so it may not call a model
itself.

The negative cases below matter more than the positive ones. Misjudging a single
lookup as multi-step turns "never fires" into "fires on everything", which is
worse than the bug being fixed.
"""

import json
import os
import re
import shutil
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(ROOT, "pi-extensions", "task-shape-bridge", "shape.ts")


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
    driver = os.path.join(ROOT, "tests", ".tmp_shape_driver.mjs")
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


def classify(prompt):
    return run_js("process.stdout.write(JSON.stringify(m.classifyRequest(%s)));" % json.dumps(prompt))


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestSingleStepRequestsAreLeftAlone(unittest.TestCase):
    """The expensive failure mode. A router that fires on everything is noise on
    every turn, and the model learns to skip the line — which is how the previous
    delivery failed in the other direction."""

    def test_a_single_lookup(self):
        self.assertFalse(classify("What is the latest released version of the Zig programming language?")["multiStep"])

    def test_a_one_line_fix(self):
        self.assertFalse(classify("fix this typo in README.md")["multiStep"])

    def test_reading_one_file(self):
        self.assertFalse(classify("read foo.ts and tell me what it does")["multiStep"])

    def test_a_single_question_in_chinese(self):
        self.assertFalse(classify("這個函式是做什麼的?")["multiStep"])

    def test_an_empty_prompt_is_not_a_crash(self):
        out = classify("")
        self.assertFalse(out["multiStep"])

    def test_punctuation_only(self):
        self.assertFalse(classify("???")["multiStep"])

    def test_a_long_but_single_deliverable_request(self):
        """Length alone must not decide it. This is one thing, said slowly."""
        self.assertFalse(classify(
            "I would really appreciate it if you could take a careful look at the "
            "authentication middleware in src/auth.ts and explain to me how the "
            "token expiry check works, because I keep getting confused by it."
        )["multiStep"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestMultiStepRequestsAreCaught(unittest.TestCase):
    def test_the_market_survey_that_started_this(self):
        out = classify("I want a market survey of the smart doorbell category in Taiwan — "
                       "who the competitors are, how they price, and which segments are underserved.")
        self.assertTrue(out["multiStep"])
        self.assertGreaterEqual(out["deliverables"], 3)

    def test_the_same_request_in_chinese(self):
        out = classify("幫我調查這個產品的市場、技術可行性、以及 UI/UX 該怎麼做")
        self.assertTrue(out["multiStep"])

    def test_a_three_way_comparison(self):
        out = classify("Compare the licensing terms, the pricing model, and the "
                       "self-hosting story of Grafana versus Kibana. I want all three covered.")
        self.assertTrue(out["multiStep"])

    def test_an_explicit_multi_part_build(self):
        out = classify("Build the login page, wire it to the session API, and add tests for both.")
        self.assertTrue(out["multiStep"])

    def test_it_says_why(self):
        """The reason goes into the routine handed to the model; an unexplained
        interruption reads as noise."""
        out = classify("Research the competitors, their pricing, and the gaps in the market.")
        self.assertTrue(out["reason"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestBroadToolDetection(unittest.TestCase):
    """Only a broad opening move is worth interrupting. Reading one file is how a
    careful agent starts and must not be treated as skipping the plan."""

    def _broad(self, tool):
        return run_js("process.stdout.write(JSON.stringify({ v: m.isBroadTool(%s) }));"
                      % json.dumps(tool))["v"]

    def test_search_and_bash_are_broad(self):
        for tool in ("web_search", "deep_research", "bash"):
            with self.subTest(tool=tool):
                self.assertTrue(self._broad(tool))

    def test_reading_is_not(self):
        for tool in ("read", "grep", "ls", "find", "edit", "write"):
            with self.subTest(tool=tool):
                self.assertFalse(self._broad(tool))

    def test_an_unknown_tool_is_not_broad(self):
        """Fail quiet: a tool nobody classified must not trigger an interruption."""
        self.assertFalse(self._broad("some_custom_tool"))




@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestRoutineHandedToTheModel(unittest.TestCase):
    """Routine (arXiv 2507.14447) raised multi-step tool-calling accuracy on
    Qwen3-14B from 32.6% to 83.3%, and its mechanism is handing the model a
    structured script — not asking it to pick from a list. A 122-entry catalogue
    at session start is the second thing; a concrete routine at the moment it
    reaches for web_search is the first.
    """

    def _routine(self, prompt):
        return run_js(
            "process.stdout.write(JSON.stringify({ t: m.buildRoutine(m.classifyRequest(%s)) }));"
            % json.dumps(prompt))["t"]

    SURVEY = ("I want a market survey of the smart doorbell category in Taiwan — "
              "who the competitors are, how they price, and which segments are underserved.")

    def test_it_names_the_skills_instead_of_offering_a_menu(self):
        t = self._routine(self.SURVEY)
        self.assertIn("planning-with-files", t)
        self.assertIn("brainstorming", t)

    def test_it_leaves_a_way_out(self):
        """A hard stop has nobody to approve it under `pi --print`, and the model
        must be able to say "this really is one lookup" and continue."""
        t = self._routine(self.SURVEY)
        self.assertRegex(t, r"(?i)single|one-off|really is")

    def test_it_says_what_it_counted(self):
        t = self._routine(self.SURVEY)
        self.assertIn("3", t)

    def test_it_stays_small(self):
        """It rides on a tool result. The advisory budget is 1200 chars for
        everything queued, and this must not eat it alone."""
        self.assertLess(len(self._routine(self.SURVEY)), 700)

    def test_a_single_step_request_gets_no_routine(self):
        self.assertEqual(self._routine("What is the latest version of Zig?"), "")


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestRoutineIsDeliveredBeforeTheFirstAction(unittest.TestCase):
    """Measured failure of the first design, and why.

    The routine was delivered — confirmed in a live session log, in the tool
    result of the first web_search — and the model ignored it across 17 tool
    calls, all searches and page opens, no plan.

    `ToolCallEventResult` is `{block, reason}`, so a tool_call handler cannot add
    text without blocking. Delivering at tool_result therefore means delivering
    *after* the search already ran, with the model committed and results in hand.

    The literature says to place an important instruction in several places at
    once — system prompt, guidelines, tool descriptions, and tool results — and
    that models attend most to the beginning and the end. The first design used
    one place, and the weakest one. `buildSystemPromptNote` is the same routine
    at the other end.
    """

    SURVEY = ("I want a market survey of the smart doorbell category in Taiwan — "
              "who the competitors are, how they price, and which segments are underserved.")

    def _note(self, prompt):
        return run_js(
            "process.stdout.write(JSON.stringify({ t: m.buildSystemPromptNote(m.classifyRequest(%s)) }));"
            % json.dumps(prompt))["t"]

    def test_a_multi_step_request_gets_a_note_for_the_system_prompt(self):
        note = self._note(self.SURVEY)
        self.assertIn("planning-with-files", note)
        self.assertIn("3", note)

    def test_a_single_step_request_gets_nothing(self):
        """Every turn pays for whatever this returns."""
        self.assertEqual(self._note("What is the latest version of Zig?"), "")

    def test_it_is_small_enough_to_sit_in_every_turn(self):
        self.assertLess(len(self._note(self.SURVEY)), 500)

    def test_it_reads_as_harness_guidance_not_as_the_user_speaking(self):
        """It lands in the system prompt. Unlabelled, an instruction there is
        indistinguishable from something the operator asked for."""
        self.assertIn("[task-shape]", self._note(self.SURVEY))
