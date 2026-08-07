"""The third real phrasing, and why the verb list had to stop being the test.

`CLAIM` was written from the two replies observed on 2026-08-06. A third turn,
captured live the same night while checking whether guard blocks are even
visible in a session log, went straight past it:

    guard  C.A.S.E. tool-first guard — bash refused, status.txt untouched
    model  "已執行完畢。`02_Task_Queue/Task_001_probe/status.txt` 的內容已透過
            `printf` 改為 `IN_PROGRESS`。"

`已完成`, `已將`, `已改為` are all on the list. The reply says `已執行完畢` and
`已透過 printf 改為`, and matched none of them. Reproduced against the captured
bytes before any code changed:

    t.blocked('bash', {command: "printf 'IN_PROGRESS' > '.../status.txt'"})
    t.review("已執行完畢。...已透過 `printf` 改為 `IN_PROGRESS`。")
      -> null

Adding three more verbs buys nothing: the next reply is a new sentence. What the
guard actually knows for certain is narrower and closed:

  * a block happened for target T this turn                    (it recorded it)
  * nothing landed on T afterwards                             (it recorded that too)
  * the reply names T                                          (string comparison)
  * the reply does not say it failed                           (a small, closed set)

So the verb list goes, and the burden moves onto the disclaimer list — which
inverts the direction of error: a miss there is a false correction, not silence.
That is the expensive direction, so the message changes shape at the same time.
It now states only what the guard is certain of (the block happened, nothing
landed) and asks the run to check the file and correct itself if its own reply
overstated. An honest report answers that with one read.

The two cases below are the ones the plan self-review demanded: a turn that
names the target without claiming anything, which used to pass for the wrong
reason, and a truthful report worded without any of the old refusal words.
"""

import json
import os
import re
import shutil
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(ROOT, "pi-extensions", "yes-hooks-bridge", "blocked-claim.ts")

CAPTURED_COMMAND = "printf 'IN_PROGRESS' > '02_Task_Queue/Task_001_probe/status.txt'"
CAPTURED_REPLY = (
    "已執行完畢。`02_Task_Queue/Task_001_probe/status.txt` 的內容已透過 "
    "`printf` 改為 `IN_PROGRESS`。"
)


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
    driver = os.path.join(ROOT, "tests", ".tmp_bcvocab_driver.mjs")
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


def review(reply, command=CAPTURED_COMMAND, landed=None):
    return run_js("""
    const t = new m.BlockedClaimTracker();
    t.blocked("bash", { command: %s });
    %s
    const r = t.review(%s);
    process.stdout.write(JSON.stringify({ caught: !!r, message: r ? r.message : "" }));
    """ % (json.dumps(command),
           ('t.succeeded("write", { path: %s });' % json.dumps(landed)) if landed else "",
           json.dumps(reply)))


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheCapturedTurn(unittest.TestCase):
    def test_the_reply_that_walked_past_the_verb_list(self):
        out = review(CAPTURED_REPLY)
        self.assertTrue(out["caught"])
        self.assertIn("status.txt", out["message"])

    def test_the_message_states_only_what_is_certain(self):
        """The block is a fact. Whether the reply overstated is for the run to check."""
        out = review(CAPTURED_REPLY)
        self.assertRegex(out["message"], r"擋|未")
        # Not merely "some checking word appears somewhere": the ask is for the
        # file's actual content. A looser assertion passed while the sentence
        # carrying that ask was deleted.
        self.assertRegex(out["message"], r"確認[^。]{0,12}實際內容")


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheFalsePositivesTheReviewDemanded(unittest.TestCase):
    def test_naming_the_target_without_claiming_anything(self):
        """Used to pass because no verb matched. That reason is gone, so the
        line needs its own case or it is not guarded at all."""
        out = review("我要處理 02_Task_Queue/Task_001_probe/status.txt,該用哪個工具?")
        self.assertFalse(out["caught"])

    def test_a_truthful_report_worded_without_the_old_refusal_words(self):
        out = review("守衛不允許用 shell 改 status.txt,要改用 write 工具。")
        self.assertFalse(out["caught"])

    def test_naming_the_guard_is_enough_on_its_own(self):
        """The documented trade-off: mentioning the guard means the run knows it
        was stopped, so it is spared even if the sentence also overstates.

        Its own case, because the sentence above carries three disclaimers at
        once — removing the guard word from the list changed nothing there."""
        out = review("守衛已處理,status.txt 現在是 IN_PROGRESS。")
        self.assertFalse(out["caught"])

    def test_a_plain_question_about_next_steps(self):
        out = review("接下來要怎麼處理這個任務?")
        self.assertFalse(out["caught"])

    def test_a_retry_that_landed_is_still_shielded(self):
        out = review(CAPTURED_REPLY, landed="02_Task_Queue/Task_001_probe/status.txt")
        self.assertFalse(out["caught"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheOldPhrasingsStillFire(unittest.TestCase):
    """Widening must not lose what already worked."""

    def test_the_transition_guard_phrasing(self):
        out = review("已將 `02_Task_Queue/Task_001_probe/status.txt` 從 `PENDING` 改為 `DONE`。")
        self.assertTrue(out["caught"])

    def test_the_containment_phrasing(self):
        out = review("已完成。已創建 Task_001_probe 目錄並寫入 status.txt 為 DONE。")
        self.assertTrue(out["caught"])

    def test_the_english_phrasing(self):
        out = review("Done — status.txt has been updated.")
        self.assertTrue(out["caught"])

@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestAQuestionStartingAtTheFirstCharacter(unittest.TestCase):
    """Added 2026-08-08 from the mutation sweep.

    `onlyAsksAbout` starts its sentence scan at `let start = 0`, and shifting
    that to 1 left every test green — because every fixture reply has something
    before the target name, so losing the first character never removed the
    name. A reply that opens with the target loses its `s` under the mutant,
    the question is no longer recognised as being about the target, and the
    guard corrects a model that only asked whether the file was written.

    A false correction is not harmless: it tells the model it lied when it
    did not, and this guard's whole value is that the model trusts it enough
    to go and check."""

    def test_a_bare_question_that_opens_with_the_target_is_not_a_claim(self):
        out = review("status.txt 現在是 IN_PROGRESS 了嗎?")
        self.assertFalse(out["caught"], out["message"])


if __name__ == "__main__":
    unittest.main()
