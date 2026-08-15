"""The check that would have caught the 2026-08-13 session before it ran.

The defect it exists for: the served chat template taught the model to emit tool
calls as `<atem:function_calls>/<atem:invoke>/<atem:parameter>` while Pi drove it
with native OpenAI `tool_calls`. The model closed its last argument the way its
template taught it and `</atem:parameter>` landed inside the argument value — 24
times in one session, once inside a `path` (ENOENT), and into 20 files on disk.

The positive fixture is REAL BYTES: `tests/fixtures/chat-template-atem.jinja` was
captured from `http://127.0.0.1:8080/props` on 2026-08-14 while the offending
server was still running, 9532 bytes, sha256 recorded below. It is pinned rather
than described because the whole class of failure here is "what the server
actually loaded is not what anyone believed", and a fixture written from belief
would reproduce the same mistake.

The negative fixture is stock ChatML — a real template that carries no tool-call
dialect at all. It is short and well known, so it is written out rather than
captured; nothing about the detector depends on its length.

None of these tests need a model server.
"""

import importlib.util
import hashlib
import json
import os
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(ROOT, "tests", "fixtures")
ATEM = os.path.join(FIXTURES, "chat-template-atem.jinja")
CHATML = os.path.join(FIXTURES, "chat-template-chatml.jinja")
# Captured 2026-08-15 from the server after the owner swapped models, and the
# reason this file grew a second real template: the first version of the script
# read this one as teaching nothing and passed it for the wrong reason. It
# teaches its dialect outright ("ONLY reply in the following format",
# "<IMPORTANT> ... MUST follow the specified format") — and that is FINE, because
# llama.cpp parses that shape back into real tool_calls. Verified live:
# finish_reason=tool_calls, arguments {"path":"README.md"}, empty content.
QWEN = os.path.join(FIXTURES, "chat-template-qwen38.jinja")
QWEN_SHA256 = "c3cf9e34abf4f9e36c2d72165aa9c132d3e2a725b6c2586aaa3a8af9d7a81041"

# Captured 2026-08-14 from the live server (model_alias muse-glimmer-30B-abliterated,
# Q6_K). If this changes, the fixture was edited and every assertion below is
# about a different template than the one that caused the defect.
ATEM_SHA256 = "6bbce2a5b3b0f154935b89c9efb0a8caf19119a9c478b268f2359e2a0946a4b2"


def load():
    spec = importlib.util.spec_from_file_location(
        "check_model_serving", os.path.join(ROOT, "scripts", "check-model-serving.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestTheFixtureIsWhatWasServed(unittest.TestCase):
    def test_the_captured_template_has_not_been_edited(self):
        got = hashlib.sha256(read(ATEM).encode("utf-8")).hexdigest()
        self.assertEqual(got, ATEM_SHA256,
                         "the pinned template changed; re-capture and update the "
                         "sha, do not edit the fixture")

    def test_it_carries_the_tags_the_session_leaked(self):
        """`</atem:parameter>` is what the model appended to its last argument.
        If the fixture no longer contains it, it is not the template under
        study."""
        raw = read(ATEM)
        self.assertIn("<atem:function_calls>", raw)
        self.assertIn("</atem:parameter>", raw)


class TestDialectDetection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_the_namespaced_dialect_is_found(self):
        """The whole defect was a prefix: the harness's own FAKE_TOOL_CALL_PATTERN
        matched `<invoke` and `<parameter name=`, so `<atem:invoke` and
        `<atem:parameter name=` walked past every detector in the repo."""
        got = self.m.find_dialects(read(ATEM))
        self.assertTrue(got, "the real template registered as clean")
        tags = {t for _n, ts in got for t in ts}
        self.assertIn("<atem:function_calls>", tags)
        self.assertIn("<atem:parameter name=", tags)

    def test_the_bare_dialect_is_still_found(self):
        """Adding the prefix must not have cost the unprefixed form."""
        tags = {t for _n, ts in self.m.find_dialects(
            '<function_calls><invoke name="x"><parameter name="y">') for t in ts}
        self.assertIn("<function_calls>", tags)
        self.assertIn("<parameter name=", tags)

    def test_other_dialects_are_recognised(self):
        for text, expect in (("<tool_call>", "qwen-style <tool_call>"),
                             ("<function=write>", "qwen-style <function=>"),
                             ("<tools>", "hermes-style <tools>")):
            with self.subTest(text=text):
                names = [n for n, _ in self.m.find_dialects(text)]
                self.assertIn(expect, names)

    def test_a_clean_template_finds_nothing(self):
        """Proving the detector can say no. A detector that fires on everything
        is the same as one that fires on nothing."""
        self.assertEqual(self.m.find_dialects(read(CHATML)), [])
        self.assertFalse(self.m.teaches_dialect(read(CHATML)))


class TestTeachingIsNotTheDefect(unittest.TestCase):
    """The correction this file exists to lock in.

    The first version of the script failed ANY template that taught a tool-call
    dialect, reasoning that Pi drives the model with native OpenAI tool_calls.
    The very first model swap after it shipped produced a counter-example: the
    Qwen3.8 template teaches `<tool_call><function=name><parameter=key>`, and a
    live probe returned `finish_reason: tool_calls` with structured arguments and
    empty content — llama.cpp has a parser for that shape and converts it back.

    Teaching a dialect is not the defect. Teaching one nothing can read back is.
    """

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_the_qwen_fixture_has_not_been_edited(self):
        got = hashlib.sha256(read(QWEN).encode("utf-8")).hexdigest()
        self.assertEqual(got, QWEN_SHA256)

    def test_the_qwen_template_does_teach_its_dialect(self):
        """The specific miss: the original TEACHES pattern had only the
        "you can/should/must invoke…" family and read this template as teaching
        nothing. It says otherwise in two places."""
        raw = read(QWEN)
        self.assertIn("reply in the following format", raw)
        self.assertTrue(self.m.teaches_dialect(raw),
                        "the heuristic is blind to this phrasing again")

    def test_a_parseable_dialect_taught_is_a_warning_not_a_failure(self):
        r = self.m.assess({}, template=read(QWEN))
        self.assertEqual(r["failures"], [], "a working configuration was failed")
        self.assertTrue(r["warnings"])

    def test_an_unparseable_dialect_taught_is_a_failure(self):
        r = self.m.assess({}, template=read(ATEM))
        self.assertTrue(r["failures"])
        self.assertIn("no server-side parser reads that shape back", r["failures"][0])

    def test_the_two_templates_are_separated_by_parseability_not_by_teaching(self):
        """Both teach. Only one is broken. If this ever collapses to one answer,
        the distinction has been lost again."""
        self.assertTrue(self.m.teaches_dialect(read(ATEM)))
        self.assertTrue(self.m.teaches_dialect(read(QWEN)))
        self.assertEqual(
            self.m.unparseable_dialects(self.m.find_dialects(read(QWEN))), [])
        self.assertEqual(
            self.m.unparseable_dialects(self.m.find_dialects(read(ATEM))),
            ["anthropic-style XML"])


class TestTheLiveProbeOutranksTheHeuristics(unittest.TestCase):
    """A jinja template is prose, and a heuristic over prose has already been
    wrong once. One request with one tool answers the actual question: does THIS
    configuration produce native tool calls."""

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_no_tool_calls_returned_is_a_failure(self):
        r = self.m.assess({}, template=read(CHATML), probe={
            "finish_reason": "stop", "native_tool_calls": 0, "arguments": [],
            "content_head": "I would call read(README.md)."})
        self.assertTrue(r["failures"])
        self.assertIn("no native tool_calls", r["failures"][0])
        self.assertIn("I would call", r["failures"][0],
                      "the text it replied with instead is the evidence")

    def test_a_real_tool_call_passes_even_on_a_dialect_teaching_template(self):
        """The measured Qwen case, end to end."""
        r = self.m.assess({}, template=read(QWEN), probe={
            "finish_reason": "tool_calls", "native_tool_calls": 1,
            "arguments": ['{"path":"README.md"}'], "content_head": ""})
        self.assertEqual(r["failures"], [])

    def test_dialect_markup_surviving_into_arguments_is_a_failure(self):
        """The 2026-08-13 shape: a native call came back and its argument still
        carried the closing tag. That text is what reaches the filesystem."""
        r = self.m.assess({}, template=read(CHATML), probe={
            "finish_reason": "tool_calls", "native_tool_calls": 1,
            "arguments": ['{"path":"README.md</atem:parameter>"}'],
            "content_head": ""})
        self.assertTrue(r["failures"])
        self.assertIn("still carry", r["failures"][0])

    def test_the_mangled_tag_is_recognised_in_an_argument(self):
        """`</atem:日>` is the tag as it actually decoded, and a template scan
        cannot find it: templates show OPENING tags, arguments carry the closing
        one. Reusing the template patterns here matched nothing, which is how
        this test earned its place."""
        r = self.m.assess({}, template=read(CHATML), probe={
            "finish_reason": "tool_calls", "native_tool_calls": 1,
            "arguments": ['{"path":"a/.gitignore</atem:日>"}'], "content_head": ""})
        self.assertTrue(r["failures"])

    def test_a_clean_argument_is_not_flagged(self):
        r = self.m.assess({}, template=read(CHATML), probe={
            "finish_reason": "tool_calls", "native_tool_calls": 1,
            "arguments": ['{"path":"README.md"}'], "content_head": ""})
        self.assertEqual(r["failures"], [])

    def test_an_unreachable_server_is_not_probed_and_not_failed(self):
        """A slow or absent server must degrade to "not probed", never to a
        verdict — the same reason the whole script SKIPs without one."""
        r = self.m.assess({}, template=read(CHATML), probe={"error": "timed out"})
        self.assertEqual(r["failures"], [])

    def test_the_probe_never_raises(self):
        got = self.m.probe_tool_call("http://127.0.0.1:59999", timeout=3)
        self.assertIn("error", got)


class TestTheJudgement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_the_real_template_fails(self):
        r = self.m.assess({}, template=read(ATEM))
        self.assertTrue(r["failures"], "the template that caused the defect passed")
        self.assertIn("no server-side parser reads that shape back", r["failures"][0])

    def test_the_clean_template_passes(self):
        r = self.m.assess({}, template=read(CHATML))
        self.assertEqual(r["failures"], [])
        self.assertEqual(r["warnings"], [])

    def test_rendering_a_dialect_without_teaching_it_is_only_a_warning(self):
        """A template that renders a tool result back in some dialect is doing
        its job. The failure is the instruction block that tells the model to
        WRITE one. Keeping these separable is what stops this check becoming a
        gate everybody routes around."""
        renders_only = '{{- "<atem:function_calls>" -}}{{- "</atem:parameter>" -}}'
        r = self.m.assess({}, template=renders_only)
        self.assertEqual(r["failures"], [])
        self.assertTrue(r["warnings"])

    def test_mmproj_is_only_mentioned_alongside_a_dialect(self):
        """Multimodal is not a defect; it is the documented trigger for the
        silent template fallback. Saying so on a clean template would be noise."""
        vision = {"modalities": {"vision": True}}
        clean = self.m.assess(dict(vision), template=read(CHATML))
        self.assertEqual(clean["warnings"], [])
        dirty = self.m.assess(dict(vision), template=read(ATEM))
        self.assertTrue(any("mmproj" in w for w in dirty["warnings"]))

    def test_the_expected_model_is_checked_against_path_and_alias(self):
        props = {"model_path": r"C:\models\Muse-Glimmer-30B-Abliterated-Q6_K.gguf",
                 "model_alias": "muse-glimmer-30B-abliterated"}
        ok = self.m.assess(props, template="", expect_model="muse-glimmer")
        self.assertEqual(ok["failures"], [])
        bad = self.m.assess(props, template="", expect_model="qwen3.6-froggeric")
        self.assertTrue(any("expected a model" in f for f in bad["failures"]))

    def test_a_loading_server_fails_rather_than_being_measured(self):
        """Checklist §1: while a model loads, /props answers and
        /v1/chat/completions returns 503. Measuring then measures the loader."""
        loading = self.m.assess({}, template="", completions_status=503)
        self.assertTrue(any("503" in f for f in loading["failures"]))
        ready = self.m.assess({}, template="", completions_status=200)
        self.assertEqual(ready["failures"], [])

    def test_the_template_hash_is_reported(self):
        """The operator's question after a restart is 'did the file take'. A
        length is not an answer; a hash is."""
        r = self.m.assess({}, template=read(ATEM))
        self.assertEqual(r["template_sha256"], ATEM_SHA256)
        self.assertEqual(r["template_bytes"], 9532)


class TestTheReportAndTheExitCode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_the_report_survives_the_session(self):
        """`ctx.ui.notify` is gone when the session ends. The file is what a
        later question can be answered from — same reason
        skill-conflict-report.json exists."""
        d = tempfile.mkdtemp()
        try:
            p = os.path.join(d, "report.json")
            self.assertTrue(self.m.write_report(
                self.m.assess({}, template=read(ATEM)), p))
            with open(p, encoding="utf-8") as f:
                back = json.load(f)
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)
        self.assertEqual(back["template_sha256"], ATEM_SHA256)
        self.assertTrue(back["failures"])

    def test_a_bad_template_exits_nonzero(self):
        d = tempfile.mkdtemp()
        try:
            code = self.m.main(["--template", ATEM,
                                "--report", os.path.join(d, "r.json")])
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)
        self.assertEqual(code, 1)

    def test_a_clean_template_exits_zero(self):
        d = tempfile.mkdtemp()
        try:
            code = self.m.main(["--template", CHATML,
                                "--report", os.path.join(d, "r.json")])
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)
        self.assertEqual(code, 0)

    def test_no_server_is_a_skip_not_a_pass_and_not_a_failure(self):
        """CI has no model server. Reporting green there would make this check
        a decoration; reporting red would make it noise. Same semantics as
        verify-bridges.py's drift check."""
        d = tempfile.mkdtemp()
        try:
            code = self.m.main(["--url", "http://127.0.0.1:59999",
                                "--report", os.path.join(d, "r.json")])
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
