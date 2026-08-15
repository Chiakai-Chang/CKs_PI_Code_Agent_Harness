"""`skipUnless` does not fail. It disappears.

Most of this repo's guard behaviour is asserted by driving the actual bridge
modules under node, which is only possible on node >= 22 (native TypeScript type
stripping). Those classes are gated on `skipUnless(NODE_OK)`. Counted
2026-08-15: **38 test files** carry such a class, and `test_universal_tool_parser`
alone is 123 tests.

Until the same day, `.github/workflows/ci.yml` installed Python and nothing else,
relying on whatever node the runner image happened to ship. That is not a
dependency, it is a coincidence — and the failure mode is silent in the worst
way: the run still prints `OK`, and the only trace is that `Ran N tests` quietly
drops by several hundred. Nobody reads N.

So this file does the one thing the skip mechanism cannot do for itself: it
FAILS when the interpreter those tests need is not there.

A machine that genuinely has no node can say so: `HARNESS_ALLOW_NO_NODE=1`. That
is a deliberate, visible opt-out, which is the difference between "we decided" and
"it vanished".
"""

import os
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TESTS = ROOT / "tests"

# The gate every one of those classes uses. Named here so this check breaks
# loudly if the convention is renamed, rather than passing on zero matches.
GATE = "skipUnless(NODE_OK"


def node_version():
    """(major, raw) for the node on PATH, or (None, reason)."""
    try:
        out = subprocess.run(["node", "--version"], capture_output=True,
                             text=True, timeout=30)
    except Exception as exc:  # noqa: BLE001
        return None, type(exc).__name__
    if out.returncode != 0:
        return None, "exit %d" % out.returncode
    raw = out.stdout.strip()
    m = re.match(r"v?(\d+)", raw)
    return (int(m.group(1)) if m else None), raw


def files_gated_on_node():
    """This file is excluded: it contains the literal only to look for it, and
    counting itself would inflate the number by one forever."""
    me = Path(__file__).name
    return sorted(p.name for p in TESTS.glob("test_*.py")
                  if p.name != me
                  and GATE in p.read_text(encoding="utf-8", errors="replace"))


class TestTheGuardTestsCanActuallyRun(unittest.TestCase):
    def test_the_gate_is_still_the_convention(self):
        """An exclusion-based check that matches nothing passes forever. If this
        count ever falls to zero the convention was renamed and the assertion
        below is measuring an empty set."""
        gated = files_gated_on_node()
        self.assertGreater(
            len(gated), 20,
            "only %d test file(s) still gate on %s — was the convention "
            "renamed? This check is blind if so." % (len(gated), GATE))

    def test_node_is_present_and_new_enough(self):
        if os.environ.get("HARNESS_ALLOW_NO_NODE"):
            self.skipTest("HARNESS_ALLOW_NO_NODE is set — a deliberate opt-out")
        major, raw = node_version()
        gated = files_gated_on_node()
        self.assertIsNotNone(
            major,
            "node is not runnable (%s), so the guard classes in %d test files "
            "silently skip and this suite reports OK while asserting almost "
            "nothing about the bridges. Install node >= 22, or set "
            "HARNESS_ALLOW_NO_NODE=1 to say that is intended here."
            % (raw, len(gated)))
        self.assertGreaterEqual(
            major, 22,
            "node %s is older than 22, which is where native TypeScript type "
            "stripping arrives. Without it the guard classes in %d test files "
            "skip. Install node >= 22, or set HARNESS_ALLOW_NO_NODE=1."
            % (raw, len(gated)))


class TestCIInstallsIt(unittest.TestCase):
    """The workflow is the only place that can make this true on a runner, and
    it is a file in this repo, so it can be checked from here.

    This is a source-text check and therefore weak — it proves the step is
    written, not that it worked. The step working is proven by the test above
    passing ON the runner, which is exactly why both exist.
    """

    def setUp(self):
        wf = ROOT / ".github" / "workflows" / "ci.yml"
        if not wf.is_file():
            self.skipTest("no workflow file")
        self.src = wf.read_text(encoding="utf-8")

    def test_the_workflow_installs_node(self):
        self.assertIn("setup-node", self.src,
                      "CI installs Python and relies on the runner image for "
                      "node; that is a coincidence, not a dependency")

    def test_the_workflow_pins_a_version_at_least_22(self):
        m = re.search(r"node-version:\s*[\"']?(\d+)", self.src)
        self.assertIsNotNone(m, "setup-node is present but pins no version")
        self.assertGreaterEqual(int(m.group(1)), 22)


if __name__ == "__main__":
    unittest.main()
