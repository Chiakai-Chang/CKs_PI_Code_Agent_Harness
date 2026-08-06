"""The containment guard had a bash-shaped hole, and a model walked through it.

Measured 2026-08-06 in a live run. Pi was launched in a temp directory; the
prompt asked it to set a task's status. Its tool calls, in order:

    write  D:/MyProject/CKs_PI_Code_Agent_Harness/02_Task_Queue/.../status.txt
           -> BLOCKED by the directory-containment guard
    bash   echo "DONE" > "D:/MyProject/CKs_PI_Code_Agent_Harness/02_Task_Queue/..."
           -> allowed
    ...four bash calls hunting for the directory...
    bash   mkdir -p ".../external/Local-Agent-Workspace/C.A.S.E._Framework/02_Task_Queue/Task_001_Probe/"
             && echo "DONE" > ".../status.txt"
           -> allowed; wrote into this harness's own vendored submodule
    then reported "已完成" to the user

The guard covered `write` and `edit`. Refused there, the run reached for `bash`
and got through — into the very submodule the vendored-skill guard exists to
protect. The containment guard was added because a run once "wrote files into a
sibling project AND edited this harness's own scripts"; it has had this hole the
whole time.

Scratch locations are deliberately allowed. Writing to /tmp, %TEMP% or /dev/null
is ordinary work, and a guard that refuses it would be turned off within a day.
What is refused is a write into somewhere that looks like another project.
"""

import json
import os
import re
import shutil
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(ROOT, "pi-extensions", "yes-hooks-bridge", "bash-containment.ts")


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
    driver = os.path.join(ROOT, "tests", ".tmp_bashc_driver.mjs")
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


CWD = "C:/Users/User/AppData/Local/Temp/tmp.project"


def blocked(command, cwd=CWD):
    out = run_js("""
    const r = m.bashContainmentBlock(%s, %s);
    process.stdout.write(JSON.stringify({ blocked: !!r, reason: r ? r.reason : "" }));
    """ % (json.dumps(command), json.dumps(cwd)))
    return out


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheHoleThatWasWalkedThrough(unittest.TestCase):
    def test_the_exact_command_from_the_live_run(self):
        out = blocked('mkdir -p "D:/MyProject/CKs_PI_Code_Agent_Harness/external/Local-Agent-Workspace/'
                      'C.A.S.E._Framework/02_Task_Queue/Task_001_Probe/" && echo "DONE" > '
                      '"D:/MyProject/CKs_PI_Code_Agent_Harness/external/Local-Agent-Workspace/'
                      'C.A.S.E._Framework/02_Task_Queue/Task_001_Probe/status.txt"')
        self.assertTrue(out["blocked"])
        self.assertIn("CKs_PI_Code_Agent_Harness", out["reason"])

    def test_the_first_retry_after_the_write_was_refused(self):
        out = blocked('echo "DONE" > "D:/MyProject/CKs_PI_Code_Agent_Harness/02_Task_Queue/x/status.txt"')
        self.assertTrue(out["blocked"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestWriteShapes(unittest.TestCase):
    def test_append_redirection(self):
        self.assertTrue(blocked('echo hi >> D:/other-project/notes.md')["blocked"])

    def test_tee(self):
        self.assertTrue(blocked('echo hi | tee D:/other-project/notes.md')["blocked"])
        self.assertTrue(blocked('echo hi | tee -a D:/other-project/notes.md')["blocked"])

    def test_copy_and_move_destinations(self):
        self.assertTrue(blocked('cp a.txt D:/other-project/a.txt')["blocked"])
        self.assertTrue(blocked('mv a.txt D:/other-project/a.txt')["blocked"])

    def test_mkdir(self):
        self.assertTrue(blocked('mkdir -p D:/other-project/newdir')["blocked"])

    def test_parent_traversal_out_of_the_project(self):
        self.assertTrue(blocked('echo x > ../../elsewhere/f.txt')["blocked"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestOrdinaryWorkIsUntouched(unittest.TestCase):
    """A guard that refuses normal commands is a guard that gets switched off."""

    def test_writes_inside_the_project(self):
        for cmd in ['echo x > out.txt', 'echo x > ./sub/out.txt',
                    'cat a > b', 'mkdir -p sub/dir', 'cp a b']:
            with self.subTest(cmd=cmd):
                self.assertFalse(blocked(cmd)["blocked"])

    def test_scratch_locations_are_allowed(self):
        for cmd in ['echo x > /tmp/scratch.txt', 'echo x > /dev/null',
                    'curl -s url -o /tmp/page.html 2>/dev/null']:
            with self.subTest(cmd=cmd):
                self.assertFalse(blocked(cmd)["blocked"])

    def test_reading_anywhere_is_allowed(self):
        for cmd in ['ls -la D:/other-project/', 'cat D:/other-project/f.md',
                    'grep -r foo D:/other-project/', 'find D:/other-project -name x']:
            with self.subTest(cmd=cmd):
                self.assertFalse(blocked(cmd)["blocked"])

    def test_a_redirection_inside_quotes_is_not_a_redirection(self):
        self.assertFalse(blocked('echo "a > D:/other-project/b"')["blocked"])

    def test_stderr_redirection_to_a_descriptor(self):
        self.assertFalse(blocked('some-cmd 2>&1')["blocked"])

    def test_an_absolute_path_inside_the_project_is_fine(self):
        self.assertFalse(blocked('echo x > %s/out.txt' % CWD)["blocked"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestFailOpen(unittest.TestCase):
    """Anything it cannot read, it must not refuse."""

    def test_no_cwd(self):
        self.assertFalse(blocked('echo x > D:/other/f', cwd="")["blocked"])

    def test_empty_command(self):
        self.assertFalse(blocked('')["blocked"])

    def test_a_command_it_cannot_parse(self):
        self.assertFalse(blocked('eval "$(cat script.sh)"')["blocked"])


if __name__ == "__main__":
    unittest.main()
