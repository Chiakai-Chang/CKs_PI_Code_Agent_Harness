"""`task-shape-bridge/plan.ts` — never swept until 2026-08-10.

T1 set out to audit assertions that cannot fail, and the audit produced a
different answer than expected. A pattern sweep found 143 candidate weak
assertions; strengthening six of them in `test_phase_tool_gate.py` and running
the counterfactual showed the strengthening caught **nothing** — 25 failures
with and without it, because sibling tests already asserted the content.

What did find every real weak check that day was the mutation sweep. So the
lever is its COVERAGE, not the wording of assertions: 33 of 48 pure modules were
never swept at all. `plan.ts` was one of them, and it is in the decision path —
`isCaseProject` decides whether the task-shape router stands down in a C.A.S.E.
project, and `isGitCommit` decides whether a commit happened.

Adding it to the sweep produced ten survivors immediately. These tests kill the
ones that describe real behaviour; the module's own comments say why each of
these branches exists, and none of them had a test.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys as _sys
_sys.path.insert(0, os.path.join(ROOT, "tests"))
from _scratch import scratch  # per-process temp names; see tests/_scratch.py

MOD = os.path.join(ROOT, "pi-extensions", "task-shape-bridge", "plan.ts")


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


def run_js(script):
    driver = scratch(".tmp_planmod_driver.mjs")
    url = "file:///" + MOD.replace("\\", "/")
    with open(driver, "w", encoding="utf-8") as f:
        f.write("import * as m from %s;\n%s" % (json.dumps(url), script))
    try:
        p = subprocess.run(["node", driver], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=ROOT,
                           timeout=120)
        if p.returncode != 0:
            raise AssertionError("node driver failed:\n%s\n%s"
                                 % (p.stdout, p.stderr))
        return json.loads(p.stdout)
    finally:
        if os.path.exists(driver):
            os.remove(driver)


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestIsGitCommit(unittest.TestCase):
    """It replaced `command.includes("git commit")`, and every reason it did so
    was untested until now."""

    def check(self, cmd):
        return run_js("process.stdout.write(JSON.stringify(m.isGitCommit(%s)));"
                      % json.dumps(cmd))

    def test_a_plain_commit(self):
        self.assertTrue(self.check("git commit -m x"))

    def test_an_empty_command_is_not_a_commit(self):
        for cmd in ("", " "):
            with self.subTest(cmd=cmd):
                self.assertFalse(self.check(cmd))

    def test_the_phrase_inside_quotes_is_not_a_commit(self):
        """`echo "git commit"` commits nothing. This is the defect the function
        was written to fix, and nothing checked it."""
        self.assertFalse(self.check('echo "git commit"'))
        self.assertFalse(self.check("grep -r 'git commit' docs/"))

    def test_commit_graph_is_not_commit(self):
        self.assertFalse(self.check("git commit-graph write"))

    def test_help_is_not_a_commit(self):
        """`git commit --help` opens the manual and creates nothing."""
        self.assertFalse(self.check("git commit --help"))
        self.assertFalse(self.check("git commit -h"))

    def test_a_dash_capital_c_directory_still_counts(self):
        """`-C <dir>` puts its value in the next word, so the subcommand sits two
        tokens further along than a plain flag leaves it. Without that handling a
        repo-scoped commit reads as no commit at all."""
        self.assertTrue(self.check("git -C /some/repo commit -m x"))

    def test_a_lowercase_dash_c_config_still_counts(self):
        self.assertTrue(self.check("git -c user.name=x commit -m y"))

    def test_it_finds_a_commit_in_a_later_segment(self):
        self.assertTrue(self.check("git add -A && git commit -m x"))


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestResolvePlanDir(unittest.TestCase):
    """Where planning-with-files keeps the active plan."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def resolve(self):
        return run_js("process.stdout.write(JSON.stringify("
                      "m.resolvePlanDir(%s)));" % json.dumps(self.tmp))

    def norm(self, p):
        return p.replace("\\", "/").rstrip("/")

    def test_no_plan_anywhere_returns_cwd(self):
        self.assertEqual(self.norm(self.resolve()), self.norm(self.tmp))

    def test_a_plan_at_the_root_wins(self):
        open(os.path.join(self.tmp, "task_plan.md"), "w").close()
        self.assertEqual(self.norm(self.resolve()), self.norm(self.tmp))

    def test_a_planning_dir_without_a_plan_returns_cwd(self):
        os.makedirs(os.path.join(self.tmp, ".planning"))
        self.assertEqual(self.norm(self.resolve()), self.norm(self.tmp))

    def test_the_active_plan_pointer_is_followed(self):
        d = os.path.join(self.tmp, ".planning", "abc123")
        os.makedirs(d)
        open(os.path.join(d, "task_plan.md"), "w").close()
        with open(os.path.join(self.tmp, ".planning", ".active_plan"), "w") as f:
            f.write("abc123")
        self.assertEqual(self.norm(self.resolve()), self.norm(d))

    def test_a_pointer_to_a_missing_plan_falls_through(self):
        """A stale `.active_plan` must not win over a directory that has one."""
        os.makedirs(os.path.join(self.tmp, ".planning", "gone"))
        real = os.path.join(self.tmp, ".planning", "real")
        os.makedirs(real)
        open(os.path.join(real, "task_plan.md"), "w").close()
        with open(os.path.join(self.tmp, ".planning", ".active_plan"), "w") as f:
            f.write("gone")
        self.assertEqual(self.norm(self.resolve()), self.norm(real))

    def test_with_no_pointer_the_last_plan_directory_is_used(self):
        for name in ("aaa", "zzz"):
            d = os.path.join(self.tmp, ".planning", name)
            os.makedirs(d)
            open(os.path.join(d, "task_plan.md"), "w").close()
        self.assertEqual(self.norm(self.resolve()),
                         self.norm(os.path.join(self.tmp, ".planning", "zzz")))


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestIsCaseProject(unittest.TestCase):
    """The predicate that decides whether the task-shape router stands down."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def call(self):
        return run_js("process.stdout.write(JSON.stringify("
                      "m.isCaseProject(%s)));" % json.dumps(self.tmp))

    def test_an_empty_directory_is_not_a_case_project(self):
        self.assertFalse(self.call())

    def test_case_md_alone_is_enough(self):
        open(os.path.join(self.tmp, "CASE.md"), "w").close()
        self.assertTrue(self.call())

    def test_a_constitution_directory_alone_is_enough(self):
        """The `||` matters: a queue project bootstrapped from the protocol has
        00_Constitution and no CASE.md. Demanding both would keep the router
        firing in exactly the projects it must not fire in."""
        os.makedirs(os.path.join(self.tmp, "00_Constitution"))
        self.assertTrue(self.call())

    def test_both_present_is_still_a_case_project(self):
        open(os.path.join(self.tmp, "CASE.md"), "w").close()
        os.makedirs(os.path.join(self.tmp, "00_Constitution"))
        self.assertTrue(self.call())


if __name__ == "__main__":
    unittest.main()
