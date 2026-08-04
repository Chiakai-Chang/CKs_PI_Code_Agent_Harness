"""Does the real ECC hook accept what we translate?

This is the level that matters. `tests/test_ecc_payload.py` proves we build the
shape we intended; only feeding it to the actual upstream script proves the
upstream accepts it — and the shape we intended is exactly what was wrong before.

The payload is built by importing `ecc-payload.ts` rather than hand-writing the
JSON here. A fixture that invents the payload is how a guard passes six tests and
fires zero times live.

`external/ecc` is a submodule; these skip when it is not checked out.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ECC = os.path.join(ROOT, "external", "ecc")
HOOKS = os.path.join(ECC, "scripts", "hooks")
PAYLOAD = os.path.join(ROOT, "pi-extensions", "ecc-hooks-bridge", "ecc-payload.ts")


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
ECC_OK = os.path.isdir(HOOKS)


def feed_hook(script, tool, pi_input, translate=True, hook_id=None, state_dir=None):
    """Run an ECC hook on a payload, returning its stdout/stderr/exit code.

    `hook_id` routes through `run-with-flags.js`, which is how the bridge invokes
    most hooks — and it matters: gateguard-fact-force exports its logic for that
    runner and produces nothing when the file is executed directly. A test that
    spawns the script its own way measures its own way, not the bridge's.

    `translate=False` sends Pi's raw input, which is what the bridge used to do —
    the negative control that proves these tests can fail.
    """
    driver = os.path.join(ROOT, "tests", ".tmp_contract_driver.mjs")
    if hook_id:
        argv = [os.path.join(HOOKS, "run-with-flags.js").replace("\\", "/"),
                hook_id, "scripts/hooks/" + script, "standard,strict"]
    else:
        argv = [os.path.join(HOOKS, script).replace("\\", "/")]
    body = """
import { spawnSync } from "node:child_process";
import * as m from %s;
const raw = %s;
const payload = %s ? m.toHookInput(%s, raw) : raw;
const r = spawnSync("node", %s, {
  input: JSON.stringify(payload), encoding: "utf-8",
  env: { ...process.env, CLAUDE_PLUGIN_ROOT: %s, GATEGUARD_STATE_DIR: %s },
});
process.stdout.write(JSON.stringify({
  stdout: r.stdout ?? "", stderr: r.stderr ?? "", status: r.status,
}));
""" % (
        json.dumps("file:///" + PAYLOAD.replace("\\", "/")),
        json.dumps(pi_input),
        "true" if translate else "false",
        json.dumps(tool),
        json.dumps(argv),
        json.dumps(ECC.replace("\\", "/")),
        json.dumps((state_dir or tempfile.mkdtemp(prefix="gg-state-")).replace("\\", "/")),
    )
    with open(driver, "w", encoding="utf-8") as f:
        f.write(body)
    try:
        p = subprocess.run(["node", driver], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=ROOT, timeout=180)
        if p.returncode != 0:
            raise AssertionError("driver failed:\n%s\n%s" % (p.stdout, p.stderr))
        return json.loads(p.stdout)
    finally:
        if os.path.exists(driver):
            os.remove(driver)


@unittest.skipUnless(NODE_OK, "node >= 22 required")
@unittest.skipUnless(ECC_OK, "external/ecc submodule is not checked out")
class TestEditWriteHooksReceiveThePath(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp(prefix="ecc-contract-")
        self.addCleanup(lambda: shutil.rmtree(self.base, ignore_errors=True))
        self.file = os.path.join(self.base, "bad.ts").replace("\\", "/")
        with open(self.file, "w", encoding="utf-8") as f:
            f.write('export const a = 1;\nconsole.log("noisy");\n')

    def test_console_warn_sees_the_file_after_translation(self):
        r = feed_hook("post-edit-console-warn.js", "write",
                      {"path": self.file, "content": "x"})
        self.assertIn("console.log found", r["stderr"])

    def test_console_warn_sees_nothing_from_pi_raw_input(self):
        """The negative control. Pi sends `path`; the hook reads `file_path`. This
        is what the bridge did for the life of the integration, and it is why six
        advisory producers could never fire."""
        r = feed_hook("post-edit-console-warn.js", "write",
                      {"path": self.file, "content": "x"}, translate=False)
        self.assertNotIn("console.log found", r["stderr"])

    def test_a_clean_file_still_says_nothing_after_translation(self):
        """Translation must not turn every edit into a warning."""
        clean = os.path.join(self.base, "clean.ts").replace("\\", "/")
        with open(clean, "w", encoding="utf-8") as f:
            f.write("export const a = 1;\n")
        r = feed_hook("post-edit-console-warn.js", "write", {"path": clean, "content": "x"})
        self.assertNotIn("console.log found", r["stderr"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
@unittest.skipUnless(ECC_OK, "external/ecc submodule is not checked out")
class TestGateGuardReceivesTheCommand(unittest.TestCase):
    def test_a_destructive_command_is_denied_after_translation(self):
        """gateguard reads data.tool_name and data.tool_input. The bash call sent
        the bare `{command}` with neither, so it evaluated nothing, ever."""
        r = feed_hook("gateguard-fact-force.js", "bash", {"command": "rm -rf build"},
                      hook_id="pre:bash:gateguard-fact-force")
        self.assertIn("permissionDecision", r["stdout"])
        self.assertIn("deny", r["stdout"])

    def test_the_bare_shape_is_waved_through(self):
        """Negative control: the same command, the shape the bridge used to send."""
        r = feed_hook("gateguard-fact-force.js", "bash", {"command": "rm -rf build"},
                      translate=False, hook_id="pre:bash:gateguard-fact-force")
        self.assertNotIn("permissionDecision", r["stdout"])

    def test_the_first_bash_command_of_a_session_is_gated_whatever_it_is(self):
        """Measured, and the reason `enableEccGateGuard` defaults to false.

        This is a fact-forcing gate, not a destructive-command filter: `ls -la`
        and `echo hi` are denied too, with "Before the first Bash command this
        session, present...". Wiring GateGuard up means every session's first
        bash call is blocked until the model presents an investigation. On the
        weak local model this harness targets, that is a large behaviour change
        and the operator should choose it deliberately.
        """
        r = feed_hook("gateguard-fact-force.js", "bash", {"command": "ls -la"},
                      hook_id="pre:bash:gateguard-fact-force")
        self.assertIn('"deny"', r["stdout"])
        self.assertIn("first Bash command", r["stdout"])

    def test_a_destructive_command_is_gated_for_a_different_reason(self):
        """Proves the command text itself survived translation — the destructive
        branch has to parse it, while the first-touch branch does not."""
        state = tempfile.mkdtemp(prefix="gg-warm-")
        self.addCleanup(lambda: shutil.rmtree(state, ignore_errors=True))
        feed_hook("gateguard-fact-force.js", "bash", {"command": "ls -la"},
                  hook_id="pre:bash:gateguard-fact-force", state_dir=state)
        r = feed_hook("gateguard-fact-force.js", "bash", {"command": "rm -rf build"},
                      hook_id="pre:bash:gateguard-fact-force", state_dir=state)
        self.assertIn("Destructive command detected", r["stdout"])


if __name__ == "__main__":
    unittest.main()
