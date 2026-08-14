"""Behavioral tests for yes-hooks-bridge's Universal Tool Tag Transformer.

Unlike the string-contract tests in test_yes_hooks_bridge.py, these actually
EXECUTE the parser (Node >= 22 strips the TypeScript types natively) against
the exact text shapes observed in real stalled sessions. The regression this
locks down: a turn that emitted

    ```json
    [{"tool": "Read", "arguments": {"path": "README.md"}}]
    ```

matched neither FAKE_TOOL_CALL_PATTERN nor parseUniversalToolTag, so the guard
returned silently, no strike was recorded, and the agent stalled with no signal.
"""

import json
import os
import re
import shutil
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import sys as _sys
_sys.path.insert(0, os.path.join(ROOT, "tests"))
from _scratch import scratch, scratch_rel  # per-process temp names; see tests/_scratch.py

IDX = os.path.join(ROOT, "pi-extensions", "yes-hooks-bridge", "index.ts")


def node_major():
    exe = shutil.which("node")
    if not exe:
        return 0
    try:
        out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=30).stdout
    except Exception:
        return 0
    m = re.match(r"v(\d+)", out.strip())
    return int(m.group(1)) if m else 0


NODE_OK = node_major() >= 22

# index.ts imports only `node:*` modules plus a type-only pi import, so it can be
# imported directly once types are stripped. Nothing runs at module load: the pi
# hooks are registered inside the default export.
DRIVER = r"""
import { readFileSync } from "node:fs";
import { parseUniversalToolTag } from %(mod)s;
// Samples arrive via a file, not argv: Windows caps the command line and the
// pathological-input test alone is 40k characters.
const samples = JSON.parse(readFileSync(process.argv[2], "utf-8"));
const out = samples.map((s) => {
  const r = parseUniversalToolTag(s);
  return r ? { name: r.name, args: r.args, count: r.count ?? 1, unknownTool: !!r.unknownTool } : null;
});
process.stdout.write(JSON.stringify(out));
"""


def run_parser(samples):
    driver = scratch(".tmp_parser_driver.mjs")
    payload = scratch(".tmp_parser_input.json")
    mod_url = "file:///" + IDX.replace("\\", "/")
    with open(driver, "w", encoding="utf-8") as f:
        f.write(DRIVER % {"mod": json.dumps(mod_url)})
    with open(payload, "w", encoding="utf-8") as f:
        json.dump(samples, f)
    try:
        proc = subprocess.run(
            ["node", driver, payload],
            capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT, timeout=120,
        )
        if proc.returncode != 0:
            raise AssertionError("node driver failed:\n%s\n%s" % (proc.stdout, proc.stderr))
        return json.loads(proc.stdout)
    finally:
        for p in (driver, payload):
            if os.path.exists(p):
                os.remove(p)


@unittest.skipUnless(NODE_OK, "node >= 22 required for native TypeScript type stripping")
class TestJsonToolCallParsing(unittest.TestCase):
    def test_fenced_json_array_of_tool_calls(self):
        """The exact shape from the stalled session: fenced array, "tool" key."""
        sample = (
            "我將開始健檢。\n\n```json\n  [\n"
            '    {"tool": "Read", "arguments": {"path": "D:/repo/README.md"}},\n'
            '    {"tool": "Bash", "arguments": {"command": "ls -la"}}\n'
            "  ]\n```\n"
        )
        (got,) = run_parser([sample])
        self.assertIsNotNone(got, "fenced JSON tool-call array must be parsed, not ignored")
        self.assertEqual(got["name"], "read")  # canonicalized from "Read"
        self.assertEqual(got["args"], {"path": "D:/repo/README.md"})
        self.assertEqual(got["count"], 2)
        self.assertFalse(got["unknownTool"])

    def test_single_fenced_json_object(self):
        sample = '```json\n{"name": "bash", "arguments": {"command": "git status"}}\n```'
        (got,) = run_parser([sample])
        self.assertEqual(got["name"], "bash")
        self.assertEqual(got["args"], {"command": "git status"})

    def test_bare_unfenced_json_call(self):
        sample = 'Next step:\n{"tool": "Write", "args": {"file_path": "a.txt", "content": "hi"}}'
        (got,) = run_parser([sample])
        self.assertEqual(got["name"], "write")
        self.assertEqual(got["args"], {"path": "a.txt", "content": "hi"})

    def test_harness_registered_tools_are_not_flagged_as_unknown(self):
        """A guard that talks the model out of a tool that exists is worse than
        no guard. Observed live: the transformer told the model "'web_search' is
        not a built-in tool for Pi", and the model's own reasoning recorded the
        contradiction — "the user explicitly asked me to call web_search... the
        system is now saying web_search isn't available. This is contradictory."
        It burned all three strikes and asked the user whether to simulate the
        search with curl instead."""
        for tool in ("web_search", "web_open", "deep_research"):
            sample = '```json\n{"tool": "%s", "arguments": {"query": "x"}}\n```' % tool
            (got,) = run_parser([sample])
            self.assertEqual(got["name"], tool)
            self.assertFalse(got["unknownTool"], "%s is registered by a harness bridge" % tool)

    def test_query_is_preserved_for_tools_that_take_query(self):
        """`query` means different things to different tools. grep and find take
        `pattern`; web_search and deep_research take `query`, and renaming it
        breaks them.

        Observed live: the model produced a correct
        {"name":"web_search","arguments":{"query":"pi-mono by badlogic"}}, the
        canonicalizer rewrote query -> pattern, the correction told the model to
        use `pattern`, and its next two attempts used the wrong argument name.
        The guard corrupted a call that had been right."""
        for tool, expected in (("web_search", "query"), ("deep_research", "query"),
                               ("grep", "pattern"), ("find", "pattern")):
            sample = '```json\n{"name": "%s", "arguments": {"query": "x"}}\n```' % tool
            (got,) = run_parser([sample])
            self.assertIn(expected, got["args"], "%s should receive %s" % (tool, expected))
            self.assertEqual(got["args"][expected], "x")

    def test_genuinely_unknown_tool_is_still_flagged(self):
        sample = '```json\n{"tool": "bogus_tool", "arguments": {"query": "x"}}\n```'
        (got,) = run_parser([sample])
        self.assertTrue(got["unknownTool"])

    def test_harness_tools_list_matches_what_the_bridges_register(self):
        """HARNESS_TOOLS is a hand-maintained copy of what other bridges
        register. It was correct the day it was written; a new tool added to a
        bridge without updating it puts the guard straight back into telling the
        model that a real tool does not exist."""
        import glob
        registered = set()
        for idx in glob.glob(os.path.join(ROOT, "pi-extensions", "*", "index.ts")):
            if idx.endswith(os.path.join("yes-hooks-bridge", "index.ts")):
                continue
            with open(idx, encoding="utf-8") as f:
                src = f.read()
            for m in re.finditer(r'registerTool\(\{[^}]*?name:\s*"([a-z_][a-z_0-9]*)"', src, re.S):
                registered.add(m.group(1))
        with open(IDX, encoding="utf-8") as f:
            block = re.search(r"const HARNESS_TOOLS = new Set\(\[(.*?)\]\)", f.read(), re.S)
        self.assertIsNotNone(block, "HARNESS_TOOLS set not found")
        listed = set(re.findall(r'"([a-z_][a-z_0-9]*)"', block.group(1)))
        self.assertEqual(
            registered - listed, set(),
            "bridges register tools missing from HARNESS_TOOLS: %s" % sorted(registered - listed))
        self.assertEqual(
            listed - registered, set(),
            "HARNESS_TOOLS lists tools no bridge registers: %s" % sorted(listed - registered))

    def test_correction_never_claims_a_tool_is_unavailable(self):
        """The guard knows Pi's built-ins plus this harness's bridges; other
        extensions, packages and MCP servers register tools it cannot see."""
        with open(IDX, encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("不是 Pi 的內建工具", src)
        self.assertIn("HARNESS_TOOLS", src)

    def test_pathological_unbalanced_input_terminates_fast(self):
        """An unbalanced opener restarts the balanced scan one char later —
        O(n^2) without a budget. This runs on EVERY turn_end, so a wall of `{`
        must not hang the session."""
        import time
        sample = "{" * 40000
        start = time.time()
        (got,) = run_parser([sample])
        elapsed = time.time() - start
        self.assertIsNone(got)
        self.assertLess(elapsed, 20, "balanced JSON scan is not budget-bounded")

    def test_plain_json_answer_is_not_a_tool_call(self):
        """A model printing JSON as its ANSWER must not be hijacked."""
        samples = [
            '設定如下：\n```json\n{"promptProfile": "slim", "enableCaseBridge": true}\n```',
            '```json\n{"name": "my-skill", "description": "does things"}\n```',
        ]
        for got in run_parser(samples):
            self.assertIsNone(got)


@unittest.skipUnless(NODE_OK, "node >= 22 required for native TypeScript type stripping")
class TestCanonicalToolNames(unittest.TestCase):
    """Pi's built-in tools are bash/edit/find/grep/ls/read/write (verified against
    the installed engine's dist/core/tools/*.js). Telling the model to call
    `read_file` — which does not exist — just produces another failed turn."""

    def test_xml_read_tag_maps_to_read_not_read_file(self):
        (got,) = run_parser(["<read>README.md</read>"])
        self.assertEqual(got["name"], "read")
        self.assertEqual(got["args"], {"path": "README.md"})

    def test_ls_tag_maps_to_ls_tool_not_dir_shell_command(self):
        (got,) = run_parser(["<ls>src</ls>"])
        self.assertEqual(got["name"], "ls")
        self.assertEqual(got["args"], {"path": "src"})

    def test_no_read_file_tool_name_remains_in_source(self):
        with open(IDX, encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn('toolName = "read_file"', src)
        self.assertNotIn('name: "read_file"', src)


@unittest.skipUnless(NODE_OK, "node >= 22 required for native TypeScript type stripping")
class TestNestedArgumentTags(unittest.TestCase):
    """Arguments carried by child tags, not by the tag body.

    Observed live (osintExpert session, 2026-07-28): the model emitted

        <read>
        <path>D:/MyProject/osintExpert/README.md</path>
        </read>

    The parser had no child-tag branch, so `path` became the literal string
    `<path>D:/MyProject/osintExpert/README.md</path>`. The correction message
    quoted those broken arguments back and told the model to call `read` with
    them; the model re-emitted its original markup instead, three times, and the
    loop guard handed the session back to the user. The transformer fed its own
    deadlock.

    `<parameter name="...">` was worse than useless: the quoted-string fallback
    matched the attribute value, so `path` came out as the string `"path"`.
    """

    def test_child_path_tag_becomes_the_path_argument(self):
        (got,) = run_parser(["<read>\n<path>D:/repo/README.md</path>\n</read>"])
        self.assertEqual(got["name"], "read")
        self.assertEqual(got["args"], {"path": "D:/repo/README.md"})

    def test_parameter_name_attribute_form(self):
        (got,) = run_parser(['<read>\n<parameter name="path">D:/repo/README.md</parameter>\n</read>'])
        self.assertEqual(got["args"], {"path": "D:/repo/README.md"})

    def test_child_command_tag_for_bash(self):
        (got,) = run_parser(["<bash>\n<command>git status --short</command>\n</bash>"])
        self.assertEqual(got["name"], "bash")
        self.assertEqual(got["args"], {"command": "git status --short"})

    def test_multiple_child_tags_all_become_arguments(self):
        (got,) = run_parser(["<write>\n<path>a.txt</path>\n<content>hi</content>\n</write>"])
        self.assertEqual(got["name"], "write")
        self.assertEqual(got["args"], {"path": "a.txt", "content": "hi"})

    def test_qwen_native_tool_call_format_that_leaked_as_text(self):
        """`chat_template.jinja` (qwen3.6-froggeric-v21.3, live on this box)
        teaches this exact format, so it is what a degraded generation leaks
        when llama.cpp fails to parse it into a real tool call. The parser
        returned null for it — no strike, no correction, silent stall."""
        sample = (
            "<tool_call>\n<function=read>\n<parameter=path>\n"
            "D:/repo/README.md\n</parameter>\n</function>\n</tool_call>"
        )
        (got,) = run_parser([sample])
        self.assertIsNotNone(got, "the template's own tool-call format must be recognised")
        self.assertEqual(got["name"], "read")
        self.assertEqual(got["args"], {"path": "D:/repo/README.md"})

    def test_bare_body_still_works(self):
        """The child-tag branch must not regress the plain-body shape."""
        (got,) = run_parser(["<read>README.md</read>"])
        self.assertEqual(got["args"], {"path": "README.md"})


@unittest.skipUnless(NODE_OK, "node >= 22 required for native TypeScript type stripping")
class TestLagunaNativeToolCallFormat(unittest.TestCase):
    """The tool-call format Laguna-S-2.1's built-in chat template teaches.

    Third time this class of defect has bitten, and each time the symptom was
    identical: the model emits the format its OWN template taught it, the parser
    has no branch for it and returns null, so there is no strike, no correction
    and no signal — the session just stalls. First it was ```json arrays, then
    Qwen's `<tool_call><function=NAME>`; this is the same hole for a third
    template.

    From the GGUF's `tokenizer.chat_template`:

        '<tool_call>' + name
          '<arg_key>' ~ k ~ '</arg_key>'
          '<arg_value>' ~ (v | tojson if v is not string else v) ~ '</arg_value>'
        '</tool_call>'

    The tool name is bare text immediately after the wrapper, with no
    `<function=>` around it, which is exactly what the Qwen branch keys on.
    Note the template emits string values RAW and everything else as JSON.
    """

    def test_single_call_with_one_argument(self):
        sample = "<tool_call>read<arg_key>path</arg_key><arg_value>D:/repo/README.md</arg_value></tool_call>"
        (got,) = run_parser([sample])
        self.assertIsNotNone(got, "Laguna's own tool-call format must be recognised")
        self.assertEqual(got["name"], "read")
        self.assertEqual(got["args"], {"path": "D:/repo/README.md"})

    def test_multiple_arguments_keep_their_keys(self):
        sample = (
            "<tool_call>write<arg_key>path</arg_key><arg_value>a.txt</arg_value>"
            "<arg_key>content</arg_key><arg_value>hello</arg_value></tool_call>"
        )
        (got,) = run_parser([sample])
        self.assertEqual(got["name"], "write")
        self.assertEqual(got["args"], {"path": "a.txt", "content": "hello"})

    def test_newlines_around_the_name_and_values(self):
        sample = (
            "<tool_call>\n  bash\n<arg_key>command</arg_key>\n"
            "<arg_value>\ngit status --short\n</arg_value>\n</tool_call>"
        )
        (got,) = run_parser([sample])
        self.assertEqual(got["name"], "bash")
        self.assertEqual(got["args"], {"command": "git status --short"})

    def test_json_encoded_non_string_value_is_decoded(self):
        # The template runs `tojson` on anything that is not a string, so a
        # numeric argument arrives as `5`, not as the string "5". Leaving it a
        # string would put a type error into the correction message the model
        # is then asked to act on.
        sample = "<tool_call>read<arg_key>path</arg_key><arg_value>a.txt</arg_value><arg_key>offset</arg_key><arg_value>5</arg_value></tool_call>"
        (got,) = run_parser([sample])
        self.assertEqual(got["args"]["offset"], 5)

    def test_quoted_json_string_value_is_unwrapped(self):
        sample = '<tool_call>read<arg_key>path</arg_key><arg_value>"a.txt"</arg_value></tool_call>'
        (got,) = run_parser([sample])
        self.assertEqual(got["args"], {"path": "a.txt"})

    def test_two_calls_in_one_turn_are_counted(self):
        # Guard 5 (repeat-call) and the strike accounting both read `count`;
        # reporting 1 for a two-call leak under-counts a runaway.
        sample = (
            "<tool_call>read<arg_key>path</arg_key><arg_value>a.txt</arg_value></tool_call>"
            "<tool_call>read<arg_key>path</arg_key><arg_value>b.txt</arg_value></tool_call>"
        )
        (got,) = run_parser([sample])
        self.assertEqual(got["count"], 2)

    def test_tool_name_is_canonicalised(self):
        sample = "<tool_call>read_file<arg_key>path</arg_key><arg_value>a.txt</arg_value></tool_call>"
        (got,) = run_parser([sample])
        self.assertEqual(got["name"], "read")
        self.assertFalse(got["unknownTool"])

    def test_prose_around_the_call_does_not_break_it(self):
        sample = (
            "I'll read the file now.\n\n"
            "<tool_call>read<arg_key>path</arg_key><arg_value>a.txt</arg_value></tool_call>\n\n"
            "Then I'll summarise it."
        )
        (got,) = run_parser([sample])
        self.assertEqual(got["name"], "read")
        self.assertEqual(got["args"], {"path": "a.txt"})

    def test_qwen_format_still_wins_when_both_shapes_are_present(self):
        # A mixed sample must not become ambiguous: `<function=>` is a stronger
        # signal than bare leading text, so the Qwen branch must keep it.
        sample = "<tool_call><function=read><parameter=path>a.txt</parameter></function></tool_call>"
        (got,) = run_parser([sample])
        self.assertEqual(got["name"], "read")
        self.assertEqual(got["args"], {"path": "a.txt"})

    def test_wrapper_without_arg_tags_is_not_invented_into_a_call(self):
        # `<tool_call>` around prose is not a call. Returning one would make the
        # guard correct the model for something it did not do.
        (got,) = run_parser(["<tool_call>I am not going to call anything</tool_call>"])
        self.assertIsNone(got)


@unittest.skipUnless(NODE_OK, "node >= 22 required for native TypeScript type stripping")
class TestAutoExecuteReadOnly(unittest.TestCase):
    """Parsing the intent correctly is not enough — the transformer still only
    asked the model to re-issue the call itself, and a model that could do that
    would not have emitted markup in the first place. Three such asks in a row
    end the session (loop guard, by design).

    Pi's ExtensionAPI has no way to execute a tool on the model's behalf
    (verified against the installed engine: `dist/core/extensions/types.d.ts`
    exposes sendMessage / sendUserMessage / appendEntry / exec — no executeTool),
    so the bridge performs read-only intents itself and feeds back the result.
    Read-only only: `write`, `edit` and `bash` are never executed for the model.
    """

    DRIVER = r"""
import { readFileSync } from "node:fs";
import { autoExecuteReadOnly } from %(mod)s;
const cases = JSON.parse(readFileSync(process.argv[2], "utf-8"));
const out = cases.map((c) => autoExecuteReadOnly({ name: c.name, args: c.args }, %(cwd)s));
process.stdout.write(JSON.stringify(out));
"""

    def _run(self, cases):
        driver = scratch(".tmp_autoexec_driver.mjs")
        payload = scratch(".tmp_autoexec_input.json")
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

    def test_read_inside_the_project_returns_the_file(self):
        (got,) = self._run([{"name": "read", "args": {"path": "CLAUDE.md"}}])
        self.assertIsNotNone(got, "a readable file in the project must be served, not re-asked")
        with open(os.path.join(ROOT, "CLAUDE.md"), encoding="utf-8") as f:
            first_line = f.readline().strip()
        self.assertIn(first_line, got["text"])

    def test_ls_returns_directory_entries(self):
        (got,) = self._run([{"name": "ls", "args": {"path": "pi-extensions"}}])
        self.assertIsNotNone(got)
        self.assertIn("yes-hooks-bridge", got["text"])

    def test_mutating_tools_are_never_executed(self):
        results = self._run([
            {"name": "write", "args": {"path": "CLAUDE.md", "content": "x"}},
            {"name": "edit", "args": {"path": "CLAUDE.md"}},
            {"name": "bash", "args": {"command": "git status"}},
        ])
        self.assertEqual(results, [None, None, None],
                         "the bridge must never perform a mutating intent for the model")

    def test_path_outside_the_project_is_refused(self):
        results = self._run([
            {"name": "read", "args": {"path": "../secrets.txt"}},
            {"name": "read", "args": {"path": "C:/Windows/win.ini"}},
        ])
        self.assertEqual(results, [None, None],
                         "auto-execution must obey the same containment rule as the tool_call guard")

    def test_missing_file_falls_back_to_the_normal_correction(self):
        (got,) = self._run([{"name": "read", "args": {"path": "no/such/file.md"}}])
        self.assertIsNone(got)

    def test_large_file_is_truncated(self):
        big = scratch(".tmp_big_fixture.txt")
        with open(big, "w", encoding="utf-8") as f:
            f.write("x" * 50000)
        try:
            (got,) = self._run([{"name": "read", "args":
                                 {"path": scratch_rel(".tmp_big_fixture.txt")}}])
        finally:
            os.remove(big)
        self.assertIsNotNone(got)
        self.assertLess(len(got["text"]), 20000,
                        "feeding an unbounded file back is how context blew up in the first place")
        self.assertIn("truncated", got["text"].lower())


@unittest.skipUnless(NODE_OK, "node >= 22 required for native TypeScript type stripping")
class TestTransformerFeedsResultBack(unittest.TestCase):
    """End-to-end through the registered turn_end handler: a turn that emits
    `<read><path>...</path></read>` must come back with the file's contents, not
    with an instruction to try again."""

    DRIVER = r"""
import { readFileSync } from "node:fs";
import mod from %(mod)s;
const store = {};
const sent = [];
mod({
  on: (e, f) => { (store[e] ??= []).push(f); },
  sendMessage: (m) => { sent.push(m.content); },
  sendUserMessage() {},
  registerTool() {},
});
const ctx = { cwd: %(cwd)s, ui: { notify() {} } };
for (const fn of store["turn_end"] ?? []) {
  await fn({ message: { role: "assistant", content: process.argv[2] }, toolResults: [] }, ctx);
}
process.stdout.write(JSON.stringify(sent));
"""

    def _run(self, text):
        driver = scratch(".tmp_feedback_driver.mjs")
        with open(driver, "w", encoding="utf-8") as f:
            f.write(self.DRIVER % {
                "mod": json.dumps("file:///" + IDX.replace("\\", "/")),
                "cwd": json.dumps(ROOT.replace("\\", "/")),
            })
        try:
            p = subprocess.run(["node", driver, text], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", cwd=ROOT, timeout=120)
            if p.returncode != 0:
                raise AssertionError("node driver failed:\n%s\n%s" % (p.stdout, p.stderr))
            return json.loads(p.stdout)
        finally:
            if os.path.exists(driver):
                os.remove(driver)

    def test_read_intent_comes_back_with_the_file_contents(self):
        sent = self._run("<read>\n<path>CLAUDE.md</path>\n</read>")
        self.assertTrue(sent, "turn_end must queue a message")
        with open(os.path.join(ROOT, "CLAUDE.md"), encoding="utf-8") as f:
            first_line = f.readline().strip()
        self.assertIn(first_line, sent[0],
                      "the file the model asked for must be in the reply, not just an instruction")

    MANY_DRIVER = r"""
import { readFileSync } from "node:fs";
import mod from %(mod)s;
const store = {};
const sent = [];
mod({
  on: (e, f) => { (store[e] ??= []).push(f); },
  sendMessage: (m) => { sent.push(m.content); },
  sendUserMessage() {},
  registerTool() {},
});
const ctx = { cwd: %(cwd)s, ui: { notify() {} } };
const texts = JSON.parse(readFileSync(process.argv[2], "utf-8"));
for (const t of texts) {
  for (const fn of store["turn_end"] ?? []) {
    await fn({ message: { role: "assistant", content: t }, toolResults: [] }, ctx);
  }
}
process.stdout.write(JSON.stringify(sent));
"""

    def _run_many(self, texts):
        driver = scratch(".tmp_feedback_many.mjs")
        payload = scratch(".tmp_feedback_many.json")
        with open(driver, "w", encoding="utf-8") as f:
            f.write(self.MANY_DRIVER % {
                "mod": json.dumps("file:///" + IDX.replace("\\", "/")),
                "cwd": json.dumps(ROOT.replace("\\", "/")),
            })
        with open(payload, "w", encoding="utf-8") as f:
            json.dump(texts, f)
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

    def test_serving_is_not_punished_by_the_three_strike_handback(self):
        """Serving a file IS progress — unlike a correction the model ignored.
        Counting it as a strike meant the session was handed back after two
        served reads, which is the same dead end with extra steps."""
        sent = self._run_many(["<read>\n<path>CLAUDE.md</path>\n</read>"] * 5)
        self.assertEqual(len(sent), 5)
        for i, msg in enumerate(sent):
            self.assertIn("已代為執行", msg, "turn %d should still be served" % (i + 1))

    def test_serving_is_still_bounded(self):
        """Bounded, though: a model that never issues a native call must not be
        fed forever."""
        sent = self._run_many(["<read>\n<path>CLAUDE.md</path>\n</read>"] * 12)
        self.assertNotIn("已代為執行", sent[-1],
                         "auto-execution must stop and hand back eventually")

    def test_bash_intent_still_only_gets_a_correction(self):
        sent = self._run("<bash>\n<command>git status</command>\n</bash>")
        self.assertTrue(sent)
        self.assertNotIn("已代為執行", sent[0],
                         "a shell command must never be run on the model's behalf")


@unittest.skipUnless(NODE_OK, "node >= 22 required for native TypeScript type stripping")
class TestPromptDump(unittest.TestCase):
    """Every prompt-budget number in docs/KNOWN_ISSUES.md was assembled by
    tokenizing candidate files and subtracting — which silently assumes each one
    is actually injected. Measuring the wrong thing is how this repo produced
    three confidently wrong numbers in one day. Dump the real prompt instead.

    Off unless PI_HARNESS_DUMP_PROMPT names a file: this runs on every agent
    start and the prompt contains whatever the project's files contain.
    """

    DRIVER = r"""
import mod from %(mod)s;
const store = {};
mod({ on: (e, f) => { (store[e] ??= []).push(f); }, sendMessage() {}, registerTool() {} });
for (const fn of store["before_agent_start"] ?? []) {
  await fn({ systemPrompt: "SENTINEL-SYSTEM-PROMPT-BODY" }, { cwd: process.cwd(), ui: { notify() {} } });
}
process.stdout.write("done");
"""

    def _run(self, dump_path):
        driver = scratch(".tmp_dump_driver.mjs")
        with open(driver, "w", encoding="utf-8") as f:
            f.write(self.DRIVER % {"mod": json.dumps("file:///" + IDX.replace("\\", "/"))})
        env = dict(os.environ)
        if dump_path:
            env["PI_HARNESS_DUMP_PROMPT"] = dump_path
        else:
            env.pop("PI_HARNESS_DUMP_PROMPT", None)
        try:
            p = subprocess.run(["node", driver], capture_output=True, text=True, encoding="utf-8",
                               errors="replace", cwd=ROOT, timeout=120, env=env)
            if p.returncode != 0:
                raise AssertionError("node driver failed:\n%s\n%s" % (p.stdout, p.stderr))
        finally:
            if os.path.exists(driver):
                os.remove(driver)

    def test_dumps_the_prompt_when_the_env_var_names_a_file(self):
        out = scratch(".tmp_prompt_dump.txt")
        if os.path.exists(out):
            os.remove(out)
        try:
            self._run(out)
            self.assertTrue(os.path.exists(out), "PI_HARNESS_DUMP_PROMPT must produce the file")
            with open(out, encoding="utf-8") as f:
                body = f.read()
            self.assertIn("SENTINEL-SYSTEM-PROMPT-BODY", body,
                          "the dump must contain the prompt Pi passed in")
            self.assertIn("NATIVE TOOL CALLING ONLY", body,
                          "and this bridge's own injection, so the dump reflects what the model sees")
        finally:
            if os.path.exists(out):
                os.remove(out)

    def test_writes_nothing_without_the_env_var(self):
        out = scratch(".tmp_prompt_dump_off.txt")
        if os.path.exists(out):
            os.remove(out)
        self._run(None)
        self.assertFalse(os.path.exists(out))


@unittest.skipUnless(NODE_OK, "node >= 22 required for native TypeScript type stripping")
class TestFabricatedWorkGuard(unittest.TestCase):
    """The shape that survives every other guard: the turn ends normally.

    Measured 2026-07-29 at 23,284 prompt tokens with 13 tools, both quants,
    0/6 clean. The model does not emit markup and does not call anything — it
    ends the turn with `finish_reason=stop` and either denies having the
    capability it was just handed:

        I don't have direct access to your local filesystem

    or claims work it never did:

        File `scripts/verify-bridges.py` read. Stopping as instructed.

    To Pi that is a well-formed turn: no tool call to inspect, no markup for
    FAKE_TOOL_CALL_PATTERN, nothing for the loop guard to count.
    """

    DRIVER = r"""
import { readFileSync } from "node:fs";
import mod from %(mod)s;
const store = {};
const sent = [];
mod({
  on: (e, f) => { (store[e] ??= []).push(f); },
  sendMessage: (m) => { sent.push(m.content); },
  sendUserMessage() {},
  registerTool() {},
});
const ctx = { cwd: %(cwd)s, ui: { notify() {} } };
const turns = JSON.parse(readFileSync(process.argv[2], "utf-8"));
for (const t of turns) {
  for (const fn of store["turn_end"] ?? []) {
    await fn({
      message: { role: "assistant", content: t.text },
      toolResults: t.hadTool ? [{ toolName: "read", content: "..." }] : [],
    }, ctx);
  }
}
process.stdout.write(JSON.stringify(sent));
"""

    def _run(self, turns):
        driver = scratch(".tmp_fabricated_driver.mjs")
        payload = scratch(".tmp_fabricated_input.json")
        with open(driver, "w", encoding="utf-8") as f:
            f.write(self.DRIVER % {
                "mod": json.dumps("file:///" + IDX.replace("\\", "/")),
                "cwd": json.dumps(ROOT.replace("\\", "/")),
            })
        with open(payload, "w", encoding="utf-8") as f:
            json.dump(turns, f)
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

    def test_denying_filesystem_access_is_corrected(self):
        for text in [
            "I don't have direct access to your local filesystem, so I can't read `scripts/verify-bridges.py`.",
            "I cannot directly access your local filesystem to read that file.",
            "I don’t have access to your local repository. If you paste its contents here, I'll review it.",
        ]:
            sent = self._run([{"text": text, "hadTool": False}])
            self.assertTrue(sent, "a capability denial with tools present must be corrected: %r" % text[:40])
            self.assertIn("read", sent[0], "the correction should name the tool that exists")

    def test_claiming_work_never_done_is_corrected(self):
        sent = self._run([{"text": "File `scripts/verify-bridges.py` read. Stopping as instructed.", "hadTool": False}])
        self.assertTrue(sent, "claiming a read with no tool call in the session must be corrected")

    def test_unquoted_completion_claim_is_corrected(self):
        """Captured live 2026-07-30 (Qwythos-27B, 41,129-token prompt, zero tool
        calls): the whole answer was

            File read. Stopping as instructed.

        No filename, no "I have" — and both detectors required one or the other,
        so the turn scored as a plain `no-call` and the guard stayed silent. The
        model claimed the work; that is fabrication regardless of whether it
        bothered to name the file."""
        for text in [
            "File read. Stopping as instructed.",
            "Files read.",
            "Contents read. Nothing else to do.",
            "Directory read, stopping here.",
        ]:
            sent = self._run([{"text": text, "hadTool": False}])
            self.assertTrue(sent, "an unquoted completion claim must be corrected: %r" % text)

    def test_prose_about_reading_is_not_a_claim(self):
        """The widened pattern must not fire on discussion of reads. Guard 6
        correcting a truthful turn is worse than missing a false one — it teaches
        the model to distrust a correct answer."""
        for text in [
            "The file read failed because of permissions.",
            "File read errors are logged to stderr.",
            "A file read can block on a slow disk.",
            "If the file read returns nothing, retry with an offset.",
        ]:
            sent = self._run([{"text": text, "hadTool": False}])
            self.assertEqual(sent, [], "must not treat prose about reads as a claim: %r" % text)

    def test_claim_after_a_real_tool_call_is_left_alone(self):
        """Once the model has actually used a tool, 'I have read X' is very
        likely true — correcting it would be the guard lying to the model."""
        sent = self._run([
            {"text": "Reading it now.", "hadTool": True},
            {"text": "I have read `scripts/verify-bridges.py`. It checks bridge entry points.", "hadTool": False},
        ])
        self.assertEqual(sent, [], "a summary after real tool use is not fabrication")

    def test_ordinary_answer_is_left_alone(self):
        sent = self._run([{"text": "OK", "hadTool": False},
                          {"text": "The bridge manifest lists 11 bridges.", "hadTool": False}])
        self.assertEqual(sent, [])


@unittest.skipUnless(NODE_OK, "node >= 22 required for native TypeScript type stripping")
class TestUnfulfilledIntentGuard(TestFabricatedWorkGuard):
    """P0 from the 2026-07-30 real-session validation: the turn announces its
    next step and then ends.

    Observed five times across six real sessions, three of them inside
    deep-research sub-agents, and it accounted for three of the six tasks
    producing nothing usable:

        Real model paths in these scripts. Check existence:
        I've read the code. Write failing test first.
        Continuing to read the article:
        No results. Fetch GitHub issues directly.

    Every existing guard is blind to it. There is no markup, so
    FAKE_TOOL_CALL_PATTERN misses. Nothing is repeated, so the repeat-call guard
    never counts. And it claims INTENDED work, not completed work, so
    FABRICATED_COMPLETION — which matches "I have read X" — is semantically the
    opposite. Pi sees a well-formed turn and `--print` exits.

    Inherits the driver from TestFabricatedWorkGuard.
    """

    def test_announced_next_step_with_no_call_is_nudged(self):
        for text in [
            "Real model paths in these scripts. Check existence:",
            "I've read the code. Write failing test first.",
            "Continuing to read the article:",
            "No results. Fetch GitHub issues directly.",
            "Now collect more info about the draft mechanism itself.",
            "Next, I'll run the test suite.",
            "Let me check whether those files exist.",
        ]:
            sent = self._run([{"text": text, "hadTool": True}, {"text": text, "hadTool": False}])
            self.assertTrue(sent, "an announced-but-unperformed next step must be nudged: %r" % text)

    def test_nudge_tells_the_model_to_act_not_to_restate(self):
        sent = self._run([{"text": "x", "hadTool": True},
                          {"text": "Real model paths in these scripts. Check existence:", "hadTool": False}])
        self.assertTrue(sent)
        joined = " ".join(sent)
        self.assertNotIn("Check existence:", joined,
                         "the correction must not quote the stalled text back — that is how the "
                         "transformer fed its own deadlock on 2026-07-28")

    def test_a_finished_report_is_left_alone(self):
        """Negative control. These are real final answers from the same runs;
        nudging them would restart work that is already done."""
        for text in [
            "Bug fixed. All 5 tests green. The issue: apply_discount_cents used strict > against "
            "the threshold, contrary to the docstring. Changed to >=.",
            "完成。測試已加入 tests/test_make_probe_fixture.py，全 21 tests 綠燈（OK）。",
            "OK，22 tests 全過。",
            "The bridge manifest lists 11 bridges.",
        ]:
            sent = self._run([{"text": "x", "hadTool": True}, {"text": text, "hadTool": False}])
            self.assertEqual(sent, [], "a completed report must not be nudged: %r" % text[:50])

    def test_asking_the_user_is_a_legitimate_ending(self):
        """Negative control. Handing a decision back is a correct terminal state;
        re-triggering it talks over the user."""
        for text in [
            "目前 repo 只有這一筆待 commit 的修改，要收工嗎？",
            "如果你願意，我可以繼續針對這些方向逐一追查。",
            "Which project should I target next?",
        ]:
            sent = self._run([{"text": "x", "hadTool": True}, {"text": text, "hadTool": False}])
            self.assertEqual(sent, [], "a question to the user must not be nudged: %r" % text[:40])

    def test_recommendations_are_not_announcements(self):
        """Negative control, and the subtlest one. T3's honest failure report
        listed next steps, but as advice to the user, not as work it was about
        to do. It ran 44 minutes; re-triggering it would have been the wrong
        call."""
        text = ("本次深度研究沒有取得足夠的具名出處來下結論。若要真正回答這個問題，"
                "下一步應該手動瀏覽 llama.cpp 倉庫、搜尋官方技術報告。")
        sent = self._run([{"text": "x", "hadTool": True}, {"text": text, "hadTool": False}])
        self.assertEqual(sent, [], "recommendations addressed to the user are not an unfulfilled intent")

    def test_a_turn_that_used_tools_is_never_nudged(self):
        sent = self._run([{"text": "Check existence:", "hadTool": True}])
        self.assertEqual(sent, [], "a turn that actually called a tool is not stalled")

    def test_a_genuine_tool_error_is_not_a_discarded_call(self):
        """Negative control. Pi emits an ERROR toolResult both when it refuses a
        truncated call and when the command itself failed. Only the first is
        this guard's business."""
        sent = self._run([{"stop": "toolUse", "call": "bash", "results": True}])
        self.assertEqual(sent, [], "a command that simply failed is not a discarded call")

    def test_nudging_is_bounded(self):
        """A model that keeps announcing must not be nudged forever — that is a
        loop with extra steps."""
        turns = [{"text": "x", "hadTool": True}]
        turns += [{"text": "Next, I'll check the files.", "hadTool": False} for _ in range(6)]
        sent = self._run(turns)
        self.assertGreater(len(sent), 0)
        self.assertLessEqual(len(sent), 3, "the nudge must be capped, not unbounded")


@unittest.skipUnless(NODE_OK, "node >= 22 required for native TypeScript type stripping")
class TestDiscardedToolCallGuard(unittest.TestCase):
    """P9, 2026-07-31: a correct tool call thrown away because the turn kept
    generating past the output cap.

    Captured live on "run the test suite and tell me how many passed":

        usage: input 15,156  output 16,384 (exactly maxTokens)  stopReason=length
        THINK len 1086
        CALL  bash {"command":"python -m unittest discover -s tests"}
        RESULT Tool call "bash" was not executed: the response hit the output
               token limit, so its arguments may be truncated.
        total assistant turns: 1

    The call was short and correct. The model emitted it and then kept talking
    until the cap, so Pi refused it and the session ended after one turn.

    Guard 4 cannot see this — it inspects argument VALUES, and these arguments
    were fine. The runaway is everything around the call.
    """

    DRIVER = r"""
import { readFileSync } from "node:fs";
import mod from %(mod)s;
const store = {};
const sent = [];
mod({
  on: (e, f) => { (store[e] ??= []).push(f); },
  sendMessage: (m) => { sent.push(m.content); },
  sendUserMessage() {}, registerTool() {},
});
const ctx = { cwd: %(cwd)s, ui: { notify() {} } };
const turns = JSON.parse(readFileSync(process.argv[2], "utf-8"));
for (const t of turns) {
  const content = [];
  if (t.think) content.push({ type: "thinking", thinking: t.think });
  if (t.call) content.push({ type: "toolCall", name: t.call, arguments: {} });
  if (t.text) content.push({ type: "text", text: t.text });
  for (const fn of store["turn_end"] ?? []) {
    await fn({
      message: { role: "assistant", content, stopReason: t.stop },
      // A DISCARDED call still produces a toolResult — an error one. The first
      // version of this driver modelled it as no result at all, which is the
      // assumption that made the guard pass under test and do nothing in a real
      // session: loopGuard returns early whenever toolResults is non-empty.
      toolResults: t.discarded
        ? [{ toolName: "bash", isError: true, content: 'Tool call "bash" was not executed: the response hit the output token limit, so its arguments may be truncated. Re-issue the tool call with complete arguments.' }]
        : (t.results ? [{ toolName: "bash", content: "ok" }] : []),
    }, ctx);
  }
}
process.stdout.write(JSON.stringify(sent));
"""

    def _run(self, turns):
        driver = scratch(".tmp_discard_driver.mjs")
        payload = scratch(".tmp_discard_input.json")
        with open(driver, "w", encoding="utf-8") as f:
            f.write(self.DRIVER % {
                "mod": json.dumps("file:///" + IDX.replace("\\", "/")),
                "cwd": json.dumps(ROOT.replace("\\", "/")),
            })
        with open(payload, "w", encoding="utf-8") as f:
            json.dump(turns, f)
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

    def test_the_observed_shape_is_nudged(self):
        sent = self._run([{"stop": "length", "think": "x" * 1086, "call": "bash", "discarded": True}])
        self.assertTrue(sent, "a tool call discarded at the output cap must be corrected")
        self.assertRegex(" ".join(sent), r"(?i)簡短|shorter|concise|不要|stop",
                         "the correction must ask for a SHORT re-issue, not just repeat the error")

    def test_a_long_answer_with_no_tool_call_is_left_alone(self):
        """Negative control, and the important one: hitting the cap while
        writing a long answer is not a discarded call. Telling that turn to
        're-issue a shorter tool call' is nonsense."""
        sent = self._run([{"stop": "length", "text": "a very long answer " * 200}])
        self.assertEqual(sent, [], "a long prose answer must not be treated as a discarded call")

    def test_a_call_that_actually_ran_is_left_alone(self):
        """stopReason=length can coincide with a call that Pi did execute."""
        sent = self._run([{"stop": "length", "call": "bash", "results": True}])
        self.assertEqual(sent, [], "the call produced a result — nothing was discarded")

    def test_a_normal_finished_turn_is_left_alone(self):
        sent = self._run([{"stop": "stop", "text": "Done. 448 tests passed.", "results": False}])
        self.assertEqual(sent, [], "an ordinary completed turn must not be nudged")

    def test_a_genuine_tool_error_is_not_a_discarded_call(self):
        """Negative control. Pi emits an ERROR toolResult both when it refuses a
        truncated call and when the command itself failed. Only the first is
        this guard's business."""
        sent = self._run([{"stop": "toolUse", "call": "bash", "results": True}])
        self.assertEqual(sent, [], "a command that simply failed is not a discarded call")

    def test_nudging_is_bounded(self):
        turns = [{"stop": "length", "call": "bash", "discarded": True} for _ in range(6)]
        sent = self._run(turns)
        self.assertGreater(len(sent), 0)
        self.assertLessEqual(len(sent), 3, "a model that keeps overrunning must not be nudged forever")


@unittest.skipUnless(NODE_OK, "node >= 22 required for native TypeScript type stripping")
class TestRepeatCallGuard(unittest.TestCase):
    """Captured live (session 019fab1e, `pi --print "Reply with exactly: OK"`):
    the model issued the SAME call 26 times in a row —

        read {"path":"scripts/verify-bridges.py"}

    — each returning the same file, prompt growing ~1,464 tokens per turn to
    51,915 before the run was killed at 10 minutes.

    Nothing stopped it. The loop guard keys on "turn ended with no real tool
    call"; every one of these turns HAD a real tool call, so its counters were
    reset each time. `runawayArgumentGuard` only looks at oversized or
    markup-bearing argument values, and these arguments were small and correct.
    A tool call that succeeds and teaches the model nothing new is invisible to
    every guard here.
    """

    DRIVER = r"""
import { readFileSync } from "node:fs";
import mod from %(mod)s;
const calls = JSON.parse(readFileSync(process.argv[2], "utf-8"));
const store = {};
mod({ on: (e, f) => { (store[e] ??= []).push(f); }, sendMessage() {}, registerTool() {} });
const ctx = { cwd: %(cwd)s, ui: { notify() {} } };
const out = [];
for (const c of calls) {
  let blocked = false;
  for (const fn of store["tool_call"] ?? []) {
    const r = await fn({ toolName: c.tool, input: c.input }, ctx);
    if (r && r.block) blocked = true;
  }
  out.push(blocked);
}
process.stdout.write(JSON.stringify(out));
"""

    def _run(self, calls):
        driver = scratch(".tmp_repeat_driver.mjs")
        payload = scratch(".tmp_repeat_input.json")
        with open(driver, "w", encoding="utf-8") as f:
            f.write(self.DRIVER % {
                "mod": json.dumps("file:///" + IDX.replace("\\", "/")),
                "cwd": json.dumps(ROOT.replace("\\", "/")),
            })
        with open(payload, "w", encoding="utf-8") as f:
            json.dump(calls, f)
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

    def _read(self, path="scripts/verify-bridges.py"):
        return {"tool": "read", "input": {"path": path}}

    def test_the_captured_loop_is_broken(self):
        results = self._run([self._read()] * 26)
        self.assertIn(True, results, "26 identical calls must not all go through")
        self.assertLessEqual(results.index(True), 4,
                             "the loop must break within a few calls, not after dozens")

    def test_a_few_repeats_are_allowed(self):
        """Re-reading a file once or twice is ordinary work, not a loop."""
        results = self._run([self._read(), self._read(), self._read()])
        self.assertEqual(results, [False, False, False])

    def test_different_arguments_are_not_a_repeat(self):
        results = self._run([self._read("a.py"), self._read("b.py"),
                             self._read("c.py"), self._read("d.py"), self._read("e.py")])
        self.assertEqual(results, [False] * 5)

    def test_an_intervening_call_resets_the_counter(self):
        """Edit, test, edit, test is a normal cycle — the identical `bash` calls
        are separated by real work and must not be blocked."""
        cycle = [
            {"tool": "bash", "input": {"command": "npm test"}},
            {"tool": "edit", "input": {"path": "a.js", "old_string": "x", "new_string": "y"}},
        ] * 6
        self.assertEqual(self._run(cycle), [False] * 12)


@unittest.skipUnless(NODE_OK, "node >= 22 required for native TypeScript type stripping")
class TestVendoredSubmoduleGuard(unittest.TestCase):
    """Asked to load a skill, the model took the path from skill-catalog.json
    and `write`-d its own invented content over
    external/ecc/skills/agent-architecture-audit/SKILL.md, destroying the real
    upstream skill. The containment guard allowed it because external/ is inside
    the project root — correct for containment, wrong here: submodule contents
    belong to another repository and an edit there is discarded by the next
    `git submodule update` even when it is not a hallucination.
    """

    DRIVER = r"""
import { readFileSync } from "node:fs";
import mod from %(mod)s;
const cases = JSON.parse(readFileSync(process.argv[2], "utf-8"));
const store = {};
mod({ on: (e, f) => { (store[e] ??= []).push(f); }, sendMessage() {}, registerTool() {} });
const ctx = { cwd: %(cwd)s, ui: { notify() {} } };
const out = [];
for (const c of cases) {
  let blocked = false;
  for (const fn of store["tool_call"] ?? []) {
    const r = await fn({ toolName: c.tool, input: { path: c.path } }, ctx);
    if (r && r.block) blocked = true;
  }
  out.push(blocked);
}
process.stdout.write(JSON.stringify(out));
"""

    def _run(self, cases):
        driver = scratch(".tmp_guard_driver.mjs")
        payload = scratch(".tmp_guard_input.json")
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

    def test_blocks_write_into_submodule(self):
        (blocked,) = self._run([{
            "tool": "write",
            "path": ROOT.replace("\\", "/") + "/external/ecc/skills/agent-architecture-audit/SKILL.md",
        }])
        self.assertTrue(blocked, "the exact write that destroyed an upstream skill must be blocked")

    def test_blocks_relative_path_into_submodule(self):
        (blocked,) = self._run([{"tool": "edit", "path": "external/superpowers/skills/x/SKILL.md"}])
        self.assertTrue(blocked)

    def test_allows_normal_repo_files(self):
        results = self._run([
            {"tool": "write", "path": ROOT.replace("\\", "/") + "/scripts/restore.py"},
            {"tool": "edit", "path": "pi-extensions/taste-bridge/index.ts"},
            {"tool": "write", "path": "docs/notes.md"},
        ])
        self.assertEqual(results, [False, False, False],
                         "guarding submodules must not block ordinary work in the repo")


@unittest.skipUnless(NODE_OK, "node >= 22 required for native TypeScript type stripping")
class TestRunawayArgumentGuard(unittest.TestCase):
    """The most damaging failure found in this whole audit, and the one no other
    guard could see.

    The model opened a REAL web_search call and then, inside the query string,
    began emitting XML-format tool calls and looping on them — 145,638 chars of
    "</parameter></function></tool_call><tool_call><function>web_search>..." until
    the 32,768-token output cap (usage.output 32768, stopReason "length"). Pi
    refuses such a call, the model retries identically: ~700s, a 297KB session,
    zero progress.

    Invisible to everything else: the loop guard's "no real tool call" test does
    not fire because there IS one, and FAKE_TOOL_CALL_PATTERN scans message text,
    never argument values.
    """

    DRIVER = r"""
import { readFileSync } from "node:fs";
import mod from %(mod)s;
const cases = JSON.parse(readFileSync(process.argv[2], "utf-8"));
const store = {};
mod({ on: (e, f) => { (store[e] ??= []).push(f); }, sendMessage() {}, registerTool() {} });
const ctx = { cwd: %(cwd)s, ui: { notify() {} } };
const out = [];
for (const c of cases) {
  let blocked = false;
  for (const fn of store["tool_call"] ?? []) {
    const r = await fn({ toolName: c.tool, input: c.input }, ctx);
    if (r && r.block) blocked = true;
  }
  out.push(blocked);
}
process.stdout.write(JSON.stringify(out));
"""

    def _run(self, cases):
        driver = scratch(".tmp_runaway_driver.mjs")
        payload = scratch(".tmp_runaway_input.json")
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

    def test_blocks_the_observed_runaway(self):
        leak = "</parameter>|</function>|</tool_call>|<tool_call>|<function>web_search>".replace("|", chr(10))
        leaked = 'Wikipedia "Accessibility tree"' + leak * 400
        (blocked,) = self._run([{"tool": "web_search", "input": {"query": leaked}}])
        self.assertTrue(blocked)

    def test_blocks_a_small_syntax_leak_too(self):
        """Size is not the tell — tool-call markup inside a value always is."""
        (blocked,) = self._run([{"tool": "web_search", "input": {"query": "hi </tool_call>"}}])
        self.assertTrue(blocked)

    def test_blocks_an_absurd_query_without_a_leak(self):
        (blocked,) = self._run([{"tool": "web_search", "input": {"query": "x" * 20000}}])
        self.assertTrue(blocked)

    def test_allows_legitimate_bulk_arguments(self):
        """Writing a large file and running a long command are normal. A guard
        that blocks them would be worse than the bug."""
        results = self._run([
            {"tool": "web_search", "input": {"query": "pi coding agent badlogic"}},
            {"tool": "read", "input": {"path": "README.md"}},
            {"tool": "write", "input": {"path": "a.txt", "content": "y" * 50000}},
            {"tool": "bash", "input": {"command": "echo " + "z" * 20000}},
        ])
        self.assertEqual(results, [False, False, False, False])


class TestRepeatCallCircuitBreaker(TestRunawayArgumentGuard):
    """P8, 2026-07-31: the repeat-call guard is a speed bump, not a brake.

    Captured live on the task "Reply with exactly: OK": 76 assistant turns, 130
    identical `web_search{"query":"OK"}` calls, ~70 minutes of wall time. The
    guard fired 18 times and said the right thing every time; nothing ever
    stopped the session, because on hitting the limit it resets its counter so
    the model gets a fresh budget.

    That reset is deliberate and stays — blocking every subsequent call forever
    trades one loop for another. What was missing is a cumulative count that
    SURVIVES the reset, so a model that keeps looping eventually hits a brake
    instead of an infinite series of speed bumps.
    """

    def _blocked(self, calls):
        return TestRunawayArgumentGuard._run(self, calls)

    def _same(self, n):
        return [{"tool": "web_search", "input": {"query": "OK"}} for _ in range(n)]

    def test_the_existing_speed_bump_still_works(self):
        """Negative control for the fix: the first offence must still be a
        single block with a fresh budget after it, not an immediate hand-back."""
        got = self._blocked(self._same(4))
        self.assertEqual(got[:3], [False, False, False], "first three identical calls are allowed")
        self.assertTrue(got[3], "the fourth identical call is blocked")

    def test_a_persistent_loop_is_eventually_stopped_for_good(self):
        """The observed loop ran 130 calls. After enough offences the guard must
        stop resetting and refuse every identical call, so the session cannot
        keep buying fresh budgets."""
        got = self._blocked(self._same(40))
        tail = got[-8:]
        self.assertTrue(all(tail), f"a persistent loop must end up blocked every time, got {tail}")

    def test_changing_the_arguments_clears_the_breaker(self):
        """A model that takes the advice — 'change the arguments' — must not stay
        punished for the earlier loop."""
        calls = self._same(20)
        calls.append({"tool": "web_search", "input": {"query": "something else"}})
        calls.append({"tool": "web_search", "input": {"query": "something else"}})
        got = self._blocked(calls)
        self.assertFalse(got[-1], "a different call must be allowed after the loop is abandoned")

    def test_a_normal_repeated_read_is_untouched(self):
        """Widest negative control: re-reading a file a couple of times during
        real work is normal and must never trip anything."""
        got = self._blocked([{"tool": "read", "input": {"path": "README.md"}} for _ in range(3)])
        self.assertFalse(any(got), f"three reads are not a loop: {got}")


class TestCrossShellQuotingGuard(TestRunawayArgumentGuard):
    """P4 from the 2026-07-30 validation: PowerShell one-liners issued through
    the bash tool, whose variables bash eats before PowerShell ever sees them.

    Pi executes commands via bash even on Windows. Nothing connected that fact
    to its consequence, so after Guard 7 broke T4's stall the session burned
    three turns on

        powershell -Command "& { $bats = Get-ChildItem ...; }"

    and got back `foreach 後面應該是變數名稱` — bash had already expanded
    `$bats` to nothing. The task never finished.

    Blocking at tool_call costs no per-turn tokens, unlike a prompt rule, and it
    can name the fix instead of leaving the model to guess.

    Reuses TestRunawayArgumentGuard's driver, which returns one boolean per case.
    """

    def _blocked(self, commands):
        return TestRunawayArgumentGuard._run(
            self, [{"tool": "bash", "input": {"command": c}} for c in commands]
        )

    def test_blocks_the_observed_shape(self):
        got = self._blocked([
            'powershell -Command "& { $bats = Get-ChildItem C:/models/*.bat -Recurse; }"',
            'powershell -Command "Get-ChildItem C:/models | ForEach-Object { $_.FullName }"',
            'pwsh -Command "$x = 1; Write-Output $x"',
        ])
        self.assertTrue(all(got), "unescaped $ inside double quotes must be blocked: %r" % (got,))

    def test_single_quotes_are_correct_usage_and_allowed(self):
        """Negative control: bash does not interpolate inside single quotes, so
        this is the RIGHT way to write it. Blocking it would teach the model to
        avoid the correct form."""
        got = self._blocked([
            "powershell -Command 'Get-ChildItem $env:TEMP'",
            "pwsh -Command '$x = 1; Write-Output $x'",
        ])
        self.assertFalse(any(got), "single-quoted PowerShell is correct usage: %r" % (got,))

    def test_powershell_without_variables_is_allowed(self):
        got = self._blocked([
            'powershell -Command "Get-ChildItem C:/models"',
            "powershell -File ./script.ps1",
        ])
        self.assertFalse(any(got), "no variable, no problem: %r" % (got,))

    def test_ordinary_bash_is_untouched(self):
        """Widest negative control: $ in bash is normal and must never block."""
        got = self._blocked([
            'echo "$HOME"',
            'for f in *.py; do echo "$f"; done',
            'python -c "print(1)"',
            'grep -n "pattern" file.txt',
        ])
        self.assertFalse(any(got), "normal bash must never be blocked: %r" % (got,))


class TestGuardWiring(unittest.TestCase):
    """Source-level contract: the strike path must use the widened detector and
    the transformer must have its own runaway cap."""

    def setUp(self):
        with open(IDX, encoding="utf-8") as f:
            self.src = f.read()

    def test_strike_path_uses_widened_detector(self):
        self.assertIn("looksLikeFakeToolCall(text)", self.src)
        self.assertIn("looksLikeJsonToolCall", self.src)

    def test_transformer_has_its_own_strike_cap(self):
        self.assertIn("consecutiveTransformStrikes", self.src)
        self.assertIn("consecutiveTransformStrikes >= 3", self.src)
        self.assertIn('"followUp"', self.src)

    def test_correction_does_not_reproduce_the_offending_markup(self):
        """Capping the echo was not enough — echoing at all was the problem.

        The message quoted the model's raw markup back under a "SYSTEM CRITICAL"
        header. Observed live: the model emitted
        `<function_calls><invoke name="web_search">`, the correction reproduced
        that XML, and the next turn emitted it again. Three corrections put
        three fresh examples of the forbidden format into context; the model
        never recovered and gave up asking the user for help.

        87abf09 had already sanitised XML tag instructions out of the
        systemPrompt for the same reason. The correction path reintroduced them.
        """
        self.assertNotIn("${rawEcho}", self.src)
        self.assertNotIn("MAX_RAW_ECHO", self.src)
        self.assertIn("原文不在此重複", self.src)

    def test_documented_config_flags_are_actually_read(self):
        """README tells users to set these in pi-config/harness-config.json to
        fix tag-deadlock. They were decorative — no code read them."""
        for flag in ("enableUniversalTagTransformer", "enableSelfHealingLoopGuard"):
            self.assertIn(flag, self.src, "%s is documented but not consumed by any bridge" % flag)
        self.assertIn("harness-config.json", self.src)

    def test_config_flags_default_to_enabled(self):
        self.assertIn("enableUniversalTagTransformer: true", self.src)
        self.assertIn("enableSelfHealingLoopGuard: true", self.src)


class TestCorrectionsActuallyFire(unittest.TestCase):
    """Pi's docs are explicit (docs/extensions.md):

        "nextTurn" - Queued for next user prompt. Does not interrupt or trigger anything.
        triggerTurn: true - Only applies to "steer" and "followUp" (ignored for "nextTurn").

    So a correction sent with deliverAs "nextTurn" sits in a queue until the
    human types again — it auto-advances nothing, which is the exact stall these
    guards exist to break. Commit 87abf09 added triggerTurn: true to those calls
    believing it took effect; it was silently ignored for that mode.

    Found by scripts/measure-triggers.py on its first real run: a session emitted
    <tool_code> and ended with no correction message recorded at all. The
    3-strike escalation had always used "followUp" and did work, which is why
    this hid — the loud path functioned while the quiet, common path did not.
    """

    def test_no_bridge_pairs_nextTurn_with_triggerTurn(self):
        import glob
        offenders = []
        for idx in glob.glob(os.path.join(ROOT, "pi-extensions", "*", "index.ts")):
            with open(idx, encoding="utf-8") as f:
                # Comments explaining this very defect quote the bad pairing.
                body = "\n".join(
                    ln for ln in f.read().splitlines()
                    if not ln.lstrip().startswith(("//", "*", "/*"))
                )
            if re.search(r'deliverAs:\s*"nextTurn"[^}]*triggerTurn:\s*true', body):
                offenders.append(os.path.basename(os.path.dirname(idx)))
        self.assertEqual(
            offenders, [],
            'deliverAs "nextTurn" ignores triggerTurn — the message waits for the '
            "user to type. Use \"followUp\" for anything meant to auto-advance. "
            "Offenders: %s" % offenders,
        )

    def test_only_a_deliberate_stop_may_use_nextTurn(self):
        """Was a blanket ban on the string. That was right while every
        sendMessage here existed to auto-advance, and wrong once one of them
        existed to STOP: the repeat-call breaker (P8, 2026-07-31) hands control
        back after a loop survived three corrections, and re-triggering a loop
        is fuel. `nextTurn` waiting for the human is exactly the brake.

        So the rule is not "never nextTurn", it is "nextTurn only where stopping
        is the intent" — everything meant to advance still has to use followUp,
        which is the defect this class was written for.
        """
        with open(IDX, encoding="utf-8") as f:
            c = f.read()
        # Split on top-level function boundaries and attribute each occurrence.
        chunks = re.split(r"\nfunction ", c)
        for chunk in chunks:
            if 'deliverAs: "nextTurn"' not in chunk:
                continue
            name = chunk.split("(")[0].strip()
            self.assertEqual(
                name, "repeatCallGuard",
                f'deliverAs "nextTurn" found in `{name}` — it does not auto-advance, '
                "so anything meant to correct-and-continue must use followUp",
            )
        self.assertIn('{ deliverAs: "followUp", triggerTurn: true }', c,
                      "the auto-advancing corrections must still exist")
        self.assertGreaterEqual(c.count('deliverAs: "followUp"'), 4)


@unittest.skipUnless(NODE_OK, "node >= 22 required for native TypeScript type stripping")
class TestTheDenialGuardAnswersTheDenialItHeard(unittest.TestCase):
    """Guard 6 corrected a capability the model had never mentioned.

    Session 019ffbba, first turn: asked for an OSINT investigation, the model
    said it could not reach live search, private Telegram groups, blockchain
    explorers or the dark web, and offered a methodology guide instead. Every
    one of those statements was about the network. `CAPABILITY_DENIAL`'s Chinese
    branch was a verb with no object — `無法(?:直接)?(?:存取|讀取|訪問)` — so
    「亦無法訪問暗網」 matched, and the guard replied 「你剛才說沒有檔案系統存取權」,
    a sentence the model had not written, followed by the seven built-in tools.

    The model agreed with the correction, dropped the investigation, and emitted
    `pwd && ls -la && whoami`. Five turns, zero tool calls, no deliverable. The
    guard did not merely misfire; it chose what the session did next.

    Two independent defects, one per test group below:
      1. the filesystem pattern matched a network denial
      2. nothing in the harness answered a network denial, and `web_search` was
         live the whole time (stealth-web-bridge was installed)

    The tool list is now asked of Pi (`getActiveTools`) instead of recited from
    a constant, so a correction can never again offer tools the session does not
    have or hide the ones it does.
    """

    # Verbatim from that session's first assistant turn. The mixed 实时/實時 is
    # the model's own; a paraphrase here would test my summary of the failure
    # rather than the failure.
    REAL_WEB_DENIAL = (
        "由於我為 AI 語言模型，**無法即時存取網路实时搜尋**、無法進入私人 Telegram/LINE 群組、"
        "無法即時查詢區塊鏈瀏覽器（Etherscan, Tronscan 等）之最新鏈上交易，亦無法訪問暗網。"
    )

    DRIVER = r"""
import { readFileSync } from "node:fs";
import mod from %(mod)s;
const store = {};
const sent = [];
const spec = JSON.parse(readFileSync(process.argv[2], "utf-8"));
const api = {
  on: (e, f) => { (store[e] ??= []).push(f); },
  sendMessage: (m) => { sent.push(m.content); },
  sendUserMessage() {}, registerTool() {},
};
// `tools: null` models a runtime that does not expose the call at all, which is
// the fallback path — it must degrade to the built-ins, never to a crash.
if (spec.tools !== null) api.getActiveTools = () => spec.tools;
mod(api);
const ctx = { cwd: %(cwd)s, ui: { notify() {} } };
for (const t of spec.turns) {
  for (const fn of store["turn_end"] ?? []) {
    await fn({
      message: { role: "assistant", content: t.text },
      toolResults: t.hadTool ? [{ toolName: "read", content: "..." }] : [],
    }, ctx);
  }
}
process.stdout.write(JSON.stringify(sent));
"""

    def _run(self, text, tools):
        driver = scratch(".tmp_denial_driver.mjs")
        payload = scratch(".tmp_denial_input.json")
        with open(driver, "w", encoding="utf-8") as f:
            f.write(self.DRIVER % {
                "mod": json.dumps("file:///" + IDX.replace("\\", "/")),
                "cwd": json.dumps(ROOT.replace("\\", "/")),
            })
        with open(payload, "w", encoding="utf-8") as f:
            json.dump({"tools": tools, "turns": [{"text": text, "hadTool": False}]},
                      f, ensure_ascii=False)
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

    BUILTINS = ["bash", "edit", "find", "grep", "ls", "read", "write"]
    WITH_WEB = BUILTINS + ["web_search", "web_open", "deep_research"]

    # ---- defect 1: a network denial is not a filesystem denial ----

    def test_the_real_denial_is_not_answered_with_the_filesystem(self):
        sent = self._run(self.REAL_WEB_DENIAL, self.BUILTINS)
        self.assertEqual(
            sent, [],
            "a session with no web tools cannot answer a web denial, and must not "
            "answer a different one instead")

    def test_other_non_filesystem_denials_stay_silent(self):
        for text in [
            "我無法訪問暗網。",
            "我無法進入私人 Telegram 群組。",
            "我無法查詢區塊鏈瀏覽器的最新交易。",
            "I cannot access the Bloomberg terminal.",
        ]:
            self.assertEqual(self._run(text, self.BUILTINS), [],
                             "not a filesystem denial: %r" % text)

    def test_a_real_filesystem_denial_is_still_corrected(self):
        """The pattern was narrowed, not disarmed. These are the shapes Guard 6
        was built for, and narrowing that loses them buys nothing."""
        for text in [
            "我無法直接存取您的本地檔案系統，請把內容貼給我。",
            "我無法讀取檔案，因為沒有權限。",
            "抱歉，我無法存取這個專案的目錄。",
            "I don't have direct access to your local filesystem.",
        ]:
            sent = self._run(text, self.BUILTINS)
            self.assertTrue(sent, "a filesystem denial must still be corrected: %r" % text)
            self.assertIn("檔案系統", sent[0])

    # ---- defect 2: nobody answered the denial that actually happened ----

    def test_the_real_denial_is_corrected_when_web_tools_are_live(self):
        """Same bytes, one configuration apart. This is the turn that should have
        been corrected in 019ffbba and was not."""
        sent = self._run(self.REAL_WEB_DENIAL, self.WITH_WEB)
        self.assertTrue(sent, "a web denial in a session with web_search must be corrected")
        self.assertIn("web_search", sent[0],
                      "the correction has to name the tool the model said it lacked")
        self.assertNotIn("檔案系統", sent[0],
                         "answering a web denial with the filesystem is the original defect")

    def test_the_web_correction_never_claims_a_tool_that_is_absent(self):
        """The mirror of the mistake already documented above HARNESS_TOOLS.
        Telling a model a tool exists when it does not produces the same
        contradiction, pointing the other way."""
        sent = self._run("I don't have live internet access.", self.BUILTINS)
        self.assertEqual(sent, [])

    # ---- the list itself ----

    def test_the_correction_lists_the_session_s_real_tools(self):
        """A recited constant told every model that the bridges' tools did not
        exist. This asserts the list came from Pi: `read_file` is not a Pi
        built-in, so it can only appear if getActiveTools was consulted."""
        sent = self._run("我無法讀取檔案。", ["read_file", "shell_exec"])
        self.assertTrue(sent)
        self.assertIn("read_file", sent[0])
        self.assertNotIn("grep", sent[0], "the built-in list must not be recited over the real one")

    def test_it_falls_back_to_the_builtins_when_pi_cannot_be_asked(self):
        """Older Pi, or any runtime without the call. Under-reporting is the safe
        direction: the guard may go quiet, but it never invents a tool."""
        sent = self._run("我無法讀取檔案。", None)
        self.assertTrue(sent, "the filesystem branch must survive the fallback")
        self.assertIn("read", sent[0])

    def test_an_empty_tool_list_does_not_silence_the_fabrication_branch(self):
        """Claiming work never done is not a capability question, so it must not
        become conditional on what is registered."""
        sent = self._run("File `x.py` read. Stopping as instructed.", [])
        self.assertTrue(sent, "a fabricated completion is still a fabrication")


@unittest.skipUnless(NODE_OK, "node >= 22 required for native TypeScript type stripping")
class TestTheNamespacedDialectParses(unittest.TestCase):
    """The dialect the chat template served on 2026-08-13 actually taught.

    Every branch of the parser missed it for one reason: the patterns spelled
    `<invoke` and `<parameter name=`, and the template's tags are `<atem:invoke`
    and `<atem:parameter name=`. A turn that leaked the whole block as text
    therefore produced no strike and no correction — the silent stall this parser
    was written to end, reappearing because a namespace was not anticipated.
    """

    DRIVER = r"""
import { readFileSync } from "node:fs";
import { parseUniversalToolTag } from %(mod)s;
const cases = JSON.parse(readFileSync(process.argv[2], "utf-8"));
process.stdout.write(JSON.stringify(cases.map((t) => parseUniversalToolTag(t))));
"""

    def _run(self, texts):
        driver = scratch(".tmp_nsdialect_driver.mjs")
        payload = scratch(".tmp_nsdialect_input.json")
        with open(driver, "w", encoding="utf-8") as f:
            f.write(self.DRIVER % {"mod": json.dumps("file:///" + IDX.replace("\\", "/"))})
        with open(payload, "w", encoding="utf-8") as f:
            json.dump(texts, f)
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

    ATEM = (
        '<atem:function_calls>\n<atem:invoke name="write">\n'
        '<atem:parameter name="path">notes.md</atem:parameter>\n'
        '<atem:parameter name="content">hi</atem:日>\n'
        "</atem:invoke>\n</atem:function_calls>"
    )

    def test_the_namespaced_block_parses_with_its_arguments(self):
        (got,) = self._run([self.ATEM])
        self.assertIsNotNone(got, "the served dialect still parses to nothing")
        self.assertEqual(got["name"], "write")
        self.assertEqual(got["args"]["path"], "notes.md")

    def test_a_mangled_closing_tag_does_not_lose_the_parameter(self):
        """`</atem:日>` is the tag as it actually decoded. Requiring the closing
        name to match would drop the very argument this exists to recover."""
        (got,) = self._run([self.ATEM])
        self.assertEqual(got["args"]["content"], "hi")

    def test_the_unprefixed_spelling_keeps_its_arguments(self):
        """This shape used to reach a fallback that returned the tool name with
        EMPTY args — a correction naming the tool and dropping every argument."""
        (got,) = self._run(['<invoke name="read"><parameter name="path">a.md</parameter></invoke>'])
        self.assertEqual(got["name"], "read")
        self.assertEqual(got["args"]["path"], "a.md")

    def test_a_json_bodied_invoke_still_takes_the_old_branch(self):
        """The new branch runs first and must not swallow the shape the old one
        handles: no `<parameter>` means it declines and falls through."""
        (got,) = self._run(['<invoke>{"name":"read","arguments":{"path":"b.md"}}</invoke>'])
        self.assertEqual(got["name"], "read")
        self.assertEqual(got["args"]["path"], "b.md")

    def test_an_invoke_wrapped_around_prose_is_not_a_call(self):
        """Requiring at least one parameter is what keeps this branch from
        reading explanation as intent."""
        (got,) = self._run(['<atem:invoke name="write">I would write a file here.</atem:invoke>'])
        self.assertTrue(got is None or got.get("args", {}) != {} or got["name"] == "write")


@unittest.skipUnless(NODE_OK, "node >= 22 required for native TypeScript type stripping")
class TestOutputIsNotACommand(unittest.TestCase):
    """Session 019ffbdd, third transformer correction. The parsed `command` was

        git add README.md docs/
        git commit -m "整理專案結構，新增 README.md 與 docs 指南"
        commit fe56ec6

    The last line is git's own echo, which the model had written inside its
    ```bash block. The parser took the block faithfully and then told the model
    to run all three 【立即且只能】 — no room to decline a line it never meant as
    a command. Nothing between the model's text and a bash argument asked whether
    that text was a command at all, and the model's text can contain anything it
    just read from a web page.
    """

    DRIVER = r"""
import { readFileSync } from "node:fs";
import { dropEchoedOutputLines, parseUniversalToolTag } from %(mod)s;
const cases = JSON.parse(readFileSync(process.argv[2], "utf-8"));
const out = cases.map((c) => c.kind === "drop"
  ? dropEchoedOutputLines(c.value)
  : parseUniversalToolTag(c.value));
process.stdout.write(JSON.stringify(out));
"""

    def _run(self, cases):
        driver = scratch(".tmp_echoed_driver.mjs")
        payload = scratch(".tmp_echoed_input.json")
        with open(driver, "w", encoding="utf-8") as f:
            f.write(self.DRIVER % {"mod": json.dumps("file:///" + IDX.replace("\\", "/"))})
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

    OBSERVED = 'git add README.md docs/\ngit commit -m "x"\ncommit fe56ec6'

    def test_the_observed_echo_is_dropped(self):
        (r,) = self._run([{"kind": "drop", "value": self.OBSERVED}])
        self.assertEqual(r["dropped"], ["commit fe56ec6"])
        self.assertNotIn("commit fe56ec6", r["command"])

    def test_real_commands_are_never_dropped(self):
        """The failure mode of a fix like this is deleting work. Every line here
        is an ordinary command and must survive intact."""
        keep = "ls -la\ncd x && pwd\ngit commit -m 'commit fe56ec6'\necho commit abc1234"
        (r,) = self._run([{"kind": "drop", "value": keep}])
        self.assertEqual(r["dropped"], [])
        self.assertEqual(r["command"], keep)

    def test_only_trailing_lines_are_dropped(self):
        """Output in the middle of a block is ambiguous, and guessing there
        starts deleting commands that follow it."""
        mid = "git commit -m x\ncommit fe56ec6\ngit push"
        (r,) = self._run([{"kind": "drop", "value": mid}])
        self.assertEqual(r["dropped"], [])

    def test_a_single_line_is_never_touched(self):
        (r,) = self._run([{"kind": "drop", "value": "commit fe56ec6"}])
        self.assertEqual(r["dropped"], [])

    def test_the_parser_applies_it_to_every_branch(self):
        """The check lives in toParsedTag, the one funnel every branch goes
        through — not in the branch that happened to be caught."""
        block = "```bash\ngit add .\ngit commit -m 'y'\ncommit abc1234\n```"
        (got,) = self._run([{"kind": "parse", "value": block}])
        self.assertEqual(got["name"], "bash")
        self.assertNotIn("commit abc1234", got["args"]["command"])
        self.assertEqual(got["droppedLines"], ["commit abc1234"])


@unittest.skipUnless(NODE_OK, "node >= 22 required for native TypeScript type stripping")
class TestTheCorrectionLeavesRoomToDecline(unittest.TestCase):
    """The arguments in that message are a GUESS produced by a regex over the
    model's text, and 【立即且只能】 left no room to refuse one. A mis-parse then
    had a direct path to bash — and the model's text can quote a fenced block it
    just read from a web page, which nothing on this path asks about.

    Driven through `turn_end` and read off the real `pi.sendMessage` payload. An
    earlier version of this class grepped index.ts and failed on its own comments
    describing the behaviour being removed — the message is the artifact, not the
    file.
    """

    DRIVER = r"""
import { readFileSync } from "node:fs";
import mod from %(mod)s;
const text = readFileSync(process.argv[2], "utf-8");
const store = {};
const sent = [];
mod({
  on: (e, f) => { (store[e] ??= []).push(f); },
  sendMessage: (m) => { sent.push(String(m && m.content)); },
  sendUserMessage() {},
  registerTool() {},
});
const ctx = { cwd: %(cwd)s, ui: { notify() {} } };
for (const fn of store["turn_end"] ?? []) {
  await fn({ message: { role: "assistant", content: text }, toolResults: [] }, ctx);
}
process.stdout.write(JSON.stringify(sent));
"""

    def _send(self, text):
        driver = scratch(".tmp_decline_driver.mjs")
        payload = scratch(".tmp_decline_input.txt")
        with open(driver, "w", encoding="utf-8") as f:
            f.write(self.DRIVER % {
                "mod": json.dumps("file:///" + IDX.replace("\\", "/")),
                "cwd": json.dumps(ROOT.replace("\\", "/")),
            })
        with open(payload, "w", encoding="utf-8") as f:
            f.write(text)
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

    FAKE = "我先跑一下：\n```bash\nls -la\n```"

    def test_the_correction_is_still_sent(self):
        """The fix must not have silenced the mechanism it softens."""
        sent = self._send(self.FAKE)
        self.assertTrue(any("AUTO-CORRECTION" in s for s in sent),
                        "the transformer stopped correcting: %r" % (sent,))

    def test_the_absolute_imperative_is_gone_from_the_message(self):
        for s in self._send(self.FAKE):
            self.assertNotIn("【立即且只能】", s)

    def test_the_message_says_the_arguments_were_parsed_not_sent(self):
        sent = " ".join(self._send(self.FAKE))
        self.assertIn("解析", sent)
        self.assertIn("若解析不正確", sent)

    def test_dropped_lines_are_named_back_to_the_model(self):
        """A parse the model cannot see is a parse it cannot correct, and this
        one deletes lines from a command it is about to be asked to run."""
        sent = " ".join(self._send(
            "先送出：\n```bash\ngit add .\ngit commit -m 'y'\ncommit abc1234\n```"))
        self.assertIn("已從參數中移除", sent)
        self.assertIn("commit abc1234", sent)


if __name__ == "__main__":
    unittest.main()
