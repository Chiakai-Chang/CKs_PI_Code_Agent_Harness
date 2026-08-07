"""The advancer moves to where the agent actually stops, and stops blaming the task.

Four ports from `reference/pi-until-done`, each answering something measured:

1. **Position.** `agent_settled` fires ONCE per agent run, 1ms after `agent_end`;
   `turn_end` fires every turn. Probed 2026-08-06 (`<scratchpad>/t015-settled`):

       agent_start / turn_start / turn_end(toolCall) / turn_start /
       turn_end(text) / agent_end / agent_settled

   The advancer spoke at `turn_end`, so a step in normal progress was declared
   stuck on the fourth turn. Five runs, none reached DONE.

2. **Stall judgement.** Not "how often did I speak" but "what did this cycle do".
   Weighted at `tool_call` the way pi-until-done does it (`hooks/tools.ts:65`):
   edit/write 3, bash 2, read/grep/find/ls 1, other tools 2 — a stall is zero.

3. **Whose state fails.** pi-until-done pauses ITSELF (`status: "paused"` on the
   loop's own state, `hooks/agent-end-helpers.ts:13`) and never touches the
   executed task. Ours told the model to write ESCALATED into `status.txt`, so
   three of five runs recorded a failed task and at least two of those tasks were
   progressing fine. Those were failures we manufactured.

4. **Terminal states.** loopy: "a loop is a feedback system with terminal states,
   not permission for endless autonomy." "Hand this to another session for
   approval" is correct and stable, and the counter escalated it as stuck.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(ROOT, "pi-extensions", "case-bridge", "queue-advancer.ts")
BRIDGE = os.path.join(ROOT, "pi-extensions", "case-bridge", "index.ts")


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
    driver = os.path.join(ROOT, "tests", ".tmp_settledloop_driver.mjs")
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


def queue(status="PENDING", files=None):
    root = tempfile.mkdtemp(prefix="settledloop-")
    d = os.path.join(root, "02_Task_Queue", "Task_001_probe")
    os.makedirs(d)
    with open(os.path.join(d, "status.txt"), "w", encoding="utf-8") as f:
        f.write(status)
    for name, body in (files or {}).items():
        with open(os.path.join(d, name), "w", encoding="utf-8") as f:
            f.write(body)
    return root, os.path.join(root, "02_Task_Queue").replace("\\", "/")


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestStallIsAboutWhatHappened(unittest.TestCase):
    """A cycle that called tools is working, however little the state moved."""

    def setUp(self):
        self.root, self.q = queue("PENDING")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def test_a_cycle_with_tool_calls_is_never_a_stall(self):
        out = run_js("""
        const a = new m.QueueAdvancer();
        const results = [];
        for (let i = 0; i < 6; i++) {
          a.noteProgress("read");
          a.noteProgress("write");
          const r = a.advance(%s);
          results.push(r ? (r.paused ? "PAUSED" : "advance") : "silent");
          a.endCycle();
        }
        process.stdout.write(JSON.stringify({ results }));
        """ % json.dumps(self.q))
        self.assertNotIn("PAUSED", out["results"],
                         "six working cycles must not be called a stall")

    def test_cycles_with_no_tool_calls_at_all_do_stall(self):
        out = run_js("""
        const a = new m.QueueAdvancer();
        const results = [];
        for (let i = 0; i < 6; i++) {
          const r = a.advance(%s);
          results.push(r ? (r.paused ? "PAUSED" : "advance") : "silent");
          a.endCycle();
        }
        process.stdout.write(JSON.stringify({ results }));
        """ % json.dumps(self.q))
        self.assertIn("PAUSED", out["results"])

    def test_progress_does_not_carry_across_cycles(self):
        """One busy cycle followed by three empty ones is a stall. Without a
        reset at the boundary the first cycle's score keeps the counter alive
        forever — a break that no other test here could see."""
        out = run_js("""
        const a = new m.QueueAdvancer();
        a.noteProgress("write");
        const results = [];
        for (let i = 0; i < 5; i++) {
          const r = a.advance(%s);
          results.push(r ? (r.paused ? "PAUSED" : "advance") : "silent");
          a.endCycle();
        }
        process.stdout.write(JSON.stringify({ results, left: a.progressThisCycle() }));
        """ % json.dumps(self.q))
        self.assertEqual(out["left"], 0, "the cycle boundary must zero the score")
        self.assertIn("PAUSED", out["results"])

    def test_the_weights_are_the_borrowed_ones(self):
        out = run_js("""
        const a = new m.QueueAdvancer();
        const w = {};
        for (const t of ["write", "edit", "bash", "read", "grep", "find", "ls", "web_search"]) {
          const b = new m.QueueAdvancer();
          b.noteProgress(t);
          w[t] = b.progressThisCycle();
        }
        process.stdout.write(JSON.stringify(w));
        """)
        self.assertEqual(out["write"], 3)
        self.assertEqual(out["edit"], 3)
        self.assertEqual(out["bash"], 2)
        self.assertEqual(out["read"], 1)
        self.assertEqual(out["grep"], 1)
        self.assertEqual(out["web_search"], 2)


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestItPausesItselfInsteadOfFailingTheTask(unittest.TestCase):
    """Three of five measured runs ended ESCALATED and at least two of those
    tasks were fine. The automation's surrender is not the task's failure."""

    def setUp(self):
        self.root, self.q = queue("PENDING")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def _pause(self):
        return run_js("""
        const a = new m.QueueAdvancer();
        let last = null;
        for (let i = 0; i < 8; i++) { const r = a.advance(%s); if (r) last = r; a.endCycle(); }
        process.stdout.write(JSON.stringify({ paused: !!(last && last.paused),
                                              message: last ? last.message : "" }));
        """ % json.dumps(self.q))

    def test_it_reports_a_pause(self):
        self.assertTrue(self._pause()["paused"])

    def test_it_never_asks_for_an_escalated_status(self):
        msg = self._pause()["message"]
        self.assertNotIn("ESCALATED", msg)
        self.assertNotIn("status.txt", msg)

    def test_the_status_file_is_untouched(self):
        self._pause()
        with open(os.path.join(self.root, "02_Task_Queue", "Task_001_probe",
                               "status.txt"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "PENDING")


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTerminalStepsAreNotStalls(unittest.TestCase):
    """REVIEW with a retro written is the protocol's stopping point: approval
    belongs to another session. Saying so once is the whole job."""

    def setUp(self):
        self.root, self.q = queue("REVIEW", {"retro.md": "## Gaps & Missteps\nx",
                                             "planning.md": "## Self-Review",
                                             "output.md": "y" * 400})
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def test_said_once_then_silence_and_no_pause(self):
        out = run_js("""
        const a = new m.QueueAdvancer();
        const results = [];
        for (let i = 0; i < 6; i++) {
          const r = a.advance(%s);
          results.push(r ? (r.paused ? "PAUSED" : "advance") : "silent");
          a.endCycle();
        }
        process.stdout.write(JSON.stringify({ results }));
        """ % json.dumps(self.q))
        self.assertEqual(out["results"][0], "advance")
        self.assertNotIn("PAUSED", out["results"],
                         "a terminal state is not a stalled one")
        self.assertEqual(set(out["results"][1:]), {"silent"})


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheBridgeDrivesItWhereDeliveryWorks(unittest.TestCase):
    """The position port was REVERSED, and these tests record why.

    `agent_settled`'s own declaration says it fires "after an agent run has
    fully settled and no automatic retry, compaction, or queued continuation
    will run" — a continuation queued there is too late by definition. Measured
    twice: nothing reached the session. `sendUserMessage`, which pi-until-done
    uses at that point, hung the process in `--print` on both attempts.

    `turn_end` + sendMessage(followUp, triggerTurn) is the channel measured to
    deliver in this project: eleven injections in the clean rerun. Delivery was
    never the defect — frequency and blame were, and those are fixed in the
    advancer itself. So the trigger stays where messages arrive, and speaks only
    on a turn that produced text and called no tools."""

    def _src(self):
        with open(BRIDGE, encoding="utf-8") as f:
            return f.read()

    def test_it_advances_from_turn_end(self):
        after = self._src().split('pi.on("turn_end"', 1)
        self.assertEqual(len(after), 2, "no turn_end handler at all")
        self.assertIn("advancer.advance", after[1][:1600])

    def test_there_is_no_second_trigger(self):
        src = self._src()
        self.assertEqual(src.count("advancer.advance("), 1,
                         "two triggers is what the recipe forbids")

    def test_it_stays_quiet_on_a_working_turn(self):
        body = self._src().split('pi.on("turn_end"', 1)[1][:1600]
        self.assertIn("progressThisCycle", body,
                      "a turn that called tools is work, not a stall")

    def test_it_stays_quiet_on_a_tool_only_turn(self):
        body = self._src().split('pi.on("turn_end"', 1)[1][:1600]
        self.assertIn("spoke", body,
                      "a turn with no text is not the end of a reply")

    def test_tool_calls_are_scored(self):
        self.assertIn("noteProgress", self._src())


if __name__ == "__main__":
    unittest.main()
