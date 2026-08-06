"""The reply that came back as a compaction summary instead of the answer.

Session 019fd702, 2026-08-06, the harness owner's real use. The turn did the
work — fifteen searches, ten pages opened, fourteen writes, and a 9,092-char
`ach-analysis-report.md` holding five competing hypotheses and thirteen pieces
of evidence with URLs. Then the reply the user saw, 6,466 chars, opened with:

    <analysis>
    Let me chronologically analyze the conversation:

    1. **First User Message (Message 1)**: User provided a massive block of ...

That is Pi's own compaction output format. `dist/core/messages.js` wraps a
compacted history in `<summary>`, behind the prefix "The conversation history
before this point was compacted into the following summary:". No compaction
happened in that session — zero compact events in the record. The model
produced the artifact spontaneously and it replaced the deliverable.

The cost is not cosmetic. The owner read that reply and concluded that
planning-with-files had stopped being used and that the run was emitting tags
matching no tool. Neither was true: task_plan.md, findings.md and progress.md
were written and edited throughout, and the last two actions of the session were
writes. One substituted reply produced two wrong diagnoses about a session that
had gone well.

Narrow on purpose. `<summary>` is ordinary HTML inside `<details>`, and this
repo's own documents use it. Only a turn that OPENS with the envelope counts,
and a real compaction is exempt because it carries Pi's prefix.
"""

import json
import os
import re
import shutil
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(ROOT, "pi-extensions", "yes-hooks-bridge", "compaction-echo.ts")


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
    driver = os.path.join(ROOT, "tests", ".tmp_cecho_driver.mjs")
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


def check(text, written=None):
    return run_js("""
    const r = m.compactionEcho(%s, %s);
    process.stdout.write(JSON.stringify({ caught: !!r, message: r ? r.message : "" }));
    """ % (json.dumps(text), json.dumps(written or [])))


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheRealOne(unittest.TestCase):
    REAL = ("<analysis>\nLet me chronologically analyze the conversation:\n\n"
            "1. **First User Message (Message 1)**: User provided a massive block of text\n")

    def test_the_reply_from_session_019fd702(self):
        self.assertTrue(check(self.REAL)["caught"])

    def test_the_correction_points_at_the_file_that_was_written(self):
        out = check(self.REAL, ["ach-analysis-report.md", "progress.md"])
        self.assertIn("ach-analysis-report.md", out["message"])

    def test_a_bare_summary_envelope_counts_too(self):
        self.assertTrue(check("<summary>\nThe user asked about X and I did Y.\n")["caught"])

    def test_leading_whitespace_does_not_hide_it(self):
        self.assertTrue(check("\n\n  <analysis>\nLet me analyze\n")["caught"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestOrdinaryRepliesAreLeftAlone(unittest.TestCase):
    """`<summary>` is ordinary HTML and this repo's own docs use it."""

    def test_a_details_block_mid_reply(self):
        text = ("以下是結果。\n\n<details>\n<summary>詳細討論</summary>\n\n內容\n</details>\n")
        self.assertFalse(check(text)["caught"])

    def test_a_details_block_at_the_very_start(self):
        text = "<details>\n<summary>展開</summary>\n\n內容\n</details>\n"
        self.assertFalse(check(text)["caught"])

    def test_the_word_analysis_in_prose(self):
        self.assertFalse(check("Here is the ACH analysis you asked for. H1 is ...")["caught"])

    def test_a_real_compaction_never_opens_with_the_bare_tag(self):
        """Pi writes its prefix first, so the envelope check alone exempts it.

        An earlier version also matched that prefix explicitly. Breaking that
        exemption changed no test — it could never run, because the
        opens-with-envelope check had already returned. It was deleted rather
        than kept as decoration, and this test records why none is needed.
        """
        text = ("The conversation history before this point was compacted into the "
                "following summary:\n\n<summary>\nEarlier the user asked ...\n")
        self.assertFalse(check(text)["caught"],
                         "a genuine compaction summary must not be corrected")

    def test_an_ordinary_answer(self):
        self.assertFalse(check("已完成,報告寫在 ach-analysis-report.md。")["caught"])

    def test_empty_text(self):
        self.assertFalse(check("")["caught"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheCorrection(unittest.TestCase):
    def test_it_says_the_reply_was_not_the_deliverable(self):
        out = check("<analysis>\nLet me chronologically analyze the conversation:\n")
        self.assertRegex(out["message"], r"(?i)壓縮|compact|摘要")

    def test_it_works_without_a_file_list(self):
        out = check("<analysis>\nLet me chronologically analyze the conversation:\n", [])
        self.assertTrue(out["message"])


if __name__ == "__main__":
    unittest.main()
