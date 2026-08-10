"""The session miner, checked against a captured session.

Every substantive finding on 2026-08-09/10 came from reading a session log, and
each time the queries were re-derived from scratch. This script is that reading,
fixed — so the thing that must not break is its ability to see what those manual
passes saw.

The fixture is EXTRACTED from a real session (019fe8a0), not written. A fixture
that invents its payload is how a guard passed six tests and fired zero times
live; the envelope shape, the role names and the injected text here are all
Pi's own bytes.
"""

import importlib.util
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIXTURE = ROOT / "tests" / "fixtures" / "session-task-claim.jsonl"


def load():
    spec = importlib.util.spec_from_file_location(
        "mine_session", ROOT / "scripts" / "mine-session.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestMining(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()
        cls.d = cls.m.mine(FIXTURE)

    def test_the_fixture_is_real_session_bytes(self):
        """Envelope shape included. Reading the outer object as the message
        produced three structural zeros in one day."""
        first = json.loads(FIXTURE.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(first.get("type"), "message")
        self.assertIn("message", first)
        self.assertIn("role", first["message"])

    def test_it_counts_turns_and_calls(self):
        self.assertGreater(self.d["assistants"], 0)
        self.assertGreater(self.d["tool_calls"], 0)

    def test_it_finds_the_task_constitution_that_was_delivered(self):
        """This is the injection whose delivery was proven by hand in 019fe8a0."""
        self.assertGreaterEqual(self.d["injections"]["task constitution"], 1)

    def test_it_finds_the_phase_gate_refusal(self):
        self.assertGreaterEqual(self.d["refusals"]["phase gate"], 1)

    def test_it_flags_the_attribution_risk(self):
        """The manual finding that mattered most in that session: the model read
        role.md and recipe.md itself before the claim, so the deliverable's use
        of them cannot be credited to the injection."""
        reads = " ".join(self.d["read_paths"]).lower()
        self.assertTrue("role.md" in reads or "recipe.md" in reads)

    def test_the_verbatim_blocks_render_without_mojibake(self):
        """`--full` prints the injected text itself, which is Chinese, and this
        console is cp950. A report that cannot be read gets skimmed past, which
        is the same as not writing it.

        Asserted on the --full path rather than the summary: the summary's own
        labels are English, and asserting Chinese there failed while the code
        was correct — a test written against what I assumed the output looked
        like instead of what it is."""
        buf = io.StringIO()
        self.m.report(self.d, True, buf)
        text = buf.getvalue()
        self.assertIn("任務專屬憲法", text)
        self.assertIn("Local DoD", text)


class TestItReportsRatherThanJudges(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_an_empty_session_reports_zero_injections_explicitly(self):
        """Silence and zero must not look the same. "no injections" is a finding
        and has to be printed as one — a blank section reads as "not checked"."""
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        f = tmp / "s.jsonl"
        f.write_text(json.dumps({"type": "message",
                                 "message": {"role": "user", "content": "hi"}}) + "\n",
                     encoding="utf-8")
        buf = io.StringIO()
        self.m.report(self.m.mine(f), False, buf)
        out = buf.getvalue()
        self.assertIn("none", out)
        self.assertIn("does not distinguish", out,
                      "an empty result must say what it cannot rule out")

    def test_consecutive_identical_refusals_are_called_out(self):
        """Five byte-identical repeats were found by hand on 2026-08-10; the
        miner exists so the next five are found by running it."""
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        f = tmp / "s.jsonl"
        same = {"type": "message", "message": {
            "role": "toolResult", "isError": True,
            "content": [{"type": "text", "text": "C.A.S.E. 階段閘(CLAIM):一樣的話"}]}}
        f.write_text("\n".join(json.dumps(same, ensure_ascii=False)
                               for _ in range(3)) + "\n", encoding="utf-8")
        buf = io.StringIO()
        self.m.report(self.m.mine(f), False, buf)
        self.assertIn("repeat the one before them", buf.getvalue())

    def test_the_label_tables_are_declared_not_derived(self):
        """Deriving these by scanning the bridges matched comments and fixtures
        too. A label that stops matching should report zero — which is a finding
        — rather than silently match something else."""
        src = (ROOT / "scripts" / "mine-session.py").read_text(encoding="utf-8")
        self.assertIn("INJECTIONS = [", src)
        self.assertIn("REFUSALS = [", src)
        self.assertIn("Declared, never derived", src)

    def test_every_declared_label_still_exists_in_a_bridge(self):
        """The other direction: a marker nobody emits any more reports zero
        forever and looks like a mechanism that never fires."""
        m = load()
        haystack = ""
        for p in (ROOT / "pi-extensions").rglob("*.ts"):
            if "node_modules" in str(p):
                continue
            haystack += p.read_text(encoding="utf-8", errors="replace")
        missing = [label for label, marker in m.INJECTIONS if marker not in haystack]
        self.assertEqual(missing, [],
                         "these injection markers are emitted by no bridge: %s"
                         % missing)


if __name__ == "__main__":
    unittest.main()
