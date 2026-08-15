"""Residue from a tool-call dialect the model was taught but Pi does not use.

Session 019ffbdd, 2026-08-13: the served chat template rendered tool calls as
`<atem:function_calls>/<atem:invoke>/<atem:parameter>` and taught the model to
emit them, while Pi drove it with native OpenAI `tool_calls`. The model closed
its last argument the way its template taught it and the closing tag — decoded
mangled as `</atem:日>` — landed INSIDE the argument value: 24 times, into 20
files that are still on disk, and once into a `path`, which produced
`ENOENT ... mkdir '…\\.gitignore<'`.

Nothing saw it. `FAKE_TOOL_CALL_PATTERN` matched `<invoke` and
`<parameter name=`; `ARG_SYNTAX_LEAK` matched `<\\/?parameter\\b`. Neither
matches `<atem:`. One namespace prefix walked an entire tool-call syntax past
every detector in this repo.

The tests below drive the bridge's PUBLIC `tool_call` entry point, not the
helper. That is the shape of a scar here: a guard passed 1287 tests with a
`ReferenceError` on every real call because the unit tests called the pure
helper and the wiring test asserted the source text contained the call.
"""

import json
import os
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import sys as _sys
_sys.path.insert(0, os.path.join(ROOT, "tests"))
from _scratch import scratch  # noqa: E402

IDX = os.path.join(ROOT, "pi-extensions", "yes-hooks-bridge", "index.ts")
MOD = os.path.join(ROOT, "pi-extensions", "yes-hooks-bridge", "dialect-residue.ts")


def node_ok():
    try:
        out = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=30)
        return out.returncode == 0 and int(out.stdout.strip().lstrip("v").split(".")[0]) >= 22
    except Exception:
        return False


NODE_OK = node_ok()

# The measured residue. Kept as an explicit constant so a test that stops
# reproducing the real shape fails loudly rather than passing on a paraphrase.
MANGLED = "</atem:日>"


@unittest.skipUnless(NODE_OK, "node >= 22 required for native TypeScript type stripping")
class TestTheStripper(unittest.TestCase):
    DRIVER = r"""
import { readFileSync } from "node:fs";
import { stripTrailingDialectTags, scrubToolInput } from %(mod)s;
const cases = JSON.parse(readFileSync(process.argv[2], "utf-8"));
const out = [];
for (const c of cases) {
  if (c.kind === "strip") out.push(stripTrailingDialectTags(c.value));
  else { const removed = scrubToolInput(c.tool, c.input); out.push({ removed, input: c.input }); }
}
process.stdout.write(JSON.stringify(out));
"""

    def _run(self, cases):
        driver = scratch(".tmp_residue_driver.mjs")
        payload = scratch(".tmp_residue_input.json")
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

    def test_the_measured_mangled_tag_is_removed(self):
        (r,) = self._run([{"kind": "strip", "value": "hello\n" + MANGLED}])
        self.assertEqual(r["value"], "hello\n")
        self.assertEqual(r["removed"], [MANGLED])

    def test_the_well_formed_tag_is_removed_too(self):
        """The mangling was a decoding accident. The same template on a better
        day emits the tag intact, and that is the same defect."""
        (r,) = self._run([{"kind": "strip", "value": "hello</atem:parameter>"}])
        self.assertEqual(r["value"], "hello")

    def test_a_stack_of_closing_tags_is_removed(self):
        """`</atem:parameter></atem:invoke></atem:function_calls>` closes three
        levels in one breath. An unanchored match finds the FIRST tag, which is
        not at the end, and leaves the whole value untouched — that was the first
        implementation, and this case caught it."""
        (r,) = self._run([{"kind": "strip",
                           "value": "hello</atem:parameter></atem:invoke></atem:function_calls>"}])
        self.assertEqual(r["value"], "hello")
        self.assertEqual(len(r["removed"]), 3)

    def test_legitimate_namespaced_markup_survives(self):
        """A file this agent might honestly write. `</xsl:template>` and
        `</svg:path>` have well-formed local names; the residue does not, and
        that is the whole difference the rule keys on."""
        cases = [{"kind": "strip", "value": v} for v in
                 ("<xsl:template>x</xsl:template>", "a</svg:path>", "<w:p>x</w:p>")]
        for r in self._run(cases):
            self.assertEqual(r["removed"], [], r["value"])

    def test_a_dialect_tag_in_the_middle_survives(self):
        """Documentation about tool calls, a captured template, this repo's own
        postmortem — all legitimate content containing the tag. Only the one the
        decoder appended sits at the very end."""
        (r,) = self._run([{"kind": "strip", "value": "see </atem:parameter> then more text"}])
        self.assertEqual(r["removed"], [])

    def test_a_non_string_or_empty_value_is_returned_unharmed(self):
        """Found by the mutation sweep: flipping `||` to `&&` in the type guard
        sends a null through to `.match` and throws inside a tool_call handler,
        which is the shape that has silently killed a guard here before — an
        exception swallowed by a caller written to fail open."""
        for value in (None, "", 0, [], {"a": 1}):
            with self.subTest(value=value):
                (r,) = self._run([{"kind": "strip", "value": value}])
                self.assertEqual(r["removed"], [])
                self.assertEqual(r["value"], value)

    def test_a_deep_stack_of_tags_is_fully_removed(self):
        """The loop bound is a real decision, not a formality: the mutation sweep
        turned 8 iterations into 7 and no test noticed. Eight closing tags is
        past anything observed and is exactly where an off-by-one shows."""
        (r,) = self._run([{"kind": "strip", "value": "hello" + "</atem:parameter>" * 8}])
        self.assertEqual(r["value"], "hello")
        self.assertEqual(len(r["removed"]), 8)

    def test_a_non_object_input_is_ignored_rather_than_thrown_on(self):
        """From the sweep: `!input || typeof input !== "object"` mutated to `&&`
        lets a null past the early return and into a property write, which throws
        inside a tool_call handler. This runs FIRST in that handler, so an
        exception here does not degrade one guard — it takes the call with it."""
        for value in (None, "text", 7, True):
            with self.subTest(value=value):
                (r,) = self._run([{"kind": "scrub", "tool": "write", "input": value}])
                self.assertEqual(r["removed"], [])

    def test_a_malformed_edits_array_does_not_throw(self):
        """Also from the sweep: `e && typeof e === "object"` mutated to `||`
        lets a null through to a property write. A model that emits a ragged
        `edits` array would then take the whole handler down."""
        (r,) = self._run([{"kind": "scrub", "tool": "edit",
                           "input": {"path": "f.md",
                                     "edits": [None, "x", 7,
                                               {"oldText": "a" + MANGLED, "newText": "b"}]}}])
        self.assertEqual(r["input"]["edits"][3]["oldText"], "a")
        self.assertEqual([x["field"] for x in r["removed"]], ["oldText"])

    def test_write_arguments_are_repaired_in_place(self):
        """Both fields, and the path is the one that produced ENOENT."""
        (r,) = self._run([{"kind": "scrub", "tool": "write",
                           "input": {"path": "a/.gitignore" + MANGLED,
                                     "content": "x\n" + MANGLED}}])
        self.assertEqual(r["input"]["path"], "a/.gitignore")
        self.assertEqual(r["input"]["content"], "x\n")
        self.assertEqual({x["field"] for x in r["removed"]}, {"path", "content"})

    def test_edit_arguments_are_repaired_including_nested_edits(self):
        """Field names come from the installed schema: edit is
        {path, edits[].oldText, edits[].newText}. A guess would repair a field
        that does not exist and leave the one that does."""
        (r,) = self._run([{"kind": "scrub", "tool": "edit",
                           "input": {"path": "f.md" + MANGLED,
                                     "edits": [{"oldText": "a" + MANGLED, "newText": "b"}]}}])
        self.assertEqual(r["input"]["path"], "f.md")
        self.assertEqual(r["input"]["edits"][0]["oldText"], "a")

    def test_bash_and_search_are_left_to_the_runaway_guard(self):
        """Not an oversight — a boundary. runawayArgumentGuard already refuses a
        call whose arguments carry tool-call syntax, and for a `command` or a
        `query` its complaint is the better one: "you kept generating instead of
        stopping at the end of the call" is a model behaviour the model can fix.
        Template residue is not, which is why write/edit are repaired instead.
        Reversing that silently for every field would undo a decision
        test_universal_tool_parser.py states outright."""
        for tool, field, value in (("bash", "command", "ls" + MANGLED),
                                   ("web_search", "query", "hi </tool_call>")):
            with self.subTest(tool=tool):
                (r,) = self._run([{"kind": "scrub", "tool": tool,
                                   "input": {field: value}}])
                self.assertEqual(r["removed"], [])
                self.assertEqual(r["input"][field], value)


@unittest.skipUnless(NODE_OK, "node >= 22 required for native TypeScript type stripping")
class TestItIsWiredIntoTheRealHandler(unittest.TestCase):
    """Through `pi.on("tool_call")`, the way production reaches it.

    The helper returning the right list proves nothing about wiring: a
    DoD-artifact guard once passed 1287 tests while throwing a `ReferenceError`
    on every real call, because the tests drove the helper and the wiring test
    asserted the source *text* contained the call.
    """

    DRIVER = r"""
import { readFileSync } from "node:fs";
import mod from %(mod)s;
const cases = JSON.parse(readFileSync(process.argv[2], "utf-8"));
const store = {};
mod({ on: (e, f) => { (store[e] ??= []).push(f); }, sendMessage() {}, registerTool() {} });
const notices = [];
const ctx = { cwd: %(cwd)s, ui: { notify: (m) => notices.push(String(m)) } };
const out = [];
for (const c of cases) {
  const event = { toolName: c.tool, input: c.input };
  let blocked = false;
  for (const fn of store["tool_call"] ?? []) {
    const r = await fn(event, ctx);
    if (r && r.block) blocked = true;
  }
  out.push({ input: event.input, blocked });
}
process.stdout.write(JSON.stringify({ results: out, notices }));
"""

    def _run(self, cases):
        driver = scratch(".tmp_residue_wire_driver.mjs")
        payload = scratch(".tmp_residue_wire_input.json")
        with open(driver, "w", encoding="utf-8") as f:
            f.write(self.DRIVER % {
                "mod": json.dumps("file:///" + IDX.replace("\\", "/")),
                "cwd": json.dumps(ROOT.replace("\\", "/")),
            })
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

    def test_the_handler_repairs_the_argument_and_lets_the_call_run(self):
        got = self._run([{"tool": "write",
                          "input": {"path": "notes.md", "content": "x\n" + MANGLED}}])
        r = got["results"][0]
        self.assertEqual(r["input"]["content"], "x\n")
        self.assertFalse(r["blocked"], "repairing must not also refuse the call")

    def test_the_path_is_clean_before_the_other_guards_read_it(self):
        """Ordering, not decoration. Session 019ffbdd produced
        `…/.gitignore</atem:日>` as a `path`; containment, the harness-root hint
        and the repeat detector would each have been reasoning about a filename
        the model never meant to write."""
        got = self._run([{"tool": "write",
                          "input": {"path": "notes.md" + MANGLED, "content": "x"}}])
        self.assertEqual(got["results"][0]["input"]["path"], "notes.md")

    def test_the_operator_is_told_and_the_model_is_not(self):
        """The model cannot change its own chat template. Telling it costs a turn
        and, on the evidence of the GateGuard misdelivery in this same session,
        can change what it does next for the worse. So: notify (operator), no
        block and no reason (model)."""
        got = self._run([{"tool": "write",
                          "input": {"path": "a.md", "content": "x" + MANGLED}}])
        self.assertTrue(any("check-model-serving" in n for n in got["notices"]),
                        "the notice must name the command that finds the cause")
        self.assertFalse(got["results"][0]["blocked"])

    def test_the_operator_is_told_once_not_once_per_call(self):
        """The measured session would have produced 24 of these. That is the
        `📝 偵測到新學習點` failure — a notice that repeated 122 times and meant
        nothing by the third."""
        got = self._run([{"tool": "write", "input": {"path": "a%d.md" % i,
                                                     "content": "x" + MANGLED}}
                         for i in range(5)])
        residue_notices = [n for n in got["notices"] if "check-model-serving" in n]
        self.assertEqual(len(residue_notices), 1)

    def test_a_clean_call_is_untouched_and_silent(self):
        got = self._run([{"tool": "write", "input": {"path": "a.md", "content": "hello"}}])
        self.assertEqual(got["results"][0]["input"]["content"], "hello")
        self.assertEqual([n for n in got["notices"] if "check-model-serving" in n], [])


class TestEveryToolCallPatternLearnedThePrefix(unittest.TestCase):
    """Every regex in this file that matches a tool-call tag, not just the two
    that were fixed first.

    On 2026-08-15 a consistency pass found the job half done: FAKE_TOOL_CALL_PATTERN
    and ARG_SYNTAX_LEAK had the prefix, and PARAM_TAG_PATTERN, the `<invoke
    name=>` fallback, the `<tool_call>` wrapper and both `<function=>` patterns
    did not. That is worse than not having started, because the comments on the
    first two say the dialect problem is handled and a reader would believe them.

    So this asserts on the SET, not on the members: a new tool-call pattern
    without a prefix fails here even if nobody remembers this class exists.
    """

    # `<bash>`, `<read>` and friends are single-word harness/Claude tags with no
    # namespace form in any template observed, and CHILD_TAG_PATTERN is a
    # generic `<name>…</name>` matcher whose whole job is to accept any name.
    # Only the tags that belong to a tool-call DIALECT are required to carry it.
    DIALECT_WORDS = ("invoke", "parameter", "function_calls", "tool_call", "function")
    PREFIX = r"(?:[A-Za-z][\w.-]*:)?"

    def setUp(self):
        with open(IDX, encoding="utf-8") as f:
            self.src = f.read()

    @staticmethod
    def _in_string_literal(line, col):
        """Whether `col` on `line` sits inside a quoted or template string.

        Needed because refusal TEXT legitimately names the tags it is warning
        about — `a value contains raw tool-call syntax (</parameter>,
        </tool_call>, <function>)` is a sentence, not a pattern. The first
        version of this check flagged it three times, which is a false positive
        that would have taught the next reader to ignore this test."""
        quote = None
        i = 0
        while i < len(line) and i < col:
            c = line[i]
            if quote:
                if c == "\\":
                    i += 2
                    continue
                if c == quote:
                    quote = None
            elif c in "\"'`":
                quote = c
            i += 1
        return quote is not None

    def test_no_dialect_tag_is_matched_without_an_optional_namespace(self):
        import re
        bare = []
        # The prefix must sit IMMEDIATELY after the opener, not merely somewhere
        # nearby. A 40-character lookback was the first version and it was too
        # lax to fail: the window reaches onto the previous line, so a
        # neighbouring pattern's prefix satisfied this one. Proven by reverting
        # a pattern in memory and watching the check stay green — the exact
        # "check that cannot fail" shape this repo counts.
        for m in re.finditer(r"<(?:\\?/)?(?=" + "|".join(self.DIALECT_WORDS) + r")",
                             self.src):
            line_start = self.src.rfind("\n", 0, m.start()) + 1
            line_end = self.src.find("\n", m.start())
            line = self.src[line_start:line_end if line_end != -1 else len(self.src)]
            stripped = line.strip()
            # Comments and prose describe the defect; they are not patterns.
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            if self._in_string_literal(line, m.start() - line_start):
                continue
            # Exact: the characters right after the opener must BE the prefix.
            if not self.src.startswith(self.PREFIX, m.end()):
                bare.append((self.src[:m.start()].count("\n") + 1, stripped[:110]))
        self.assertEqual(sorted(set(bare)), [],
                         "these tool-call patterns still match only the "
                         "unprefixed spelling: %s" % sorted(set(bare)))

    def test_the_fake_tool_call_pattern_accepts_a_namespace(self):
        import re
        m = re.search(r"const FAKE_TOOL_CALL_PATTERN = /(.*)/i;", self.src)
        self.assertIsNotNone(m, "the pattern was renamed; this test is now blind")
        pat = re.compile(m.group(1).replace(r"\/", "/"), re.I)
        self.assertTrue(pat.search("<atem:invoke name=\"write\">"))
        self.assertTrue(pat.search("</atem:parameter>"))
        self.assertTrue(pat.search("<invoke name=\"x\">"),
                        "the unprefixed spelling must still match")

    def test_the_argument_leak_pattern_accepts_a_namespace(self):
        import re
        m = re.search(r"const ARG_SYNTAX_LEAK = /(.*)/i;", self.src)
        self.assertIsNotNone(m)
        pat = re.compile(m.group(1).replace(r"\/", "/"), re.I)
        self.assertTrue(pat.search("</atem:parameter>"))
        self.assertTrue(pat.search("</tool_call>"), "the unprefixed spelling must still match")


if __name__ == "__main__":
    unittest.main()
