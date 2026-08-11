"""The plan-order classifier, driven against captured session shapes.

`scripts/report-plan-order.py` reads ~/.pi/agent/sessions, which does not exist
on a CI runner, so the script itself is not wired into CI — it would print zero
and pass forever. What CAN be wrong in a way that hides a defect is the
classifier: which tool counts as a search, which file counts as a plan, and
which of the two came first. That is what these drive, on JSONL written here.

The measurement this guards reported `search-first 0` over 31 real sessions,
which is the finding that stopped a gate from being built. A classifier that
silently could not return `search-first` would have produced the same number.
"""

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = importlib.util.spec_from_file_location(
    "report_plan_order", os.path.join(ROOT, "scripts", "report-plan-order.py"))
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def session(calls):
    """A session file containing one assistant message per call."""
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        for name, args in calls:
            f.write(json.dumps({
                "type": "message",
                "message": {"role": "assistant",
                            "content": [{"type": "toolCall", "id": "x",
                                         "name": name, "arguments": args}]},
            }) + "\n")
    return Path(path)


class TestTheClassifier(unittest.TestCase):
    def verdict(self, calls):
        p = session(calls)
        self.addCleanup(os.remove, p)
        return mod.verdict(p)

    def test_a_session_that_never_searched_is_not_eligible(self):
        self.assertIsNone(self.verdict([("write", {"path": "task_plan.md"})]))

    def test_plan_before_search(self):
        got = self.verdict([("write", {"path": "task_plan.md"}),
                            ("web_search", {"query": "x"})])
        self.assertEqual(got[0], "plan-first")

    def test_search_before_plan(self):
        """The verdict the real corpus returned zero of. A classifier that
        cannot produce it would report the same zero."""
        got = self.verdict([("web_search", {"query": "x"}),
                            ("web_search", {"query": "y"}),
                            ("write", {"path": "D:/p/task_plan.md"})])
        self.assertEqual(got[0], "search-first")
        self.assertEqual((got[1], got[2]), (1, 3))

    def test_search_and_no_plan_at_all(self):
        got = self.verdict([("web_search", {"query": "x"}),
                            ("write", {"path": "findings.md"})])
        self.assertEqual(got[0], "no-plan")
        self.assertIsNone(got[2])

    def test_findings_md_is_not_a_plan(self):
        """A research artifact is not a plan. Counting it would turn the runs
        this measurement is about into successes."""
        got = self.verdict([("write", {"path": "findings.md"}),
                            ("web_search", {"query": "x"})])
        self.assertEqual(got[0], "no-plan")

    def test_a_plan_in_a_planning_subdirectory_counts(self):
        got = self.verdict([("write", {"path": ".planning/abc/task_plan.md"}),
                            ("web_search", {"query": "x"})])
        self.assertEqual(got[0], "plan-first")

    def test_edit_counts_as_writing_a_plan(self):
        got = self.verdict([("edit", {"path": "planning.md"}),
                            ("web_search", {"query": "x"})])
        self.assertEqual(got[0], "plan-first")

    def test_deep_research_counts_as_a_search(self):
        got = self.verdict([("deep_research", {"query": "x"})])
        self.assertEqual(got[0], "no-plan")

    def test_the_call_count_is_every_call_not_just_the_two(self):
        got = self.verdict([("bash", {"command": "ls"}),
                            ("web_search", {"query": "x"}),
                            ("read", {"path": "a.md"})])
        self.assertEqual(got[3], 3)


if __name__ == "__main__":
    unittest.main()
