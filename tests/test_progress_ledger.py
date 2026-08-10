"""PROGRESS.md is the one file that has to be read, so it must stay true.

This repo's most repeated failure is a record nobody reads. `global_dod.md` sat
for weeks as an unfilled template whose one real criterion was the exact fallacy
its own source warned about, and nothing noticed because nothing checked. A
master ledger maintained by memory becomes that within a month.

So the ledger is guarded the same way the prior-art register is: every analysis
document under docs/case/ and docs/measurements/ must be linked from it. A
document that exists and is not linked is a finding nobody will find again.
"""

import os
import re
import unittest
from pathlib import Path

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEDGER = ROOT / "PROGRESS.md"

# Directories whose contents are findings rather than working notes.
TRACKED = ("docs/case", "docs/measurements")


def ledger_text():
    return LEDGER.read_text(encoding="utf-8")


class TestTheLedgerExists(unittest.TestCase):
    def test_it_is_at_the_repo_root(self):
        self.assertTrue(LEDGER.is_file(),
                        "PROGRESS.md is the entry point; it must be findable")

    def test_claude_md_points_at_it(self):
        """An index nobody is told about is an index nobody opens."""
        claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("PROGRESS.md", claude)


class TestEveryFindingIsLinked(unittest.TestCase):
    """The check that actually fails when someone forgets."""

    def test_every_analysis_document_is_linked(self):
        text = ledger_text()
        missing = []
        for rel in TRACKED:
            d = ROOT / rel
            if not d.is_dir():
                continue
            for f in sorted(d.glob("*.md")):
                link = "%s/%s" % (rel, f.name)
                if link not in text:
                    missing.append(link)
        self.assertEqual(missing, [],
                         "these findings are not linked from PROGRESS.md: %s"
                         % missing)

    def test_no_link_points_at_a_missing_file(self):
        """The other direction. A ledger citing a document that was renamed or
        deleted reads as complete and leads nowhere."""
        dead = []
        for m in re.finditer(r"\]\((docs/[^)#]+\.md)\)", ledger_text()):
            if not (ROOT / m.group(1)).is_file():
                dead.append(m.group(1))
        for m in re.finditer(r"\]\((01_Roadmap/[^)#]+\.md)\)", ledger_text()):
            if not (ROOT / m.group(1)).is_file():
                dead.append(m.group(1))
        self.assertEqual(dead, [], "PROGRESS.md links to missing files: %s" % dead)


class TestTheLedgerCarriesTheThingsThatMatter(unittest.TestCase):
    """Structure, not prose. Each of these sections earned its place by being
    something that went wrong when it was absent."""

    def test_it_says_what_is_being_worked_on_now(self):
        self.assertIn("現在在做什麼", ledger_text())

    def test_it_carries_a_real_status_not_just_a_task_list(self):
        """`roadmap.md`'s checkboxes were stale — eight items marked `- [ ]`
        whose own text said DONE or REVIEW. A status section that repeats the
        checkboxes would inherit the same lie, so this one is written from
        evidence and says so."""
        text = ledger_text()
        self.assertIn("進度真實狀態", text)
        self.assertIn("做了但沒有結論", text,
                      "a status list with no 'done but unproven' row will "
                      "quietly promote unverified work to finished")

    def test_it_records_learnings_and_not_only_tasks(self):
        self.assertIn("工作紀錄", ledger_text())
        self.assertIn("收穫", ledger_text())


if __name__ == "__main__":
    unittest.main()
