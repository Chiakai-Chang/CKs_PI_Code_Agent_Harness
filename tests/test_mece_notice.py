"""The MECE-Autopilot notice has to say where to run the thing.

Run 10, 2026-08-12. The bridge already injected the orchestrator's absolute
path, and the model still ran

    cd "<harness repo>" && node "external/mece-autopilot/scripts/…" --init "…"

from a session whose workspace was elsewhere, leaving `wiki/` and `skills/`
inside the harness. The orchestrator writes its state beside whatever directory
it runs in, and the notice ended by telling the model to check
`wiki/.mece_state.json` — relative, with nothing saying relative to what.

Containment now refuses that crossing. This is the other half: not pulling the
model there in the first place.
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
from _scratch import scratch  # per-process temp names; see tests/_scratch.py

MOD = os.path.join(ROOT, "pi-extensions", "mece-autopilot-bridge", "notice.ts")
INDEX = os.path.join(ROOT, "pi-extensions", "mece-autopilot-bridge", "index.ts")


def _node_major():
    if not shutil.which("node"):
        return 0
    try:
        out = subprocess.run(["node", "--version"], capture_output=True,
                             text=True, timeout=30).stdout
    except Exception:
        return 0
    m = re.match(r"v(\d+)", out.strip())
    return int(m.group(1)) if m else 0


NODE_OK = _node_major() >= 22


def notice(script):
    driver = scratch(".tmp_mece_notice.mjs")
    url = "file:///" + MOD.replace("\\", "/")
    with open(driver, "w", encoding="utf-8") as f:
        f.write("import { buildNotice } from %s;\n"
                "process.stdout.write(JSON.stringify(buildNotice(%s)));"
                % (json.dumps(url), json.dumps(script)))
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
class TestTheNoticeNamesTheWorkingDirectory(unittest.TestCase):
    SCRIPT = "D:/harnessroot/external/mece-autopilot/scripts/mece-autopilot-orchestrator.js"

    def setUp(self):
        self.parts = notice(self.SCRIPT)
        self.text = "\n".join(self.parts)

    def test_the_absolute_script_path_is_still_given(self):
        """Four commands, each with the full path — a relative one resolves
        nowhere in the user's workspace."""
        self.assertEqual(self.text.count(self.SCRIPT), 4)

    def test_it_says_to_run_from_the_workspace(self):
        self.assertIn("YOUR workspace", self.text)

    def test_it_says_not_to_cd_into_the_harness(self):
        self.assertIn("cd", self.text)
        self.assertIn("harness", self.text)

    def test_the_state_check_is_no_longer_an_unanchored_relative_path(self):
        """`wiki/.mece_state.json` on its own is what sent the run into the
        harness: a relative path with no directory named."""
        line = [p for p in self.parts if ".mece_state.json" in p][0]
        self.assertIn("IN YOUR WORKSPACE", line)

    def test_the_bridge_uses_this_builder(self):
        """index.ts opens with require.resolve and cannot be imported here, so
        this one assertion is read rather than driven."""
        with open(INDEX, encoding="utf-8") as f:
            src = f.read()
        self.assertIn("buildNotice(ORCHESTRATOR_SCRIPT)", src)
        self.assertNotIn("MECE-Autopilot reasoning engine is available", src,
                         "the text moved to notice.ts; a second copy would drift")


if __name__ == "__main__":
    unittest.main()
