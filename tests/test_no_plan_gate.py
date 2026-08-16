"""The owner's actual complaint, and the case the planning bridge never handled.

「我抱怨的是他沒有先規劃就開始」. Measured 2026-08-16 with
`scripts/report-plan-order.py --all`, over 41 real sessions that searched at
least once:

    plan-first     5   12.2%
    search-first   2    4.9%
    no-plan       34   82.9%
    sessions with 20+ tool calls and no plan file: 11 of 18

`planning-with-files-bridge` is named after this and could not touch it. Every
handler it had opened with `if (!hasActivePlan(cwd) && !hasPlanningDir(cwd))
return;` or `if (!hasAnyPlan(cwd)) return;` — before_agent_start, tool_result
and turn_end alike. It helped sessions that already plan. Nobody noticed for
weeks because every check asked whether the injection was DELIVERED, never
whether it reached the case the bridge exists for.

Why the gate refuses a write rather than advising or blocking searches is argued
in no-plan-gate.ts and rests on two measurements this repo already paid for: a
routing note reshaped three ways was ignored 3/3, and the phase gate — which
refused SEARCHES — took premature searches from 15 to 0 and real research from
15 to 0 in the same run. The citation gate refused the DELIVERABLE and worked.
This copies the citation gate.

These tests drive the gate directly. Whether it changes the 82.9% is NOT
established here and must not be claimed from a green suite; only accumulated
real sessions can say, and the trigger condition is recorded in PROGRESS.md.
"""

import json
import os
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import sys as _sys
_sys.path.insert(0, os.path.join(ROOT, "tests"))
from _scratch import scratch  # noqa: E402

MOD = os.path.join(ROOT, "pi-extensions", "planning-with-files-bridge", "no-plan-gate.ts")
IDX = os.path.join(ROOT, "pi-extensions", "planning-with-files-bridge", "index.ts")


def node_ok():
    try:
        out = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=30)
        return out.returncode == 0 and int(out.stdout.strip().lstrip("v").split(".")[0]) >= 22
    except Exception:
        return False


NODE_OK = node_ok()


@unittest.skipUnless(NODE_OK, "node >= 22 required for native TypeScript type stripping")
class TestTheGate(unittest.TestCase):
    DRIVER = r"""
import { readFileSync } from "node:fs";
import { NoPlanGate } from %(mod)s;
const cases = JSON.parse(readFileSync(process.argv[2], "utf-8"));
const out = [];
for (const c of cases) {
  const g = new NoPlanGate(...(c.ctor ?? []));
  for (let i = 0; i < (c.calls ?? 0); i++) g.observe();
  const results = (c.checks ?? []).map(([tool, path, planExists]) => {
    const r = g.check(tool, path, planExists);
    return r ? { blocked: true, block: r.block, reason: r.reason } : { blocked: false };
  });
  out.push({ results, stats: g.stats() });
}
process.stdout.write(JSON.stringify(out));
"""

    def _run(self, cases):
        driver = scratch(".tmp_noplan_driver.mjs")
        payload = scratch(".tmp_noplan_input.json")
        with open(driver, "w", encoding="utf-8") as f:
            f.write(self.DRIVER % {"mod": json.dumps("file:///" + MOD.replace("\\", "/"))})
        with open(payload, "w", encoding="utf-8") as f:
            json.dump(cases, f)
        try:
            p = subprocess.run(["node", driver, payload], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", cwd=ROOT, timeout=120)
            if p.returncode != 0:
                raise AssertionError("node driver failed:\n%s\n%s" % (p.stdout, p.stderr))
            return json.loads(p.stdout)
        finally:
            for x in (driver, payload):
                if os.path.exists(x):
                    os.remove(x)

    def test_a_short_session_is_never_gated(self):
        """Every session of 1-9 tool calls in the measurement had no plan and
        none of them needed one. A question is not a project."""
        (r,) = self._run([{"calls": 9, "checks": [["write", "out.md", False]]}])
        self.assertFalse(r["results"][0]["blocked"])

    def test_it_fires_once_enough_work_has_happened(self):
        (r,) = self._run([{"calls": 12, "checks": [["write", "findings/report.md", False]]}])
        self.assertTrue(r["results"][0]["blocked"])

    def test_it_speaks_once_and_then_stands_down(self):
        """The depth guard refused three times while the model issued twenty more
        searches. Repeating a message the model already declined teaches nothing
        and costs a turn each time."""
        (r,) = self._run([{"calls": 20, "checks": [
            ["write", "a.md", False], ["write", "b.md", False], ["write", "c.md", False]]}])
        self.assertEqual([x["blocked"] for x in r["results"]], [True, False, False])
        self.assertEqual(r["stats"]["refusals"], 1)

    def test_writing_the_plan_is_never_blocked(self):
        """The escape must be in-band and immediate, or the gate deadlocks: the
        only way out of a write gate is a write."""
        (r,) = self._run([{"calls": 30, "checks": [
            ["write", "task_plan.md", False], ["write", "docs/plan.md", False],
            ["write", "progress.md", False], ["edit", "findings.md", False]]}])
        self.assertEqual([x["blocked"] for x in r["results"]], [False] * 4)

    def test_an_existing_plan_disarms_it(self):
        (r,) = self._run([{"calls": 50, "checks": [["write", "out.md", True]]}])
        self.assertFalse(r["results"][0]["blocked"])

    def test_the_road_stays_open(self):
        """The phase gate refused searches and took real research from 15 to 0 in
        the same run it took premature searches from 15 to 0. Nothing that moves
        the work forward is touched here — only the first durable artifact."""
        (r,) = self._run([{"calls": 40, "checks": [
            ["bash", None, False], ["web_search", None, False], ["read", "x.md", False],
            ["web_open", None, False], ["grep", None, False]]}])
        self.assertEqual([x["blocked"] for x in r["results"]], [False] * 5)

    def test_trivial_and_tool_generated_artifacts_are_exempt(self):
        """Refusing these is pure friction: nobody plans before writing a
        .gitignore, and lockfiles are written by tooling, not by the work."""
        (r,) = self._run([{"calls": 40, "checks": [
            ["write", ".gitignore", False], ["write", "package-lock.json", False],
            ["write", "out.log", False], ["write", "README.md", False],
            ["write", "assets/logo.png", False]]}])
        self.assertEqual([x["blocked"] for x in r["results"]], [False] * 5)

    def test_the_refusal_says_what_to_write_and_that_one_line_is_enough(self):
        """A refusal that removes an option must say how the option comes back,
        and the cost of compliance has to be visibly small or it gets routed
        around."""
        (r,) = self._run([{"calls": 12, "checks": [["write", "out.md", False]]}])
        reason = r["results"][0]["reason"]
        self.assertIn("task_plan.md", reason)
        self.assertIn("一行就夠", reason)
        self.assertIn("out.md", reason, "the refusal must name the file it stopped")
        self.assertIn("12", reason, "and show the count it is acting on")

    def test_the_refusal_actually_carries_block_true(self):
        """`{ block: true }` in the object literal is the field Pi reads; the
        identical spelling inside the interface declaration is erased at runtime.
        The mutation allowlist says outright that the literal form is never
        equivalent and belongs in a test — this is that test."""
        (r,) = self._run([{"calls": 12, "checks": [["write", "out.md", False]]}])
        self.assertIs(r["results"][0]["block"], True)

    def test_a_bad_path_argument_does_not_fire(self):
        (r,) = self._run([{"calls": 40, "checks": [
            ["write", None, False], ["write", "", False], ["write", 7, False]]}])
        self.assertEqual([x["blocked"] for x in r["results"]], [False] * 3)

    def test_the_thresholds_are_settable(self):
        """Calibration, not protocol — they must move with a measurement rather
        than with an edit to the mechanism."""
        (r,) = self._run([{"ctor": [2, 3], "calls": 2, "checks": [
            ["write", "a.md", False], ["write", "b.md", False],
            ["write", "c.md", False], ["write", "d.md", False]]}])
        self.assertEqual([x["blocked"] for x in r["results"]], [True, True, True, False])


class TestItIsWiredWhereItCanFire(unittest.TestCase):
    """The bridge's other four handlers all return early when there is no plan.
    If this one grows the same guard it becomes another mechanism that cannot
    reach its own case — which is the defect being fixed, not a style point."""

    def setUp(self):
        with open(IDX, encoding="utf-8") as f:
            self.src = f.read()

    def test_the_gate_runs_on_tool_call(self):
        self.assertIn("new NoPlanGate()", self.src)
        self.assertIn("noPlanGate.observe()", self.src)
        self.assertIn("noPlanGate.check(", self.src)

    def test_the_gate_is_not_behind_a_has_plan_early_return(self):
        head = self.src.split("pi.on(\"tool_call\"", 1)[1].split("noPlanGate.check(", 1)[0]
        self.assertNotIn("hasAnyPlan(ctx.cwd)) return", head,
                         "the no-plan gate must not skip sessions without a plan")
        self.assertNotIn("hasActivePlan", head)

    def test_it_still_honours_the_bridge_off_switch(self):
        head = self.src.split("pi.on(\"tool_call\"", 1)[1].split("noPlanGate.observe", 1)[0]
        self.assertIn("planningBridgeEnabled()", head)


if __name__ == "__main__":
    unittest.main()
