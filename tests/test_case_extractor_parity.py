"""The bash-target extractors on both sides of the C.A.S.E. split must agree.

`yes-hooks-bridge/bash-containment.ts` lives here; the C.A.S.E. adapter's
`task-queue-guard.ts` lives in the protocol's own repository since 2026-08-17.
Two extractors answering "which paths would this command write to" is a contract
BETWEEN the repositories — when they disagree, one of them refuses a command the
other allows, and the model gets two different accounts of the same shell line.
That has happened here before: a `2>/dev/null` redirect broke both extractors in
OPPOSITE directions, one refusing an innocent `ls` and the other letting a copy
escape the project.

So this test belongs where both are present, which is the harness. It skips
when the submodule is not checked out — CI pulls no submodules, and this repo
has been red twice for forgetting that.
"""

import json
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ADAPTER = ROOT / "external" / "Local-Agent-Workspace" / "adapters" / "pi" / "case-bridge"
HAS_ADAPTER = ADAPTER.is_dir()


def node_ok():
    try:
        out = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=30)
        return out.returncode == 0 and int(out.stdout.strip().lstrip("v").split(".")[0]) >= 22
    except Exception:
        return False


NODE_OK = node_ok() and HAS_ADAPTER

import sys as _sys
_sys.path.insert(0, str(ROOT / "tests"))
from _parity_helpers import GUARD, CONTAINMENT, run_js, as_url  # noqa: E402

class TestTheTwoExtractorsAgree(unittest.TestCase):
    """Two copies of the same logic drift. This repo has the scar: uninstall.py
    managed five bridges while restore.py managed eleven.

    They are not shared by import on purpose — installed bridges are sibling
    directories and a cross-bridge dependency is fragile — so a test holds them
    together instead.
    """

    CASES = [
        'echo x > out.txt',
        'printf "y" >> a/b.md',
        'cat > "some dir/f.md" << EOF\nbody\nEOF',
        'echo hi | tee notes.md',
        'cp a.txt b/c.txt',
        'mv a.txt b/c.txt',
        'mkdir -p a/b',
        'ls -la /somewhere',
        'grep -r foo .',
        'echo "a > b"',
        'some-cmd 2>&1',
        # Redirections among the operands. Both extractors got these wrong in
        # opposite directions until 2026-08-10: the queue guard read
        # `2>/dev/null` as a write and refused innocent `ls` calls, while
        # containment let `2>/dev/null` stand in as a cp destination and
        # stopped seeing the real one.
        'ls 02_Task_Queue/ 2>/dev/null',
        'find . -type f 2>/dev/null',
        'cp a.txt b/c.txt 2>/dev/null',
        'mv a.txt b/c.txt 2>/dev/null',
        'ls > out.txt 2>/dev/null',
        'mkdir -p a/b 2>/dev/null',
        'echo x > /dev/null',
        'eval "$(cat script.sh)"',
        # Task_013. Added to BOTH copies in the same change, because parity is
        # silent when both sides are wrong: every one of these returned [] on
        # both extractors before the change, so the parity test was green while
        # the hole was open.
        "sed -i 's/a/b/' notes.md",
        "sed -i.bak 's/a/b/' notes.md",
        "sed -i -e 's|a|b|' f1.md f2.md",
        "sed 's/a/b/' notes.md",
        "perl -pi -e 's/a/b/' notes.md",
        'dd if=in.bin of=out.bin bs=1M',
        'dd if=in.bin bs=1M',
    ]

    def test_the_new_forms_are_actually_extracted(self):
        """Parity alone would pass if both copies still returned nothing. This
        pins the answers, so a future edit that quietly drops a form fails here
        as well as in the containment tests."""
        imports = ('import * as g from %s;\n'
                   % json.dumps("file:///" + GUARD.replace("\\", "/")))
        out = run_js("""
        process.stdout.write(JSON.stringify({
          inPlace: g.bashWriteTargets("sed -i 's/a/b/' notes.md"),
          readOnly: g.bashWriteTargets("sed 's/a/b/' notes.md"),
          dd: g.bashWriteTargets("dd if=in.bin of=out.bin bs=1M"),
        }));
        """, imports=imports)
        self.assertEqual(out["inPlace"], ["notes.md"])
        self.assertEqual(out["readOnly"], [])
        self.assertEqual(out["dd"], ["out.bin"])

    def test_same_targets_for_the_same_commands(self):
        imports = ('import * as g from %s;\nimport * as c from %s;\n'
                   % (json.dumps("file:///" + GUARD.replace("\\", "/")),
                      json.dumps("file:///" + CONTAINMENT.replace("\\", "/"))))
        out = run_js("""
        const cases = %s;
        const rows = cases.map(cmd => ({
          cmd,
          guard: g.bashWriteTargets(cmd),
          containment: c.writeTargets(cmd),
        }));
        process.stdout.write(JSON.stringify({ rows }));
        """ % json.dumps(self.CASES), imports=imports)
        for row in out["rows"]:
            with self.subTest(cmd=row["cmd"]):
                self.assertEqual(row["guard"], row["containment"],
                                 "the two extractors disagree, so one of them is wrong")


if __name__ == "__main__":
    unittest.main()


if __name__ == "__main__":
    unittest.main()
