"""Register a bridge's handlers, then actually call them.

2026-08-06: `turnWrites` was used inside yes-hooks-bridge's `tool_result`
handler and never declared. Every check passed — 774 unit tests, verify-bridges,
validate-config, check-prompt-conflicts, and a restore that reported the
installed copy byte-identical. The handler would have thrown
`ReferenceError: turnWrites is not defined` on the first tool result of every
session.

Nothing caught it because nothing ran it. Importing a module surfaces a syntax
error — an earlier stray newline inside a string literal was caught that way —
but an undefined identifier inside a function body is a runtime error, and the
function bodies were never executed outside a live Pi session.

So this registers each bridge's handlers with a stub `pi` and fires them with
minimal plausible events. It asserts nothing about behaviour; the point is only
that the code paths execute. A handler that throws is a handler that does
nothing, and Pi swallows it.

Bridges that pull runtime packages resolvable only inside Pi (typebox,
@earendil-works/pi-coding-agent) cannot be imported by bare node and are
reported as skipped rather than quietly dropped — an unlisted skip is how a
list stops covering what it claims to.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRIDGES = os.path.join(ROOT, "pi-extensions")


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

# Enough of an event for a handler to do its work without pretending to be real.
# A handler that needs more than this should fail open, which is the house rule
# for every guard here.
DRIVER = r"""
import * as mod from %(url)s;

const handlers = {};
const noop = () => {};
const pi = {
  on: (name, fn) => { (handlers[name] ||= []).push(fn); },
  sendMessage: noop,
  registerTool: noop,
  registerCommand: noop,
  registerShortcut: noop,
};
const ctx = {
  cwd: process.cwd(),
  hasUI: false,
  ui: {
    notify: noop, setStatus: noop, setWorkingMessage: noop,
    setWidget: noop, setWorkingVisible: noop,
  },
};

const events = {
  session_start: {},
  session_shutdown: {},
  before_agent_start: { prompt: "hello", systemPrompt: "sys" },
  tool_call: { toolName: "write", input: { path: "notes.md", content: "x" } },
  tool_result: { toolName: "write", input: { path: "notes.md" },
                 content: [{ type: "text", text: "ok" }], isError: false },
  turn_end: { message: { content: [{ type: "text", text: "done" }] }, toolResults: [] },
  session_compact: { messages: [] },
  session_before_compact: { messages: [] },
  agent_settled: {},
  resources_discover: { resources: [] },
  context: { messages: [] },
};

const failures = [];
try {
  mod.default(pi);
} catch (e) {
  failures.push("default export threw: " + e.message);
}

for (const [name, fns] of Object.entries(handlers)) {
  const event = events[name];
  if (event === undefined) continue;   // unknown event shape: not this test's business
  for (const fn of fns) {
    try {
      await fn(structuredClone(event), ctx);
    } catch (e) {
      failures.push(name + ": " + e.message);
    }
  }
}
process.stdout.write(JSON.stringify({ registered: Object.keys(handlers), failures }));
"""


def drive(bridge):
    entry = os.path.join(BRIDGES, bridge, "index.ts").replace("\\", "/")
    driver = os.path.join(ROOT, "tests", ".tmp_handlers_%s.mjs" % bridge)
    with open(driver, "w", encoding="utf-8") as f:
        f.write(DRIVER % {"url": json.dumps("file:///" + entry)})
    try:
        # A temp cwd, not the repo. Handlers have side effects: driving
        # skill-namespace-guard once wrote a conflict report into
        # ./TODO_SET_BY_RESTORE/pi-config/, because the repo copy of a bridge's
        # package.json still carries that placeholder for its harness root
        # until restore substitutes it. The stray file was committed before
        # anyone noticed.
        sandbox = tempfile.mkdtemp(prefix="bridge-handlers-")
        try:
            p = subprocess.run(["node", driver], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", cwd=sandbox, timeout=180)
        finally:
            shutil.rmtree(sandbox, ignore_errors=True)
        if p.returncode != 0:
            return {"import_failed": (p.stderr or p.stdout).strip()[:200]}
        return json.loads(p.stdout)
    finally:
        if os.path.exists(driver):
            os.remove(driver)


def bridge_names():
    if not os.path.isdir(BRIDGES):
        return []
    return sorted(n for n in os.listdir(BRIDGES)
                  if os.path.isfile(os.path.join(BRIDGES, n, "index.ts")))


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestHandlersExecute(unittest.TestCase):
    def test_every_importable_bridge_runs_its_handlers(self):
        skipped, checked, needs_pi = [], [], []
        for bridge in bridge_names():
            result = drive(bridge)
            if "import_failed" in result:
                skipped.append(bridge)
                continue
            # Pi's loader shims `require`; bare node does not. This repo has
            # already paid for confusing the two — a root cause was once
            # "proved" in the wrong runtime and shipped. A handler that trips
            # only on that is not broken here, but it is also not covered, so
            # it is named rather than swallowed.
            real = [f for f in result["failures"] if "require is not defined" not in f]
            if not real and result["failures"]:
                needs_pi.append(bridge)
                continue
            checked.append(bridge)
            self.assertEqual(
                real, [],
                "%s: a handler threw. Pi swallows this, so the guard simply "
                "stops working — which is how an undeclared `turnWrites` "
                "survived 774 tests and a clean install." % bridge)
        self.assertTrue(checked, "no bridge could be driven at all")
        # Named rather than silent: a skip nobody sees is a gap nobody closes.
        print("\n  handlers driven: %s" % ", ".join(checked))
        if needs_pi:
            print("  handlers need Pi's require shim, uncovered here: %s" % ", ".join(needs_pi))
        if skipped:
            print("  not importable under bare node (Pi-only deps): %s" % ", ".join(skipped))

    def test_the_regression_that_motivated_this(self):
        """yes-hooks-bridge's tool_result handler, specifically."""
        result = drive("yes-hooks-bridge")
        self.assertNotIn("import_failed", result)
        self.assertIn("tool_result", result["registered"])
        self.assertEqual(result["failures"], [])


if __name__ == "__main__":
    unittest.main()
