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
import re
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

    @staticmethod
    def _bridge_sources():
        haystack = ""
        # The C.A.S.E. adapter moved to the protocol's repository on 2026-08-17.
        # Its guards still refuse inside real sessions, so their markers are not
        # dead — the source just is not under pi-extensions any more. Scanning
        # only there would have declared eight live C.A.S.E. markers dead the
        # day after the split, which is the same class of wrong reading this
        # check exists to prevent.
        roots = [ROOT / "pi-extensions",
                 ROOT / "external" / "Local-Agent-Workspace" / "adapters"]
        for root in roots:
            if not root.is_dir():
                continue  # a clone without submodules is a normal state
            for p in root.rglob("*.ts"):
                if "node_modules" in str(p):
                    continue
                haystack += p.read_text(encoding="utf-8", errors="replace")
        return haystack

    def test_every_declared_label_still_exists_in_a_bridge(self):
        """The other direction: a marker nobody emits any more reports zero
        forever and looks like a mechanism that never fires.

        This checked INJECTIONS only until 2026-08-14, and three REFUSAL markers
        had died behind the gap: `queue guard`/`C.A.S.E. 任務佇列` (superseded by
        the per-rule labels), `research depth`/`研究深度`, and
        `citation gate`/`引用`. The last one is why the omission mattered —
        `引用` is ordinary Chinese, so on a Chinese session it did not report
        zero, it reported two, from prose. A dead marker is not silent; it is
        silent about its own guard and loud about everything else."""
        m = load()
        haystack = self._bridge_sources()
        # Markers whose guard lives in the C.A.S.E. adapter, an optional
        # submodule since 2026-08-17. Without it checked out they cannot be
        # found here — and that is not a dead marker: the guard still refuses
        # inside real sessions, its source is simply in another repository.
        # Listed by name so a marker that dies in THIS repo still fails while
        # the adapter is away.
        adapter = ROOT / "external" / "Local-Agent-Workspace" / "adapters"
        skip = set() if adapter.is_dir() else {
            "phase gate", "dod artifacts", "status value", "transition",
            "one-at-a-time", "retrospective", "dual-track", "boundary",
            "tool-first", "task constitution", "phase reopened",
            "task goal restatement",
        }
        missing = [label for label, marker in m.INJECTIONS + m.REFUSALS
                   if label not in skip and marker not in haystack]
        self.assertEqual(missing, [],
                         "these markers are emitted by no bridge: %s" % missing)

    def test_every_guard_in_a_bridge_has_a_marker(self):
        """The other direction, and the one that was missing.

        `test_every_declared_label_still_exists_in_a_bridge` asks whether a
        marker still matches something. Nothing asked whether a GUARD has a
        marker, so a refusal text could ship with no way to see it — and four
        had: Repeat-lookup, Repeat-call, Repeat-call breaker and Turn-end
        context. On 2026-08-16 `Repeat-lookup guard` refused EIGHTEEN times in a
        single run while the report showed no loop refusals at all, and that was
        about to be written up as "the loop guard stayed silent".

        Guards are found by their own naming convention rather than by a list,
        so a new one cannot arrive unnoticed.
        """
        m = load()
        markers = [mk for _l, mk in m.INJECTIONS + m.REFUSALS]
        pat = re.compile(r"[A-Z][\w -]{2,28}?(?: guard| gate| breaker| detector):")
        uncovered = {}
        for p in (ROOT / "pi-extensions").rglob("*.ts"):
            if "node_modules" in str(p):
                continue
            src = p.read_text(encoding="utf-8", errors="replace")
            # Comments describe guards; only emitted strings need a marker.
            src = re.sub(r"/\*[\s\S]*?\*/", "", src)
            src = re.sub(r"(?m)^\s*//.*$", "", src)
            lines = src.splitlines()
            for hit in pat.finditer(src):
                name = hit.group(0)
                if any(mk in name or name in mk for mk in markers):
                    continue
                # `ctx.ui.notify` paints the TUI and reaches no session log, so
                # a marker for it would report 0 forever and read as a dead
                # guard. Requiring one is how "Repeat-call breaker:" was nearly
                # counted as a guard that never fires -- and then nearly deleted.
                ln = src[:hit.start()].count(chr(10))
                window = chr(10).join(lines[max(0, ln - 3):ln + 1])
                if "ui.notify(" in window:
                    continue
                uncovered.setdefault(name, p.name)
        self.assertEqual(
            uncovered, {},
            "these guards emit a refusal no marker can see, so every report "
            "shows them as never firing: %s" % uncovered)

    def test_no_marker_can_be_swallowed_by_another(self):
        """Two labels cannot share a hit. If one marker contains another, the
        shorter one fires on every message the longer one matches, and the
        report shows two mechanisms where one spoke."""
        m = load()
        table = m.INJECTIONS + m.REFUSALS
        clashes = [(a, b) for a, ma in table for b, mb in table
                   if a != b and ma in mb]
        self.assertEqual(clashes, [],
                         "marker of the first is contained in the second: %s"
                         % clashes)

    def test_every_customtype_a_bridge_sends_is_claimed(self):
        """A delivery channel this script does not recognise reads as 'that
        guard never fired'. Session 019ffbba was mined as `injections: none /
        refusals: none` while carrying four custom messages."""
        m = load()
        declared = set(re.findall(r'customType:\s*"([^"]+)"',
                                  self._bridge_sources()))
        self.assertTrue(declared, "found no customType at all — regex rotted")
        unclaimed = sorted(declared - set(m.CUSTOM_TYPE_ALLOWED))
        self.assertEqual(unclaimed, [],
                         "not in CUSTOM_TYPE_ALLOWED: %s" % unclaimed)

    def test_the_allowed_labels_are_real_labels(self):
        """A typo in CUSTOM_TYPE_ALLOWED silently forbids everything for that
        type, which looks exactly like a guard that never fires."""
        m = load()
        known = {l for l, _ in m.INJECTIONS} | {l for l, _ in m.REFUSALS}
        for ctype, labels in m.CUSTOM_TYPE_ALLOWED.items():
            with self.subTest(ctype=ctype):
                self.assertEqual(sorted(set(labels) - known), [],
                                 "%s allows labels that do not exist" % ctype)


class TestTheSendMessageChannel(unittest.TestCase):
    """The miner read one channel and reported on two.

    `records()` kept only `{"type":"message"}`, so everything a bridge delivers
    through `pi.sendMessage` — a `custom_message` record — was dropped before any
    counting. Session 019ffbba was mined as "injections: none / refusals: none"
    while carrying four corrections, and the labels `blocked-claim` and
    `loop guard` could never have counted anything at all, because both of those
    guards speak only on this channel.

    The fixture is a contiguous slice of that session's own bytes (records 5–12:
    the four corrections and the four turns between them). The big first turn and
    the user's prompt are outside the slice; nothing in it is written by hand."""

    FIXTURE = ROOT / "tests" / "fixtures" / "session-fake-tool-call-loop.jsonl"

    @classmethod
    def setUpClass(cls):
        cls.m = load()
        cls.d = cls.m.mine(cls.FIXTURE)

    def test_the_fixture_is_real_session_bytes(self):
        first = json.loads(self.FIXTURE.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(first.get("type"), "custom_message")
        self.assertIn("customType", first)
        self.assertIn("content", first)

    def test_custom_messages_are_counted_at_all(self):
        self.assertEqual(sum(self.d["custom_messages"].values()), 4)

    def test_they_are_counted_by_the_type_the_sender_declared(self):
        """Not by a marker guessed from the wording. The sender knows which
        mechanism spoke; a marker only knows which sentence matched, and this
        repo has already attributed one bridge's wording to another's label."""
        self.assertEqual(self.d["custom_messages"]["loop-guard"], 2)
        self.assertEqual(self.d["custom_messages"]["universal-tag-transformer"], 2)

    def test_a_sendmessage_only_guard_now_appears_in_the_refusals_table(self):
        """`blocked-claim`'s marker is 「你剛才說」 and it has only ever been
        delivered by sendMessage — so its label reported zero in every session
        ever mined, which reads as "the guard never fired"."""
        self.assertGreaterEqual(self.d["refusals"]["blocked-claim"], 1)

    def test_the_report_names_the_channel(self):
        buf = io.StringIO()
        self.m.report(self.d, False, buf)
        out = buf.getvalue()
        self.assertIn("custom messages   4", out)
        self.assertIn("sendMessage", out)
        self.assertIn("universal-tag-transformer", out)

    def test_a_verbatim_repeat_on_this_channel_is_called_out(self):
        """Two of the four corrections are byte-identical — the transformer sent
        the same parsed-intent message twice and the model repeated its fake call
        both times. That is the finding in this session, and it is on a channel
        the repeat detector could not see."""
        buf = io.StringIO()
        self.m.report(self.d, False, buf)
        self.assertIn("custom message(s) repeat the one before them", buf.getvalue())

    def test_the_transformers_own_wording_is_not_a_loop_guard_refusal(self):
        """The defect this fixture happens to carry, and the one measured on
        session 019ffbdd: the transformer's message says 「原文不在此重複」, the
        loop-guard marker was 重複, and the report claimed the loop guard refused
        three times in a session where it refused none. The same three messages
        were already listed correctly by customType, so one batch was counted
        twice under two mechanisms."""
        raw = self.FIXTURE.read_text(encoding="utf-8")
        self.assertIn("原文不在此重複", raw, "fixture no longer carries the wording")
        self.assertEqual(self.d["refusals"]["loop guard"], 0)
        self.assertEqual(self.d["custom_messages"]["universal-tag-transformer"], 2)

    def test_a_type_cannot_borrow_another_types_label(self):
        """Prove the restriction can refuse. The payload here is synthetic on
        purpose — what is under test is the routing, not the wording: a message
        carrying the loop guard's own marker, sent under the transformer's type,
        must not be counted as a loop-guard refusal."""
        m = load()
        rec = {"type": "custom_message", "id": "x",
               "customType": "universal-tag-transformer", "display": True,
               "content": "[SYSTEM] 你發出了完全相同的呼叫、被糾正 3 次仍在重複。"}
        d = tempfile.mkdtemp()
        try:
            p = Path(d) / "s.jsonl"
            p.write_text(json.dumps(rec, ensure_ascii=False) + "\n",
                         encoding="utf-8")
            got = m.mine(p)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        self.assertEqual(got["custom_messages"]["universal-tag-transformer"], 1)
        self.assertEqual(got["refusals"]["loop guard"], 0,
                         "the type did not restrict which label may match")

    def test_an_unknown_customtype_is_reported_not_dropped(self):
        m = load()
        rec = {"type": "custom_message", "id": "x", "customType": "brand-new",
               "display": True, "content": "hello"}
        d = tempfile.mkdtemp()
        try:
            p = Path(d) / "s.jsonl"
            p.write_text(json.dumps(rec, ensure_ascii=False) + "\n",
                         encoding="utf-8")
            got = m.mine(p)
            buf = io.StringIO()
            m.report(got, False, buf)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        self.assertIn("brand-new", got["unknown_custom_types"])
        self.assertIn("customType this script does not know", buf.getvalue())

    def test_a_session_with_no_custom_messages_still_says_so(self):
        """Zero and unchecked must not look the same — the reason this whole
        blind spot survived is that "none" was printed for both."""
        buf = io.StringIO()
        self.m.report(self.m.mine(FIXTURE), False, buf)
        out = buf.getvalue()
        self.assertIn("custom messages   0", out)


if __name__ == "__main__":
    unittest.main()
