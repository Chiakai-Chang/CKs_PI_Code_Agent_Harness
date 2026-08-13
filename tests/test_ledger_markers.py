"""The ledger's own status markers drift, and it has cost real work three times.

* T4's Local DoD was satisfied on 2026-08-11 by runs 7 and 8 (both blocked an
  empty REVIEW, session log as evidence). Nobody came back to tick it, so it sat
  under "not started" for a day and was nearly re-done.
* T-A11's step 1 shipped on 2026-08-13 and the heading stayed red; the owner
  spotted it, not us.
* T-A5 was finished and approved on 2026-08-12 and still read 「認領中」 the
  next day.

Three occurrences of the same shape, and unlike most of what this repo chases,
this one is mechanically decidable: the checkboxes and the marker are both in the
file. No model, no live run, no judgement call — which is exactly why it is worth
a test while the one-observation items are not.

The rules are deliberately narrow. They say nothing about whether a task *should*
be done; they only require the two places that state its status to agree.
"""

import io
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "PROGRESS.md")

DONE = "✅"
CLAIMED = "🔵"
# Markers that mean "this was never carried out, and its boxes are meant to
# stay empty" — a revoked task keeps its original text on purpose, because an
# undocumented rejection gets rebuilt by the next person.
NOT_ATTEMPTED = ("🚫", "🔗")

HEADING = re.compile(r"^### (\S)\s*(T-?A?\d+\w*)")
BOX = re.compile(r"^\s*[-*] \[([ xX])\]")


def sections(text):
    """(marker, task id, [checked booleans]) for every task heading."""
    out = []
    cur = None
    for line in text.split("\n"):
        m = HEADING.match(line)
        if m:
            cur = [m.group(1), m.group(2), []]
            out.append(cur)
            continue
        if cur is None:
            continue
        b = BOX.match(line)
        if b:
            cur[2].append(b.group(1).lower() == "x")
    return out


class TestTheMarkerAgreesWithTheBoxes(unittest.TestCase):
    def setUp(self):
        self.text = io.open(LEDGER, encoding="utf-8").read()
        self.sections = sections(self.text)

    def test_the_parser_finds_the_ledger(self):
        """An exclusion-based check that parses nothing passes forever. Both
        numbers below are floors, not counts — they may grow."""
        self.assertGreater(len(self.sections), 10,
                           "parsed only: %s" % [s[1] for s in self.sections])
        with_boxes = [s for s in self.sections if s[2]]
        self.assertGreater(len(with_boxes), 2)

    def test_all_boxes_ticked_means_the_marker_says_done(self):
        """The drift that cost T4 a day: the evidence was written into the
        section and the heading still said otherwise."""
        for marker, task, boxes in self.sections:
            if not boxes or marker in NOT_ATTEMPTED:
                continue
            if all(boxes):
                with self.subTest(task=task):
                    self.assertEqual(
                        marker, DONE,
                        "%s has every Local DoD box ticked but is marked %s"
                        % (task, marker))

    def test_done_means_no_box_is_left_unticked(self):
        """The same drift in the other direction, and it was live when this test
        was written: T-A1 and T-A6 were marked DONE with four empty boxes each,
        their evidence sitting three paragraphs below. A half-ticked DONE is
        unreadable — you cannot tell whether the rest was skipped or forgotten."""
        for marker, task, boxes in self.sections:
            if marker != DONE or not boxes:
                continue
            with self.subTest(task=task):
                self.assertTrue(
                    all(boxes),
                    "%s is marked DONE with %d unticked box(es)"
                    % (task, sum(1 for b in boxes if not b)))

    def test_at_most_one_task_is_claimed(self):
        """The ledger's own rule is 一次認領一個, and it is the rule the whole
        queue rests on. Two claimed tasks means one of them is stale."""
        claimed = [t for m, t, _ in self.sections if m == CLAIMED]
        self.assertLessEqual(len(claimed), 1, "claimed at once: %s" % claimed)

    def test_the_header_line_agrees_about_what_is_claimed(self):
        """The top of the file states the current claim in prose. It has been
        wrong twice — both times naming a task that had already been approved."""
        claimed = [t for m, t, _ in self.sections if m == CLAIMED]
        head = self.text.split("## 宏觀目標", 1)[0]
        m = re.search(r"\*\*當前認領中:\*\*\s*(\S+)", head)
        self.assertIsNotNone(m, "the header no longer states a current claim")
        stated = m.group(1)
        if claimed:
            self.assertIn(claimed[0], stated,
                          "header says %r, markers say %s" % (stated, claimed))
        else:
            self.assertTrue(
                stated.startswith("無"),
                "no task is marked claimed, but the header says %r" % stated)


class TestTheRulesCanFail(unittest.TestCase):
    """Each rule above only ever asserts about sections it finds. Feed the same
    parser a ledger that breaks each rule and require it to notice — otherwise a
    typo in the heading regex would make all of them pass on an empty list.

    These are fixtures, but the rules are not hypothetical: run against
    PROGRESS.md as it stood on 2026-08-13,
    `test_done_means_no_box_is_left_unticked` failed twice — T-A1 and T-A6, four
    empty boxes each, both finished and approved days earlier. (An earlier draft
    recorded that as a test method whose body was `assertTrue(True)`. A check
    that cannot fail is the thing this repo counts, so it is a docstring.)
    """

    BAD_TICKED = "### 🔵 T-99 — x\n* a\n  - [x] one\n  - [x] two\n"
    BAD_DONE = "### ✅ T-98 — x\n* a\n  - [x] one\n  - [ ] two\n"
    BAD_TWO_CLAIMS = "### 🔵 T-97 — x\n\n### 🔵 T-96 — y\n"

    def test_a_fully_ticked_non_done_section_is_detected(self):
        (marker, task, boxes), = sections(self.BAD_TICKED)
        self.assertEqual(marker, "🔵")
        self.assertTrue(all(boxes) and len(boxes) == 2)

    def test_a_done_section_with_an_empty_box_is_detected(self):
        (_, _, boxes), = sections(self.BAD_DONE)
        self.assertEqual(boxes, [True, False])

    def test_two_claims_are_detected(self):
        got = [m for m, _, _ in sections(self.BAD_TWO_CLAIMS)]
        self.assertEqual(got, ["🔵", "🔵"])


if __name__ == "__main__":
    unittest.main()
