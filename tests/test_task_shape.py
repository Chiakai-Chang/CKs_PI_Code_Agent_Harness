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
import tempfile
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


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestNonInteractiveRunsMustNotStallOnQuestions(unittest.TestCase):
    """One run in five asked four scoping questions and stopped.

    Its questions were good ones — geography, time window, product definition,
    output format — and interactively that is the right move before a market
    survey. Under `pi --print` there is nobody to answer, so the run ended with
    no work done and no artifacts.

    The model cannot tell which mode it is in. The harness can: ExtensionContext
    carries `hasUI`, documented as "whether dialog-capable UI is available (true
    in TUI and RPC modes)". So the harness says it rather than asking the model
    to guess.
    """

    SURVEY = ("I want a market survey of the smart doorbell category in Taiwan — "
              "who the competitors are, how they price, and which segments are underserved.")

    def _note(self, interactive):
        return run_js(
            "process.stdout.write(JSON.stringify({ t: m.buildSystemPromptNote("
            "m.classifyRequest(%s), { interactive: %s }) }));"
            % (json.dumps(self.SURVEY), "true" if interactive else "false"))["t"]

    def test_without_a_user_it_says_to_assume_and_proceed(self):
        note = self._note(False)
        self.assertRegex(note, r"(?i)assumption|assume|proceed")

    def test_with_a_user_it_still_offers_to_ask(self):
        """Asking first is the better behaviour when someone is there to answer;
        the fix must not delete it."""
        note = self._note(True)
        self.assertIn("brainstorming", note)

    def test_the_default_keeps_the_interactive_wording(self):
        """Callers that pass no options must behave as before."""
        note = run_js("process.stdout.write(JSON.stringify({ t: m.buildSystemPromptNote("
                      "m.classifyRequest(%s)) }));" % json.dumps(self.SURVEY))["t"]
        self.assertIn("brainstorming", note)

    def test_a_single_step_request_gets_nothing_either_way(self):
        for interactive in (True, False):
            with self.subTest(interactive=interactive):
                out = run_js(
                    "process.stdout.write(JSON.stringify({ t: m.buildSystemPromptNote("
                    "m.classifyRequest(%s), { interactive: %s }) }));"
                    % (json.dumps("What is the latest version of Zig?"),
                       "true" if interactive else "false"))["t"]
                self.assertEqual(out, "")

@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestChinesePunctuationIsSeparatorsToo(unittest.TestCase):
    """The classifier was nearly blind to the language its owner writes in.

    Session 019fe60f ran sixteen turns of real research and this bridge stayed
    silent, because the separator set held `,` `、` `;` `；` and not the
    FULLWIDTH COMMA. That prompt contains five of them, no ASCII commas and no
    ideographic commas, so it counted two deliverables and classified as
    single-step.

    Adding the character is half the fix. Chinese commas mostly separate clauses
    inside one sentence rather than deliverables, so the `deliverables >= 4`
    shortcut — sufficient on its own before — began promoting a question about
    whether to walk to the car wash. Measured over 106 real first-prompts from
    this machine: with the shortcut 35% multi-step including the car wash,
    without it 17% and still catching 019fe60f."""

    def test_the_request_this_work_started_from(self):
        prompt = ("請分析了解最近比較重要的社會事件，找出是否有關連，循線找出脈絡，"
                  "若有關聯則進一步找出可能是誰在推動，目的是什麼，真相是什麼，"
                  "請MECE的分析哪些利害關係人會受影響，該怎麼應對比較好，"
                  "並復盤這些建議是否合適、有無遺漏或可更完善之處")
        shape = classify(prompt)
        self.assertTrue(shape["multiStep"])
        self.assertGreaterEqual(shape["deliverables"], 5)

    def test_a_chatty_question_with_commas_is_not_multi_step(self):
        """Verbatim from the same history. Four clauses, three fullwidth commas,
        one question — and no research verb, which is what now keeps it out."""
        shape = classify("我想洗車，洗車店離我家只有50公尺，你覺得我該走過去，還是開車去？")
        self.assertFalse(shape["multiStep"])

    def test_a_chinese_research_request_with_several_asks(self):
        shape = classify("請盤點哪些啟動腳本失效，並附上證據，說明每個檔案是否真的存在，"
                         "最後整理成一份清單")
        self.assertTrue(shape["multiStep"])



if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheClassifierBoundaries(unittest.TestCase):
    """Sites the mutation sweep reached only after coverage was measured.

    `shape.ts` was in the sweep, but these three had no test: the 25-character
    floor, the zeroed deliverable count below it, and the research-verb branch
    that reports at least two deliverables. Each decides whether a run gets a
    routine at all."""

    def test_a_prompt_just_under_the_floor_is_single_step(self):
        """24 characters. The floor exists so a greeting is never routed."""
        out = classify("x" * 24)
        self.assertFalse(out["multiStep"])
        self.assertEqual(out["deliverables"], 0,
                         "below the floor nothing has been counted yet")

    def test_the_floor_itself_is_examined(self):
        """25 characters: long enough to look at. It still needs real signals to
        be multi-step, so this asserts it was CLASSIFIED, not that it fired."""
        out = classify("研究並比較三個競品的定價與功能差異,並整理成表格")
        self.assertTrue(out["multiStep"])

    def test_a_research_verb_alone_is_not_enough(self):
        """The `&&` matters: a research verb with nothing plural is one lookup."""
        self.assertFalse(classify(
            "研究一下這個函式的效能瓶頸在哪裡,大概講一下就好")["multiStep"])

    def test_a_plural_noun_alone_is_not_enough(self):
        self.assertFalse(classify(
            "把這些檔案的結尾空白都清掉,不用做別的事情謝謝")["multiStep"])

    def test_research_plus_plural_reports_at_least_two_deliverables(self):
        out = classify("請研究這幾家競品的定價策略,整理給我看,謝謝你")
        self.assertTrue(out["multiStep"])
        self.assertGreaterEqual(out["deliverables"], 2,
                                "a research request naming several things is "
                                "never a one-deliverable job")
