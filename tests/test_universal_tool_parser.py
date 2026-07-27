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

    def test_unknown_tool_is_flagged_not_dropped(self):
        sample = '```json\n{"tool": "web_search", "arguments": {"query": "pi agent"}}\n```'
        (got,) = run_parser([sample])
        self.assertEqual(got["name"], "web_search")
        self.assertTrue(got["unknownTool"], "non-builtin tool must be flagged so the prompt can list valid tools")

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

    def test_raw_echo_is_capped(self):
        self.assertIn("MAX_RAW_ECHO", self.src)

    def test_documented_config_flags_are_actually_read(self):
        """README tells users to set these in pi-config/harness-config.json to
        fix tag-deadlock. They were decorative — no code read them."""
        for flag in ("enableUniversalTagTransformer", "enableSelfHealingLoopGuard"):
            self.assertIn(flag, self.src, "%s is documented but not consumed by any bridge" % flag)
        self.assertIn("harness-config.json", self.src)

    def test_config_flags_default_to_enabled(self):
        self.assertIn("enableUniversalTagTransformer: true", self.src)
        self.assertIn("enableSelfHealingLoopGuard: true", self.src)


if __name__ == "__main__":
    unittest.main()
