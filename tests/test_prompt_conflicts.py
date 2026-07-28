"""The cross-bridge prompt audit, and the defect it exists to catch.

Nine bridges inject confident instructions into the same system prompt and
nothing ever looked at the combination. That gap produced two measured failures
on 2026-07-28, both traced to one line in stealth-web-bridge claiming an
unconditional scope ("call web_search for any task needing current or external
information"):

  * the model web_searched for a LOCAL skill file whose path it had just read
    out of skill-catalog.json;
  * told "Call the deep_research tool once", it called web_search instead.

These tests check the checker against that real wording — not a synthetic
example — and pin the repo's own guidance clean.
"""

import os
import subprocess
import sys
import tempfile
import shutil
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "check-prompt-conflicts.py")


def run(root, *extra):
    p = subprocess.run([sys.executable, SCRIPT, "--root", root, *extra],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=120)
    return p.returncode, p.stdout + p.stderr


def make_bridge(root, name, body):
    d = os.path.join(root, "pi-extensions", name)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "index.ts"), "w", encoding="utf-8") as f:
        f.write(body)


class TestCatchesTheRealDefect(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_flags_the_exact_line_that_caused_two_failures(self):
        make_bridge(self.tmp, "web-bridge", '''
export default function (pi) {
  pi.registerTool({
    name: "web_search",
    promptGuidelines: [
      "You CAN access the internet: call web_search for any task needing current or external information. Never say you cannot browse.",
    ],
  });
}
''')
        code, out = run(self.tmp)
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL", out)
        self.assertIn("for any task", out)

    def test_scoped_wording_passes(self):
        make_bridge(self.tmp, "web-bridge", '''
export default function (pi) {
  pi.registerTool({
    name: "web_search",
    promptGuidelines: [
      "You CAN access the internet: call web_search for a lookup you want the results of in THIS conversation.",
    ],
  });
}
''')
        code, out = run(self.tmp)
        self.assertEqual(code, 0, out)

    def test_ignores_comments_that_quote_the_bad_wording(self):
        """Comments explaining a past bug quote the phrasing verbatim. Auditing
        them would flag the explanation instead of the instruction."""
        make_bridge(self.tmp, "web-bridge", '''
export default function (pi) {
  // This used to say "call web_search for any task needing current or external
  // information", which swallowed every other route to the web.
  pi.registerTool({
    name: "web_search",
    promptGuidelines: ["Call web_search for a single lookup."],
  });
}
''')
        code, out = run(self.tmp)
        self.assertEqual(code, 0, out)

    def test_reports_shared_trigger_vocabulary(self):
        make_bridge(self.tmp, "a-bridge", '''
export default function (pi) {
  pi.registerTool({ name: "a_tool", promptGuidelines: ["Use this to search the web."] });
}
''')
        make_bridge(self.tmp, "b-bridge", '''
export default function (pi) {
  pi.registerTool({ name: "b_tool", promptGuidelines: ["Use this to search the web too."] });
}
''')
        code, out = run(self.tmp)
        self.assertEqual(code, 0, "shared vocabulary is a warning, not a failure:\n%s" % out)
        self.assertIn("Shared trigger vocabulary", out)
        self.assertIn("a-bridge", out)
        self.assertIn("b-bridge", out)

    def test_names_its_own_blind_spot(self):
        """A silent gap in a conflict checker is worse than a named one."""
        make_bridge(self.tmp, "c-bridge", '''
export default function (pi) {
  pi.on("before_agent_start", (event) => ({ systemPrompt: event.systemPrompt + "extra rules" }));
}
''')
        code, out = run(self.tmp)
        self.assertIn("NOT COVERED", out)
        self.assertIn("c-bridge", out)


class TestRepoIsClean(unittest.TestCase):
    def test_shipped_bridges_have_no_absolutist_guidance(self):
        code, out = run(ROOT)
        self.assertEqual(code, 0, out)

    def test_reports_the_total_injected_budget(self):
        _code, out = run(ROOT)
        self.assertIn("Total injected guidance", out)


if __name__ == "__main__":
    unittest.main()
