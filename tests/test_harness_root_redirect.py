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


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheSecondRefusalShowsInsteadOfDescribing(unittest.TestCase):
    """Four of five runs resolved "this project" as the harness install.

    The redirect hint fired twice with the corrected absolute path and was
    ignored both times, while the same refusal repeated verbatim three times in
    one run. A guard repeating itself has taught nothing — the CLAIM gate learned
    that on 2026-08-10, and the run after its third rung started printing the
    real queue was the first to return to its own cwd unaided.

    The model is not confused. Pi's system prompt names the harness root 28 times
    as skill `<location>` and the cwd once, and on a developer machine that path
    holds a real 02_Task_Queue. It picked the better-evidenced workspace. So the
    second refusal supplies the missing half of the evidence."""

    TREE = {
        "C:/work/p": ["00_Constitution", "01_Roadmap", "02_Task_Queue", "src", ".hidden"],
        "C:/work/p/02_Task_Queue": ["Task_001_ConfigSurvey", "Task_002_Other", "notes"],
    }

    def refusal(self, seen):
        return run_js("""
        const tree = %s;
        const entries = (d) => tree[d] ?? [];
        const isDir = (p) => Boolean(tree[p]);
        process.stdout.write(JSON.stringify(m.containmentRefusal(
          "write", "D:/harness/wiki/a.md", "C:/work/p", "D:/harness", %d,
          () => m.workspaceListing("C:/work/p", entries, isDir))));
        """ % (json.dumps(self.TREE), seen))

    def test_the_first_refusal_does_not_dump_a_listing(self):
        """The short form gets its chance. A wall of paths on the first refusal
        buries the one sentence that explains what happened."""
        out = self.refusal(0)
        self.assertNotIn("Task_001_ConfigSurvey", out)
        self.assertIn("harness 的安裝位置", out)

    def test_the_second_refusal_names_the_tasks_in_the_workspace(self):
        out = self.refusal(1)
        self.assertIn("Task_001_ConfigSurvey", out)
        self.assertIn("02_Task_Queue", out)

    def test_it_counts_so_the_repetition_is_visible(self):
        self.assertIn("第 2 次", self.refusal(1))
        self.assertIn("第 3 次", self.refusal(2))

    def test_hidden_entries_are_left_out(self):
        self.assertNotIn(".hidden", self.refusal(1))

    def test_only_task_folders_are_listed_from_the_queue(self):
        """`notes` sits in the queue directory and is not a task."""
        out = self.refusal(1)
        self.assertIn("Task_002_Other", out)
        self.assertNotIn("notes", out)

    def test_an_unreadable_workspace_degrades_to_the_short_form(self):
        """Failing open matters more here than the listing: a guard that throws
        while refusing turns a refusal into a crash."""
        out = run_js("""
        process.stdout.write(JSON.stringify(m.containmentRefusal(
          "write", "D:/harness/x", "C:/work/p", "D:/harness", 3,
          () => { throw new Error("boom"); })));
        """)
        self.assertIn("Directory containment", out)
        self.assertNotIn("第 4 次", out)

    def test_the_listing_starts_at_the_first_entry(self):
        """`slice(1, …)` drops the first name silently, and the first name is
        often the one that matters — 00_Constitution sorts first."""
        self.assertIn("00_Constitution", self.refusal(1))

    def test_the_top_level_listing_is_capped_at_twelve(self):
        out = run_js("""
        const many = Array.from({length: 30}, (_, i) => "dir" + i);
        const text = m.workspaceListing("C:/w", () => many, () => true);
        process.stdout.write(JSON.stringify(
          (text.match(/^  - /gm) || []).length));
        """)
        self.assertEqual(out, 12)

    def test_the_task_listing_is_capped_at_six(self):
        out = run_js("""
        const tasks = Array.from({length: 20}, (_, i) => "Task_0" + i + "_x");
        const entries = (d) => d.endsWith("02_Task_Queue") ? tasks : ["02_Task_Queue"];
        const text = m.workspaceListing("C:/w", entries, () => true);
        process.stdout.write(JSON.stringify(
          (text.split("這裡面有:")[1] || "").split("、").length));
        """)
        self.assertEqual(out, 6)

    def test_the_default_is_the_short_form(self):
        """`seen` defaults to 0, so a caller that forgets it gets the first-refusal
        behaviour rather than dumping a listing on every refusal."""
        # A listing IS supplied and `seen` is omitted. The first version passed
        # neither, so the escalation was suppressed by the missing listing rather
        # than by the default, and changing the default to 1 changed nothing the
        # test could see.
        out = run_js("""
        process.stdout.write(JSON.stringify(m.containmentRefusal(
          "write", "D:/harness/x", "C:/work/p", "D:/harness",
          undefined, () => "LISTING")));
        """)
        self.assertNotIn("直接給你看", out)
        self.assertNotIn("LISTING", out)

    def test_the_listing_alone_is_null_for_an_empty_workspace(self):
        out = run_js("""
        process.stdout.write(JSON.stringify(
          m.workspaceListing("C:/empty", () => [], () => false)));
        """)
        self.assertIsNone(out)


class TestTheEscalationIsWired(unittest.TestCase):
    """A pure function nobody advances is a mechanism that never escalates.

    Replacing `containmentRefusals++` with `0` left every test above green,
    because they all call the pure function directly. The counter lives in the
    bridge and only a source check reaches it."""

    def setUp(self):
        self.src = (open(os.path.join(ROOT, "pi-extensions", "yes-hooks-bridge",
                                      "index.ts"), encoding="utf-8").read())

    def test_the_guard_passes_an_advancing_counter(self):
        call = self.src.split("containmentRefusal(", 1)[1].split("))", 1)[0]
        self.assertIn("containmentRefusals++", call,
                      "the refusal count is passed but never advances")

    def test_it_passes_a_listing_reader(self):
        call = self.src.split("containmentRefusal(", 1)[1].split("))", 1)[0]
        self.assertIn("workspaceListing", call)

    def test_the_counter_resets_each_session(self):
        """Carried over, the listing would appear on the first refusal of the
        next session, before the short form has had its chance."""
        start = self.src.split('pi.on("session_start"', 1)[1].split("});", 1)[0]
        self.assertIn("containmentRefusals = 0", start)

