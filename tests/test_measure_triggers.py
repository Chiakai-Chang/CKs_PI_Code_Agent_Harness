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
