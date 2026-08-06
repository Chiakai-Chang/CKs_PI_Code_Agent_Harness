"""A refused change reported as done.

Watched live twice on 2026-08-06, in a real C.A.S.E. project:

    guard   C.A.S.E. transition guard fired x2 — status.txt untouched
    model   "已將 `02_Task_Queue/Task_001_Probe/status.txt` 從 `PENDING` 改為 `DONE`。"
            (having first said out loud that the protocol wants IN_PROGRESS first)

and earlier the same day:

    guard   Directory containment — write refused
    model   "已完成。已創建 `Task_001_Probe` 目錄並寫入 `status.txt` 為 DONE。"

Neither existing guard sees this. The fabricated-work guard matches turns that
END WITHOUT CALLING ANYTHING while claiming work; these turns called plenty and
were refused. The unfulfilled-intent guard matches turns that ANNOUNCE a next
step and stop; these announced completion.

That makes it the third member of the family and the most damaging, because a
guard doing its job produces a session record that says the opposite. A user
reading the reply believes the file changed. The whole point of refusing was
that it should not.

Decidable without reading intent: a block happened for target T this turn, no
successful write to T followed, and the closing text claims success.
"""

import json
import os
import re
import shutil
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(ROOT, "pi-extensions", "yes-hooks-bridge", "blocked-claim.ts")


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
    driver = os.path.join(ROOT, "tests", ".tmp_bclaim_driver.mjs")
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


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheTwoRunsThatMotivatedIt(unittest.TestCase):
    def test_the_transition_guard_case(self):
        out = run_js("""
        const t = new m.BlockedClaimTracker();
        t.blocked("write", { path: "02_Task_Queue/Task_001_Probe/status.txt" });
        const r = t.review("已將 `02_Task_Queue/Task_001_Probe/status.txt` 從 `PENDING` 改為 `DONE`。");
        process.stdout.write(JSON.stringify({ caught: !!r, message: r ? r.message : "" }));
        """)
        self.assertTrue(out["caught"])
        self.assertIn("status.txt", out["message"])

    def test_the_containment_case(self):
        out = run_js("""
        const t = new m.BlockedClaimTracker();
        t.blocked("write", { path: "D:/other/02_Task_Queue/Task_001_Probe/status.txt" });
        const r = t.review("已完成。已創建 `Task_001_Probe` 目錄並寫入 `status.txt` 為 DONE。");
        process.stdout.write(JSON.stringify({ caught: !!r }));
        """)
        self.assertTrue(out["caught"])

    def test_english_completion_claims_too(self):
        out = run_js("""
        const t = new m.BlockedClaimTracker();
        t.blocked("write", { path: "notes.md" });
        const r = t.review("Done — I've updated notes.md as requested.");
        process.stdout.write(JSON.stringify({ caught: !!r }));
        """)
        self.assertTrue(out["caught"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestHonestTurnsAreLeftAlone(unittest.TestCase):
    """A guard that fires on an honest report teaches the run to stop reporting."""

    def test_a_turn_that_reports_the_block_is_not_corrected(self):
        out = run_js("""
        const t = new m.BlockedClaimTracker();
        t.blocked("write", { path: "status.txt" });
        const r = t.review("我試著把 status.txt 改成 DONE,但被 C.A.S.E. 守衛擋下了,因為要先經過 IN_PROGRESS。");
        process.stdout.write(JSON.stringify({ caught: !!r }));
        """)
        self.assertFalse(out["caught"])

    def test_a_retry_that_succeeded_is_not_corrected(self):
        out = run_js("""
        const t = new m.BlockedClaimTracker();
        t.blocked("write", { path: "status.txt" });
        t.succeeded("write", { path: "status.txt" });
        const r = t.review("已將 status.txt 改好了。");
        process.stdout.write(JSON.stringify({ caught: !!r }));
        """)
        self.assertFalse(out["caught"], "the write did land in the end");

    def test_a_turn_with_no_block_is_never_touched(self):
        out = run_js("""
        const t = new m.BlockedClaimTracker();
        t.succeeded("write", { path: "a.md" });
        const r = t.review("已完成,已寫入 a.md。");
        process.stdout.write(JSON.stringify({ caught: !!r }));
        """)
        self.assertFalse(out["caught"])

    def test_a_block_with_no_completion_claim_is_not_touched(self):
        out = run_js("""
        const t = new m.BlockedClaimTracker();
        t.blocked("write", { path: "status.txt" });
        const r = t.review("接下來要怎麼處理這個任務?");
        process.stdout.write(JSON.stringify({ caught: !!r }));
        """)
        self.assertFalse(out["caught"])

    def test_a_block_on_a_different_target_does_not_shield_a_real_claim(self):
        """Two files, one refused. A claim about the other is true."""
        out = run_js("""
        const t = new m.BlockedClaimTracker();
        t.blocked("write", { path: "status.txt" });
        t.succeeded("write", { path: "output.md" });
        const r = t.review("已寫入 output.md。");
        process.stdout.write(JSON.stringify({ caught: !!r }));
        """)
        self.assertFalse(out["caught"],
                         "the claim names only the file that was written")


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheCorrection(unittest.TestCase):
    def test_it_names_the_target_and_says_it_did_not_happen(self):
        out = run_js("""
        const t = new m.BlockedClaimTracker();
        t.blocked("write", { path: "02_Task_Queue/Task_001/status.txt" });
        const r = t.review("已將 status.txt 改為 DONE。");
        process.stdout.write(JSON.stringify({ message: r.message }));
        """)
        self.assertIn("status.txt", out["message"])
        self.assertRegex(out["message"], r"(?i)未|沒有|not|refus|擋")

    def test_reset_clears_the_turn(self):
        out = run_js("""
        const t = new m.BlockedClaimTracker();
        t.blocked("write", { path: "status.txt" });
        t.reset();
        const r = t.review("已將 status.txt 改為 DONE。");
        process.stdout.write(JSON.stringify({ caught: !!r }));
        """)
        self.assertFalse(out["caught"])

    def test_bash_blocks_count_too(self):
        out = run_js("""
        const t = new m.BlockedClaimTracker();
        t.blocked("bash", { command: 'echo DONE > "D:/other/status.txt"' });
        const r = t.review("已完成,已寫入 D:/other/status.txt。");
        process.stdout.write(JSON.stringify({ caught: !!r }));
        """)
        self.assertTrue(out["caught"])

    def test_unreadable_input_does_not_throw(self):
        out = run_js("""
        const t = new m.BlockedClaimTracker();
        const a = {}; a.self = a;
        let threw = false;
        try { t.blocked("write", a); t.review("已完成"); } catch { threw = true; }
        process.stdout.write(JSON.stringify({ threw }));
        """)
        self.assertFalse(out["threw"])


if __name__ == "__main__":
    unittest.main()
