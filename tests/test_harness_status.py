"""The sixty-second status screen, checked against a captured session.

Written after the owner said 「我看不懂,沒辦法決定」: forming a view on one config
flag required five concepts across three documents. The screen exists so that
"is this thing helping" has an answer somebody can read without a briefing.

Which makes its NUMBERS the thing that must not be wrong. A status page that
quietly under-reports is worse than none — it is the reassuring version of no
information, and this repo has the scar in the other direction (`global_dod.md`
sat for weeks as an unfilled template that nothing checked).

`scan()` takes its files as an argument precisely so this can drive it without a
`~/.pi` on the machine, which is also why the screen is excluded from CI: on a
runner its input does not exist and it would print zeros and exit 0 forever.
"""

import importlib.util
import io
import os
import unittest
from pathlib import Path

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIXTURE = ROOT / "tests" / "fixtures" / "session-task-claim.jsonl"


def load():
    spec = importlib.util.spec_from_file_location(
        "harness_status", ROOT / "scripts" / "harness-status.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestTheNumbersComeFromTheSessions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()
        cls.s = cls.m.scan([str(FIXTURE)])

    def test_the_fixture_is_real_session_bytes(self):
        """Same fixture the session miner uses — extracted from session
        019fe8a0, not written. A fixture that invents its payload is how a guard
        passed six tests and fired zero times live."""
        self.assertTrue(FIXTURE.is_file())
        first = io.open(FIXTURE, encoding="utf-8").readline()
        self.assertIn('"type": "message"', first)

    def test_it_counts_the_tool_calls(self):
        self.assertGreater(self.s["calls"], 0,
                           "a session with tool calls reported none")

    def test_it_knows_which_guards_ever_fired(self):
        """The number the owner reads as 'how much of this is doing anything'.
        It must come from the miner's marker table, not a second copy that can
        drift from it."""
        self.assertEqual(set(self.s["guard_names"]), load_miner_labels(),
                         "the status page and the miner disagree about the "
                         "guard list, so one of them is reporting on a "
                         "different set than it names")

    def test_an_empty_input_reports_zero_rather_than_crashing(self):
        """A machine with no sessions is a new install, which is exactly when
        somebody runs this."""
        empty = self.m.scan([])
        self.assertEqual(empty["calls"], 0)
        self.assertEqual(empty["sessions"], 0)
        self.assertEqual(len(empty["with_skill"]), 0)

    def test_a_harness_touch_is_counted_only_outside_this_repo(self):
        """`other_harness_touch` is the number that answers 'does it drag me
        back here while I work elsewhere'. Counting the harness's own sessions
        in it would make the figure meaningless and always high."""
        self.assertLessEqual(self.s["other_harness_touch"], self.s["harness_touch"])
        self.assertLessEqual(self.s["other_calls"], self.s["calls"])


def load_miner_labels():
    spec = importlib.util.spec_from_file_location(
        "mine_session", ROOT / "scripts" / "mine-session.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {l for l, _m in mod.REFUSALS}


class TestItSurvivesTheOwnersConsole(unittest.TestCase):
    """The first run of this script died on an emoji AFTER printing most of the
    screen. The owner's default Windows console is cp950; on it a
    UnicodeEncodeError is not cosmetic, it makes the harness look broken when
    only the last line was unprintable."""

    def test_no_astral_characters_are_printed(self):
        src = (ROOT / "scripts" / "harness-status.py").read_text(encoding="utf-8")
        printed = []
        for line in src.splitlines():
            stripped = line.strip()
            if not stripped.startswith(("print(", "_safe_print(")):
                continue
            for ch in line:
                if ord(ch) > 0xFFFF:
                    printed.append((ch, line.strip()[:60]))
        self.assertEqual(printed, [],
                         "these would raise UnicodeEncodeError on cp950: %s"
                         % printed)

    def test_the_safe_printer_does_not_call_itself(self):
        """A blanket rename once turned the fallback into infinite recursion,
        and only running it under cp950 caught it."""
        src = (ROOT / "scripts" / "harness-status.py").read_text(encoding="utf-8")
        body = src.split("def _safe_print(", 1)[1].split("\ndef ", 1)[0]
        self.assertNotIn("_safe_print(", body,
                         "_safe_print calls itself — that is a recursion loop")

    def test_the_fallback_degrades_instead_of_raising(self):
        m = load()
        # A character no cp950 console can render, through the real function.
        try:
            m._safe_print("ok \U0001f7e1")
        except UnicodeEncodeError:
            self.fail("_safe_print raised instead of degrading")


if __name__ == "__main__":
    unittest.main()
