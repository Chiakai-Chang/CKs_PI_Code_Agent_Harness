"""A plan from last week is not a plan for this request.

Measured 2026-08-11 in the owner's own session. He opened
`D:/MyProject/DiscoverTurth` — a project carrying a `task_plan.md` last written
on 2026-08-06 — and asked a ten-part investigation question. Reproduced against
the shipped classifier:

    classify   -> {"multiStep": true, "deliverables": 10, ...}
    hasAnyPlan -> true          <-- five days old
    isCase     -> false

So the router recognised the request perfectly and then stood down, because a
plan "existed". Nothing advised planning; the run opened with three `web_search`
calls and no plan file — which is, word for word, the complaint this bridge was
built to answer: 「我抱怨的是他沒有先規劃就開始」.

The fix is not a tuned staleness threshold. The bridge already knows when the
session began, and that is the honest boundary: a plan touched after this session
started means the model is planning right now and repeating the advice would be
noise; anything older is history.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import sys as _sys
_sys.path.insert(0, os.path.join(ROOT, "tests"))
from _scratch import scratch  # per-process temp names; see tests/_scratch.py

MOD = os.path.join(ROOT, "pi-extensions", "task-shape-bridge", "plan.ts")
INDEX = os.path.join(ROOT, "pi-extensions", "task-shape-bridge", "index.ts")


def _node_major():
    if not shutil.which("node"):
        return 0
    try:
        out = subprocess.run(["node", "--version"], capture_output=True,
                             text=True, timeout=30).stdout
    except Exception:
        return 0
    m = re.match(r"v(\d+)", out.strip())
    return int(m.group(1)) if m else 0


NODE_OK = _node_major() >= 22


def run_js(script):
    driver = scratch(".tmp_staleplan_driver.mjs")
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
class TestOnlyThisRunsPlanCounts(unittest.TestCase):
    def setUp(self):
        self.cwd = tempfile.mkdtemp(prefix="stale-plan-")
        self.addCleanup(shutil.rmtree, self.cwd, True)
        self.plan = os.path.join(self.cwd, "task_plan.md")
        with open(self.plan, "w", encoding="utf-8") as f:
            f.write("# task_plan\n- [ ] something from another week\n")

    def has(self, since=None):
        arg = "" if since is None else ", %d" % since
        return run_js("process.stdout.write(JSON.stringify("
                      "m.hasAnyPlan(%s%s)));" % (json.dumps(self.cwd), arg))

    def age(self, seconds):
        old = time.time() - seconds
        os.utime(self.plan, (old, old))

    def test_a_five_day_old_plan_does_not_count(self):
        self.age(5 * 24 * 3600)
        self.assertFalse(self.has(int(time.time() * 1000)))

    def test_a_plan_written_during_this_session_does_count(self):
        started = int(time.time() * 1000) - 60_000
        self.assertTrue(self.has(started))

    def test_a_plan_written_at_the_exact_moment_the_session_began_counts(self):
        """The boundary, and a mutation survivor before this test existed:
        `>=` and `>` differ on exactly this input. A plan whose mtime equals the
        session start belongs to the session — the session did not exist before
        that instant, so nothing older can have been written by it, and nothing
        written at it can be history."""
        started = int(time.time() * 1000) - 5000
        os.utime(self.plan, (started / 1000.0, started / 1000.0))
        self.assertTrue(self.has(started))

    def test_a_plan_a_minute_older_than_the_session_does_not(self):
        """The boundary itself. One minute is not staleness — it is 'written
        before this conversation existed', which is the whole distinction."""
        self.age(60)
        self.assertFalse(self.has(int(time.time() * 1000) - 1000))

    def test_without_a_session_time_the_old_answer_stands(self):
        """Three bridges share this predicate and `test_plan_detection_parity`
        drives all three without a timestamp. Changing the no-argument answer
        would break agreement between them for no reason."""
        self.age(5 * 24 * 3600)
        self.assertTrue(self.has())

    def test_no_plan_is_still_no_plan(self):
        os.remove(self.plan)
        self.assertFalse(self.has(int(time.time() * 1000)))
        self.assertFalse(self.has())


class TestTheBridgePassesItsSessionTime(unittest.TestCase):
    """The predicate being session-aware buys nothing if the call site still
    asks the old question. `index.ts` opens with `require.resolve`, which only
    exists under Pi's shim, so this one is read rather than driven — and the
    behaviour it guards is covered above."""

    def setUp(self):
        with open(INDEX, encoding="utf-8") as f:
            self.src = f.read()

    def test_the_call_site_passes_the_session_start(self):
        self.assertIn("hasAnyPlan(ctx.cwd, sessionStartedAt)", self.src)

    def test_session_start_resets_it(self):
        handler = self.src.split('pi.on("session_start"', 1)[1].split("});", 1)[0]
        self.assertIn("sessionStartedAt = Date.now()", handler)


if __name__ == "__main__":
    unittest.main()
