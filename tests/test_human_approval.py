"""Path A was in the protocol the whole time, and this harness had it switched off.

`references/for_agents.md` Section 7, verbatim:

    Path A — Human-in-the-Loop (default for supervised/interactive deployments):
    Checkers and Humans communicate approval or rejection via natural language in
    the chat session. The AI Agent translates these statements to state changes:
    APPROVE (Human responds with approval phrases like "pass", "looks good",
    "approved", "OK"): transitions status.txt to DONE.

`references/for_humans.md`, 步驟三:

    當 AI 自我檢驗 100% 通過後,才會在對話中向人類回報成果。人類只需以大白話與
    AI 對話,不需要手動修改任何 status.txt 檔案或逐項勾選。

And Section 1 says only: "A Worker MUST NOT self-approve its own output as final."

The Checker in Path A is the human. A person saying "pass" in the chat satisfies
dual-track completely — nothing in Section 1 asks for a new session. Only Path B,
for unattended runs, requires a fresh context, and this harness hard-coded Path B
as if it were the only road: the advancer told the user to open a new session, and
the queue guard refused REVIEW -> DONE from the session that claimed the task,
which makes Path A impossible to execute.

The evidence for approval may only be a real user prompt. `before_agent_start`
carries `prompt: string` — "The raw user prompt text (after expansion)" — which
the bridge reads for itself. The model's word is worth what `blocked-claim`
measured it to be worth: a run reported "已執行完畢" for a call that had been
refused, and only a guard reading the actual record caught it.
"""

import importlib.util
import json
import os
import re
import shutil
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys as _sys
_sys.path.insert(0, os.path.join(ROOT, "tests"))
from _scratch import scratch  # per-process temp names; see tests/_scratch.py

MOD = os.path.join(ROOT, "pi-extensions", "case-bridge", "approval.ts")


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
    driver = scratch(".tmp_approval_driver.mjs")
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


def approves(text):
    return run_js("""
    process.stdout.write(JSON.stringify({ ok: m.isHumanApproval(%s) }));
    """ % json.dumps(text))["ok"]


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestWhatIsNotApproval(unittest.TestCase):
    """First, because closing a task is a signal that cannot be taken back.

    A false negative costs one more sentence from the user. A false positive
    marks unfinished work as accepted and moves the queue on, and nothing
    downstream re-opens it."""

    def test_asking_for_changes_is_not_approval(self):
        for text in ("這裡字型大小幫我調整一下", "不行,再改", "先不要,我想想",
                     "還有一個地方沒處理", "改一下再給我看",
                     "not yet", "needs work", "please fix the second one"):
            with self.subTest(text=text):
                self.assertFalse(approves(text))

    def test_a_question_about_approval_is_not_approval(self):
        """"可以通過了嗎?" is the user asking, not the user deciding."""
        for text in ("可以通過了嗎?", "這樣算通過嗎?", "是不是 OK 了?",
                     "can I approve this?", "is it ok?"):
            with self.subTest(text=text):
                self.assertFalse(approves(text))

    def test_a_negated_approval_is_not_approval(self):
        for text in ("還不能通過", "不通過", "沒有通過", "not approved", "don't approve"):
            with self.subTest(text=text):
                self.assertFalse(approves(text))

    def test_our_own_injected_text_is_never_approval(self):
        """The advancer triggers turns with its own text. If that text ever
        reaches `before_agent_start` as a prompt, a guard reading approvals
        would accept the harness's own words as the user's — worse than having
        no guard, because it would look like consent.

        The prefix filter makes the design correct whether or not injections
        arrive there, which is why it does not depend on measuring that."""
        for text in ("[C.A.S.E.] Task_001 已在 REVIEW,通過了嗎",
                     "[SYSTEM] 上一則 status.txt 的變更被擋下,OK",
                     "[C.A.S.E.] 下一步:通過"):
            with self.subTest(text=text):
                self.assertFalse(approves(text))

    def test_a_long_message_that_merely_contains_ok_is_not_approval(self):
        """Approval is a short, deliberate act. A paragraph that happens to use
        the word is a paragraph, and treating it as consent is how a guard
        starts inventing permission."""
        self.assertFalse(approves(
            "我看了一下,OK 的部分是前三項,但是第四項的處理方式我覺得有問題,"
            "你要不要再想想有沒有別的做法?另外第五項也還沒有測試,"
            "而且我覺得那個命名不太好懂,可以換一個嗎"))

    def test_empty_and_junk(self):
        for text in ("", "   ", "?", "嗯"):
            with self.subTest(text=text):
                self.assertFalse(approves(text))


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestWhatIsApproval(unittest.TestCase):
    def test_the_phrases_the_protocol_lists(self):
        """Section 7 names these four outright."""
        for text in ("pass", "looks good", "approved", "OK"):
            with self.subTest(text=text):
                self.assertTrue(approves(text))

    def test_the_phrases_for_humans_lists(self):
        """步驟三 names these two outright."""
        for text in ("沒問題,通過", "OK,收工"):
            with self.subTest(text=text):
                self.assertTrue(approves(text))

    def test_ordinary_ways_a_person_says_yes(self):
        for text in ("通過", "可以通過", "沒問題", "好,結案", "同意,結案",
                     "LGTM", "ship it", "approve"):
            with self.subTest(text=text):
                self.assertTrue(approves(text))

    def test_case_and_padding_do_not_matter(self):
        for text in ("  Pass  ", "ok!", "APPROVED"):
            with self.subTest(text=text):
                self.assertTrue(approves(text))


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheEvidenceIsConsumed(unittest.TestCase):
    """One "OK" closes one task. Without consumption a single approval would
    keep closing every task after it — the same cross-boundary leak that made
    `blocked-claim` silent for a day."""

    def test_a_recorded_approval_is_spent_once(self):
        out = run_js("""
        const r = new m.ApprovalRecord();
        r.note("通過");
        process.stdout.write(JSON.stringify({
          first: r.take(), second: r.take(), third: r.take() }));
        """)
        self.assertTrue(out["first"])
        self.assertFalse(out["second"])
        self.assertFalse(out["third"])

    def test_a_rejection_records_nothing(self):
        out = run_js("""
        const r = new m.ApprovalRecord();
        r.note("這裡改一下");
        process.stdout.write(JSON.stringify({ taken: r.take() }));
        """)
        self.assertFalse(out["taken"])

    def test_reset_clears_it(self):
        out = run_js("""
        const r = new m.ApprovalRecord();
        r.note("通過");
        r.reset();
        process.stdout.write(JSON.stringify({ taken: r.take() }));
        """)
        self.assertFalse(out["taken"])

@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheLengthBoundaryIsExact(unittest.TestCase):
    """From the mutation sweep. The 40-character ceiling is the whole defence
    against a paragraph that happens to contain "OK" reading as consent, and
    nothing pinned it — shifting it to 41 changed no test."""

    def test_at_the_ceiling_it_still_counts_and_past_it_it_does_not(self):
        at = "通過" + "。" * 38            # exactly 40 characters
        over = "通過" + "。" * 39           # 41
        self.assertEqual(len(at), 40)
        self.assertTrue(approves(at))
        self.assertFalse(approves(over))



if __name__ == "__main__":
    unittest.main()
