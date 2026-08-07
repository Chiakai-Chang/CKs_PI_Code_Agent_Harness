"""The C.A.S.E. guards had the same bash-shaped hole, and a run walked through it.

Measured 2026-08-06 in a clean rerun of the queue advancer. The task went from
PENDING to DONE and not one of the five guards fired, because the model never
touched the write tool:

    bash  printf "IN_PROGRESS" > .../status.txt
    bash  printf "REVIEW"      > .../status.txt
    bash  printf "DONE"        > .../status.txt

`task-queue-guard.ts` watched `write` and `edit`. Illegal transitions, one task
at a time, dual-track, retro-before-DONE and the task boundary were all
invisible to a shell redirect — including Section 1's non-negotiable rule that a
Worker may not approve its own work, which is exactly what that DONE was.

Second time in one day: the directory-containment guard had the identical hole
this morning.

The fix enforces a rule the protocol already states rather than inventing one.
SKILL.md's example of what to never do is, word for word, the behaviour
observed:

    **NEVER** run host shell redirection commands
    (e.g. `echo "IN_PROGRESS" > status.txt`)

and for_agents.md allows shell mutation only "unless high-level API tools are
completely unavailable" — an exception the existing three-strike retirement
already honours.

Deliberately not parsing what bash writes. `printf "DONE" >` yields its content;
`cat > f << EOF`, `echo $VAR >` and `sed -i` do not. Partial parsing is worse
than none, because it would suggest the transition rules apply to shell writes
when they would only apply to some spellings.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(ROOT, "pi-extensions", "case-bridge", "task-queue-guard.ts")
CONTAINMENT = os.path.join(ROOT, "pi-extensions", "yes-hooks-bridge", "bash-containment.ts")


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


def run_js(script, imports=None):
    driver = os.path.join(ROOT, "tests", ".tmp_cgb_driver.mjs")
    head = imports or ('import * as m from %s;\n' % json.dumps("file:///" + GUARD.replace("\\", "/")))
    with open(driver, "w", encoding="utf-8") as f:
        f.write(head + "import fs from 'node:fs';\n" + script)
    try:
        p = subprocess.run(["node", driver], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=ROOT, timeout=120)
        if p.returncode != 0:
            raise AssertionError("node driver failed:\n%s\n%s" % (p.stdout, p.stderr))
        return json.loads(p.stdout)
    finally:
        if os.path.exists(driver):
            os.remove(driver)


class Queue:
    def __init__(self):
        self.root = tempfile.mkdtemp(prefix="cgb-")
        self.dir = os.path.join(self.root, "02_Task_Queue")
        os.makedirs(self.dir)

    def task(self, name, status="PENDING"):
        d = os.path.join(self.dir, name)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "status.txt"), "w", encoding="utf-8") as fh:
            fh.write(status)
        return d.replace("\\", "/")

    def cleanup(self):
        shutil.rmtree(self.root, ignore_errors=True)


def bash_check(command):
    return run_js("""
    const g = new m.TaskQueueGuard();
    const r = g.check("bash", { command: %s }, "");
    process.stdout.write(JSON.stringify({ blocked: !!r, block: r ? r.block : null,
                                          reason: r ? r.reason : "" }));
    """ % json.dumps(command))


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheHoleThatWasWalkedThrough(unittest.TestCase):
    def setUp(self):
        self.q = Queue()
        self.addCleanup(self.q.cleanup)

    def test_the_exact_command_that_reached_DONE(self):
        d = self.q.task("Task_001_probe", "REVIEW")
        out = bash_check('printf "DONE" > "%s/status.txt" && echo ok' % d)
        self.assertTrue(out["blocked"])

    def test_the_reason_names_the_tool_to_use_instead(self):
        d = self.q.task("Task_001_probe", "PENDING")
        out = bash_check('printf "IN_PROGRESS" > "%s/status.txt"' % d)
        self.assertRegex(out["reason"], r"write")
        self.assertRegex(out["reason"], r"(?i)tool-first|SKILL\.md|for_agents")

    def test_the_refusal_actually_carries_block_true(self):
        """`block: true` in this refusal survived the mutation sweep on
        2026-08-08. Every assertion above reads `!!r`, and a refusal object with
        `block: false` is still truthy — so the tool-first guard could keep
        matching the command, keep quoting SKILL.md at the model, and stop
        blocking, with nothing red.

        This is the guard with live evidence behind it: 21 status writes in the
        Task_008 runs went through `write`/`edit` and none through `bash`,
        against a baseline of three that all used `bash`. Pi reads the field."""
        d = self.q.task("Task_001_probe", "PENDING")
        out = bash_check('printf "IN_PROGRESS" > "%s/status.txt"' % d)
        self.assertIs(out["block"], True)

    def test_echo_redirection_too(self):
        d = self.q.task("Task_001_probe", "PENDING")
        self.assertTrue(bash_check('echo IN_PROGRESS > %s/status.txt' % d)["blocked"])

    def test_a_heredoc_into_status_is_still_refused(self):
        """Content is never parsed, so every spelling is refused alike."""
        d = self.q.task("Task_001_probe", "PENDING")
        self.assertTrue(bash_check('cat > "%s/status.txt" << EOF\nDONE\nEOF' % d)["blocked"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestOtherFilesFollowTheBoundaryRule(unittest.TestCase):
    def setUp(self):
        self.q = Queue()
        self.addCleanup(self.q.cleanup)

    def test_writing_into_a_task_that_is_not_the_open_one(self):
        self.q.task("Task_001_a", "IN_PROGRESS")
        d2 = self.q.task("Task_002_b", "PENDING")
        out = bash_check('cat > "%s/output.md" << EOF\nresult\nEOF' % d2)
        self.assertTrue(out["blocked"])
        self.assertIn("Task_001_a", out["reason"])

    def test_writing_into_the_open_task_is_fine(self):
        d1 = self.q.task("Task_001_a", "IN_PROGRESS")
        self.q.task("Task_002_b", "PENDING")
        self.assertFalse(bash_check('cat > "%s/output.md" << EOF\nresult\nEOF' % d1)["blocked"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestEverythingElseIsUntouched(unittest.TestCase):
    """A guard that widens its reach every time is a guard someone turns off."""

    def setUp(self):
        self.q = Queue()
        self.addCleanup(self.q.cleanup)

    def test_writes_outside_any_task_package(self):
        self.q.task("Task_001_a", "IN_PROGRESS")
        for cmd in ('echo x > /tmp/scratch.txt',
                    'printf "y" > notes.md',
                    'cat > src/index.ts << EOF\nx\nEOF'):
            with self.subTest(cmd=cmd):
                self.assertFalse(bash_check(cmd)["blocked"])

    def test_reading_inside_a_task_package(self):
        d = self.q.task("Task_001_a", "IN_PROGRESS")
        for cmd in ('cat "%s/status.txt"' % d,
                    'ls -la "%s"' % d,
                    'grep -r x "%s"' % d):
            with self.subTest(cmd=cmd):
                self.assertFalse(bash_check(cmd)["blocked"])

    def test_the_write_tool_path_is_unchanged(self):
        """Existing behaviour must not shift; the transition rules still apply
        there and this task adds nothing to them."""
        d = self.q.task("Task_001_a", "PENDING")
        out = run_js("""
        const g = new m.TaskQueueGuard();
        const r = g.check("write", { path: %s, content: "DONE" }, "");
        process.stdout.write(JSON.stringify({ blocked: !!r, reason: r ? r.reason : "" }));
        """ % json.dumps(d + "/status.txt"))
        self.assertTrue(out["blocked"])
        self.assertIn("transition guard", out["reason"])

    def test_an_unparseable_command_fails_open(self):
        self.assertFalse(bash_check('eval "$(cat script.sh)"')["blocked"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestItRetires(unittest.TestCase):
    """for_agents.md allows shell mutation when high-level tools are completely
    unavailable. A run that keeps trying is telling us that is the case."""

    def setUp(self):
        self.q = Queue()
        self.addCleanup(self.q.cleanup)

    def test_three_refusals_then_it_steps_aside(self):
        d = self.q.task("Task_001_a", "PENDING")
        out = run_js("""
        const g = new m.TaskQueueGuard();
        let blocks = 0, allowedAfter = 0;
        for (let i = 0; i < 12; i++) {
          if (g.check("bash", { command: 'printf "IN_PROGRESS" > "%s/status.txt"' }, "")) blocks++;
          else if (blocks > 0) allowedAfter++;
        }
        process.stdout.write(JSON.stringify({ blocks, allowedAfter }));
        """ % d)
        self.assertGreater(out["blocks"], 0)
        self.assertGreater(out["allowedAfter"], 0)
        self.assertLessEqual(out["blocks"], 4)


@unittest.skipUnless(NODE_OK, "node >= 22 required")
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
