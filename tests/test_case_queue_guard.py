"""C.A.S.E. state transitions are tool calls, so they can be refused.

Every transition in the protocol is one write to `status.txt`:

    PENDING     -> IN_PROGRESS   Worker starts
    IN_PROGRESS -> REVIEW        Worker submits
    REVIEW      -> DONE          Checker approves
    REVIEW      -> PENDING       Checker rejects
    * -> ESCALATED               halted

A write is a `tool_call`, and `tool_call` fires before the tool runs — so the
old value is still on disk and the harness can compare, and refuse. That is the
one channel measured to change behaviour in this harness: the citation guard
fired 3/3 and took URLs written into files from 0 to 10/15, while the same
instruction as skill text was skipped 3/3 and `case-framework` sitting in the
core tier with a full description was loaded 0/3.

What code cannot do is decide to *start*. A transition has a before and an
after to compare; beginning to use a framework has neither. These guards apply
only once a task queue exists, and say nothing about getting one.

Scope is deliberately narrow: writes landing inside `02_Task_Queue/Task_NNN_*/`.
Nothing else in a project is touched, so a user who does not use C.A.S.E. never
meets any of this.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(ROOT, "pi-extensions", "case-bridge", "task-queue-guard.ts")


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


def run_js(script, extra=""):
    driver = os.path.join(ROOT, "tests", ".tmp_queue_driver.mjs")
    url = "file:///" + MOD.replace("\\", "/")
    with open(driver, "w", encoding="utf-8") as f:
        f.write("import * as m from %s;\nimport fs from 'node:fs';\nimport path from 'node:path';\n%s%s"
                % (json.dumps(url), extra, script))
    try:
        p = subprocess.run(["node", driver], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=ROOT, timeout=120)
        if p.returncode != 0:
            raise AssertionError("node driver failed:\n%s\n%s" % (p.stdout, p.stderr))
        return json.loads(p.stdout)
    finally:
        if os.path.exists(driver):
            os.remove(driver)


class QueueFixture:
    """A real 02_Task_Queue on disk. The guard reads files, so the tests give it
    files rather than a stand-in — a fixture that invents the payload is how a
    guard in this repo passed six tests and fired zero times live."""

    def __init__(self):
        self.root = tempfile.mkdtemp(prefix="case-guard-")
        self.queue = os.path.join(self.root, "02_Task_Queue")
        os.makedirs(self.queue)

    def task(self, name, status="PENDING", retro=False):
        d = os.path.join(self.queue, name)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "status.txt"), "w", encoding="utf-8") as f:
            f.write(status)
        if retro:
            with open(os.path.join(d, "retro.md"), "w", encoding="utf-8") as f:
                f.write("# Retro\n## Gaps & Missteps\n-\n## Optimization Opportunities\n-\n"
                        "## Lessons Learned\n-\n## Feedback to CASE\n-\n")
        return d.replace("\\", "/")

    def cleanup(self):
        shutil.rmtree(self.root, ignore_errors=True)


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestScope(unittest.TestCase):
    """A project that does not use C.A.S.E. must never meet this."""

    def setUp(self):
        self.fx = QueueFixture()
        self.addCleanup(self.fx.cleanup)

    def test_writes_outside_a_task_queue_are_ignored(self):
        out = run_js("""
        const g = new m.TaskQueueGuard();
        const r = g.check("write", { path: "src/index.ts", content: "anything" }, %s);
        process.stdout.write(JSON.stringify({ blocked: !!r }));
        """ % json.dumps(self.fx.root.replace("\\", "/")))
        self.assertFalse(out["blocked"])

    def test_other_tools_are_ignored(self):
        d = self.fx.task("Task_001_A", "PENDING")
        out = run_js("""
        const g = new m.TaskQueueGuard();
        let blocked = 0;
        for (const t of ["bash", "read", "web_search", "grep"])
          if (g.check(t, { path: %s + "/status.txt", content: "DONE" }, "")) blocked++;
        process.stdout.write(JSON.stringify({ blocked }));
        """ % json.dumps(d))
        self.assertEqual(out["blocked"], 0)

    def test_a_status_file_outside_the_queue_is_not_a_task_transition(self):
        """The scope tests above have no teeth on their own.

        Both were written first and both passed against a deliberately broken
        `taskDirOf` that treated every path as a task directory — because the
        paths they used could not reach a rule either way. This one can: a
        project with its own `status.txt` at the root, holding PENDING, written
        to DONE. Correctly scoped, the guard never looks at it. Wrongly scoped,
        it is an illegal transition and gets refused.
        """
        self.fx.task("Task_001_A", "IN_PROGRESS")
        root_status = os.path.join(self.fx.root, "status.txt")
        with open(root_status, "w", encoding="utf-8") as f:
            f.write("PENDING")
        out = run_js("""
        const g = new m.TaskQueueGuard();
        const r = g.check("write", { path: %s, content: "DONE" }, "");
        process.stdout.write(JSON.stringify({ blocked: !!r, reason: r ? r.reason : "" }));
        """ % json.dumps(root_status.replace("\\", "/")))
        self.assertFalse(out["blocked"],
                         "a status.txt outside 02_Task_Queue/Task_NNN_* is somebody "
                         "else's file: %s" % out["reason"])

    def test_a_normal_file_inside_a_task_package_is_fine(self):
        d = self.fx.task("Task_001_A", "IN_PROGRESS")
        out = run_js("""
        const g = new m.TaskQueueGuard();
        const r = g.check("write", { path: %s + "/output.md", content: "findings" }, "");
        process.stdout.write(JSON.stringify({ blocked: !!r }));
        """ % json.dumps(d))
        self.assertFalse(out["blocked"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestIllegalTransitions(unittest.TestCase):
    def setUp(self):
        self.fx = QueueFixture()
        self.addCleanup(self.fx.cleanup)

    def test_pending_straight_to_done_is_refused(self):
        d = self.fx.task("Task_001_A", "PENDING", retro=True)
        out = run_js("""
        const g = new m.TaskQueueGuard();
        const r = g.check("write", { path: %s + "/status.txt", content: "DONE" }, "");
        process.stdout.write(JSON.stringify({ blocked: !!r, reason: r ? r.reason : "" }));
        """ % json.dumps(d))
        self.assertTrue(out["blocked"])
        self.assertIn("PENDING", out["reason"])

    def test_the_retro_refusal_actually_carries_block_true(self):
        """Section 13a's guard, same shape as the other two closed today: the
        object literal form is never an equivalent mutant, because Pi reads the
        field. Without it the guard would keep detecting the missing retro,
        keep quoting 13a, and let DONE through."""
        d = self.fx.task("Task_001_A", "REVIEW")
        out = run_js("""
        const g = new m.TaskQueueGuard();
        const r = g.check("write", { path: %s + "/status.txt", content: "DONE" }, "");
        process.stdout.write(JSON.stringify({ block: r ? r.block : null,
                                              reason: r ? r.reason : "" }));
        """ % json.dumps(d))
        self.assertIn("retro", out["reason"])
        self.assertIs(out["block"], True)

    def test_the_dual_track_refusal_actually_carries_block_true(self):
        """Added 2026-08-08 from the mutation sweep.

        `block: true` in the self-approval refusal could be flipped to `false`
        and the whole suite stayed green: every assertion in this file reads
        `!!r`, and a refusal object with `block: false` is still truthy. Pi
        reads the field, so the guard would keep detecting that the Worker is
        approving itself, keep quoting Section 1 at the model, and let the write
        through.

        Section 1 is the protocol's one non-negotiable rule. It is worth a test
        that names the field."""
        d = self.fx.task("Task_001_A", "PENDING", retro=True)
        out = run_js("""
        const g = new m.TaskQueueGuard();
        // The guard inspects; it does not write. The file has to move for the
        // current status to change, or every later check still sees PENDING
        // and answers with the transition rule instead.
        g.check("write", { path: %(d)s + "/status.txt", content: "IN_PROGRESS" }, "");
        fs.writeFileSync(%(d)s + "/status.txt", "REVIEW");
        const r = g.check("write", { path: %(d)s + "/status.txt", content: "DONE" }, "");
        process.stdout.write(JSON.stringify({ block: r ? r.block : null,
                                              reason: r ? r.reason : "" }));
        """ % {"d": json.dumps(d)})
        self.assertIn("Section 1", out["reason"])
        self.assertIs(out["block"], True)

    def test_the_normal_path_is_allowed(self):
        d = self.fx.task("Task_001_A", "PENDING")
        out = run_js("""
        const g = new m.TaskQueueGuard();
        const p = %s + "/status.txt";
        const steps = [];
        steps.push(!!g.check("write", { path: p, content: "IN_PROGRESS" }, ""));
        fs.writeFileSync(p, "IN_PROGRESS");
        steps.push(!!g.check("write", { path: p, content: "REVIEW" }, ""));
        process.stdout.write(JSON.stringify({ steps }));
        """ % json.dumps(d))
        self.assertEqual(out["steps"], [False, False])

    def test_escalation_is_always_allowed(self):
        d = self.fx.task("Task_001_A", "PENDING")
        out = run_js("""
        const g = new m.TaskQueueGuard();
        const r = g.check("write", { path: %s + "/status.txt", content: "ESCALATED" }, "");
        process.stdout.write(JSON.stringify({ blocked: !!r }));
        """ % json.dumps(d))
        self.assertFalse(out["blocked"], "a run must always be able to stop and escalate")

    def test_an_unreadable_current_status_fails_open(self):
        """No old value means nothing to compare. Refusing on a guess is worse
        than allowing."""
        d = self.fx.task("Task_001_A", "PENDING")
        os.remove(os.path.join(d.replace("/", os.sep), "status.txt"))
        out = run_js("""
        const g = new m.TaskQueueGuard();
        const r = g.check("write", { path: %s + "/status.txt", content: "DONE" }, "");
        process.stdout.write(JSON.stringify({ blocked: !!r }));
        """ % json.dumps(d))
        self.assertFalse(out["blocked"])

    def test_an_unrecognised_token_is_refused(self):
        """REVERSED 2026-08-09, and the old assertion is quoted here rather than
        deleted: it said "an unknown token is the verifier's business, not this
        guard's" and expected the write to pass.

        There is no verifier in this loop, and a live run showed the cost. It
        claimed its task, wrote COMPLETE, then an empty string, and both were
        allowed; from then on every nextStep() read a status it could not parse,
        fell back to "claim this task", and repeated that while the model
        carried on believing it had finished. The run never reached REVIEW.

        A deliberate, written-down deferral outlived the situation that
        justified it — the other half of the scar that says undocumented
        rejections get rebuilt."""
        d = self.fx.task("Task_001_A", "PENDING")
        out = run_js("""
        const g = new m.TaskQueueGuard();
        const r = g.check("write", { path: %s + "/status.txt", content: "FINISHED" }, "");
        process.stdout.write(JSON.stringify({ blocked: !!r, block: r ? r.block : null }));
        """ % json.dumps(d))
        self.assertIs(out["block"], True)


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestOneTaskAtATime(unittest.TestCase):
    """The promise the queue exists for."""

    def setUp(self):
        self.fx = QueueFixture()
        self.addCleanup(self.fx.cleanup)

    def test_starting_a_second_task_is_refused(self):
        self.fx.task("Task_001_A", "IN_PROGRESS")
        d2 = self.fx.task("Task_002_B", "PENDING")
        out = run_js("""
        const g = new m.TaskQueueGuard();
        const r = g.check("write", { path: %s + "/status.txt", content: "IN_PROGRESS" }, "");
        process.stdout.write(JSON.stringify({ blocked: !!r, reason: r ? r.reason : "" }));
        """ % json.dumps(d2))
        self.assertTrue(out["blocked"])
        self.assertIn("Task_001_A", out["reason"], "name the task that is already open")

    def test_starting_the_only_task_is_fine(self):
        self.fx.task("Task_001_A", "DONE", retro=True)
        d2 = self.fx.task("Task_002_B", "PENDING")
        out = run_js("""
        const g = new m.TaskQueueGuard();
        const r = g.check("write", { path: %s + "/status.txt", content: "IN_PROGRESS" }, "");
        process.stdout.write(JSON.stringify({ blocked: !!r }));
        """ % json.dumps(d2))
        self.assertFalse(out["blocked"])

    def test_resuming_the_same_task_is_not_a_second_task(self):
        d = self.fx.task("Task_001_A", "IN_PROGRESS")
        out = run_js("""
        const g = new m.TaskQueueGuard();
        const r = g.check("write", { path: %s + "/status.txt", content: "IN_PROGRESS" }, "");
        process.stdout.write(JSON.stringify({ blocked: !!r }));
        """ % json.dumps(d))
        self.assertFalse(out["blocked"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestWorkerMayNotSelfApprove(unittest.TestCase):
    """Core axiom: Worker and Checker are separate roles, and a Worker must not
    approve its own output."""

    def setUp(self):
        self.fx = QueueFixture()
        self.addCleanup(self.fx.cleanup)

    def test_the_session_that_started_the_task_cannot_close_it(self):
        d = self.fx.task("Task_001_A", "PENDING", retro=True)
        out = run_js("""
        const g = new m.TaskQueueGuard();
        const p = %s + "/status.txt";
        g.check("write", { path: p, content: "IN_PROGRESS" }, "");
        fs.writeFileSync(p, "IN_PROGRESS");
        g.check("write", { path: p, content: "REVIEW" }, "");
        fs.writeFileSync(p, "REVIEW");
        const r = g.check("write", { path: p, content: "DONE" }, "");
        process.stdout.write(JSON.stringify({ blocked: !!r, reason: r ? r.reason : "" }));
        """ % json.dumps(d))
        self.assertTrue(out["blocked"])
        self.assertRegex(out["reason"], r"(?i)checker|self")

    def test_a_fresh_session_may_close_it(self):
        d = self.fx.task("Task_001_A", "REVIEW", retro=True)
        out = run_js("""
        const g = new m.TaskQueueGuard();
        const r = g.check("write", { path: %s + "/status.txt", content: "DONE" }, "");
        process.stdout.write(JSON.stringify({ blocked: !!r }));
        """ % json.dumps(d))
        self.assertFalse(out["blocked"])

    def test_reset_clears_the_worker_history(self):
        d = self.fx.task("Task_001_A", "REVIEW", retro=True)
        out = run_js("""
        const g = new m.TaskQueueGuard();
        const p = %s + "/status.txt";
        fs.writeFileSync(p, "PENDING");
        g.check("write", { path: p, content: "IN_PROGRESS" }, "");
        g.reset();
        fs.writeFileSync(p, "REVIEW");
        const r = g.check("write", { path: p, content: "DONE" }, "");
        process.stdout.write(JSON.stringify({ blocked: !!r }));
        """ % json.dumps(d))
        self.assertFalse(out["blocked"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestRetrospectiveGate(unittest.TestCase):
    """Section 13a: a mandatory retrospective before every DONE."""

    def setUp(self):
        self.fx = QueueFixture()
        self.addCleanup(self.fx.cleanup)

    def test_done_without_a_retro_is_refused(self):
        d = self.fx.task("Task_001_A", "REVIEW", retro=False)
        out = run_js("""
        const g = new m.TaskQueueGuard();
        const r = g.check("write", { path: %s + "/status.txt", content: "DONE" }, "");
        process.stdout.write(JSON.stringify({ blocked: !!r, reason: r ? r.reason : "" }));
        """ % json.dumps(d))
        self.assertTrue(out["blocked"])
        self.assertIn("retro.md", out["reason"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestWritingOutsideTheActiveTask(unittest.TestCase):
    """Section 5 permission boundary: a worker writes in its own task folder."""

    def setUp(self):
        self.fx = QueueFixture()
        self.addCleanup(self.fx.cleanup)

    def test_writing_into_another_task_is_refused(self):
        d1 = self.fx.task("Task_001_A", "IN_PROGRESS")
        d2 = self.fx.task("Task_002_B", "PENDING")
        out = run_js("""
        const g = new m.TaskQueueGuard();
        const r = g.check("write", { path: %s + "/output.md", content: "x".repeat(50) }, "");
        process.stdout.write(JSON.stringify({ blocked: !!r, reason: r ? r.reason : "" }));
        """ % json.dumps(d2))
        self.assertTrue(out["blocked"])
        self.assertIn("Task_001_A", out["reason"])

    def test_writing_into_the_active_task_is_fine(self):
        d1 = self.fx.task("Task_001_A", "IN_PROGRESS")
        self.fx.task("Task_002_B", "PENDING")
        out = run_js("""
        const g = new m.TaskQueueGuard();
        const r = g.check("write", { path: %s + "/output.md", content: "x".repeat(50) }, "");
        process.stdout.write(JSON.stringify({ blocked: !!r }));
        """ % json.dumps(d1))
        self.assertFalse(out["blocked"])

    def test_with_no_task_open_nothing_is_the_wrong_task(self):
        d = self.fx.task("Task_001_A", "PENDING")
        out = run_js("""
        const g = new m.TaskQueueGuard();
        const r = g.check("write", { path: %s + "/planning.md", content: "x".repeat(50) }, "");
        process.stdout.write(JSON.stringify({ blocked: !!r }));
        """ % json.dumps(d))
        self.assertFalse(out["blocked"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestItCannotTrapTheRun(unittest.TestCase):
    def setUp(self):
        self.fx = QueueFixture()
        self.addCleanup(self.fx.cleanup)

    def test_a_rule_refused_three_times_steps_aside(self):
        d = self.fx.task("Task_001_A", "PENDING", retro=True)
        out = run_js("""
        const g = new m.TaskQueueGuard();
        const p = %s + "/status.txt";
        let blocks = 0, allowedAfter = 0;
        for (let i = 0; i < 20; i++) {
          if (g.check("write", { path: p, content: "DONE" }, "")) blocks++;
          else if (blocks > 0) allowedAfter++;
        }
        process.stdout.write(JSON.stringify({ blocks, allowedAfter }));
        """ % json.dumps(d))
        self.assertGreater(out["allowedAfter"], 0, "the run must be able to continue")
        self.assertLessEqual(out["blocks"], 4)

    def test_unserializable_input_does_not_throw(self):
        out = run_js("""
        const g = new m.TaskQueueGuard();
        const a = {}; a.self = a;
        let threw = false;
        try { g.check("write", a, ""); } catch { threw = true; }
        process.stdout.write(JSON.stringify({ threw }));
        """)
        self.assertFalse(out["threw"])

@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestAnInvalidStatusStopsTheMachine(unittest.TestCase):
    """Measured 2026-08-09, run 2 of the CLAIM budget experiment:

        INJECT  把 status.txt 改成 IN_PROGRESS
        WRITE   status.txt <- 'IN_PROGRESS'     claimed
        WRITE   status.txt <- 'COMPLETE'        allowed
        INJECT  請認領                            the advancer no longer understands
        WRITE   status.txt <- ''                allowed
        INJECT  x2                               the same sentence again

    `checkTransition` returned null for anything outside VALID_STATUSES with
    the comment "the verifier's business" — it checked transitions BETWEEN
    valid states and never checked that the value was a state. One invalid
    write stops the machine: every later nextStep() reads a status it cannot
    parse, falls back to "claim this task", and repeats while the model
    believes it has finished. That run never reached REVIEW.

    The deferral was deliberate and written down, and there is no verifier in
    this loop. The recorded scar is that undocumented rejections get rebuilt;
    this is the other half, where a documented one outlives its reason.

    The contract is tighter than "one of five". It is: refuse exactly what
    `readStatus` would later fail to read. Lowercase parses as JSON-ish text
    and fails that read, so it has to be refused too, or the machine stops in
    the same way by a politer route."""

    def setUp(self):
        self.fx = QueueFixture()
        self.addCleanup(self.fx.cleanup)

    def _write(self, content, status="IN_PROGRESS"):
        d = self.fx.task("Task_001_A", status)
        return run_js("""
        const g = new m.TaskQueueGuard();
        const r = g.check("write", { path: %s + "/status.txt", content: %s }, "");
        process.stdout.write(JSON.stringify({ blocked: !!r, block: r ? r.block : null,
                                              reason: r ? r.reason : "" }));
        """ % (json.dumps(d), json.dumps(content)))

    def test_the_exact_value_that_broke_the_run(self):
        out = self._write("COMPLETE")
        self.assertIs(out["block"], True)

    def test_an_empty_status_is_refused(self):
        self.assertIs(self._write("")["block"], True)

    def test_lowercase_is_refused_because_readStatus_cannot_read_it(self):
        for text in ("in_progress", "Review", "done"):
            with self.subTest(text=text):
                self.assertIs(self._write(text)["block"], True)

    def test_the_refusal_names_the_values_that_work(self):
        """Refusing removes the wrong path and supplies nothing unless it is
        told to — today's recurring lesson, applied here."""
        reason = self._write("COMPLETE")["reason"]
        for name in ("PENDING", "IN_PROGRESS", "REVIEW", "DONE", "ESCALATED"):
            self.assertIn(name, reason)
        self.assertIn("COMPLETE", reason, "say what was written, not just what is allowed")

    def test_whitespace_around_a_valid_status_is_fine(self):
        # chr() rather than escapes: tenth backslash lost to the heredoc
        # in this stretch, and a trailing newline is exactly what is being
        # tested, so it cannot be written as an escape that might vanish.
        NL, CR = chr(10), chr(13)
        # REVIEW and DONE both come from IN_PROGRESS via legal transitions?
        # No — IN_PROGRESS>DONE is in ILLEGAL, so a DONE case here would be
        # measuring the transition rule instead of the whitespace handling.
        # Fixture corrected rather than the expectation.
        for text in ("IN_PROGRESS" + NL, "  REVIEW  ", "REVIEW" + CR + NL):
            with self.subTest(text=repr(text)):
                self.assertFalse(self._write(text, status="IN_PROGRESS")["blocked"],
                                 "a trailing newline is how files end")

    def test_a_write_with_no_extractable_content_still_fails_open(self):
        """`bash` writes carry no parseable content and this repo refuses to
        half-parse them (Task_004). A write whose content cannot be read must
        keep passing, or the fix would block the paths it never covered."""
        d = self.fx.task("Task_001_A", "IN_PROGRESS")
        out = run_js("""
        const g = new m.TaskQueueGuard();
        const r = g.check("write", { path: %s + "/status.txt" }, "");
        process.stdout.write(JSON.stringify({ blocked: !!r }));
        """ % json.dumps(d))
        self.assertFalse(out["blocked"])

@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestARuleRetires(unittest.TestCase):
    """From the mutation sweep: `return false` in the retirement path could be
    flipped to `return true` with nothing turning red, which would mean a rule
    that never stands aside.

    The protocol allows the exception explicitly (for_agents.md: unless the
    higher-level tool is entirely unavailable), and this repo's own measurement
    is blunter — a wall with no door gets the guard switched off, and a guard
    that is off protects nothing."""

    def setUp(self):
        self.fx = QueueFixture()
        self.addCleanup(self.fx.cleanup)

    def test_the_same_rule_stands_aside_after_its_limit(self):
        d = self.fx.task("Task_001_A", "PENDING", retro=True)
        out = run_js("""
        const g = new m.TaskQueueGuard();
        const verdicts = [];
        for (let i = 0; i < m.MAX_BLOCKS_PER_RULE + 2; i++) {
          const r = g.check("write", { path: %s + "/status.txt", content: "DONE" }, "");
          verdicts.push(r ? "blocked" : "allowed");
        }
        process.stdout.write(JSON.stringify({ verdicts, limit: m.MAX_BLOCKS_PER_RULE }));
        """ % json.dumps(d))
        self.assertEqual(out["verdicts"][0], "blocked")
        self.assertIn("allowed", out["verdicts"],
                      "a rule that never retires is a wall with no door")
        self.assertEqual(out["verdicts"].count("blocked"), out["limit"])



if __name__ == "__main__":
    unittest.main()
