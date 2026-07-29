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
    driver = os.path.join(ROOT, "tests", ".tmp_parser_driver.mjs")
    payload = os.path.join(ROOT, "tests", ".tmp_parser_input.json")
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
        driver = os.path.join(ROOT, "tests", ".tmp_autoexec_driver.mjs")
        payload = os.path.join(ROOT, "tests", ".tmp_autoexec_input.json")
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
        big = os.path.join(ROOT, "tests", ".tmp_big_fixture.txt")
        with open(big, "w", encoding="utf-8") as f:
            f.write("x" * 50000)
        try:
            (got,) = self._run([{"name": "read", "args": {"path": "tests/.tmp_big_fixture.txt"}}])
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
        driver = os.path.join(ROOT, "tests", ".tmp_feedback_driver.mjs")
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
        driver = os.path.join(ROOT, "tests", ".tmp_feedback_many.mjs")
        payload = os.path.join(ROOT, "tests", ".tmp_feedback_many.json")
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
        driver = os.path.join(ROOT, "tests", ".tmp_dump_driver.mjs")
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
        out = os.path.join(ROOT, "tests", ".tmp_prompt_dump.txt")
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
        out = os.path.join(ROOT, "tests", ".tmp_prompt_dump_off.txt")
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
        driver = os.path.join(ROOT, "tests", ".tmp_fabricated_driver.mjs")
        payload = os.path.join(ROOT, "tests", ".tmp_fabricated_input.json")
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
        driver = os.path.join(ROOT, "tests", ".tmp_repeat_driver.mjs")
        payload = os.path.join(ROOT, "tests", ".tmp_repeat_input.json")
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
        driver = os.path.join(ROOT, "tests", ".tmp_guard_driver.mjs")
        payload = os.path.join(ROOT, "tests", ".tmp_guard_input.json")
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
        driver = os.path.join(ROOT, "tests", ".tmp_runaway_driver.mjs")
        payload = os.path.join(ROOT, "tests", ".tmp_runaway_input.json")
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

    def test_transformer_and_retry_use_followUp(self):
        with open(IDX, encoding="utf-8") as f:
            c = f.read()
        self.assertNotIn('deliverAs: "nextTurn"', c)
        self.assertGreaterEqual(c.count('deliverAs: "followUp"'), 4)


if __name__ == "__main__":
    unittest.main()
