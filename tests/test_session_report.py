"""One session reader, instead of thirteen throwaway ones.

This session wrote thirteen ad-hoc scripts to answer the same questions about a
session file, and two of them produced wrong conclusions:

  * The depth and artifact gates showed 0 firings, so they were recorded as
    "structurally unverifiable by the probe". They were verifiable; the probe's
    scenario never reached the condition.
  * Task_002's first count used a glob with an extra directory level and
    returned 0 for a session containing 4 advances — one step from declaring the
    advancer dead and escalating a task that was working.

Both failures look identical on screen: the number 0. So the first thing this
prints is how many files it scanned and which ones, because a zero from an empty
match set and a zero from a real absence are different answers to different
questions and must never render the same.

Everything else it reports is what those thirteen scripts kept re-deriving:
tool counts, which guards fired, which skills were read, addresses written to
files against addresses actually opened, and the custom messages the harness
injected.
"""

import json
import os
import subprocess
import sys
import tempfile
import shutil
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "session-report.py")

sys.path.insert(0, os.path.join(ROOT, "scripts"))


def load():
    import importlib.util
    spec = importlib.util.spec_from_file_location("session_report", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_session(path, rows):
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def assistant(calls=(), text=""):
    content = [{"type": "toolCall", "name": n, "arguments": a} for n, a in calls]
    if text:
        content.append({"type": "text", "text": text})
    return {"type": "message", "message": {"role": "assistant", "content": content}}


def result(tool, text, is_error=False):
    return {"type": "message", "message": {"role": "toolResult", "toolName": tool,
                                           "isError": is_error,
                                           "content": [{"type": "text", "text": text}]}}


def custom(kind, text="x"):
    return {"type": "custom_message", "customType": kind, "content": text}


class Fixture:
    def __init__(self):
        self.dir = tempfile.mkdtemp(prefix="sessrep-")

    def session(self, name, rows):
        p = os.path.join(self.dir, name)
        write_session(p, rows)
        return p

    def cleanup(self):
        shutil.rmtree(self.dir, ignore_errors=True)


class TestAZeroIsNeverSilent(unittest.TestCase):
    """The failure this script exists to prevent."""

    def setUp(self):
        self.fx = Fixture()
        self.addCleanup(self.fx.cleanup)
        self.m = load()

    def test_it_reports_which_files_it_scanned(self):
        self.fx.session("a.jsonl", [assistant([("web_search", {"query": "q"})])])
        rep = self.m.report(self.fx.dir)
        self.assertEqual(len(rep["files"]), 1)
        self.assertTrue(rep["files"][0].endswith("a.jsonl"))

    def test_a_directory_with_no_sessions_says_so(self):
        rep = self.m.report(self.fx.dir)
        self.assertEqual(rep["files"], [])
        self.assertIn("scanned", rep["warnings"][0].lower())

    def test_a_path_that_does_not_exist_says_so(self):
        rep = self.m.report(os.path.join(self.fx.dir, "nope"))
        self.assertEqual(rep["files"], [])
        self.assertTrue(rep["warnings"])

    def test_nested_sessions_are_found(self):
        """Task_002's miss: the file sat directly under .sess/, and the glob
        expected one more directory level."""
        deep = os.path.join(self.fx.dir, "a", "b")
        os.makedirs(deep)
        write_session(os.path.join(deep, "s.jsonl"), [custom("case-advance")])
        rep = self.m.report(self.fx.dir)
        self.assertEqual(len(rep["files"]), 1)
        self.assertEqual(rep["custom"]["case-advance"], 1)


class TestWhatItCounts(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()
        self.addCleanup(self.fx.cleanup)
        self.m = load()

    def test_tools(self):
        self.fx.session("a.jsonl", [
            assistant([("web_search", {"query": "a"}), ("web_open", {"url": "https://x.example/p"})]),
            assistant([("write", {"path": "f.md", "content": "see https://x.example/p"})]),
        ])
        rep = self.m.report(self.fx.dir)
        self.assertEqual(rep["tools"]["web_search"], 1)
        self.assertEqual(rep["tools"]["write"], 1)

    def test_guards_are_counted_from_tool_results(self):
        """Grepping the raw file counts the model echoing a refusal in its own
        prose; by hand that gave 2,1,2 where the tool results gave 2,1,1."""
        self.fx.session("a.jsonl", [
            result("write", "Citation guard: this file is 900 chars...", is_error=True),
            assistant(text="I hit the Citation guard, so I will add sources."),
        ])
        rep = self.m.report(self.fx.dir)
        self.assertEqual(rep["guards"].get("Citation guard"), 1)

    def test_urls_written_against_urls_opened(self):
        self.fx.session("a.jsonl", [
            assistant([("web_open", {"url": "https://a.example/one"})]),
            assistant([("write", {"path": "f.md",
                                  "content": "https://a.example/one and https://invented.example/s?q=x"})]),
        ])
        rep = self.m.report(self.fx.dir)
        self.assertEqual(rep["urls_in_files"], 2)
        self.assertEqual(rep["urls_opened"], 1)

    def test_skills_read(self):
        self.fx.session("a.jsonl", [
            assistant([("read", {"path": "/x/skills/case-framework/SKILL.md"}),
                       ("read", {"path": "/x/skills/case-framework/SKILL.md"})]),
        ])
        self.assertEqual(self.m.report(self.fx.dir)["skills"], ["case-framework"])

    def test_custom_messages_by_type(self):
        self.fx.session("a.jsonl", [custom("case-advance"), custom("case-advance"),
                                    custom("compaction-echo")])
        rep = self.m.report(self.fx.dir)
        self.assertEqual(rep["custom"]["case-advance"], 2)
        self.assertEqual(rep["custom"]["compaction-echo"], 1)

    def test_it_reports_the_most_injections_between_two_turns(self):
        """The cross-bridge question Task_001 raised and Task_002 answered with
        'not observed this time' — which is not evidence. This turns it into a
        number that accumulates across sessions."""
        self.fx.session("a.jsonl", [
            assistant(text="done"),
            custom("compaction-echo"), custom("case-advance"),
            assistant(text="ok"),
            custom("case-advance"),
        ])
        self.assertEqual(self.m.report(self.fx.dir)["max_injections_per_turn"], 2)


class TestGuardMarkersStayInSync(unittest.TestCase):
    """Two lists of the same guards drift, and this repo has the scar:
    uninstall.py managed 5 bridges while restore.py managed 11."""

    def test_every_marker_measure_triggers_knows_is_known_here_too(self):
        m = load()
        src = open(os.path.join(ROOT, "scripts", "measure-triggers.py"),
                   encoding="utf-8").read()
        block = src.split("GUARD_MARKERS = (", 1)[1].split(")", 1)[0]
        theirs = {line.strip().strip('",') for line in block.splitlines() if '"' in line}
        missing = sorted(theirs - set(m.GUARD_MARKERS))
        self.assertEqual(missing, [], "measure-triggers.py knows guards this does not")


class TestUnharvestedTasks(unittest.TestCase):
    """A finished task's output.md and retro.md live in a gitignored queue.
    Task_002's conclusion survived only because `git commit` said "nothing to
    commit" and that was noticed."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="harvest-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.q = os.path.join(self.root, "02_Task_Queue")
        self.docs = os.path.join(self.root, "docs")
        os.makedirs(self.q)
        os.makedirs(self.docs)
        self.m = load()

    def _task(self, name, with_output=True):
        d = os.path.join(self.q, name)
        os.makedirs(d)
        if with_output:
            with open(os.path.join(d, "output.md"), "w", encoding="utf-8") as fh:
                fh.write("result")
        return d

    def test_a_task_with_output_and_no_mention_in_docs_is_listed(self):
        self._task("Task_001_thing")
        self.assertEqual(self.m.unharvested(self.q, self.docs), ["Task_001_thing"])

    def test_a_task_mentioned_in_docs_is_not_listed(self):
        self._task("Task_001_thing")
        with open(os.path.join(self.docs, "note.md"), "w", encoding="utf-8") as fh:
            fh.write("see Task_001_thing for details")
        self.assertEqual(self.m.unharvested(self.q, self.docs), [])

    def test_a_task_with_no_output_is_not_listed(self):
        self._task("Task_002_wip", with_output=False)
        self.assertEqual(self.m.unharvested(self.q, self.docs), [])

    def test_a_missing_queue_is_not_an_error(self):
        self.assertEqual(self.m.unharvested(os.path.join(self.root, "nope"), self.docs), [])

    def test_a_mentioned_task_is_still_listed_with_its_status(self):
        """The first real run reported "all clear" because a task name appeared
        inside a quoted session transcript, while that task's retro — three
        pieces of upstream feedback — existed nowhere outside the gitignored
        queue. A mention is not preservation, so every task is listed and the
        judgement stays with a human."""
        self._task("Task_001_thing")
        self._task("Task_002_other")
        with open(os.path.join(self.docs, "note.md"), "w", encoding="utf-8") as fh:
            fh.write("...transcript line mentioning Task_001_thing in passing...")
        rows = self.m.harvest_status(self.q, self.docs)
        self.assertEqual([n for n, _ in rows], ["Task_001_thing", "Task_002_other"])
        self.assertEqual(dict(rows)["Task_001_thing"], True)
        self.assertEqual(dict(rows)["Task_002_other"], False)


class TestItRuns(unittest.TestCase):
    def test_the_script_executes_and_prints_the_file_count(self):
        fx = Fixture()
        self.addCleanup(fx.cleanup)
        fx.session("a.jsonl", [assistant([("bash", {"command": "ls"})])])
        p = subprocess.run([sys.executable, SCRIPT, fx.dir], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=120)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("1", p.stdout)
        self.assertRegex(p.stdout.lower(), r"scanned|session")


if __name__ == "__main__":
    unittest.main()
