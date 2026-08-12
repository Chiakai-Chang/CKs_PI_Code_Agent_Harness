"""The guard was listening on an event that never fires for a blocked call.

Measured 2026-08-06 with a temporary probe on the installed bridge, one run per
row, and this is the whole reason the task exists:

    blocked call:  tool_execution_start  args = {command: "printf ... > status.txt"}
                   tool_execution_end    isError: true, result = the refusal text
                   tool_call             — not fired
                   tool_result           — NOT FIRED
    allowed call:  all four fired

`BlockedClaimTracker` was fed from `tool_result`, so it never learned that
anything had been refused, so `review()` always saw an empty set. Twelve unit
tests passed the whole time. The file's own comment asserted that refusals
"arrive as a tool_result with isError set" — an assumption that reads like an
observation, and the session transcript backs it up misleadingly: Pi writes a
`role: toolResult` record with isError true into the log. That record is not the
event.

The pairing is what makes this awkward. `ToolExecutionEndEvent` carries
`toolCallId`, `toolName`, `result` and `isError` — and no input. The path being
written is only in `ToolExecutionStartEvent.args`. Miss the pairing and the
tracker gets a block with no target, which it discards, which produces exactly
the guard we already had: fixed and still silent.

Not every failure is a refusal. A command that runs and exits non-zero also
arrives with isError set; correcting the run for that would be a guard
contradicting an honest report of a real failure.
"""

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

MOD = os.path.join(ROOT, "pi-extensions", "yes-hooks-bridge", "blocked-claim.ts")

CALL_ID = "dxe3lAZhwNQ4zpZVviVeKQyLErx3XHvF"
ARGS = {"command": "printf 'IN_PROGRESS' > \"02_Task_Queue/Task_001_probe/status.txt\""}
REFUSAL = {"content": [{"type": "text", "text": (
    "C.A.S.E. tool-first guard: this changes Task_001_probe's status with a shell "
    "redirect, which the protocol names as the thing never to do.")}]}
ORDINARY_FAILURE = {"content": [{"type": "text", "text":
                                 "bash: line 1: frobnicate: command not found"}]}
CAPTURED_REPLY = ("已執行完畢。`02_Task_Queue/Task_001_probe/status.txt` 的內容已透過 "
                  "`printf` 改為 `IN_PROGRESS`。")
# Named rather than inlined: writing it into the generated JS by hand is how the
# newline stopped being an escape and became a line break, three times today.
BLANK_REPLY = "   \n  "


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
    driver = scratch(".tmp_bcchan_driver.mjs")
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


def through_execution_events(start=True, result=REFUSAL, is_error=True,
                             reply=CAPTURED_REPLY, reset_before_review=False):
    return run_js("""
    const t = new m.BlockedClaimTracker();
    %s
    t.executionEnd(%s, "bash", %s, %s);
    %s
    const r = t.review(%s);
    process.stdout.write(JSON.stringify({ caught: !!r, message: r ? r.message : "",
                                          pending: t.pendingCount() }));
    """ % (('t.executionStart(%s, "bash", %s);' % (json.dumps(CALL_ID), json.dumps(ARGS)))
           if start else "",
           json.dumps(CALL_ID), "true" if is_error else "false", json.dumps(result),
           "t.reset();" if reset_before_review else "",
           json.dumps(reply)))


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheEventsThatActuallyFire(unittest.TestCase):
    def test_a_refusal_seen_through_start_and_end_is_recorded(self):
        out = through_execution_events()
        self.assertTrue(out["caught"])
        self.assertIn("status.txt", out["message"])

    def test_an_end_with_no_matching_start_is_dropped_quietly(self):
        """No args means no target, and a correction with no target is one this
        guard must not send. It must also not throw."""
        out = through_execution_events(start=False)
        self.assertFalse(out["caught"])

    def test_an_ordinary_command_failure_is_not_a_refusal(self):
        out = through_execution_events(result=ORDINARY_FAILURE)
        self.assertFalse(out["caught"])

    def test_a_successful_call_clears_an_earlier_refusal(self):
        out = run_js("""
        const t = new m.BlockedClaimTracker();
        t.executionStart("a", "bash", %s);
        t.executionEnd("a", "bash", true, %s);
        t.executionStart("b", "write", { path: "02_Task_Queue/Task_001_probe/status.txt" });
        t.executionEnd("b", "write", false, { content: [{ type: "text", text: "ok" }] });
        const r = t.review(%s);
        process.stdout.write(JSON.stringify({ caught: !!r }));
        """ % (json.dumps(ARGS), json.dumps(REFUSAL), json.dumps(CAPTURED_REPLY)))
        self.assertFalse(out["caught"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestThePairingTableIsBounded(unittest.TestCase):
    """A map keyed by call id that nobody empties grows for the whole session."""

    def test_a_matched_pair_leaves_nothing_behind(self):
        out = through_execution_events()
        self.assertEqual(out["pending"], 0)

    def test_reset_clears_starts_that_never_ended(self):
        out = run_js("""
        const t = new m.BlockedClaimTracker();
        for (let i = 0; i < 5; i++) t.executionStart("id" + i, "bash", %s);
        const before = t.pendingCount();
        t.reset();
        process.stdout.write(JSON.stringify({ before, after: t.pendingCount() }));
        """ % json.dumps(ARGS))
        self.assertEqual(out["before"], 5)
        self.assertEqual(out["after"], 0)


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheOldEntryPointsStillWork(unittest.TestCase):
    """`blocked()` and `succeeded()` stay public: the write/edit guards in this
    same bridge know their own refusals directly and need no pairing."""

    def test_blocked_and_succeeded_are_unchanged(self):
        out = run_js("""
        const t = new m.BlockedClaimTracker();
        t.blocked("write", { path: "02_Task_Queue/Task_001_probe/status.txt" });
        const r = t.review(%s);
        process.stdout.write(JSON.stringify({ caught: !!r }));
        """ % json.dumps(CAPTURED_REPLY))
        self.assertTrue(out["caught"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestATurnWithNoReplyIsNotTheEndOfOne(unittest.TestCase):
    """The block and the claim land in different turns.

    Probed live on 2026-08-06 with the execution pair already wired correctly:

        start / end (isError: true)          <- the block
        turn_end  text: ""                   <- the turn that only called a tool
        turn_end  text: "已執行完畢…"          <- the claim

    `reset()` ran on the first one and emptied the history, so the turn that
    actually made the false statement had nothing recorded against it. Events
    fired, pairing worked, `pendingCount()` was 0 — and the correction still
    never went out. A turn that produced no text is not the end of a reply.
    """

    def test_a_textless_turn_does_not_erase_the_block(self):
        out = run_js("""
        const t = new m.BlockedClaimTracker();
        t.executionStart("a", "bash", %s);
        t.executionEnd("a", "bash", true, %s);
        const first = t.turnEnded("");
        const second = t.turnEnded(%s);
        process.stdout.write(JSON.stringify({ first: !!first, second: !!second }));
        """ % (json.dumps(ARGS), json.dumps(REFUSAL), json.dumps(CAPTURED_REPLY)))
        self.assertFalse(out["first"])
        self.assertTrue(out["second"], "the claim arrived in the next turn, and it is still false")

    def test_a_turn_with_a_reply_clears_the_history(self):
        out = run_js("""
        const t = new m.BlockedClaimTracker();
        t.executionStart("a", "bash", %s);
        t.executionEnd("a", "bash", true, %s);
        t.turnEnded("好的。");
        const again = t.turnEnded(%s);
        process.stdout.write(JSON.stringify({ again: !!again }));
        """ % (json.dumps(ARGS), json.dumps(REFUSAL), json.dumps(CAPTURED_REPLY)))
        self.assertFalse(out["again"], "a refusal from a finished turn must not follow the run around")

    def test_whitespace_only_counts_as_no_reply(self):
        out = run_js("""
        const t = new m.BlockedClaimTracker();
        t.executionStart("a", "bash", %s);
        t.executionEnd("a", "bash", true, %s);
        t.turnEnded(%s);
        const second = t.turnEnded(%s);
        process.stdout.write(JSON.stringify({ second: !!second }));
        """ % (json.dumps(ARGS), json.dumps(REFUSAL), json.dumps(BLANK_REPLY),
               json.dumps(CAPTURED_REPLY)))
        self.assertTrue(out["second"])


if __name__ == "__main__":
    unittest.main()
