"""The refusal that names the mistake but not the way out.

cwd confusion is the largest single failure source measured on 2026-08-06: two of
five advancer runs were consumed by it (11 and 72 refusals, status never leaving
PENDING), and a Task_016 run tried to write its report into THIS repository. In
every case the model resolved a relative path against the harness install rather
than its own workspace — which is not mysterious. The system prompt names the
harness's absolute path 28 times, mostly as `<location>` on skills, and names the
cwd once.

The containment guard already refuses these and already names the cwd. The model
kept retrying anyway — nine times in one run. Today's central lesson says why: a
refusal removes the wrong path and supplies nothing. So when the target is inside
the harness install and the cwd is somewhere else, the refusal now carries the
same path rewritten into the workspace, ready to copy.

Deliberately narrow. A target outside the project that has nothing to do with the
harness gets the ordinary refusal — inventing a destination for it would be a
guess, and a guard that guesses is one nobody trusts.
"""

import json
import os
import re
import shutil
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(ROOT, "pi-extensions", "yes-hooks-bridge", "harness-root.ts")


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
    driver = os.path.join(ROOT, "tests", ".tmp_hroot_driver.mjs")
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


HARNESS = "D:/MyProject/CKs_PI_Code_Agent_Harness"
WORK = "C:/tmp/some-workspace"


def hint(target, cwd=WORK, harness=HARNESS):
    return run_js("""
    const h = m.harnessRootHint(%s, %s, %s);
    process.stdout.write(JSON.stringify({ hint: h }));
    """ % (json.dumps(target), json.dumps(cwd), json.dumps(harness)))


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestItOffersTheWorkspacePath(unittest.TestCase):
    def test_the_shape_that_ate_two_runs(self):
        out = hint(HARNESS + "/02_Task_Queue/Task_001_probe/status.txt")
        self.assertIsNotNone(out["hint"])
        self.assertIn(WORK + "/02_Task_Queue/Task_001_probe/status.txt", out["hint"])

    def test_it_says_why_the_wrong_path_looked_right(self):
        """The prompt names the harness path on every skill. Saying so is the
        difference between "no" and "here is where that belief came from"."""
        out = hint(HARNESS + "/wiki/research/report.md")
        self.assertRegex(out["hint"], r"技能|skills|<location>|安裝")

    def test_the_vendored_submodule_case(self):
        out = hint(HARNESS + "/external/Local-Agent-Workspace/C.A.S.E._Framework/02_Task_Queue/x/status.txt")
        self.assertIsNotNone(out["hint"])
        self.assertIn(WORK, out["hint"])

    def test_backslashes_are_the_same_path(self):
        """Windows hands paths back with backslashes and the same place must not
        read as a different one. Built with chr(92) rather than escapes: four
        layers of quoting (python source, python string, json, JS) is how a
        backslash silently went missing three times today."""
        bs = chr(92)
        out = hint(HARNESS.replace("/", bs) + bs + "02_Task_Queue" + bs + "x.md")
        self.assertIsNotNone(out["hint"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestItDoesNotGuess(unittest.TestCase):
    def test_an_unrelated_directory_gets_no_invented_destination(self):
        """Two shapes, because one of them survived a deliberate break: a path
        that shares no prefix with the harness, and one that shares the parent
        directory but is a different project."""
        for target in ("D:/SomeoneElsesProject/src/main.ts",
                       "D:/MyProject/AnotherRepo/src/main.ts",
                       "C:/Windows/System32/drivers/etc/hosts"):
            with self.subTest(target=target):
                self.assertIsNone(hint(target)["hint"])

    def test_an_unrelated_path_longer_than_the_harness_root(self):
        """The break Task_003 could not catch, caught.

        Deleting the whole `if (!t.startsWith(h + "/")) return null;`
        precondition left all eleven tests green on 2026-08-08, and the
        mutation runner could not reach it either — statement deletion is not
        one of its operators. Only reproducing the original break by hand found
        it, which is the third time a fixture has been unable to distinguish a
        removed guard from a present one.

        The reason the other cases pass is arithmetic, not coverage: every
        unrelated path above is SHORTER than the harness root, so without the
        precondition `t.slice(h.length + 1)` yields "" and the next line's
        `if (!rest) return null` catches it by accident. A longer one falls
        through and produces a redirection built from someone else's path."""
        target = ("D:/SomeoneElsesProject/deeply/nested/source/tree/"
                  "that/is/longer/than/the/harness/root/main.ts")
        self.assertGreater(len(target), len(HARNESS),
                           "the whole point of this case is the length")
        self.assertIsNone(hint(target)["hint"])

    def test_working_inside_the_harness_itself_is_not_confusion(self):
        """Someone editing this repository is not lost — there is nowhere to
        redirect them to."""
        self.assertIsNone(hint(HARNESS + "/scripts/setup.py", cwd=HARNESS)["hint"])

    def test_no_harness_root_known(self):
        self.assertIsNone(hint(HARNESS + "/02_Task_Queue/x", harness="")["hint"])

    def test_a_target_that_is_the_harness_root_itself(self):
        self.assertIsNone(hint(HARNESS)["hint"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestEachMissingInputIsItsOwnReason(unittest.TestCase):
    """Added 2026-08-08 because the mutation runner found the hole, not because
    anyone suspected it.

    `harness-root.ts:40` reads `if (!t || !c || !h) return null;`. Flipping
    either `||` to `&&` — so the guard bails only when ALL THREE are empty —
    left the whole suite green. `test_no_harness_root_known` looks like it
    covers this and does not: with an empty harness root the mutant falls
    through to `t.startsWith("/")`, which is false for a Windows path, so null
    comes back through a different door and the test passes either way.

    An empty cwd is the case that shows it. The mutant builds a hint whose
    workspace path is `/02_Task_Queue/x` — a confident redirection to the root
    of the drive, offered to a model that is already lost."""

    def test_an_empty_cwd_gets_no_hint(self):
        self.assertIsNone(hint(HARNESS + "/02_Task_Queue/x", cwd="")["hint"])

    def test_an_empty_target_gets_no_hint(self):
        self.assertIsNone(hint("")["hint"])


def refusal(target, cwd=WORK, harness=HARNESS, tool="write"):
    return run_js("""
    const r = m.containmentRefusal(%s, %s, %s, %s);
    process.stdout.write(JSON.stringify({ reason: r }));
    """ % (json.dumps(tool), json.dumps(target), json.dumps(cwd), json.dumps(harness)))["reason"]


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheRefusalCarriesIt(unittest.TestCase):
    """Task_003's second surviving break, closed by moving the code rather than
    by tightening the assertion.

    The old test read `index.ts` and looked for `harnessRootHint(...)` near
    `reason:`. Replacing the call with `null` left it green, because the
    identifier appears twice in that expression and the assertion was textual.
    No amount of regex fixes that: `index.ts` needs Pi's runtime, so nothing
    there is driven by a behavioural test.

    So the refusal string is now built by a pure function here — the repo's own
    pure-logic/runtime split, borrowed from auto-pi's `workflow-gate-logic.ts`
    and already used for `phase-gate.ts`. `index.ts` calls it and formats
    nothing, and this module is inside the mutation sweep."""

    def test_the_hint_is_part_of_what_the_model_reads(self):
        reason = refusal(HARNESS + "/02_Task_Queue/Task_001/status.txt")
        self.assertIn(WORK + "/02_Task_Queue/Task_001/status.txt", reason)

    def test_the_base_refusal_is_still_there(self):
        reason = refusal(HARNESS + "/wiki/x.md")
        self.assertIn("Directory containment", reason)
        self.assertIn(WORK, reason)

    def test_an_unrelated_target_gets_the_refusal_unchanged(self):
        """The DoD item that says the ordinary refusal must not drift. Compared
        against the same call with no harness root known, which is the shape a
        machine without PI_HARNESS_ROOT produces."""
        target = "D:/SomeoneElsesProject/deeply/nested/tree/longer/than/harness/main.ts"
        self.assertEqual(refusal(target), refusal(target, harness=""))

    def test_the_tool_name_reaches_the_text(self):
        self.assertIn("edit", refusal(HARNESS + "/x/y.md", tool="edit"))


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheBridgeUsesIt(unittest.TestCase):
    def test_index_delegates_instead_of_formatting_its_own(self):
        with open(os.path.join(ROOT, "pi-extensions", "yes-hooks-bridge", "index.ts"),
                  encoding="utf-8") as f:
            src = f.read()
        self.assertIn("containmentRefusal(", src)
        self.assertNotIn("harnessRootHint(target, cwd, harnessRoot())", src,
                         "the refusal is built in one place now, and it is not here")


if __name__ == "__main__":
    unittest.main()
