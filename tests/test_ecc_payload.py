"""Translating Pi events into what ECC hooks actually read.

Fifteen ECC hooks are wired into this bridge and exactly one of them worked.
`block-no-verify` scans raw text, so shape never mattered to it. Every other hook
was handed a payload it could not read, and answered on a channel nobody was
listening to.

Measured 2026-08-04, against the installed Pi and the vendored ECC:

    dist/core/tools/write.d.ts:5   path: TString;  content: TString
    dist/core/tools/edit.d.ts:11   path: TString;  edits: [{oldText,newText}]

    post-edit-console-warn.js:28   input.tool_input?.file_path
    quality-gate.js:143            input.tool_input?.file_path
    config-protection.js:93        tool_input?.file_path || tool_input?.file
    gateguard-fact-force.js:1145   data.tool_name / data.tool_input

    $ printf '{"tool_name":"write","tool_input":{"path":"…/bad.ts"}}' | node post-edit-console-warn.js
    (nothing)
    $ printf '{"tool_name":"write","tool_input":{"file_path":"…/bad.ts"}}' | node post-edit-console-warn.js
    [Hook] WARNING: console.log found in …/bad.ts

`external/ecc` is a submodule, so the translation belongs on this side. These are
the pure functions that do it; tests/test_ecc_hook_contract.py then feeds the
result to the real hooks, which is the only level that can catch this class of
defect — a unit test proves we built the shape we intended, not that the other
side accepts it.
"""

import json
import os
import re
import shutil
import tempfile
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(ROOT, "pi-extensions", "ecc-hooks-bridge", "ecc-payload.ts")


def _node_major():
    if not shutil.which("node"):
        return 0
    try:
        out = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=30).stdout
    except Exception:
        return 0
    m = re.match(r"v(\d+)", out.strip())
    return int(m.group(1)) if m else 0


NODE_OK = _node_major() >= 22


def run_js(script):
    driver = os.path.join(ROOT, "tests", ".tmp_payload_driver.mjs")
    url = "file:///" + MOD.replace("\\", "/")
    with open(driver, "w", encoding="utf-8") as f:
        f.write("import * as m from %s;\n%s" % (json.dumps(url), script))
    try:
        p = subprocess.run(["node", driver], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=ROOT, timeout=120)
        if p.returncode != 0:
            raise AssertionError("node driver failed:\n%s\n%s" % (p.stdout, p.stderr))
        return json.loads(p.stdout)
    finally:
        if os.path.exists(driver):
            os.remove(driver)


def to_hook_input(tool, payload, output=None):
    args = "%s, %s" % (json.dumps(tool), json.dumps(payload))
    if output is not None:
        args += ", " + json.dumps(output)
    return run_js("process.stdout.write(JSON.stringify(m.toHookInput(%s)));" % args)


def parse_output(result):
    return run_js("process.stdout.write(JSON.stringify(m.parseHookOutput(%s)));" % json.dumps(result))


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestInboundTranslation(unittest.TestCase):
    def test_bash_gets_the_wrapper_it_never_had(self):
        """The bash call sent `JSON.stringify(event.input)`. gateguard reads
        data.tool_name and data.tool_input; both were undefined, so it returned
        the input unchanged and evaluated nothing, ever."""
        out = to_hook_input("bash", {"command": "rm -rf build"})
        self.assertEqual(out["tool_name"], "bash")
        self.assertEqual(out["tool_input"]["command"], "rm -rf build")

    def test_write_path_becomes_the_file_path_hooks_read(self):
        out = to_hook_input("write", {"path": "/tmp/a.ts", "content": "x"})
        self.assertEqual(out["tool_input"]["file_path"], "/tmp/a.ts")
        self.assertEqual(out["tool_input"]["content"], "x")

    def test_edit_path_becomes_file_path_and_edits_survive(self):
        edits = [{"oldText": "a", "newText": "b"}]
        out = to_hook_input("edit", {"path": "/tmp/a.ts", "edits": edits})
        self.assertEqual(out["tool_input"]["file_path"], "/tmp/a.ts")
        self.assertEqual(out["tool_input"]["edits"], edits)

    def test_the_original_path_field_is_kept_alongside(self):
        """Costs one field and means an upstream that starts reading `path`
        does not break this a second time."""
        out = to_hook_input("write", {"path": "/tmp/a.ts", "content": "x"})
        self.assertEqual(out["tool_input"]["path"], "/tmp/a.ts")

    def test_tool_output_is_folded_in_for_post_hooks(self):
        out = to_hook_input("bash", {"command": "ls"}, {"output": "a\nb"})
        self.assertEqual(out["tool_output"]["output"], "a\nb")

    def test_no_tool_output_key_when_there_is_none(self):
        out = to_hook_input("write", {"path": "/tmp/a.ts"})
        self.assertNotIn("tool_output", out)

    def test_an_unknown_tool_still_produces_a_wrapper(self):
        out = to_hook_input("grep", {"pattern": "x"})
        self.assertEqual(out["tool_name"], "grep")
        self.assertEqual(out["tool_input"]["pattern"], "x")

    def test_a_missing_input_is_not_a_crash(self):
        out = run_js('process.stdout.write(JSON.stringify(m.toHookInput("write", null)));')
        self.assertEqual(out["tool_name"], "write")
        self.assertEqual(out["tool_input"], {})


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestGateGuardBlockingIsOptIn(unittest.TestCase):
    """GateGuard has never evaluated a bash command on this machine, and it is a
    fact-forcing gate rather than a destructive-command filter: measured against
    the real hook, it denies the FIRST bash command of every session whatever it
    is — `ls -la` and `echo hi` included, each with "Before the first Bash command
    this session, present...".

    Repairing the translation would therefore switch on a hard block, on turn one,
    on a weak local model, without anyone choosing it. Blocking is opt-in; the
    finding still reaches the model as advice when the flag is off.
    """

    def _with_config(self, body):
        base = tempfile.mkdtemp(prefix="gateguard-cfg-")
        self.addCleanup(lambda: shutil.rmtree(base, ignore_errors=True))
        if body is not None:
            os.makedirs(os.path.join(base, "pi-config"))
            with open(os.path.join(base, "pi-config", "harness-config.json"), "w",
                      encoding="utf-8") as f:
                f.write(body)
        out = run_js('process.stdout.write(JSON.stringify({ v: m.gateGuardBlocksEnabled(%s) }));'
                     % json.dumps(base.replace("\\", "/")))
        return out["v"]

    def test_off_by_default_when_the_key_is_absent(self):
        self.assertFalse(self._with_config('{"promptProfile": "auto"}'))

    def test_off_when_there_is_no_config_at_all(self):
        """Fails CLOSED, unlike the advisory switch. An unset flag must not turn
        on a gate that blocks the first command of every session."""
        self.assertFalse(self._with_config(None))

    def test_off_when_the_config_is_malformed(self):
        self.assertFalse(self._with_config("{ not json at all"))

    def test_on_only_when_the_operator_says_so(self):
        self.assertTrue(self._with_config('{"enableEccGateGuard": true}'))

    def test_explicit_false_stays_off(self):
        self.assertFalse(self._with_config('{"enableEccGateGuard": false}'))


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestOutboundTranslation(unittest.TestCase):
    def test_exit_two_blocks(self):
        out = parse_output({"stdout": "", "stderr": "nope\ndetails", "exitCode": 2})
        self.assertTrue(out["block"])
        self.assertIn("nope", out["reason"])

    def test_a_stdout_deny_blocks_even_though_the_exit_code_is_zero(self):
        """gateguard returns exitCode 0 and says deny on stdout. The bridge only
        looked at exitCode 2, so the gate never closed."""
        payload = {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                          "permissionDecision": "deny",
                                          "permissionDecisionReason": "[Fact-Forcing Gate] list the files"}}
        out = parse_output({"stdout": json.dumps(payload), "stderr": "", "exitCode": 0})
        self.assertTrue(out["block"])
        self.assertIn("Fact-Forcing Gate", out["reason"])

    def test_additional_context_becomes_an_advisory(self):
        """suggest-compact's own comment: non-blocking stderr does not reach the
        model, so it emits hookSpecificOutput.additionalContext instead."""
        payload = {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                          "additionalContext": "[StrategicCompact] 50 tool calls"}}
        out = parse_output({"stdout": json.dumps(payload), "stderr": "", "exitCode": 0})
        self.assertNotIn("block", out)
        self.assertIn("StrategicCompact", out["advisory"])

    def test_a_hook_echoing_its_input_says_nothing(self):
        """Hooks pass the input through on stdout when they have no opinion.
        Treating that as an advisory would put the model's own tool arguments
        back in front of it on every single call."""
        out = parse_output({"stdout": '{"command":"rm -rf build"}', "stderr": "", "exitCode": 0})
        self.assertEqual(out, {})

    def test_broken_stdout_json_falls_back_to_stderr(self):
        out = parse_output({"stdout": "{not json", "stderr": "[Hook] WARNING: x", "exitCode": 0})
        self.assertIn("WARNING", out["advisory"])

    def test_plain_stderr_is_an_advisory(self):
        out = parse_output({"stdout": "", "stderr": "[QualityGate] Prettier check failed", "exitCode": 0})
        self.assertIn("Prettier", out["advisory"])

    def test_silence_in_silence_out(self):
        self.assertEqual(parse_output({"stdout": "", "stderr": "", "exitCode": 0}), {})

    def test_blocking_wins_over_advising(self):
        """A blocked call already returns its reason to the model; also queueing
        an advisory would say it twice."""
        payload = {"hookSpecificOutput": {"permissionDecision": "deny",
                                          "permissionDecisionReason": "denied"}}
        out = parse_output({"stdout": json.dumps(payload), "stderr": "also this", "exitCode": 2})
        self.assertTrue(out["block"])
        self.assertNotIn("advisory", out)


if __name__ == "__main__":
    unittest.main()
