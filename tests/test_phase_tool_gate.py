"""Plan first, enforced where it can actually be enforced.

The owner's complaint, twice, verbatim: Pi "還是會直接開始搜尋網頁,然後煞有其事的
搜尋可能十幾次,然後給我一個結論" — and then the correction that matters:
"他多搜幾次是好的阿?越多越好不是? 我抱怨的是他沒有先規劃就開始."

So this gate does not restrain searching. It restrains *starting without
claiming and planning*. Measured 2026-08-06 in the research-shaped run: the
first eleven actions were six searches and three page opens, the first advancer
injection landed after them, and the task's status never left PENDING. Our own
verdict from that measurement says the advancer speaks at `turn_end` and cannot
catch a turn that already searched — only `tool_call` can.

`research/auto-pi` implements exactly that (`extensions/loop.ts:1020`): a phase
tool allowlist enforced at `tool_call`, where PLAN is read-only. What is NOT
copied is its phase model — ours is derived from C.A.S.E. protocol state, because
a second state machine running beside the protocol would fight it.

  PENDING, nothing claimed   -> CLAIM phase: research tools refused, reads fine,
                                writing status.txt fine. Claiming costs one write.
  IN_PROGRESS, no plan yet   -> PLAN phase: deliverables refused, research tools
                                WIDE OPEN — planning is exactly when you look
                                things up.
  plan present               -> nothing refused.

And a layer taken from OmniHeal's 3-Strike: the second refusal must say something
different from the first — offer another way — before the third stands aside. A
guard that repeats itself verbatim and then gives up has taught nothing.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(ROOT, "pi-extensions", "case-bridge", "phase-gate.ts")


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
    driver = os.path.join(ROOT, "tests", ".tmp_phasegate_driver.mjs")
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


class Queue:
    """A C.A.S.E. task package on disk, because the phase is read from files."""

    def __init__(self, status="PENDING", planning=None, name="Task_001_probe"):
        self.root = tempfile.mkdtemp(prefix="phasegate-")
        self.dir = os.path.join(self.root, "02_Task_Queue")
        self.task = os.path.join(self.dir, name)
        os.makedirs(self.task)
        self.write("status.txt", status)
        self.write("role.md", "role")
        self.write("recipe.md", "recipe")
        if planning is not None:
            self.write("planning.md", planning)

    def write(self, name, content):
        with open(os.path.join(self.task, name), "w", encoding="utf-8") as f:
            f.write(content)

    @property
    def queue_dir(self):
        return self.dir.replace("\\", "/")

    def cleanup(self):
        shutil.rmtree(self.root, ignore_errors=True)


def gate(queue_dir, tool, input_obj, times=1):
    """`times` counts TURNS, one call each.

    It counted calls until 2026-08-08, which is the unit the exit ramp was
    measured to have wrong: the model issues five parallel calls per turn, so a
    call-counted budget was spent inside the first batch before any refusal
    reached it. These tests always meant turns — the live session they came from
    showed refusals across separate turns — so the loop now ends each turn the
    way the bridge does."""
    return run_js("""
    const g = new m.PhaseGate();
    const out = [];
    for (let i = 0; i < %d; i++) {
      const r = g.check(%s, %s, %s);
      out.push(r ? r.reason : null);
      g.turnEnded();
    }
    process.stdout.write(JSON.stringify({ reasons: out,
                                          phase: m.phaseOf(%s) }));
    """ % (times, json.dumps(queue_dir), json.dumps(tool), json.dumps(input_obj),
           json.dumps(queue_dir)))


def assert_refused_by(case, reason, phase):
    """A refusal exists AND it is the one this test means.

    `assertIsNotNone(reason)` passes for ANY refusal, including the wrong guard's
    or the wrong phase's. Three checks-that-cannot-fail turned up in one day
    (2026-08-10) and this is their shape: asserting that something was blocked
    without asserting why. MECE Round 12 ranked fixing it above new features.

    The gate's two phases are distinguishable in the text it emits, so the test
    can say which one it expects instead of accepting either."""
    case.assertIsNotNone(reason, "expected a %s refusal, got none" % phase)
    marker = "階段閘(%s" % phase
    case.assertIn(marker, reason,
                  "expected a %s refusal, got: %s" % (phase, reason[:90]))


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestClaimPhase(unittest.TestCase):
    """PENDING means nobody has taken the task. One write fixes that."""

    def setUp(self):
        self.q = Queue(status="PENDING")
        self.addCleanup(self.q.cleanup)

    def test_the_first_search_of_the_research_run_is_refused(self):
        out = gate(self.q.queue_dir, "web_search", {"query": "harness completion guards"})
        self.assertIsNotNone(out["reasons"][0])
        self.assertIn("IN_PROGRESS", out["reasons"][0])

    def test_the_refusal_says_searching_is_not_the_problem(self):
        """A run that learns "this harness dislikes searching" is a run that
        stops looking things up. The reason has to say the opposite."""
        out = gate(self.q.queue_dir, "web_search", {"query": "x"})
        self.assertRegex(out["reasons"][0], r"認領|一次寫入|之後.*全開|不是.*搜")

    def test_reading_and_searching_the_repo_are_untouched(self):
        for tool, args in (("read", {"path": "a.md"}), ("grep", {"pattern": "x"}),
                           ("ls", {"path": "."}), ("find", {"pattern": "*.md"})):
            with self.subTest(tool=tool):
                out = gate(self.q.queue_dir, tool, args)
                self.assertIsNone(out["reasons"][0])

    def test_claiming_the_task_is_allowed(self):
        out = gate(self.q.queue_dir, "write",
                   {"path": self.q.task.replace("\\", "/") + "/status.txt",
                    "content": "IN_PROGRESS"})
        self.assertIsNone(out["reasons"][0])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestPlanPhase(unittest.TestCase):
    """Claimed but unplanned: deliverables wait, research does not."""

    def setUp(self):
        self.q = Queue(status="IN_PROGRESS")
        self.addCleanup(self.q.cleanup)

    def test_writing_the_deliverable_before_a_plan_is_refused(self):
        out = gate(self.q.queue_dir, "write",
                   {"path": self.q.task.replace("\\", "/") + "/output.md",
                    "content": "findings"})
        self.assertIsNotNone(out["reasons"][0])
        self.assertIn("planning.md", out["reasons"][0])

    def test_writing_the_plan_is_the_way_out(self):
        out = gate(self.q.queue_dir, "write",
                   {"path": self.q.task.replace("\\", "/") + "/planning.md",
                    "content": "## Self-Review"})
        self.assertIsNone(out["reasons"][0])

    def test_searching_is_wide_open_here(self):
        """Planning is exactly when you look things up. The owner said so."""
        out = gate(self.q.queue_dir, "web_search", {"query": "x"})
        self.assertIsNone(out["reasons"][0])

    def test_bash_written_deliverables_count_too(self):
        cmd = 'cat > "%s/output.md" << EOF\nfindings\nEOF' % self.q.task.replace("\\", "/")
        out = gate(self.q.queue_dir, "bash", {"command": cmd})
        assert_refused_by(self, out["reasons"][0], "PLAN")

    def test_a_plan_with_self_review_opens_everything(self):
        self.q.write("planning.md", "# plan\n\n## Self-Review\nchecked")
        out = gate(self.q.queue_dir, "write",
                   {"path": self.q.task.replace("\\", "/") + "/output.md",
                    "content": "findings"})
        self.assertIsNone(out["reasons"][0])
        self.assertEqual(out["phase"], "open")


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestItStandsAsideButOffersAnotherWayFirst(unittest.TestCase):
    """OmniHeal's 3-Strike has a layer ours lacked: try another way before
    giving up. A guard that repeats itself and then folds taught nothing."""

    def setUp(self):
        self.q = Queue(status="PENDING")
        self.addCleanup(self.q.cleanup)

    def test_the_second_refusal_is_not_the_first_one_repeated(self):
        out = gate(self.q.queue_dir, "web_search", {"query": "x"}, times=2)
        assert_refused_by(self, out["reasons"][0], "CLAIM")
        assert_refused_by(self, out["reasons"][1], "CLAIM")
        self.assertNotEqual(out["reasons"][0], out["reasons"][1],
                            "the second refusal must offer another way, not repeat")

    def test_it_retires_eventually(self):
        """Was "the third call goes through". The first live run showed two
        refusals were cheaper to absorb than one write, so the count moved to
        four; the property that matters — it does retire — is asserted here and
        the cost argument in TestWhatTheFirstLiveRunShowed."""
        out = gate(self.q.queue_dir, "web_search", {"query": "x"}, times=12)
        self.assertIsNone(out["reasons"][-1], "a gate that cannot retire deadlocks")


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestWhatTheFirstLiveRunShowed(unittest.TestCase):
    """The gate fired and the run ignored it. Both holes are measured, not
    imagined — session t016-live, 2026-08-06:

      * it refused `web_search` twice, then `web_open` twice, then retired and
        the run carried on searching. Two refusals per tool is cheaper to wait
        out than to satisfy;
      * it wrote its 6,358-byte report to `research/…report.md`, OUTSIDE the
        task package, where the deliverable rule has no opinion at all.

    Status never left PENDING. A threshold defines the shape of the evasion, and
    this is the shape it took on the first try."""

    def setUp(self):
        self.q = Queue(status="PENDING")
        self.addCleanup(self.q.cleanup)

    def test_writing_a_report_anywhere_before_claiming_is_refused(self):
        """The evasion was not subtle: write the deliverable somewhere else."""
        out = gate(self.q.queue_dir, "write",
                   {"path": "research/anti-hallucination-harness-report.md",
                    "content": "# findings\n" * 200})
        self.assertIsNotNone(out["reasons"][0])
        self.assertIn("IN_PROGRESS", out["reasons"][0])

    def test_claiming_is_still_the_one_write_that_gets_through(self):
        out = gate(self.q.queue_dir, "write",
                   {"path": self.q.task.replace("\\", "/") + "/status.txt",
                    "content": "IN_PROGRESS"})
        self.assertIsNone(out["reasons"][0])

    def test_waiting_it_out_costs_more_than_complying(self):
        """Two refusals was cheaper to absorb than one write. Four, each saying
        something new, is not — and it still retires, because a guard that can
        deadlock an unfamiliar project gets switched off."""
        out = gate(self.q.queue_dir, "web_search", {"query": "x"}, times=12)
        refused = [r for r in out["reasons"] if r]
        self.assertGreaterEqual(len(refused), 8)
        # Distinctness is asserted over the texts that carry NEW information —
        # the first three escalate, the middle repeats the third, and the last
        # is reserved for the turn that really is last. Demanding all eight be
        # different would demand eight things to say; demanding none repeat a
        # false promise is the property that matters.
        self.assertEqual(refused.count(refused[-1]), 1,
                         "the text that announces it is the last block must be "
                         "used once, on the turn that really is last")
        self.assertGreaterEqual(len(set(refused)), 4,
                                "the escalation must still say new things")
        self.assertIsNone(out["reasons"][-1], "it must still retire")


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestFailOpen(unittest.TestCase):
    """A gate that misfires in an unfamiliar project gets switched off within a
    day, and then it protects nothing at all."""

    def test_no_queue_at_all(self):
        d = tempfile.mkdtemp(prefix="phasegate-empty-")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        out = gate(os.path.join(d, "02_Task_Queue").replace("\\", "/"),
                   "web_search", {"query": "x"})
        self.assertIsNone(out["reasons"][0])

    def test_an_unrecognised_status(self):
        q = Queue(status="SOMETHING_ELSE")
        self.addCleanup(q.cleanup)
        out = gate(q.queue_dir, "web_search", {"query": "x"})
        self.assertIsNone(out["reasons"][0])

    def test_two_open_tasks_means_it_says_nothing(self):
        """Needs a PENDING task alongside the two open ones, or the branch is
        unobservable: without a PENDING task the function returns "open" for
        another reason and deleting the guard changes nothing. The first version
        of this test was that unobservable one — it passed with the check
        removed."""
        q = Queue(status="IN_PROGRESS")
        self.addCleanup(q.cleanup)
        for name, status in (("Task_002_other", "IN_PROGRESS"),
                             ("Task_003_waiting", "PENDING")):
            d = os.path.join(q.dir, name)
            os.makedirs(d)
            with open(os.path.join(d, "status.txt"), "w", encoding="utf-8") as f:
                f.write(status)
        out = gate(q.queue_dir, "web_search", {"query": "x"})
        self.assertIsNone(out["reasons"][0],
                          "two open tasks: another guard reports that, this one guesses nothing")
        self.assertEqual(out["phase"], "open")

    def test_writes_outside_the_task_package_are_not_this_gate_s_business(self):
        q = Queue(status="IN_PROGRESS")
        self.addCleanup(q.cleanup)
        out = gate(q.queue_dir, "write", {"path": "src/index.ts", "content": "x"})
        self.assertIsNone(out["reasons"][0])

@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheExitRampCountsTurnsNotCalls(unittest.TestCase):
    """Measured 2026-08-08 on a real research run, and the fixture below is that
    run's shape rather than an invented one.

    The model issues FIVE parallel web_search calls per turn:

        turn 1: 5 calls [web_search x 5]
        turn 2: 5 calls [web_search x 5]
        turn 3: 5 calls [web_search x 5]

    The exit ramp let a rule refuse four times and then stepped aside, so the
    entire budget was spent inside the first batch — before a single refusal had
    come back to the model. The refusal text is good and names the next action;
    nothing read it in time.

    The ramp exists so a model is not stuck against one wall forever. That
    intent is about turns the model could have learned from, not about raw
    calls, and 2026-08-06 got the same unit wrong from the other direction
    (exit at two, while claiming cost one write, so absorbing was cheaper than
    complying)."""

    def setUp(self):
        self.q = Queue(status="PENDING")
        self.addCleanup(self.q.cleanup)

    def _burst(self, turns, per_turn):
        return run_js("""
        const g = new m.PhaseGate();
        const rows = [];
        for (let t = 0; t < %d; t++) {
          const turn = [];
          for (let i = 0; i < %d; i++) {
            const r = g.check(%s, "web_search", { query: "x" + i });
            turn.push(r ? r.reason : null);
          }
          rows.push(turn);
          g.turnEnded();
        }
        process.stdout.write(JSON.stringify({ rows }));
        """ % (turns, per_turn, json.dumps(self.q.dir)))["rows"]

    def test_one_parallel_batch_does_not_spend_the_whole_budget(self):
        rows = self._burst(turns=1, per_turn=5)
        self.assertTrue(all(r is not None for r in rows[0]),
                        "a batch issued before any refusal arrived must be "
                        "refused in full, not partly waved through")

    def test_a_turn_speaks_with_one_voice(self):
        """Five different escalating texts inside one batch is four wasted
        escalations: the model chose all five before reading any of them."""
        self.assertEqual(len(set(self._burst(turns=1, per_turn=5)[0])), 1)

    def test_the_text_escalates_between_turns(self):
        rows = self._burst(turns=3, per_turn=2)
        firsts = [r[0] for r in rows]
        self.assertEqual(len(set(firsts)), 3, "each turn must say something new")

    def test_it_still_gets_out_of_the_way(self):
        """Bounded is the point. After MAX_REFUSAL_TURNS turns of refusing the
        same rule, the model is not learning and the wall has to come down."""
        rows = self._burst(turns=14, per_turn=2)
        self.assertTrue(any(all(c is None for c in row) for row in rows),
                        "the ramp must still end")

@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheBridgeEndsTheTurn(unittest.TestCase):
    """A budget that never advances is a wall with no door — the opposite
    failure, and just as effective at getting a guard switched off."""

    def test_index_calls_turn_ended(self):
        with open(os.path.join(ROOT, "pi-extensions", "case-bridge", "index.ts"),
                  encoding="utf-8") as f:
            body = f.read().split('pi.on("turn_end"', 1)[1]
        self.assertIn("phaseGate.turnEnded()", body[:900])

    def test_it_runs_before_the_early_returns(self):
        """The handler returns early when the advancer is off or the project is
        not C.A.S.E. If the turn is ended after those, the gate refuses forever
        on every machine with the flag off — which is every machine today."""
        with open(os.path.join(ROOT, "pi-extensions", "case-bridge", "index.ts"),
                  encoding="utf-8") as f:
            body = f.read().split('pi.on("turn_end"', 1)[1][:1400]
        # A statement, not the word: the comment above the call says "early
        # return", and matching bare text made this assertion fail against
        # correct code.
        first_return = re.search(r"^\s*(if \(.*\) )?return\b", body, re.M)
        self.assertIsNotNone(first_return, "no early return to be ahead of")
        self.assertLess(body.index("phaseGate.turnEnded()"), first_return.start())

@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheRefusalsActuallyCarryBlockTrue(unittest.TestCase):
    """Both `block: true` object literals in this gate survived the mutation
    sweep: every assertion above reads the reason, and a refusal with
    `block: false` still has one. Pi reads the field, so the gate would keep
    deriving the phase, keep writing the text that names the next action, and
    let the call through.

    Same shape closed in task-queue-guard and loop-detect on 2026-08-08. Third
    time, so it is a class and not an incident."""

    def test_the_claim_refusal_blocks(self):
        q = Queue(status="PENDING")
        self.addCleanup(q.cleanup)
        out = run_js("""
        const g = new m.PhaseGate();
        const r = g.check(%s, "web_search", { query: "x" });
        process.stdout.write(JSON.stringify({ block: r ? r.block : null }));
        """ % json.dumps(q.dir))
        self.assertIs(out["block"], True)

    def test_the_plan_refusal_blocks(self):
        # chr(10), not an escape: seventh backslash lost to the heredoc today.
        q = Queue(status="IN_PROGRESS",
                  planning="# Plan" + chr(10) + "no self review" + chr(10))
        self.addCleanup(q.cleanup)
        out = run_js("""
        const g = new m.PhaseGate();
        const r = g.check(%s, "write", { path: %s });
        process.stdout.write(JSON.stringify({ block: r ? r.block : null }));
        """ % (json.dumps(q.dir), json.dumps(os.path.join(q.task, "output.md").replace("\\", "/"))))
        self.assertIs(out["block"], True)

@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheBudgetBelongsToThePhaseNotTheTool(unittest.TestCase):
    """Measured 2026-08-08, the run after the turn-based ramp landed:

        turn 1-3  web_search  refused, texts 第一次 / 第二次 / 第三次
        turn 4    web_open    refused, text 第一次 AGAIN
        turn 5    web_search  refused, 最後一次

    The key was `${phase}:${toolName}`, so every research tool carried its own
    four turns and rotating tools bought a fresh budget with the escalation
    restarted. Four research tools is up to sixteen turns of refusals — which is
    where the model got enough evidence to conclude the tools were simply
    unavailable, and then stopped searching for the rest of the run even after
    the phase opened.

    The refusals are about the phase. `web_open` before claiming is the same
    mistake as `web_search` before claiming, and telling the model "第一次" for
    the second one is a lie about how long this has been going on."""

    def setUp(self):
        self.q = Queue(status="PENDING")
        self.addCleanup(self.q.cleanup)

    def _mixed(self, tools):
        return run_js("""
        const g = new m.PhaseGate();
        const out = [];
        for (const t of %s) {
          const r = g.check(%s, t, { query: "x" });
          out.push(r ? r.reason : null);
          g.turnEnded();
        }
        process.stdout.write(JSON.stringify({ out }));
        """ % (json.dumps(tools), json.dumps(self.q.queue_dir)))["out"]

    def test_switching_tools_does_not_restart_the_escalation(self):
        out = self._mixed(["web_search", "web_search", "web_open", "web_search"])
        said = [r for r in out if r]
        # The property is "no restart", not "all different". Since the budget
        # became eight while there are four texts, the middle turns repeat the
        # third — that is holding position, not starting over. What must never
        # happen is the opening text returning, which is what a per-tool budget
        # did: web_open arrived and was told "第一次" after web_search had
        # already been refused three times.
        self.assertEqual(said.count(said[0]), 1,
                         "the opening refusal must never be said twice — that is "
                         "the escalation restarting")
        self.assertGreaterEqual(len(set(said)), 3,
                                "switching tools must not stall the escalation either")

    def test_the_budget_is_spent_across_tools_not_per_tool(self):
        """Six turns rotating four tools. With a per-tool budget none of them
        would have reached its limit and all six would be refused."""
        out = self._mixed(["web_search", "web_open"] * 6)
        self.assertIn(None, out, "the ramp must end for the phase, not per tool")
        self.assertEqual(len([r for r in out if r]), 8)

    def test_a_different_phase_keeps_its_own_budget(self):
        """CLAIM and PLAN refuse different mistakes, so spending one must not
        spend the other."""
        q = Queue(status="IN_PROGRESS")
        self.addCleanup(q.cleanup)
        out = run_js("""
        const g = new m.PhaseGate();
        const claimQ = %s, planQ = %s;
        for (let i = 0; i < 4; i++) { g.check(claimQ, "web_search", { query: "x" }); g.turnEnded(); }
        const r = g.check(planQ, "write", { path: %s });
        process.stdout.write(JSON.stringify({ planRefused: !!r }));
        """ % (json.dumps(self.q.queue_dir), json.dumps(q.queue_dir),
               json.dumps(os.path.join(q.task, "output.md").replace("\\", "/"))))
        self.assertTrue(out["planRefused"])

@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestThePlanRefusalEscalatesToo(unittest.TestCase):
    """From the mutation sweep. `planFirst(seen > 0, name)` had its 0 shifted to
    1 and nothing turned red — every PLAN test refused once and stopped, so the
    second wording was never read.

    It is the same lesson OmniHeal's layered 3-Strike encodes and the same one
    the CLAIM texts already follow: a guard that repeats itself verbatim has
    taught nothing, and the model that gave up on searching had seen exactly
    that kind of repetition."""

    def setUp(self):
        self.q = Queue(status="IN_PROGRESS")
        self.addCleanup(self.q.cleanup)

    def test_the_second_plan_refusal_says_something_new(self):
        out = gate(self.q.queue_dir, "write",
                   {"path": self.q.task.replace("\\", "/") + "/output.md",
                    "content": "findings"}, times=2)
        first, second = out["reasons"][0], out["reasons"][1]
        assert_refused_by(self, first, "PLAN")
        assert_refused_by(self, second, "PLAN")
        self.assertNotEqual(first, second)

@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheBudgetCanBeTightenedPerProject(unittest.TestCase):
    """So an experiment lives in its fixture instead of in shipped code. The
    2026-08-09 budget attempt edited the constant and depended on remembering
    to revert it; it was reverted, and remembering is still not a mechanism."""

    def _refusals(self, local=None, turns=14):
        q = Queue(status="PENDING")
        self.addCleanup(q.cleanup)
        if local is not None:
            with open(os.path.join(q.root, ".pi-harness.json"), "w", encoding="utf-8") as f:
                json.dump(local, f)
        out = gate(q.queue_dir, "web_search", {"query": "x"}, times=turns)
        return len([r for r in out["reasons"] if r])

    def test_the_default_stands_when_the_project_says_nothing(self):
        """8 since 2026-08-09: measured 2/2 runs reaching REVIEW with zero
        successful searches before claiming and research resuming after."""
        self.assertEqual(self._refusals(), 8)

    def test_a_project_may_raise_it(self):
        self.assertEqual(self._refusals({"caseClaimRefusalTurns": 12}), 12)

    def test_a_project_may_not_lower_it(self):
        """Setting 1 would switch the gate off through the config door."""
        self.assertEqual(self._refusals({"caseClaimRefusalTurns": 1}), 8)



if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestNoRefusalPromisesWhatItCannotKeep(unittest.TestCase):
    """A guard that says "I will not block next time" and then blocks seven more
    times is training the model to ignore every guard here.

    Measured 2026-08-10, session 019fe880: the second rung said 下一次我不會再擋
    and the gate refused seven more times after it. An earlier fix had removed
    the same false promise from the FOURTH rung and left it in the second — one
    instance of a class repaired, another left standing.

    The same run also landed on rung 3 for turns 3 through 7, byte-identical
    every time. These tests are behavioural rather than textual for that reason:
    what matters is what a sequence of refusals actually says, not how the
    strings are spelled in the source."""

    def setUp(self):
        self.q = Queue(status="PENDING", name="Task_001_Inventory")
        self.addCleanup(self.q.cleanup)
        with open(MOD, encoding="utf-8") as f:
            self.src = f.read()

    def ladder(self, turns=8):
        """The refusal text of each turn of a full budget, in order."""
        out = gate(self.q.queue_dir, "web_search", {"query": "x"}, times=turns)
        return [r for r in out["reasons"] if r]

    def test_no_rung_promises_it_will_stop_blocking(self):
        self.assertNotIn("下一次我不會再擋", self.src)

    def test_only_the_final_refusal_calls_itself_the_last(self):
        texts = self.ladder()
        claiming = [i for i, t in enumerate(texts) if "最後一次" in t]
        self.assertEqual(claiming, [len(texts) - 1],
                         "refusals %s claim to be the last, of %d"
                         % (claiming, len(texts)))

    def test_no_two_consecutive_refusals_are_identical(self):
        """Five verbatim repeats taught nothing five times. The rung that used
        to repeat now prints the queue it can see, and counts, so consecutive
        refusals differ by their own content."""
        texts = self.ladder()
        dupes = [i for i in range(1, len(texts)) if texts[i] == texts[i - 1]]
        self.assertEqual(dupes, [], "refusals %s repeat the one before them" % dupes)

    def test_the_middle_rungs_show_the_real_queue_path(self):
        """The live failure was a path resolved against the harness install
        while the gate recited a path SHAPE. It has the queue directory in hand;
        printing it is the thing that run actually lacked."""
        named = [t for t in self.ladder()
                 if "Task_001_Inventory" in t and "status.txt" in t]
        self.assertTrue(named, "no refusal named the actual task and file to write")

    def test_the_first_refusal_stays_short(self):
        """The listing belongs to the rung that repeats, not to the opening one:
        a wall of paths on the first refusal buries the one sentence explaining
        what the gate is about."""
        self.assertNotIn("Task_001_Inventory", self.ladder()[0])

    def test_a_long_queue_is_truncated_and_says_so(self):
        """The listing is capped so one refusal does not become a directory
        dump, and the cap has to be visible: a silently clipped list reads as a
        complete one, and "my task is not in the list" is then a wrong
        conclusion the model would act on."""
        for i in range(2, 9):                      # 8 PENDING tasks in total
            extra = os.path.join(self.q.dir, "Task_%03d_extra" % i)
            os.makedirs(extra)
            with open(os.path.join(extra, "status.txt"), "w", encoding="utf-8") as f:
                f.write("PENDING")
        listing = [t for t in self.ladder() if "Task_" in t][0]
        shown = listing.count("status.txt")
        self.assertEqual(shown, 5, "expected 5 tasks listed, got %d" % shown)
        self.assertIn("另外還有 3 個", listing)


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestFailsOpenOnWhatItCannotRecognise(unittest.TestCase):
    """The module's own docstring promises "fails open on anything it does not
    recognise", and nothing tested that promise.

    The mutation sweep found it: three guard clauses could be inverted with no
    test noticing, and checking them by hand showed they were not equivalent —
    they were unreached. A precondition that only ever sees well-formed input is
    a precondition nobody has verified, and the surrounding code is one caller
    away from depending on it."""

    def setUp(self):
        self.q = Queue(status="PENDING")
        self.addCleanup(self.q.cleanup)

    def phase(self, value):
        return run_js("process.stdout.write(JSON.stringify(m.phaseOf(%s)));"
                      % json.dumps(value))

    def test_a_non_string_queue_is_open(self):
        for bad in (None, 5, {}, []):
            with self.subTest(value=bad):
                self.assertEqual(self.phase(bad), "open")

    def test_an_empty_or_missing_queue_is_open(self):
        self.assertEqual(self.phase(""), "open")
        self.assertEqual(self.phase("/definitely/missing/queue"), "open")

    def test_check_refuses_nothing_for_a_non_string_queue(self):
        for bad in (None, 5, {}, []):
            with self.subTest(value=bad):
                out = run_js("""
                const g = new m.PhaseGate();
                process.stdout.write(JSON.stringify(
                  g.check(%s, "web_search", { query: "x" })));
                """ % json.dumps(bad))
                self.assertIsNone(out)

    def test_a_write_with_a_non_string_path_is_not_treated_as_a_write(self):
        """`{ path: 5 }` must not become a write target. Reading it as one would
        have the gate refuse a call whose destination it cannot even name."""
        for bad in (5, None, "", {}):
            with self.subTest(path=bad):
                out = gate(self.q.queue_dir, "write", {"path": bad, "content": "x"})
                self.assertIsNone(out["reasons"][0])

    def test_a_task_named_by_a_relative_path_is_recognised(self):
        """The task is identified by its folder name as well as by its full path.

        This replaces `test_a_deliverable_written_to_the_wrong_root_is_still
        _recognised`, written 2026-08-10 on the strength of a mutation survivor,
        which asserted that a deliverable under a DIFFERENT root must still be
        refused here. Session 019fe912 showed that to be exactly backwards: the
        gate refusing those calls is what kept the containment guard — the one
        that knows the run is in the wrong project — from ever speaking.

        The folder-name half of taskOf is still needed, and this is what it is
        actually for: a relative path shares no absolute prefix with the queue."""
        q = Queue(status="IN_PROGRESS")
        self.addCleanup(q.cleanup)
        out = gate(q.queue_dir, "write",
                   {"path": "02_Task_Queue/Task_001_probe/output.md",
                    "content": "findings"})
        self.assertIsNotNone(out["reasons"][0],
                             "a relative deliverable path was not recognised")
        self.assertIn("planning.md", out["reasons"][0])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestItYieldsToTheGuardWithTheBetterComplaint(unittest.TestCase):
    """Only one handler may block a `tool_call`, so whoever refuses first is the
    only voice the model hears.

    Session 019fe912: a run resolved "this project" as the harness install,
    worked there for 25 calls, and tried three times to write into it. The phase
    gate blocked all three and said "claim a task first" — true, and the wrong
    thing to say. Containment, which knows the target is in another project and
    hands back the corrected path, never got a turn. The run followed the advice
    it was given, inside the wrong project, until it ran out.

    Standing down lets nothing through: containment refuses exactly the calls
    declined here."""

    def setUp(self):
        self.q = Queue(status="PENDING")
        self.addCleanup(self.q.cleanup)
        # A path that really is outside on THIS platform.
        #
        # The first version hard-coded `D:/some/other/checkout/...`. On Linux
        # that is a RELATIVE path, so it resolved inside the project, nothing
        # escaped, and the gate was right to refuse — the tests failed in CI
        # while the code was correct. "Green on my machine" is the first rule in
        # CLAUDE.md and this broke it in the most literal way available.
        # Absolute on both platforms and scratch on neither: a temp dir would be
        # `/tmp/...` on Linux, which containment deliberately ALLOWS, so it would
        # not stand for "another project". Nothing is created — the gate only
        # does path arithmetic.
        self.outside = os.path.abspath(os.sep + "elsewhere-not-this-project"
                                       ).replace("\\", "/")

    def test_claim_phase_yields_on_a_write_to_another_project(self):
        out = gate(self.q.queue_dir, "write",
                   {"path": self.outside + "/wiki/module-index.md",
                    "content": "x"})
        self.assertIsNone(out["reasons"][0],
                          "the gate answered a complaint that is not its own")

    def test_plan_phase_yields_on_a_write_to_another_project(self):
        q = Queue(status="IN_PROGRESS")
        self.addCleanup(q.cleanup)
        out = gate(q.queue_dir, "write",
                   {"path": self.outside + "/02_Task_Queue/Task_001_probe/output.md",
                    "content": "x"})
        self.assertIsNone(out["reasons"][0])

    def test_a_bash_write_to_another_project_also_yields(self):
        out = gate(self.q.queue_dir, "bash",
                   {"command": 'mkdir -p "%s/wiki" && echo x > "%s/wiki/a.md"'
                                % (self.outside, self.outside)})
        self.assertIsNone(out["reasons"][0])

    def test_a_write_inside_the_project_is_still_refused(self):
        """The yield is narrow. A deliverable in this project during CLAIM is
        still the gate's own business."""
        out = gate(self.q.queue_dir, "write",
                   {"path": self.q.task.replace("\\", "/") + "/output.md",
                    "content": "x"})
        assert_refused_by(self, out["reasons"][0], "CLAIM")

    def test_a_mixed_call_is_still_refused(self):
        """One target inside the project is enough to keep the complaint. Only
        when EVERY write escapes does someone else have the better one."""
        inside = self.q.task.replace("\\", "/") + "/output.md"
        out = gate(self.q.queue_dir, "bash",
                   {"command": 'echo a > "%s" && echo b > "%s/x.md"'
                                % (inside, self.outside)})
        assert_refused_by(self, out["reasons"][0], "CLAIM")

    def test_research_tools_are_unaffected(self):
        """The yield is about write targets. A premature search has no target
        and is still the gate's business."""
        out = gate(self.q.queue_dir, "web_search", {"query": "x"})
        assert_refused_by(self, out["reasons"][0], "CLAIM")

    def test_a_windows_drive_path_escapes_on_every_platform(self):
        """The two guards must agree about what "absolute" means.

        `bash-containment.escapesCwd` has always tested `/^[A-Za-z]:[\/]/`, so a
        `D:/...` target reads as absolute even off Windows. This one did not, so
        on Linux the same path resolved INSIDE the project and the gate said "not
        escaping" while containment said the opposite. CI caught it as a red test
        on 2026-08-10 and the first fix only corrected the fixture — the
        disagreement in the production code survived that round.

        Written with a literal drive letter on purpose: the point is the path
        that is absolute on one platform and not the other.

        HONEST LIMIT: this test cannot fail on Windows. There `isAbsolute("D:/x")`
        is already true, so deleting the drive-letter test changes nothing local.
        Its teeth are in CI, on Linux — which is also where the defect lived. A
        deliberate break was attempted here and could not be made to turn red;
        that is recorded rather than glossed, because "I broke it and it went
        red" is the evidence this repo runs on and it is not available here."""
        out = gate(self.q.queue_dir, "write",
                   {"path": "D:/definitely-another-checkout/wiki/x.md",
                    "content": "x"})
        self.assertIsNone(out["reasons"][0],
                          "a drive-letter path was treated as inside the project")

    def test_a_posix_absolute_path_escapes_on_every_platform(self):
        out = gate(self.q.queue_dir, "write",
                   {"path": "/definitely-another-checkout/wiki/x.md",
                    "content": "x"})
        self.assertIsNone(out["reasons"][0])

