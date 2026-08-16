"""Node driver shared by the cross-repo extractor parity test.

Kept in its own file rather than generated into the test: the generated version
was written by a script that had to escape its own escapes, and produced an
unterminated string literal twice. Code that writes code needs a reason; this
did not have one.
"""

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ADAPTER = ROOT / "external" / "Local-Agent-Workspace" / "adapters" / "pi" / "case-bridge"
GUARD = str(ADAPTER / "task-queue-guard.ts")
CONTAINMENT = str(ROOT / "pi-extensions" / "yes-hooks-bridge" / "bash-containment.ts")

import sys as _sys

_sys.path.insert(0, str(ROOT / "tests"))
from _scratch import scratch  # noqa: E402


def as_url(path):
    return "file:///" + str(path).replace("\\", "/")


def run_js(script, imports=None):
    driver = scratch(".tmp_parity_driver.mjs")
    head = imports or ("import * as m from %s;\n" % json.dumps(as_url(GUARD)))
    with open(driver, "w", encoding="utf-8") as f:
        f.write(head + "import fs from 'node:fs';\n" + script)
    try:
        p = subprocess.run(["node", driver], capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           cwd=str(ROOT), timeout=120)
        if p.returncode != 0:
            raise AssertionError("node driver failed:\n%s\n%s" % (p.stdout, p.stderr))
        return json.loads(p.stdout)
    finally:
        if os.path.exists(driver):
            os.remove(driver)
