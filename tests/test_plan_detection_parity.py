"""Two bridges, one question: is there an active plan?

ecc-hooks-bridge asked `existsSync(join(process.cwd(), "task_plan.md"))` and
nagged about `/plan` whenever the answer was no. planning-with-files-bridge asked
`resolvePlanDir()`, which also honours `.planning/.active_plan` and
`.planning/<id>/task_plan.md`. A plan kept anywhere but the repo root therefore
existed for one bridge and not the other, and every commit drew the nag.

Duplicated logic that nobody compares is the failure in
`unguarded-lists-drift-silently`: uninstall.py managed 5 bridges against
restore.py's 11 and seven extensions loaded forever. This file compares them, so
the next edit that moves one implementation and not the other goes red.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ECC = os.path.join(ROOT, "pi-extensions", "ecc-hooks-bridge", "plan.ts")
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
    driver = os.path.join(ROOT, "tests", ".tmp_parity_driver.mjs")
    with open(driver, "w", encoding="utf-8") as f:
        f.write(
            "import * as ecc from %s;\nimport * as pwf from %s;\n%s"
            % (
                json.dumps("file:///" + ECC.replace("\\", "/")),
                json.dumps("file:///" + PWF.replace("\\", "/")),
                script,
            )
        )
    try:
        p = subprocess.run(["node", driver], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=ROOT, timeout=120)
        if p.returncode != 0:
            raise AssertionError("node driver failed:\n%s\n%s" % (p.stdout, p.stderr))
        return json.loads(p.stdout)
    finally:
        if os.path.exists(driver):
            os.remove(driver)


def write(path, text=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class PlanLayouts:
    """Each builder returns the cwd both bridges are asked about."""

    @staticmethod
    def plan_in_root(base):
        write(os.path.join(base, "task_plan.md"), "# plan")
        return base

    @staticmethod
    def plan_via_active_plan_pointer(base):
        write(os.path.join(base, ".planning", "2026-08-04-work", "task_plan.md"), "# plan")
        write(os.path.join(base, ".planning", ".active_plan"), "2026-08-04-work\n")
        return base

    @staticmethod
    def plan_in_planning_dir_without_pointer(base):
        write(os.path.join(base, ".planning", "some-plan", "task_plan.md"), "# plan")
        return base

    @staticmethod
    def planning_dir_but_no_plan_file(base):
        write(os.path.join(base, ".planning", "empty", "notes.md"), "x")
        return base

    @staticmethod
    def no_plan_at_all(base):
        write(os.path.join(base, "README.md"), "x")
        return base


LAYOUTS_WITH_A_PLAN = [
    "plan_in_root",
    "plan_via_active_plan_pointer",
    "plan_in_planning_dir_without_pointer",
]
LAYOUTS_WITHOUT_A_PLAN = [
    "planning_dir_but_no_plan_file",
    "no_plan_at_all",
]


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestPlanDetectionParity(unittest.TestCase):
    def _both(self, layout_name):
        base = tempfile.mkdtemp(prefix="plan-parity-")
        try:
            cwd = getattr(PlanLayouts, layout_name)(base)
            return run_js(
                'const cwd = %s;\n'
                'process.stdout.write(JSON.stringify({\n'
                '  ecc: ecc.resolvePlanDir(cwd), pwf: pwf.resolvePlanDir(cwd),\n'
                '  eccHas: ecc.hasAnyPlan(cwd), pwfHas: pwf.hasAnyPlan(cwd),\n'
                '}));' % json.dumps(cwd)
            )
        finally:
            shutil.rmtree(base, ignore_errors=True)

    def test_both_bridges_resolve_the_same_directory(self):
        for layout in LAYOUTS_WITH_A_PLAN + LAYOUTS_WITHOUT_A_PLAN:
            with self.subTest(layout=layout):
                out = self._both(layout)
                self.assertEqual(
                    os.path.normcase(os.path.normpath(out["ecc"])),
                    os.path.normcase(os.path.normpath(out["pwf"])),
                )

    def test_both_bridges_agree_a_plan_exists(self):
        for layout in LAYOUTS_WITH_A_PLAN:
            with self.subTest(layout=layout):
                out = self._both(layout)
                self.assertTrue(out["pwfHas"], layout)
                self.assertEqual(out["eccHas"], out["pwfHas"], layout)

    def test_both_bridges_agree_no_plan_exists(self):
        """The nag has to still fire when there genuinely is no plan — a parity
        fix that makes both sides answer 'yes' everywhere would pass the test
        above while deleting the feature."""
        for layout in LAYOUTS_WITHOUT_A_PLAN:
            with self.subTest(layout=layout):
                out = self._both(layout)
                self.assertFalse(out["pwfHas"], layout)
                self.assertEqual(out["eccHas"], out["pwfHas"], layout)


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestGitCommitDetection(unittest.TestCase):
    """`command.includes("git commit")` fired on any bash that merely said the
    words — writing this very file would have tripped it."""

    def _is_commit(self, command):
        out = run_js('process.stdout.write(JSON.stringify({ v: ecc.isGitCommit(%s) }));'
                     % json.dumps(command))
        return out["v"]

    def test_recognises_real_commits(self):
        for cmd in [
            'git commit -m "x"',
            "git commit",
            "git   commit -am x",
            'git add . && git commit -m "x"',
            'cd /tmp; git commit -m "x"',
            # Flags that take a value sit between `git` and the subcommand. A
            # first cut consumed `-C` and then choked on the path after it.
            'git -C /some/repo commit -m "x"',
            "git --git-dir=/r/.git commit -m x",
        ]:
            with self.subTest(cmd=cmd):
                self.assertTrue(self._is_commit(cmd))

    def test_ignores_commands_that_only_mention_committing(self):
        for cmd in [
            'echo "git commit"',
            'grep -rn "git commit" docs/',
            "git commit --help",
            "git log --grep='git commit'",
            "git commit-graph write",
        ]:
            with self.subTest(cmd=cmd):
                self.assertFalse(self._is_commit(cmd))


class TestBridgeSourceHygiene(unittest.TestCase):
    """Source-level guards for wiring that cannot be imported and called.

    Comment lines are stripped before matching. A first cut of these two guards
    matched the prose as well as the code, so documenting the very fix they
    describe turned them red.
    """

    def _code_lines(self, rel):
        with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
            out = []
            for line in f:
                s = line.strip()
                if s.startswith("//") or s.startswith("*") or s.startswith("/*"):
                    continue
                out.append(s)
            return out

    def test_ecc_bridge_asks_the_session_for_its_cwd(self):
        """process.cwd() is where Pi was launched; ctx.cwd is where the session
        is. Every other bridge uses ctx.cwd, and so did line 279 of this one.

        One occurrence is allowed: the documented fallback that seeds sessionCwd
        before session_start has fired. Any second one is a hook auditing the
        wrong directory again.
        """
        uses = [ln for ln in self._code_lines("pi-extensions/ecc-hooks-bridge/index.ts")
                if "process.cwd()" in ln]
        self.assertEqual(uses, ["let sessionCwd = process.cwd();"])

    def test_planning_bridge_reminder_goes_to_content_not_details(self):
        """AgentToolResult.details is documented 'for logs or UI rendering'. The
        reminder returned through it was never read by anything."""
        uses = [ln for ln in self._code_lines("pi-extensions/planning-with-files-bridge/index.ts")
                if "planningReminder" in ln]
        self.assertEqual(uses, [], "reminder still routed through details")


if __name__ == "__main__":
    unittest.main()
