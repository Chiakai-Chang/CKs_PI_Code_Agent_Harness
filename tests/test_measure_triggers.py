"""Tests for the trigger-rate harness.

The harness itself must be trustworthy before its numbers mean anything — this
whole session produced five confidently-stated measurements that were wrong, so
the measuring tool gets tested like anything else. Everything here exercises the
pure scoring logic; the model runs are far too slow for a test suite.
"""

import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import importlib.util

spec = importlib.util.spec_from_file_location(
    "measure_triggers", os.path.join(ROOT, "scripts", "measure-triggers.py"))
mt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mt)


class TestJudge(unittest.TestCase):
    def test_expected_tool_called_passes(self):
        sc = {"expect_tools": ["web_open", "web_search"]}
        ok, note = mt.judge(sc, ["web_open"], [], "")
        self.assertTrue(ok, note)

    def test_expected_tool_missing_fails_and_says_what_ran(self):
        sc = {"expect_tools": ["deep_research"]}
        ok, note = mt.judge(sc, ["web_search", "web_open"], [], "")
        self.assertFalse(ok)
        self.assertIn("web_search", note)

    def test_forbidden_tool_fails(self):
        """Measuring only 'did it fire' rewards ever more forceful guidance —
        which is exactly how web_search's 'for any task' wording came to swallow
        every other tool. Negative scenarios are what stop that."""
        sc = {"expect_tools": ["web_search"], "forbid_tools": ["deep_research"]}
        ok, note = mt.judge(sc, ["web_search", "deep_research"], [], "")
        self.assertFalse(ok)
        self.assertIn("forbidden", note)

    def test_skill_read_expectation(self):
        sc = {"expect_skill_read": ["systematic-debugging", "diagnosing-bugs"]}
        self.assertTrue(mt.judge(sc, ["read"], ["systematic-debugging"], "")[0])
        ok, note = mt.judge(sc, ["read"], ["brandkit"], "")
        self.assertFalse(ok)
        self.assertIn("brandkit", note)

    def test_reading_view_check_only_looks_at_page_results(self):
        sc = {"expect_tools": ["web_open"], "expect_result": {"no_element_refs": True}}
        clean = "[tab abc — now the current page; ...]\n\n- heading \"Title\""
        self.assertTrue(mt.judge(sc, ["web_open"], [], clean)[0])
        dirty = "[tab abc — now the current page; ...]\n\n- link \"X\" [e3]"
        ok, note = mt.judge(sc, ["web_open"], [], dirty)
        self.assertFalse(ok)
        self.assertIn("[eN]", note)

    def test_element_refs_elsewhere_do_not_fail_the_run(self):
        """A ref mentioned in some other tool's output is not a page result."""
        sc = {"expect_tools": ["web_open"], "expect_result": {"no_element_refs": True}}
        other = "some bash output mentioning [e1] in passing"
        self.assertTrue(mt.judge(sc, ["web_open"], [], other)[0])


class TestOutcomeChecks(unittest.TestCase):
    """Scoring the deliverable, not the activation.

    Every criterion in this file until now asked whether a mechanism fired. That
    is a proxy, and once it is the acceptance criterion every future change drifts
    toward firing more often — which is not the goal. The goal is the work being
    done well.

    Mechanical only, deliberately. The local model is the thing under test; using
    it to grade its own output is self-certification, and this repo already has a
    scar for that.
    """

    def test_an_answer_covering_every_deliverable_passes(self):
        sc = {"expect_output": {"covers": [["competitor", "品牌"], ["price", "價格"]]}}
        ok, note = mt.judge(sc, [], [], "", answer="Main competitors are X and Y; price ranges NT$2000-5000.")
        self.assertTrue(ok, note)

    def test_a_missing_deliverable_fails_and_names_it(self):
        """A survey that answers two of three asks is not two-thirds done — the
        third is simply absent, and the report does not say so."""
        sc = {"expect_output": {"covers": [["competitor"], ["price"], ["segment", "區隔"]]}}
        ok, note = mt.judge(sc, [], [], "", answer="Competitors are X and Y, priced around NT$3000.")
        self.assertFalse(ok)
        self.assertIn("segment", note)

    def test_any_synonym_in_a_group_counts(self):
        """The answer may be in either language; the deliverable is the same."""
        sc = {"expect_output": {"covers": [["segment", "區隔", "客群"]]}}
        ok, _ = mt.judge(sc, [], [], "", answer="未被滿足的客群是租屋族。")
        self.assertTrue(ok)

    def test_an_unsourced_research_answer_fails(self):
        """A research deliverable with no sources cannot be checked by the person
        who asked for it, which is most of what makes it a deliverable."""
        sc = {"expect_output": {"min_sources": 2}}
        ok, note = mt.judge(sc, [], [], "", answer="The market is growing fast and prices are falling.")
        self.assertFalse(ok)
        self.assertIn("source", note.lower())

    def test_sources_are_counted_distinctly(self):
        """Citing one page three times is one source."""
        sc = {"expect_output": {"min_sources": 2}}
        one = "See https://a.example/x and https://a.example/x and https://a.example/x"
        ok, _ = mt.judge(sc, [], [], "", answer=one)
        self.assertFalse(ok)
        ok2, _ = mt.judge(sc, [], [], "", answer=one + " and https://b.example/y")
        self.assertTrue(ok2)

    def test_outcome_and_activation_are_both_required_when_both_are_stated(self):
        """A scenario may ask for both. Passing one must not carry the other."""
        sc = {"expect_skill_read": ["planning-with-files"],
              "expect_output": {"min_sources": 1}}
        ok, note = mt.judge(sc, [], ["planning-with-files"], "", answer="no links here")
        self.assertFalse(ok, note)

    def test_a_scenario_without_output_expectations_is_unaffected(self):
        """Existing scenarios must keep judging exactly as before."""
        sc = {"expect_tools": ["web_search"]}
        ok, _ = mt.judge(sc, ["web_search"], [], "", answer="")
        self.assertTrue(ok)


class TestTheDeliverableIncludesWhatWasWritten(unittest.TestCase):
    """Scoring only the chat answer penalised the behaviour being encouraged.

    Measured: a run that did everything asked — read the routing skill, wrote
    task_plan.md, worked the phases — produced a 1,250-char summary with zero
    links and a findings.md with ten distinct sources. The first outcome
    criterion looked at the chat text alone and scored it 0 sources.

    `planning-with-files` says findings belong in a file. A criterion that only
    reads the reply marks the methodology down for following its own instruction.
    The deliverable is the answer plus the artifacts.
    """

    def test_sources_in_a_written_file_count(self):
        sc = {"expect_output": {"min_sources": 2}}
        ok, note = mt.judge(sc, [], [], "", answer="Summary of findings, details in findings.md.",
                            artifacts="see https://a.example/x and https://b.example/y")
        self.assertTrue(ok, note)

    def test_coverage_can_come_from_the_artifacts_too(self):
        sc = {"expect_output": {"covers": [["segment", "區隔"]]}}
        ok, _ = mt.judge(sc, [], [], "", answer="Done, written up in findings.md.",
                         artifacts="## 未被滿足的區隔\n租屋族")
        self.assertTrue(ok)

    def test_a_run_that_wrote_nothing_and_cited_nothing_still_fails(self):
        """The relaxation must not turn into a free pass."""
        sc = {"expect_output": {"min_sources": 1}}
        ok, note = mt.judge(sc, [], [], "", answer="The market is growing.", artifacts="")
        self.assertFalse(ok)

    def test_artifacts_default_to_empty(self):
        """Callers that pass no artifacts must judge exactly as before."""
        sc = {"expect_output": {"min_sources": 1}}
        ok, _ = mt.judge(sc, [], [], "", answer="https://a.example/x")
        self.assertTrue(ok)


class TestSomethingMustSurviveTheSession(unittest.TestCase):
    """An answer that exists only in the reply cannot be checked later.

    The harness owner chose this criterion on 2026-08-06, after session
    019fd29d ran a three-turn investigation to completion with 38 `web_search`
    calls and `write/edit` = 0. The working directory afterwards held `.git` and
    nothing else — no way to review a claim, resume the work, or find out where
    any of it came from.

    Deliberately not "did a methodology skill load". That metric drifts into
    firing more often; this one is satisfied only by leaving something behind.
    """

    SC = {"expect_output": {"min_artifacts": 1}}

    def test_a_run_that_wrote_nothing_fails(self):
        ok, note = mt.judge(self.SC, ["web_search", "web_open"], [], "", answer="Here is what I found.")
        self.assertFalse(ok)
        self.assertIn("nothing survives", note)

    def test_a_run_that_wrote_a_real_file_passes(self):
        ok, note = mt.judge(self.SC, ["web_search", "write"], [], "", answer="Written up.",
                            artifacts="x" * 250)
        self.assertTrue(ok, note)

    def test_a_token_file_does_not_count(self):
        """`write("notes.md", "ok")` satisfies the letter and defeats the point."""
        ok, note = mt.judge(self.SC, ["write"], [], "", answer="Done.", artifacts="ok")
        self.assertFalse(ok)
        self.assertIn("too little to resume", note)

    def test_an_edit_counts_as_leaving_something_behind(self):
        ok, note = mt.judge(self.SC, ["edit"], [], "", answer="Updated the plan.",
                            artifacts="y" * 250)
        self.assertTrue(ok, note)

    def test_scenarios_that_do_not_ask_for_artifacts_are_unaffected(self):
        ok, _ = mt.judge({"expect_output": {"covers": [["price", "價格"]]}}, [], [], "",
                         answer="價格約 NT$3000")
        self.assertTrue(ok)


class TestCitationsMustBeVisited(unittest.TestCase):
    """Counting URLs rewards inventing them.

    Measured: the one run that passed the outcome criterion cited 14 URLs and had
    opened 8. Seven of the fourteen were never visited — plausible-looking
    addresses assembled from link text, because `web_search` results carry no
    URLs at all (632 searches across five runs, zero URLs returned).

    `pi-rules/AGENTS.md` §9 makes fabrication the absolute floor. A criterion that
    counts citations without checking them is worse than no criterion: it scores
    a fabricated bibliography higher than an honest empty one.
    """

    def test_a_cited_page_that_was_opened_counts(self):
        sc = {"expect_output": {"min_sources": 1}}
        ok, note = mt.judge(sc, [], [], "", answer="see https://a.example/x",
                            visited=["https://a.example/x"])
        self.assertTrue(ok, note)

    def test_a_cited_page_that_was_never_opened_does_not_count(self):
        sc = {"expect_output": {"min_sources": 1}}
        ok, note = mt.judge(sc, [], [], "", answer="see https://invented.example/y",
                            visited=["https://a.example/x"])
        self.assertFalse(ok)
        self.assertIn("source", note.lower())

    def test_the_note_says_how_many_were_unvisited(self):
        """Silently dropping them would read as "it cited nothing", which is a
        different and much less alarming failure than "it made them up"."""
        sc = {"expect_output": {"min_sources": 3}}
        ok, note = mt.judge(
            sc, [], [], "",
            answer="https://a.example/x https://made.example/1 https://made.example/2",
            visited=["https://a.example/x"])
        self.assertFalse(ok)
        self.assertIn("2", note)

    def test_trailing_punctuation_does_not_break_the_match(self):
        sc = {"expect_output": {"min_sources": 1}}
        ok, _ = mt.judge(sc, [], [], "", answer="source: https://a.example/x.",
                         visited=["https://a.example/x"])
        self.assertTrue(ok)

    def test_any_invented_citation_fails_the_run(self):
        """Enough real sources does not buy the right to invent others.

        A report where half the citations were never opened is worse than one
        with none: it looks checkable and is not. AGENTS.md §9 makes fabrication
        the absolute floor, and while `web_search` returns no URLs at all, a
        cited page that was never opened was necessarily reconstructed. If search
        results ever carry URLs again, revisit this — citing a listed result
        without opening it would then be weak sourcing rather than invention.
        """
        sc = {"expect_output": {"min_sources": 2}}
        answer = ("https://a.example/x https://b.example/y "
                  "https://made.example/1 https://made.example/2")
        ok, note = mt.judge(sc, [], [], "", answer=answer,
                            visited=["https://a.example/x", "https://b.example/y"])
        self.assertFalse(ok, "two invented citations must fail even with two real ones")
        self.assertIn("never opened", note)

    def test_without_a_visited_list_it_judges_as_before(self):
        """Callers that cannot supply the list must not be silently failed."""
        sc = {"expect_output": {"min_sources": 1}}
        ok, _ = mt.judge(sc, [], [], "", answer="https://a.example/x")
        self.assertTrue(ok)


class TestHonestyAndRigourAreDifferentFailures(unittest.TestCase):
    """Citing a search result you did not read is sloppy. Citing a page that
    never existed anywhere is a different thing entirely.

    While `web_search` returned no URLs at all, the two were indistinguishable:
    any citation the model had not opened was necessarily reconstructed. With
    addresses restored, the same five runs break down as 37 citations, 24 of them
    unopened — but 20 of those 20 appeared in a search result the model had read.
    Only 4 were assembled out of nothing, things like
    `https://www.momoshop.com.tw/search/智慧門鈴`.

    Treating both as fabrication hid the improvement the URL fix actually made,
    from nearly-all-reconstructed down to 4 in 37. So: invention fails outright,
    because AGENTS.md §9 makes that the floor; reading what you cite is measured
    by how many sources were opened.
    """

    SC = {"expect_output": {"min_sources": 2}}

    def test_an_address_that_appeared_nowhere_fails(self):
        ok, note = mt.judge(self.SC, [], [], "", answer="https://invented.example/x",
                            visited=["https://a.example/1", "https://a.example/2"],
                            seen=["https://a.example/1", "https://a.example/2"])
        self.assertFalse(ok)
        self.assertIn("never appeared", note)

    def test_citing_a_search_result_without_opening_it_is_not_invention(self):
        ok, note = mt.judge(
            self.SC, [], [], "",
            answer="https://a.example/1 https://a.example/2 https://seen.example/3",
            visited=["https://a.example/1", "https://a.example/2"],
            seen=["https://a.example/1", "https://a.example/2", "https://seen.example/3"])
        self.assertTrue(ok, note)

    def test_but_it_is_reported(self):
        """Silently accepting it would let a report of unread pages look clean."""
        _ok, note = mt.judge(
            self.SC, [], [], "",
            answer="https://a.example/1 https://a.example/2 https://seen.example/3",
            visited=["https://a.example/1", "https://a.example/2"],
            seen=["https://a.example/1", "https://a.example/2", "https://seen.example/3"])
        self.assertIn("not opened", note)

    def test_the_source_count_is_pages_that_were_read(self):
        """Three citations, one page read: the report rests on one page."""
        ok, note = mt.judge(
            self.SC, [], [], "",
            answer="https://a.example/1 https://s.example/2 https://s.example/3",
            visited=["https://a.example/1"],
            seen=["https://a.example/1", "https://s.example/2", "https://s.example/3"])
        self.assertFalse(ok)
        self.assertIn("verified", note)

    def test_without_a_seen_list_everything_unopened_is_still_invention(self):
        """Callers that cannot say what the run saw keep the older, stricter
        reading — which is correct for any harness whose search returns no URLs."""
        ok, _ = mt.judge(self.SC, [], [], "", answer="https://x.example/1",
                         visited=["https://a.example/1", "https://a.example/2"])
        self.assertFalse(ok)


class TestScoringReadsTheSessionFile(unittest.TestCase):
    """Score the run from its record, not from a stream that may be lossy.

    A measurement reported 3/5 while re-scoring the same five sessions with the
    same `judge` gave 0/5. The live path parsed the `--print --mode json` stdout;
    the re-score parsed the session JSONL. They disagreed about what the runs had
    produced — the live side saw fewer citations, all of them visited, and passed
    runs that had cited five to thirteen pages they never opened.

    The session file is the durable record of what happened. Parsing it makes the
    live score and any later re-score the same number, which is the only way a
    baseline means anything.

    The fixture is a real session, trimmed — not one written to match the parser.
    """

    FIXTURE = os.path.join(ROOT, "tests", "fixtures", "session-research-run.jsonl")

    def test_it_finds_the_tool_calls(self):
        r = mt.parse_session(self.FIXTURE)
        self.assertIn("web_open", r["tools"])
        self.assertGreater(len(r["tools"]), 5)

    def test_it_collects_pages_that_were_opened(self):
        r = mt.parse_session(self.FIXTURE)
        self.assertTrue(r["visited"], "web_open urls are how citations get verified")
        self.assertTrue(all(v.startswith("http") for v in r["visited"]))

    def test_it_collects_what_was_written(self):
        """findings.md is half the deliverable; a scorer that cannot see it
        marks the methodology down for putting findings in a file."""
        r = mt.parse_session(self.FIXTURE)
        self.assertTrue(r["artifacts"])

    def test_the_answer_is_the_last_assistant_text(self):
        r = mt.parse_session(self.FIXTURE)
        self.assertIsInstance(r["answer"], str)

    def test_a_missing_file_yields_empty_not_an_exception(self):
        r = mt.parse_session(os.path.join(ROOT, "nope.jsonl"))
        self.assertEqual(r["tools"], [])
        self.assertEqual(r["visited"], [])

    def test_a_corrupt_line_does_not_stop_the_parse(self):
        import tempfile
        path = os.path.join(tempfile.mkdtemp(), "s.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            f.write("{not json\n")
            f.write(open(self.FIXTURE, encoding="utf-8").read())
        self.assertTrue(mt.parse_session(path)["tools"],
                        "one bad line must not cost the whole run's record")


class TestRepeatsAreIndependent(unittest.TestCase):
    """Each repeat must start in a directory the previous one never touched.

    The script's own design note says the cwd is neutral "so the model does not
    see this repo's active plan". It created that directory once and reused it
    for every repeat, so run 1 wrote task_plan.md and runs 2-5 began with a plan
    already sitting there. Measured consequence: task-shape-bridge gates on
    `hasAnyPlan(cwd)`, so it did nothing at all for four of five runs, and run 4
    wrote `findings_01` rather than overwrite run 1's file. A 1/5 read as a score
    for the bridge was mostly a score for something else.
    """

    def test_the_work_dir_is_created_inside_the_repeat_loop(self):
        import ast
        import inspect
        import textwrap

        def makes_a_cwd(node):
            """A tempfile.mkdtemp whose prefix names the per-run directory."""
            for sub in ast.walk(node):
                if not isinstance(sub, ast.Call):
                    continue
                if getattr(sub.func, "attr", None) != "mkdtemp":
                    continue
                for kw in sub.keywords:
                    if isinstance(kw.value, ast.Constant) and "cwd" in str(kw.value.value):
                        return True
            return False

        tree = ast.parse(textwrap.dedent(inspect.getsource(mt.main)))
        loops = [n for n in ast.walk(tree) if isinstance(n, ast.For)]
        self.assertTrue(loops, "main has no loop to check")
        self.assertTrue(
            any(makes_a_cwd(loop) for loop in loops),
            "the per-run working directory must be created inside the repeat loop; "
            "sharing it lets one run's task_plan.md change what the next run sees",
        )


class TestRunOnceArity(unittest.TestCase):
    """Every exit from run_once must hand back the same shape.

    Adding the answer to the returned tuple updated the successful path and
    missed the timeout path, so a scenario that timed out crashed the whole run
    — after the first scenario had already spent its minutes. The unit tests
    could not see it: they call `judge` directly and never go through run_once.
    """

    def test_the_timeout_path_returns_the_same_arity_as_the_normal_one(self):
        """Parsed, not pattern-matched.

        A first version counted commas per line and broke the moment a return was
        wrapped across two lines — a guard that fails on formatting is a guard
        someone eventually loosens instead of reading.
        """
        import ast
        import inspect
        import textwrap
        tree = ast.parse(textwrap.dedent(inspect.getsource(mt.run_once)))
        widths = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Tuple):
                widths.add(len(node.value.elts))
        self.assertTrue(widths, "run_once returns no tuples to compare")
        self.assertEqual(
            len(widths), 1,
            "run_once returns different tuple widths on different paths: %s" % sorted(widths),
        )


class TestScenarioHygiene(unittest.TestCase):
    """A scenario that names the tool measures nothing — the model is just
    following an instruction. Three trigger tests earlier today did exactly
    that, which is why none of them proved autonomous selection."""

    def test_no_scenario_names_the_mechanism_it_expects(self):
        for sc in mt.SCENARIOS:
            prompt = sc["prompt"].lower()
            named = []
            for t in sc.get("expect_tools", []) + sc.get("forbid_tools", []):
                if t.lower() in prompt:
                    named.append(t)
            for s in sc.get("expect_skill_read", []):
                if s.lower() in prompt:
                    named.append(s)
            self.assertEqual(named, [], "scenario %s names %s in its prompt" % (sc["id"], named))

    def test_every_scenario_states_why(self):
        for sc in mt.SCENARIOS:
            self.assertTrue(sc.get("why"), "scenario %s has no rationale" % sc["id"])

    def test_has_both_positive_and_negative_scenarios(self):
        neg = [s for s in mt.SCENARIOS if s.get("forbid_tools")]
        self.assertGreaterEqual(len(neg), 2, "need negative scenarios to catch over-triggering")

    def test_scenario_ids_are_unique(self):
        ids = [s["id"] for s in mt.SCENARIOS]
        self.assertEqual(len(ids), len(set(ids)))


class TestIsolation(unittest.TestCase):
    def test_runs_use_an_isolated_session_dir(self):
        """Without this the harness pollutes the very history it measures — one
        skill showed 4 loads in the real history and all 4 were test runs."""
        with open(os.path.join(ROOT, "scripts", "measure-triggers.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertIn("--session-dir", src)
        self.assertIn("mkdtemp", src)

    def test_runs_in_a_neutral_cwd(self):
        with open(os.path.join(ROOT, "scripts", "measure-triggers.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertIn("pi-trigger-cwd-", src)

    def test_refuses_to_report_zeros_when_pi_is_absent(self):
        """Reporting 0% for a run that never happened is the failure this whole
        session kept hitting in other forms."""
        p = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "measure-triggers.py"),
                            "--only", "nope-does-not-exist"],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=60)
        self.assertNotEqual(p.returncode, 0)


if __name__ == "__main__":
    unittest.main()
