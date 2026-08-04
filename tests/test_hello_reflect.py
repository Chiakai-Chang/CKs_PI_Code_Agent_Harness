"""hello-reflect was reading Claude Code's session format against Pi's files.

`reflect_core.extract_user_messages` looked for a top-level `role` and a string
`content`. A Pi session line is:

    {"type":"message","message":{"role":"user","content":[{"type":"text","text":"…"}]}}

so the role is nested and the content is a list of blocks. Measured against a real
session file on 2026-08-04:

    exists: True
    extract_user_messages -> 0 messages
    a real user line: top-level role = None | nested role = user | content type = list

It has never read a single message, which is why the bridge's turn_end hook could
detect learnings on no session it was ever given.

Both shapes stay supported: the skill is distilled from claude-reflect and may be
pointed at a Claude Code transcript somewhere else.
"""

import importlib.util
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "pi-skills", "core", "hello-reflect", "scripts")

spec = importlib.util.spec_from_file_location(
    "reflect_core", os.path.join(SCRIPTS, "reflect_core.py"))
reflect = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reflect)


def session(lines):
    base = tempfile.mkdtemp(prefix="reflect-")
    path = os.path.join(base, "s.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    return base, Path(path)


class TestPiSessionFormat(unittest.TestCase):
    def _extract(self, lines):
        base, path = session(lines)
        self.addCleanup(lambda: shutil.rmtree(base, ignore_errors=True))
        return reflect.extract_user_messages(path)

    def test_reads_a_pi_user_message(self):
        out = self._extract([
            {"type": "message", "message": {"role": "user",
                                            "content": [{"type": "text", "text": "no, do it this way"}]}},
        ])
        self.assertEqual(out, ["no, do it this way"])

    def test_joins_several_text_blocks_from_one_message(self):
        out = self._extract([
            {"type": "message", "message": {"role": "user", "content": [
                {"type": "text", "text": "first"},
                {"type": "text", "text": "second"},
            ]}},
        ])
        self.assertEqual(len(out), 1)
        self.assertIn("first", out[0])
        self.assertIn("second", out[0])

    def test_ignores_non_text_blocks(self):
        """A toolResult block is not something the user said."""
        out = self._extract([
            {"type": "message", "message": {"role": "user", "content": [
                {"type": "toolResult", "text": "command output"},
                {"type": "text", "text": "actual words"},
            ]}},
        ])
        self.assertEqual(out, ["actual words"])

    def test_ignores_assistant_and_tool_result_messages(self):
        out = self._extract([
            {"type": "message", "message": {"role": "assistant",
                                            "content": [{"type": "text", "text": "mine"}]}},
            {"type": "message", "message": {"role": "toolResult",
                                            "content": [{"type": "text", "text": "output"}]}},
            {"type": "message", "message": {"role": "user",
                                            "content": [{"type": "text", "text": "theirs"}]}},
        ])
        self.assertEqual(out, ["theirs"])

    def test_skips_session_metadata_lines(self):
        out = self._extract([
            {"type": "session", "id": "x"},
            {"type": "model_change", "model": "y"},
            {"type": "message", "message": {"role": "user",
                                            "content": [{"type": "text", "text": "hi"}]}},
        ])
        self.assertEqual(out, ["hi"])

    def test_an_empty_message_is_not_returned(self):
        out = self._extract([
            {"type": "message", "message": {"role": "user", "content": [{"type": "text", "text": "   "}]}},
        ])
        self.assertEqual(out, [])


class TestClaudeCodeSessionFormatStillWorks(unittest.TestCase):
    """Distilled from claude-reflect; it may still be pointed at one of those."""

    def _extract(self, lines):
        base, path = session(lines)
        self.addCleanup(lambda: shutil.rmtree(base, ignore_errors=True))
        return reflect.extract_user_messages(path)

    def test_reads_a_top_level_role_with_string_content(self):
        out = self._extract([{"role": "user", "content": "remember to run tests"}])
        self.assertEqual(out, ["remember to run tests"])

    def test_still_ignores_the_assistant(self):
        out = self._extract([
            {"role": "assistant", "content": "mine"},
            {"role": "user", "content": "theirs"},
        ])
        self.assertEqual(out, ["theirs"])


class TestMalformedInput(unittest.TestCase):
    def test_a_broken_line_does_not_stop_the_scan(self):
        base = tempfile.mkdtemp(prefix="reflect-bad-")
        self.addCleanup(lambda: shutil.rmtree(base, ignore_errors=True))
        path = os.path.join(base, "s.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            f.write("{not json\n")
            f.write(json.dumps({"type": "message", "message": {
                "role": "user", "content": [{"type": "text", "text": "survived"}]}}) + "\n")
        self.assertEqual(reflect.extract_user_messages(Path(path)), ["survived"])

    def test_a_missing_file_is_empty_not_an_error(self):
        self.assertEqual(reflect.extract_user_messages(Path("nope.jsonl")), [])


class TestAgainstARealPiSession(unittest.TestCase):
    """The fixtures above encode what I believe Pi writes. This one reads what Pi
    actually wrote, and skips where there is nothing to read."""

    def test_a_real_session_yields_messages(self):
        base = os.path.join(os.path.expanduser("~"), ".pi", "agent", "sessions")
        if not os.path.isdir(base):
            self.skipTest("no local Pi sessions to read")
        newest, newest_mtime = None, 0
        for dirpath, _dirs, files in os.walk(base):
            for fn in files:
                if not fn.endswith(".jsonl"):
                    continue
                full = os.path.join(dirpath, fn)
                try:
                    mtime = os.path.getmtime(full)
                except OSError:
                    continue
                if mtime > newest_mtime:
                    newest, newest_mtime = full, mtime
        if not newest:
            self.skipTest("no session files found")
        self.assertGreater(len(reflect.extract_user_messages(Path(newest))), 0,
                           "read no user messages from %s" % newest)


if __name__ == "__main__":
    unittest.main()
