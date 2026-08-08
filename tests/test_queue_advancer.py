"""The harness works out the next step, instead of hoping the model proposes one.

Ten rounds of discussion converged on one sentence: code can decide *how* a task
is worked, and cannot decide *whether* to start. Promoting `case-framework` into
the tier that carries descriptions was the last attempt at the second half, and
it was measured at 0/3 loads on a three-deliverable brief.

The 2026 literature names the two modes. Agent-proposed activation puts a skill
in front of the model and waits; policy-mediated activation has the system
decide from configuration and triggers. Anthropic's guidance is blunter — a
deterministic backbone owns the flow, the model fills specific steps.

Pi has the backbone parts already, and this repo already uses them: a
`sendMessage` with `followUp` and `triggerTurn` is how async-exec wakes the
agent. Verified in a real session (019fcf32) before any of this was written:

     8  ASSISTANT  text                       turn ended
     9  CUSTOM     universal-tag-transformer  injected
    10  ASSISTANT  bash                       a new turn, with a real tool call

No user message between 8 and 10. The mechanism advances a turn; it had only
ever been used to correct one.

So the next step is looked up, never invented. Every row of the table below
points at a clause of `external/Local-Agent-Workspace/references/for_agents.md`,
and every condition is file existence — nothing here judges content.
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
    driver = os.path.join(ROOT, "tests", ".tmp_advancer_driver.mjs")
    url = "file:///" + MOD.replace("\\", "/")
    with open(driver, "w", encoding="utf-8") as f:
        f.write("import * as m from %s;\nimport fs from 'node:fs';\n%s" % (json.dumps(url), script))
    try:
        p = subprocess.run(["node", driver], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=ROOT, timeout=120)
        if p.returncode != 0:
            raise AssertionError("node driver failed:\n%s\n%s" % (p.stdout, p.stderr))
        return json.loads(p.stdout)
    finally:
        if os.path.exists(driver):
            os.remove(driver)


class Queue:
    """A real queue on disk. The guard reads files, so it gets files — a fixture
    that invents the payload is how something in this repo passed six tests and
    fired zero times live."""

    def __init__(self):
        self.root = tempfile.mkdtemp(prefix="advancer-")
        self.dir = os.path.join(self.root, "02_Task_Queue")
        os.makedirs(self.dir)

    def task(self, name, status="PENDING", planning=None, output=None, retro=False):
        d = os.path.join(self.dir, name)
        os.makedirs(d, exist_ok=True)
        self._w(os.path.join(d, "status.txt"), status)
        self._w(os.path.join(d, "role.md"), "# Role\n")
        self._w(os.path.join(d, "recipe.md"), "# Recipe\n## Objective\nx\n## Local Definition of Done\n- y\n")
        if planning is not None:
            self._w(os.path.join(d, "planning.md"), planning)
        if output is not None:
            self._w(os.path.join(d, "output.md"), output)
        if retro:
            self._w(os.path.join(d, "retro.md"),
                    "## Gaps & Missteps\n-\n## Optimization Opportunities\n-\n"
                    "## Lessons Learned\n-\n## Feedback to CASE\n-\n")
        return d

    @staticmethod
    def _w(path, text):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    @property
    def js(self):
        return json.dumps(self.dir.replace("\\", "/"))

    def cleanup(self):
        shutil.rmtree(self.root, ignore_errors=True)


def step_of(queue):
    return run_js("""
    const s = m.nextStep(%s);
    process.stdout.write(JSON.stringify(s || {}));
    """ % queue.js)


PLAN_OK = "# Plan\nsteps\n## Self-Review\nchecked\n"
OUTPUT_OK = "A real deliverable, long enough to count as one. " * 6


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheLookupTable(unittest.TestCase):
    """Seven rows, each pointing at a clause of the protocol."""

    def setUp(self):
        self.q = Queue()
        self.addCleanup(self.q.cleanup)

    def test_pending_starts(self):
        self.q.task("Task_001_a", "PENDING")
        s = step_of(self.q)
        self.assertEqual(s["status"], "PENDING")
        self.assertIn("IN_PROGRESS", s["instruction"])

    def test_in_progress_without_a_plan_writes_one(self):
        self.q.task("Task_001_a", "IN_PROGRESS")
        s = step_of(self.q)
        self.assertEqual(s["missing"], "planning")
        self.assertIn("planning.md", s["instruction"])

    def test_a_plan_without_self_review_is_not_a_plan(self):
        self.q.task("Task_001_a", "IN_PROGRESS", planning="# Plan\njust steps\n")
        s = step_of(self.q)
        self.assertEqual(s["missing"], "self-review")
        self.assertIn("Self-Review", s["instruction"])

    def test_planned_but_no_output(self):
        self.q.task("Task_001_a", "IN_PROGRESS", planning=PLAN_OK)
        s = step_of(self.q)
        self.assertEqual(s["missing"], "output")
        self.assertIn("output.md", s["instruction"])

    def test_a_placeholder_output_does_not_count(self):
        self.q.task("Task_001_a", "IN_PROGRESS", planning=PLAN_OK, output="ok")
        self.assertEqual(step_of(self.q)["missing"], "output")

    def test_everything_present_submits_for_review(self):
        self.q.task("Task_001_a", "IN_PROGRESS", planning=PLAN_OK, output=OUTPUT_OK)
        s = step_of(self.q)
        self.assertEqual(s["missing"], "")
        self.assertIn("REVIEW", s["instruction"])

    def test_review_without_a_retro(self):
        self.q.task("Task_001_a", "REVIEW", planning=PLAN_OK, output=OUTPUT_OK)
        s = step_of(self.q)
        self.assertEqual(s["missing"], "retro")
        self.assertIn("retro.md", s["instruction"])

    def test_review_with_a_retro_waits_for_a_separate_checker(self):
        """Section 1 is non-negotiable and Path B still requires a fresh
        context, so the advancer must not tell this session to approve.

        The first assertion here matched "session|checker", which the wording
        satisfies either way — a build rewritten to say "approve it now" still
        mentions a session in the next clause, so the test passed against it.
        It now demands the separateness itself and refuses the opposite.
        """
        self.q.task("Task_001_a", "REVIEW", planning=PLAN_OK, output=OUTPUT_OK, retro=True)
        s = step_of(self.q)
        self.assertEqual(s["missing"], "")
        self.assertRegex(s["instruction"], r"(另一個 session|fresh context|separate session)")
        self.assertNotRegex(s["instruction"], r"(直接核可|可以核可|approve it now)")

    def test_done_and_escalated_are_left_alone(self):
        for status in ("DONE", "ESCALATED"):
            with self.subTest(status=status):
                q = Queue()
                self.addCleanup(q.cleanup)
                q.task("Task_001_a", status, planning=PLAN_OK, output=OUTPUT_OK, retro=True)
                self.assertEqual(step_of(q), {})


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestWhichTask(unittest.TestCase):
    def setUp(self):
        self.q = Queue()
        self.addCleanup(self.q.cleanup)

    def test_the_open_one_wins_over_a_pending_one(self):
        self.q.task("Task_001_a", "DONE", planning=PLAN_OK, output=OUTPUT_OK, retro=True)
        self.q.task("Task_002_b", "IN_PROGRESS", planning=PLAN_OK, output=OUTPUT_OK)
        self.q.task("Task_003_c", "PENDING")
        self.assertEqual(step_of(self.q)["task"], "Task_002_b")

    def test_with_nothing_open_the_lowest_pending_starts(self):
        self.q.task("Task_001_a", "DONE", planning=PLAN_OK, output=OUTPUT_OK, retro=True)
        self.q.task("Task_002_b", "PENDING")
        self.q.task("Task_003_c", "PENDING")
        self.assertEqual(step_of(self.q)["task"], "Task_002_b")

    def test_two_open_tasks_are_not_guessed_between(self):
        """The queue guard already refuses that state; advancing on a guess
        would file the next step against the wrong task.

        The third, pending task is what gives this teeth. Without it, deleting
        the two-open check changes nothing — the lookup falls through to "no
        pending tasks" and returns null either way, so the test passed against
        a deliberately broken build. With it, a broken build answers
        `Task_003_c` and a correct one answers nothing.
        """
        self.q.task("Task_001_a", "IN_PROGRESS")
        self.q.task("Task_002_b", "IN_PROGRESS")
        self.q.task("Task_003_c", "PENDING")
        self.assertEqual(step_of(self.q), {})

    def test_an_empty_or_finished_queue_has_no_next_step(self):
        self.assertEqual(step_of(self.q), {})
        self.q.task("Task_001_a", "DONE", planning=PLAN_OK, output=OUTPUT_OK, retro=True)
        self.assertEqual(step_of(self.q), {})

    def test_a_project_with_no_queue_at_all(self):
        out = run_js("""
        const s = m.nextStep("definitely/not/here");
        process.stdout.write(JSON.stringify({ s: s }));
        """)
        self.assertIsNone(out["s"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestItStopsRatherThanRepeats(unittest.TestCase):
    """Advancing forever is a loop with extra steps."""

    def setUp(self):
        self.q = Queue()
        self.addCleanup(self.q.cleanup)

    def test_idle_cycles_then_it_pauses_itself(self):
        """Was "three injections then ESCALATE". Both halves of that were wrong,
        and measurement said so:

          * counting injections declared steps in normal progress stuck — five
            runs, none reached DONE;
          * escalating wrote the automation's surrender into the task's own
            status, so three of five runs recorded failed tasks and at least two
            of those tasks were fine.

        Now: cycles that call no tools at all are what retire it, and it pauses
        ITSELF. `endCycle()` marks the boundary — one agent run, not one turn."""
        self.q.task("Task_001_a", "IN_PROGRESS")
        out = run_js("""
        const a = new m.QueueAdvancer();
        const seen = [];
        for (let i = 0; i < 6; i++) {
          const r = a.advance(%s);
          seen.push(r ? (r.paused ? "PAUSED" : "advance") : "silent");
          a.endCycle();
        }
        process.stdout.write(JSON.stringify({ seen }));
        """ % self.q.js)
        self.assertEqual(out["seen"][:3], ["advance", "advance", "advance"])
        self.assertEqual(out["seen"][3], "PAUSED")
        self.assertEqual(out["seen"][4:], ["silent", "silent"],
                         "after pausing it must stop, not keep talking")

    def test_progress_resets_the_count(self):
        d = self.q.task("Task_001_a", "IN_PROGRESS")
        out = run_js("""
        const a = new m.QueueAdvancer();
        const before = [];
        for (let i = 0; i < 2; i++) before.push(!!a.advance(%s));
        fs.writeFileSync(%s + "/planning.md", "# Plan\\n## Self-Review\\nok\\n");
        const after = [];
        for (let i = 0; i < 3; i++) {
          const r = a.advance(%s);
          after.push(r && !r.escalate ? "advance" : (r ? "ESCALATE" : "silent"));
        }
        process.stdout.write(JSON.stringify({ before, after }));
        """ % (self.q.js, json.dumps(d.replace("\\", "/")), self.q.js))
        self.assertEqual(out["before"], [True, True])
        self.assertEqual(out["after"][0], "advance",
                         "a different next step is a fresh budget")

    def test_reset_clears_the_session(self):
        self.q.task("Task_001_a", "IN_PROGRESS")
        out = run_js("""
        const a = new m.QueueAdvancer();
        for (let i = 0; i < 4; i++) a.advance(%s);
        a.reset();
        const r = a.advance(%s);
        process.stdout.write(JSON.stringify({ again: !!r && !r.escalate }));
        """ % (self.q.js, self.q.js))
        self.assertTrue(out["again"])

    def test_an_unreadable_queue_does_not_throw(self):
        out = run_js("""
        const a = new m.QueueAdvancer();
        let threw = false;
        try { a.advance(null); } catch { threw = true; }
        process.stdout.write(JSON.stringify({ threw }));
        """)
        self.assertFalse(out["threw"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheInstruction(unittest.TestCase):
    def setUp(self):
        self.q = Queue()
        self.addCleanup(self.q.cleanup)

    def test_it_names_the_task(self):
        self.q.task("Task_007_thing", "IN_PROGRESS")
        self.assertIn("Task_007_thing", step_of(self.q)["instruction"])

    def test_it_says_where_the_rule_comes_from(self):
        """Every row points at a clause, so a reader can check it rather than
        take the harness's word."""
        self.q.task("Task_001_a", "IN_PROGRESS")
        self.assertRegex(step_of(self.q)["instruction"], r"(?i)C\.A\.S\.E|for_agents|§|Section")

@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheOutputThresholdIsExact(unittest.TestCase):
    """Added 2026-08-08 from the mutation sweep, not from a suspicion.

    `OUTPUT_MIN_CHARS = 200` shifted to 201 and nothing turned red, because
    every fixture writes either a stub or a wall of text. The number decides
    when the advancer stops asking for a deliverable and starts asking for a
    handover, so an unpinned threshold means the step boundary can drift
    without a single test noticing.

    Also pinned here: an empty queue directory. `if (typeof queueDir !==
    "string" || !queueDir) return null` had its `||` flipped to `&&` and
    survived — no case passed an empty string, so the fail-open path for a
    project without a queue was never exercised at its own boundary."""

    def setUp(self):
        self.q = Queue()
        self.addCleanup(self.q.cleanup)

    def _step(self, output):
        # chr(10) rather than an escape: this is the sixth backslash today lost
        # between the shell, the heredoc and the file.
        self.q.task("Task_001_probe", "IN_PROGRESS",
                    planning="## Self-Review" + chr(10) + "ok" + chr(10),
                    output=output)
        # nextStep(), not advance(): advance() returns the wrapper {message},
        # so `s.missing` was undefined and JSON.stringify dropped the key
        # entirely — a KeyError that reads like a broken fixture and is really
        # the wrong function.
        return run_js("""
        const s = m.nextStep(%s);
        process.stdout.write(JSON.stringify({ missing: s ? s.missing : null,
                                              min: m.OUTPUT_MIN_CHARS }));
        """ % json.dumps(self.q.dir.replace("\\", "/")))

    def test_one_char_short_still_asks_for_the_deliverable(self):
        out = self._step("z" * 199)
        self.assertEqual(out["min"], 200)
        self.assertEqual(out["missing"], "output")

    def test_exactly_at_the_threshold_moves_on(self):
        self.assertNotEqual(self._step("z" * 200)["missing"], "output")

    def test_an_empty_queue_directory_returns_nothing(self):
        out = run_js("""
        process.stdout.write(JSON.stringify({ next: m.nextStep("") }));
        """)
        self.assertIsNone(out["next"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestAReviewWithNoDeliverable(unittest.TestCase):
    """Baseline run 2, 2026-08-08: reached REVIEW with planning.md and retro.md
    and no output.md, and the advancer called it terminal — "hand this to
    another session" for work that does not exist.

    `nextStep()` treats REVIEW plus a retro as the stopping point and never
    looks back at the deliverable, and IN_PROGRESS -> REVIEW is a legal
    transition, so nothing else catches it either. Process completed, nothing
    produced — the shape this repo keeps meeting."""

    def setUp(self):
        self.q = Queue()
        self.addCleanup(self.q.cleanup)

    def _step(self, **kw):
        self.q.task("Task_001_a", "REVIEW", **kw)
        return step_of(self.q)

    def test_review_without_output_asks_for_the_deliverable(self):
        s = self._step(planning=PLAN_OK, retro=True)
        self.assertEqual(s["missing"], "output")
        self.assertIn("output.md", s["instruction"])

    def test_a_stub_output_does_not_count_here_either(self):
        s = self._step(planning=PLAN_OK, output="ok", retro=True)
        self.assertEqual(s["missing"], "output")

    def test_review_with_everything_is_still_terminal(self):
        """The existing behaviour must not move: a complete package at REVIEW
        hands over to another session, exactly once."""
        s = self._step(planning=PLAN_OK, output=OUTPUT_OK, retro=True)
        self.assertEqual(s["missing"], "")
        self.assertRegex(s["instruction"], r"(另一個 session|fresh context|separate session)")


if __name__ == "__main__":
    unittest.main()
