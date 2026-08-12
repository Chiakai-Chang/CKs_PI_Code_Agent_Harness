"""The gate closed a door and nobody said when it opened again.

Measured 2026-08-08, the 4b research run. The turn-based exit ramp worked
exactly as designed — twenty refusals across four turns, one voice per turn,
and not one successful search before the task was claimed, down from fifteen.

Then the model claimed the task and never searched again. Twelve turns of
bash, read and write, zero `web_search`, although research is WIDE OPEN in the
PLAN phase. It wrote the reason into its own deliverable:

    ⚠️ 未經驗證: `web_search` 工具被 C.A.S.E. 框架攔截,以下版本號來自知識庫,
    可能已過時。

Its generalisation was rational. It had seen twenty refusals and zero "you can
now". The owner had been explicit that searching more is good and only the
ordering was wrong, so premature searches 15 -> 0 is the win and real research
15 -> 0 is the bill.

Third time for this shape: the citation gate took URLs in files from 0 to 10
and fabricated ones from 0 to 4; the first phase gate refused and the status
never left PENDING. The sharper statement is not "a threshold defines the shape
of the evasion" — there was no evasion here, the model dropped the capability.
It is: **a guard that removes an option must be paired with something that
speaks when the option comes back.**

The carrier cannot be the advancer. It speaks only on a turn that produced text
and called no tools, and turns 6 to 15 all called tools, so the notice would
have arrived at turn 16. It has to ride the tool result of the claim itself —
one of the two channels measured to reach the model in this project.
"""

import importlib.util
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys as _sys
_sys.path.insert(0, os.path.join(ROOT, "tests"))
from _scratch import scratch  # per-process temp names; see tests/_scratch.py

MOD = os.path.join(ROOT, "pi-extensions", "case-bridge", "phase-notice.ts")


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
    driver = scratch(".tmp_notice_driver.mjs")
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
    """The state on disk AFTER the call ran.

    `tool_result` fires once the write has happened, so a claim is observed as
    a task that already reads IN_PROGRESS. The first version of this fixture
    set PENDING — the state before the write — and every claim case came back
    silent against correct code. Fourth time today that a fixture encoded the
    wrong moment rather than the wrong value."""

    def __init__(self, status="PENDING", name="Task_001_probe"):
        self.root = tempfile.mkdtemp(prefix="notice-")
        self.dir = os.path.join(self.root, "02_Task_Queue")
        self.task = os.path.join(self.dir, name)
        os.makedirs(self.task)
        self.write("status.txt", status)
        self.write("role.md", "role")
        self.write("recipe.md", "recipe")

    def write(self, name, content):
        with open(os.path.join(self.task, name), "w", encoding="utf-8") as f:
            f.write(content)

    @property
    def js(self):
        return json.dumps(self.dir.replace("\\", "/"))

    @property
    def status_path(self):
        return json.dumps(os.path.join(self.task, "status.txt").replace("\\", "/"))

    def cleanup(self):
        shutil.rmtree(self.root, ignore_errors=True)


def notice(queue, tool="write", path=None, content="IN_PROGRESS", is_error=False, repeat=1):
    return run_js("""
    const n = new m.PhaseNotice();
    const out = [];
    for (let i = 0; i < %d; i++) {
      out.push(n.afterToolResult(%s, %s, { path: %s, content: %s }, %s));
    }
    process.stdout.write(JSON.stringify({ out }));
    """ % (repeat, queue.js, json.dumps(tool),
           path if path is not None else queue.status_path,
           json.dumps(content), "true" if is_error else "false"))["out"]


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestItStaysQuiet(unittest.TestCase):
    """First, because noise is what makes a notice get skipped, and a notice
    that gets skipped is the same as the silence it was built to fix."""

    def test_an_ordinary_write_says_nothing(self):
        q = Queue(status="IN_PROGRESS")
        self.addCleanup(q.cleanup)
        self.assertIsNone(notice(q, path=json.dumps(
            os.path.join(q.task, "output.md").replace("\\", "/")), content="findings")[0])

    def test_a_refused_write_says_nothing(self):
        """The claim did not happen, so nothing opened."""
        q = Queue(status="PENDING")
        self.addCleanup(q.cleanup)
        self.assertIsNone(notice(q, is_error=True)[0])

    def test_a_read_says_nothing(self):
        """IN_PROGRESS on purpose. With PENDING the status check refuses it
        anyway, so the case could not tell a correct tool test from a broken
        one — the mutation sweep proved that by surviving a flip of the `edit`
        comparison, which would have made every `read` of a status.txt count as
        a claim."""
        q = Queue(status="IN_PROGRESS")
        self.addCleanup(q.cleanup)
        self.assertIsNone(notice(q, tool="read")[0])

    def test_a_status_write_that_is_not_a_claim_says_nothing(self):
        """REVIEW does not reopen research; only leaving CLAIM does."""
        q = Queue(status="REVIEW")
        self.addCleanup(q.cleanup)
        self.assertIsNone(notice(q, content="REVIEW")[0])

    def test_it_speaks_once_and_then_stops(self):
        """Repeating it every turn would turn the one message that matters into
        the wallpaper the model already learned to ignore."""
        q = Queue(status="IN_PROGRESS")
        self.addCleanup(q.cleanup)
        out = notice(q, repeat=4)
        self.assertIsNotNone(out[0])
        self.assertEqual(out[1:], [None, None, None])

    def test_a_write_whose_path_is_not_a_string_says_nothing(self):
        """From the mutation sweep. Tool arguments arrive from the model, so
        `path` is whatever it produced — a number, an object, null. Treating a
        non-string as a path pushes it into resolve() and relies on an
        exception for correctness."""
        q = Queue(status="IN_PROGRESS")
        self.addCleanup(q.cleanup)
        for arg in ("123", "null", "{}", "[]"):
            with self.subTest(arg=arg):
                out = run_js("""
                const n = new m.PhaseNotice();
                process.stdout.write(JSON.stringify({ v: n.afterToolResult(%s, "write",
                  { path: %s, content: "IN_PROGRESS" }, false) }));
                """ % (q.js, arg))
                self.assertIsNone(out["v"])

    def test_a_project_with_no_queue_says_nothing(self):
        out = run_js("""
        const n = new m.PhaseNotice();
        process.stdout.write(JSON.stringify({ v: n.afterToolResult(
          "/nowhere/02_Task_Queue", "write",
          { path: "/nowhere/02_Task_Queue/Task_001/status.txt", content: "IN_PROGRESS" },
          false) }));
        """)
        self.assertIsNone(out["v"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestWhatItSays(unittest.TestCase):
    """The model had seen twenty refusals and zero permissions. This message is
    the permission, so it has to be unmistakable about the thing that was
    refused."""

    def setUp(self):
        self.q = Queue(status="IN_PROGRESS")
        self.addCleanup(self.q.cleanup)
        self.text = notice(self.q)[0]

    def test_it_names_the_tool_that_was_refused(self):
        self.assertIn("web_search", self.text)

    def test_it_says_the_refusals_have_stopped(self):
        # `不會再被擋` is the natural passive and the regex was written before
        # the text existed, so it only had the active voice. Widened to the
        # phrasings that mean the same thing — not to whatever the text happens
        # to say, which is why 放開 and 開放 are here and a bare 擋 is not.
        self.assertRegex(self.text, r"不會再被擋|不會再擋|不再擋|放開|開放|全開")

    def test_it_does_not_merely_describe_the_phase(self):
        """"You are now in PLAN" is a status line. The run that produced this
        task needed to be told it may search again, in those words."""
        self.assertRegex(self.text, r"可以.*搜|去搜|搜尋.*可以|盡量搜")

    def test_it_is_short(self):
        """It rides on a tool result the model is already reading. A paragraph
        there competes with the result itself."""
        self.assertLess(len(self.text), 260)


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestBashClaimsCountToo(unittest.TestCase):
    """The tool-first guard refuses shell writes to status.txt, but the exit
    ramp lets one through after enough refusals, and a claim is a claim. Missing
    it would leave exactly the run that fought hardest with no notice."""

    def test_a_heredoc_claim_is_recognised(self):
        q = Queue(status="IN_PROGRESS")
        self.addCleanup(q.cleanup)
        cmd = 'printf "IN_PROGRESS" > "%s/status.txt"' % q.task.replace("\\", "/")
        out = run_js("""
        const n = new m.PhaseNotice();
        process.stdout.write(JSON.stringify({ v: n.afterToolResult(%s, "bash",
          { command: %s }, false) }));
        """ % (q.js, json.dumps(cmd)))
        self.assertIsNotNone(out["v"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheBridgeDeliversIt(unittest.TestCase):
    """`ctx.ui.notify` reaches nobody and a `turn_end` return value reaches
    nobody. A `tool_result` handler returning `{ content: [...existing, block] }`
    is one of the two channels measured to arrive, so the notice rides the
    result of the claim itself — which is also the moment it is true."""

    def _handler(self):
        """The whole handler, not a fixed slice of its first 1200 characters.

        The slice silently stopped covering the assertions the day a second
        rider joined this channel: the notice moved past character 1200 and two
        tests failed while the code was correct. A window that shrinks as the
        handler grows is a check that quietly stops checking."""
        with open(os.path.join(ROOT, "pi-extensions", "case-bridge", "index.ts"),
                  encoding="utf-8") as f:
            after = f.read().split('pi.on("tool_result"', 1)[1]
        # Up to the next handler registration, so this stays scoped to one.
        return after.split("pi.on(", 1)[0]

    def test_it_returns_a_content_array(self):
        body = self._handler()
        self.assertIn("phaseNotice.afterToolResult", body)
        self.assertRegex(body, r"content:\s*\[")

    def test_it_keeps_the_existing_blocks(self):
        """Returning a bare block instead of appending is how eleven green
        tests once shipped a handler Pi dropped in silence."""
        self.assertRegex(self._handler(), r"\.\.\.")

    def test_the_action_log_still_runs(self):
        self.assertIn("actionLog.record", self._handler())


if __name__ == "__main__":
    unittest.main()
