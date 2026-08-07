"""The audit trail should not be something the model is asked to remember.

C.A.S.E. requires `action_log.jsonl` — one JSON object per tool call — and the
verifier only ever warned about its absence, so in practice it was optional. The
deeper problem is who writes it: asking the agent under audit to keep its own
audit trail is worth nothing, and it was measured worth exactly that. Session
019fd29d made 40 tool calls and wrote no files at all.

The harness sees every tool call already. It can write the log itself, with no
cooperation, no reminder, and no way for a run to skip it.

Two deliberate limits:

  * Only when exactly one task is IN_PROGRESS. With none, there is no task the
    call belongs to; with two, guessing would file the evidence under the wrong
    task, which is worse than not filing it.
  * Arguments are summarised, never copied. A log that embeds the content of
    every write is a second copy of the deliverable, and `output.md` is already
    the deliverable.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(ROOT, "pi-extensions", "case-bridge", "action-log.ts")


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
    driver = os.path.join(ROOT, "tests", ".tmp_alog_driver.mjs")
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


class Workspace:
    def __init__(self, nested=False):
        self.root = tempfile.mkdtemp(prefix="case-alog-")
        base = os.path.join(self.root, "C.A.S.E._Framework") if nested else self.root
        os.makedirs(base, exist_ok=True)
        self.queue = os.path.join(base, "02_Task_Queue")
        os.makedirs(self.queue)

    def task(self, name, status="PENDING"):
        d = os.path.join(self.queue, name)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "status.txt"), "w", encoding="utf-8") as f:
            f.write(status)
        return d

    def log_lines(self, name):
        p = os.path.join(self.queue, name, "action_log.jsonl")
        if not os.path.exists(p):
            return []
        with open(p, encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()]

    def cleanup(self):
        shutil.rmtree(self.root, ignore_errors=True)


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestSummaries(unittest.TestCase):
    """What goes in the line, and what deliberately does not."""

    def test_a_write_records_the_path_and_not_the_content(self):
        out = run_js("""
        process.stdout.write(JSON.stringify(
          m.summarizeInput("write", { path: "a/b.md", content: "x".repeat(5000) })));
        """)
        self.assertEqual(out.get("path"), "a/b.md")
        self.assertNotIn("content", out)

    def test_a_long_command_is_truncated(self):
        out = run_js("""
        process.stdout.write(JSON.stringify(
          m.summarizeInput("bash", { command: "echo " + "y".repeat(2000) })));
        """)
        self.assertLessEqual(len(out["command"]), 260)
        self.assertTrue(out["command"].startswith("echo yyy"))

    def test_a_search_records_its_query(self):
        out = run_js("""
        process.stdout.write(JSON.stringify(
          m.summarizeInput("web_search", { query: "台灣 智慧門鈴" })));
        """)
        self.assertEqual(out["query"], "台灣 智慧門鈴")

    def test_an_unknown_tool_records_nothing_it_cannot_name(self):
        out = run_js("""
        process.stdout.write(JSON.stringify(
          m.summarizeInput("mystery_tool", { secret: "value", path: "p" })));
        """)
        self.assertEqual(out.get("path"), "p")
        self.assertNotIn("secret", out)


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestWritingTheLog(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace()
        self.addCleanup(self.ws.cleanup)

    def js(self, script):
        return run_js(script.replace("__ROOT__", json.dumps(self.ws.root.replace("\\", "/"))))

    def test_a_call_lands_in_the_open_task(self):
        self.ws.task("Task_001_A", "IN_PROGRESS")
        self.js("""
        const lg = new m.ActionLogger();
        lg.record(__ROOT__, "web_search", { query: "q" }, false);
        process.stdout.write(JSON.stringify({}));
        """)
        lines = self.ws.log_lines("Task_001_A")
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["tool"], "web_search")
        self.assertEqual(lines[0]["query"], "q")
        self.assertIn("at", lines[0])

    def test_calls_append_rather_than_replace(self):
        self.ws.task("Task_001_A", "IN_PROGRESS")
        self.js("""
        const lg = new m.ActionLogger();
        for (let i = 0; i < 5; i++) lg.record(__ROOT__, "bash", { command: "run " + i }, false);
        process.stdout.write(JSON.stringify({}));
        """)
        self.assertEqual(len(self.ws.log_lines("Task_001_A")), 5)

    def test_a_failed_call_is_recorded_as_failed(self):
        self.ws.task("Task_001_A", "IN_PROGRESS")
        self.js("""
        const lg = new m.ActionLogger();
        lg.record(__ROOT__, "bash", { command: "false" }, true);
        process.stdout.write(JSON.stringify({}));
        """)
        self.assertTrue(self.ws.log_lines("Task_001_A")[0]["error"])

    def test_a_successful_call_carries_no_error_field(self):
        self.ws.task("Task_001_A", "IN_PROGRESS")
        self.js("""
        const lg = new m.ActionLogger();
        lg.record(__ROOT__, "read", { path: "x" }, false);
        process.stdout.write(JSON.stringify({}));
        """)
        self.assertNotIn("error", self.ws.log_lines("Task_001_A")[0])

    def test_nothing_is_written_when_no_task_is_open(self):
        self.ws.task("Task_001_A", "PENDING")
        out = self.js("""
        const lg = new m.ActionLogger();
        const w = lg.record(__ROOT__, "web_search", { query: "q" }, false);
        process.stdout.write(JSON.stringify({ wrote: w }));
        """)
        self.assertIsNone(out["wrote"])
        self.assertEqual(self.ws.log_lines("Task_001_A"), [])

    def test_two_open_tasks_are_not_guessed_between(self):
        """Filing evidence under the wrong task is worse than not filing it."""
        self.ws.task("Task_001_A", "IN_PROGRESS")
        self.ws.task("Task_002_B", "IN_PROGRESS")
        out = self.js("""
        const lg = new m.ActionLogger();
        const w = lg.record(__ROOT__, "web_search", { query: "q" }, false);
        process.stdout.write(JSON.stringify({ wrote: w }));
        """)
        self.assertIsNone(out["wrote"])
        self.assertEqual(self.ws.log_lines("Task_001_A"), [])
        self.assertEqual(self.ws.log_lines("Task_002_B"), [])

    def test_a_project_with_no_queue_is_left_alone(self):
        """A directory of its own, not process.cwd().

        This used cwd until 2026-08-06, when the harness repo was bootstrapped
        as a C.A.S.E. project — and the test failed, correctly, because the
        logger found the repo's own queue and wrote there. A fixture that
        borrows the repository is a fixture that changes when the repository
        does.
        """
        bare = tempfile.mkdtemp(prefix="case-noqueue-")
        self.addCleanup(shutil.rmtree, bare, ignore_errors=True)
        out = run_js("""
        const lg = new m.ActionLogger();
        const w = lg.record(%s, "web_search", { query: "q" }, false);
        process.stdout.write(JSON.stringify({ wrote: w }));
        """ % json.dumps(bare.replace("\\", "/")))
        self.assertIsNone(out["wrote"])

    def test_unserializable_input_does_not_throw(self):
        self.ws.task("Task_001_A", "IN_PROGRESS")
        out = self.js("""
        const lg = new m.ActionLogger();
        const a = {}; a.self = a;
        let threw = false;
        try { lg.record(__ROOT__, "write", a, false); } catch { threw = true; }
        process.stdout.write(JSON.stringify({ threw }));
        """)
        self.assertFalse(out["threw"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestNestedLayout(unittest.TestCase):
    """The reference workspace keeps the queue under C.A.S.E._Framework/."""

    def setUp(self):
        self.ws = Workspace(nested=True)
        self.addCleanup(self.ws.cleanup)

    def test_the_queue_is_found_one_level_down(self):
        self.ws.task("Task_001_A", "IN_PROGRESS")
        run_js("""
        const lg = new m.ActionLogger();
        lg.record(%s, "read", { path: "x" }, false);
        process.stdout.write(JSON.stringify({}));
        """ % json.dumps(self.ws.root.replace("\\", "/")))
        self.assertEqual(len(self.ws.log_lines("Task_001_A")), 1)



@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheTruncationBoundaryIsExact(unittest.TestCase):
    """Added 2026-08-08 from the mutation sweep. `MAX_FIELD_CHARS = 256` shifted
    to 257 and nothing turned red: every existing case is either far under the
    limit or far over it, so the number could be anything within a wide band.

    The log is the evidence trail the measurements are read from — a field that
    silently keeps one more or one fewer character is a small thing, but "the
    number nobody pinned" is how a measurement stops being reproducible."""

    def test_a_field_at_the_limit_is_untouched_and_one_past_it_is_cut(self):
        out = run_js("""
        const at = "x".repeat(256), over = "y".repeat(257);
        const a = m.summarizeInput("bash", { command: at });
        const b = m.summarizeInput("bash", { command: over });
        process.stdout.write(JSON.stringify({ at: a.command, over: b.command }));
        """)
        self.assertEqual(len(out["at"]), 256, "exactly at the limit must not be cut")
        self.assertTrue(out["over"].endswith("…"))
        self.assertEqual(len(out["over"]), 257, "256 kept plus the ellipsis")


if __name__ == "__main__":
    unittest.main()
