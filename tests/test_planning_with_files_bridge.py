"""planning-with-files-bridge: the progress.md reminder nobody received.

The bridge returned its reminder as `{ details: { planningReminder: msg } }` from
a tool_result handler. Checked against the installed runtime,
`@earendil-works/pi-agent-core dist/types.d.ts:310`:

    interface AgentToolResult<T> {
      content: (TextContent | ImageContent)[];  // "returned to the model"
      details: T;                               // "for logs or UI rendering"
    }

`details` is not a channel to the model, so for the life of the bridge the
reminder went to the session record and stopped. The source comment said as much
without noticing — "just log for model awareness via system prompt pattern" is a
hope, not a mechanism.

Moving it to `content` puts it on every single write and edit, which is its own
problem, so the reminder is throttled and that throttle is pinned here.
"""

import json
import os
import re
import shutil
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PWF = os.path.join(ROOT, "pi-extensions", "planning-with-files-bridge", "index.ts")


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
    driver = os.path.join(ROOT, "tests", ".tmp_pwf_driver.mjs")
    url = "file:///" + PWF.replace("\\", "/")
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


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestProgressReminderThrottle(unittest.TestCase):
    def test_does_not_remind_on_every_single_edit(self):
        """A reminder appended to every write and edit is a reminder the model
        learns to skip, and it is paid for in context on each one."""
        out = run_js("""
        const fired = [];
        for (let i = 1; i <= 12; i++) if (m.shouldRemindProgress(i)) fired.push(i);
        process.stdout.write(JSON.stringify({ fired }));
        """)
        self.assertLess(len(out["fired"]), 12)
        self.assertGreater(len(out["fired"]), 0)

    def test_reminds_at_a_fixed_interval(self):
        out = run_js("""
        const fired = [];
        for (let i = 1; i <= 12; i++) if (m.shouldRemindProgress(i, 4)) fired.push(i);
        process.stdout.write(JSON.stringify({ fired }));
        """)
        self.assertEqual(out["fired"], [4, 8, 12])

    def test_the_zeroth_edit_is_not_a_reminder(self):
        """Before any edit there is nothing to record in progress.md."""
        out = run_js('process.stdout.write(JSON.stringify({ v: m.shouldRemindProgress(0, 4) }));')
        self.assertFalse(out["v"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestPlanDetectionCoversNonRootPlans(unittest.TestCase):
    def test_hasAnyPlan_is_exported_for_the_parity_check(self):
        """ecc-hooks-bridge carries a copy of this logic; the parity test needs
        both sides callable or it silently checks nothing."""
        out = run_js("""
        process.stdout.write(JSON.stringify({
          resolve: typeof m.resolvePlanDir, has: typeof m.hasAnyPlan,
        }));
        """)
        self.assertEqual(out["resolve"], "function")
        self.assertEqual(out["has"], "function")


if __name__ == "__main__":
    unittest.main()
