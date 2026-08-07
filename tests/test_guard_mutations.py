"""Break the guards on purpose, mechanically, and require something to turn red.

Four failures of the same class are on record, and all four were "the check
could not fail":

* `research-depth`'s break fixture used `sed -i`, which the extractor does not
  recognise — removing the guard changed nothing
* `phase-gate`'s "two open tasks" fixture had no PENDING task, so the broken
  version returned the same answer as the correct one
* a guard passed twelve unit tests and had never fired in a real session
* an e2e printed PASS while measuring nothing (`grep -c` exits 1, `[` errored
  into the else branch)

The 2026-08-06 retrospective named this class and recorded that it had
discipline and no mechanism. On 2026-08-08 the discipline failed again:
Task_003's five deliberate breaks produced three catches, and one survivor's
root cause was a string assertion standing in for a behavioural one.

`research/metaharness`'s ADR-010 declined mutation testing in v1.0 —
"the perf cost on a large test suite is significant" — and wrote the condition
for reversing that: "if we measure that it would have caught real bugs." The
four failures above are that measurement. The perf objection is answered by
scope: seven guard modules, each running only its own test modules, stopping at
the first red.

What this file tests is the runner, not the guards. The runner's own failure
mode is the one that matters — a mutation that never reached the file, counted
as killed, reports a clean sweep over code nobody tested.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "check-guard-mutations.py")

spec = importlib.util.spec_from_file_location("guard_mutations", SCRIPT)
gm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gm)


class TestTheOperatorsChangeTheCode(unittest.TestCase):
    def test_each_operator_produces_a_different_source(self):
        src = "if (a === b && c <= 3) { return true; }\n"
        seen = {m.mutated for m in gm.mutations(src)}
        self.assertNotIn(src, seen, "a mutation identical to the original is a no-op")
        self.assertGreaterEqual(len(seen), 5,
                                "at least five operators, per the Local DoD")

    def test_the_five_named_operators_are_all_present(self):
        src = "if (a === b && c <= 3 && d !== e || f) { return true; } // n = 1\n"
        kinds = {m.kind for m in gm.mutations(src)}
        for expected in ("&&->||", "===->!==", "<=-><", "!==->===", "true->false"):
            self.assertIn(expected, kinds)

    def test_a_negation_is_removed(self):
        """Added 2026-08-08 after the first sweep could not reach the line
        Task_003 broke. Its surviving break deleted a whole precondition —
        `if (!t.startsWith(h + "/")) return null;` — and the operator set had
        no site on that line at all, so the tool finishing said nothing about
        whether the condition was met. Guard clauses are written `if (!x)
        return`, and dropping the `!` inverts exactly that shape."""
        kinds = {m.kind for m in gm.mutations("if (!ok) return null;\n")}
        self.assertIn("!x->x", kinds)

    def test_the_bang_of_a_not_equals_is_left_alone(self):
        """`!==` is its own operator and `!=` would become `=`, which is an
        assignment, not a mutation — it would not parse as a comparison and the
        result would be noise rather than a survivor."""
        for src in ("if (a !== b) return 1;\n", "if (a != b) return 1;\n"):
            with self.subTest(src=src):
                self.assertNotIn("!x->x", {m.kind for m in gm.mutations(src)})

    def test_an_integer_threshold_is_shifted(self):
        found = [m for m in gm.mutations("const MAX = 4;\n") if "4" in m.kind]
        self.assertTrue(found, "thresholds are the parameter most often wrong")
        self.assertIn("5", found[0].mutated)


class TestItDoesNotMutateProseOrStrings(unittest.TestCase):
    """These files are more comment than code. A refusal message reading
    'blocked && refused' is not a branch, and reporting it as an untested
    mutation trains the reader to skim the survivors — which is the same as
    having no survivors list."""

    def test_a_line_comment_is_left_alone(self):
        self.assertEqual(gm.mutations("// a === b && c\n"), [])

    def test_a_block_comment_is_left_alone(self):
        self.assertEqual(gm.mutations("/* a === b\n   && c <= 3 */\n"), [])

    def test_a_string_literal_is_left_alone(self):
        self.assertEqual(gm.mutations('const s = "a === b && c";\n'), [])

    def test_a_template_literal_is_left_alone(self):
        self.assertEqual(gm.mutations("const s = `blocked && refused === no`;\n"), [])

    def test_a_regex_literal_is_left_alone(self):
        """The runner's own first false positive. `blocked-claim.ts:67` is
        `const TERMINATOR = /[。！？!?\\n]|\\.(?=\\s|$)/g;` and the `!` inside the
        character class was reported as an untested negation — a pattern is
        data, exactly as a string is, and a survivor list with noise in it is a
        survivor list nobody reads."""
        src = "const T = /[!?a-z]|x/g;\n"
        self.assertEqual(gm.mutations(src), [])

    def test_division_is_not_mistaken_for_a_pattern(self):
        """`a / b` after a value is arithmetic. Masking it would hide real
        operators on that line."""
        kinds = {m.kind for m in gm.mutations("const r = total / count >= 2 && ok;\n")}
        self.assertIn(">=->>", kinds)
        self.assertIn("&&->||", kinds)

    def test_code_beside_a_comment_is_still_mutated(self):
        kinds = {m.kind for m in gm.mutations("if (a && b) return 1; // x === y\n")}
        self.assertIn("&&->||", kinds)


class TestAMutationThatNeverLandedIsNotAKill(unittest.TestCase):
    """The runner's own version of the class it exists to catch. `brk.py` grew a
    'did the patch apply' precheck after three runs printed OK without having
    changed anything; a mutation runner without one reports a clean sweep over
    code it never touched."""

    def test_applying_a_mutation_whose_text_is_absent_raises(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "m.ts")
            with open(p, "w", encoding="utf-8") as f:
                f.write("const a = 1;\n")
            bogus = gm.Mutation(offset=0, kind="fake", original="const a = 1;\n",
                                mutated="const a = 2;\n")
            bogus = bogus._replace(original="THIS TEXT IS NOT IN THE FILE")
            with self.assertRaises(gm.MutationNotApplied):
                gm.apply_mutation(p, bogus)


class TestItAlwaysPutsTheFileBack(unittest.TestCase):
    """A check that can corrupt the source is worse than no check. The recipe's
    escalation trigger says so."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)
        self.p = os.path.join(self.d, "guard.ts")
        self.body = "export const f = (a, b) => a && b;\n"
        with open(self.p, "w", encoding="utf-8") as f:
            f.write(self.body)

    def test_the_bytes_come_back_after_a_normal_run(self):
        with gm.mutated_file(self.p, gm.mutations(self.body)[0]):
            with open(self.p, encoding="utf-8") as f:
                self.assertNotEqual(f.read(), self.body)
        with open(self.p, encoding="utf-8") as f:
            self.assertEqual(f.read(), self.body)

    def test_the_bytes_come_back_when_the_body_raises(self):
        with self.assertRaises(RuntimeError):
            with gm.mutated_file(self.p, gm.mutations(self.body)[0]):
                raise RuntimeError("the test runner died mid-mutation")
        with open(self.p, encoding="utf-8") as f:
            self.assertEqual(f.read(), self.body)


class TestTheModuleMapIsDeclaredNotDerived(unittest.TestCase):
    """Deriving the map by grepping test files for a module name was tried and
    was wrong on the first module: `test_installed_drift.py` mentions
    `harness-root.ts` in its docstring and tests nothing about it. A mutation
    scored against the wrong test module is a result with no meaning."""

    def test_every_mapped_module_and_test_exists(self):
        self.assertTrue(gm.GUARD_MODULES, "an empty map checks nothing")
        for module, tests in gm.GUARD_MODULES.items():
            self.assertTrue(os.path.isfile(os.path.join(ROOT, module)), module)
            self.assertTrue(tests, f"{module} has no test module")
            for t in tests:
                self.assertTrue(
                    os.path.isfile(os.path.join(ROOT, "tests", t + ".py")), t)

    def test_the_measured_effective_guards_are_all_covered(self):
        """The four guards with live evidence behind them, plus the two that
        drive the C.A.S.E. loop. If the mechanism does not cover these, it does
        not cover the code that changes model behaviour."""
        for module in ("pi-extensions/case-bridge/task-queue-guard.ts",
                       "pi-extensions/case-bridge/phase-gate.ts",
                       "pi-extensions/case-bridge/queue-advancer.ts",
                       "pi-extensions/yes-hooks-bridge/bash-containment.ts",
                       "pi-extensions/yes-hooks-bridge/blocked-claim.ts",
                       "pi-extensions/yes-hooks-bridge/research-depth.ts",
                       "pi-extensions/yes-hooks-bridge/harness-root.ts"):
            self.assertIn(module, gm.GUARD_MODULES)


class TestSurvivorsMustBeNamed(unittest.TestCase):
    def test_an_unlisted_survivor_fails_the_run(self):
        self.assertEqual(gm.verdict(survivors=[("m.ts", "3:9", "&&->||")], allowed={}), 1)

    def test_a_listed_survivor_with_a_reason_passes(self):
        allowed = {"m.ts:3:9:&&->||": "equivalent mutant: both branches return the same refusal"}
        self.assertEqual(gm.verdict(survivors=[("m.ts", "3:9", "&&->||")], allowed=allowed), 0)

    def test_two_operators_on_one_line_are_separate_entries(self):
        """harness-root.ts:40 carries two `||` in one condition and both
        survived the first real run. Keyed by line alone they collapse into one
        entry, and explaining the first would silence the second."""
        allowed = {"m.ts:40:9:||->&&": "the first one, argued"}
        self.assertEqual(gm.verdict(survivors=[("m.ts", "40:9", "||->&&"),
                                               ("m.ts", "40:17", "||->&&")],
                                    allowed=allowed), 1)

    def test_a_listed_survivor_with_an_empty_reason_still_fails(self):
        """An allowlist entry is a claim someone has to defend. A blank one is
        the percentage target this design rejected, spelled differently."""
        self.assertEqual(gm.verdict(survivors=[("m.ts", "3:9", "&&->||")],
                                    allowed={"m.ts:3:9:&&->||": "   "}), 1)

    def test_line_and_column_are_both_reported(self):
        # Built with chr(10) rather than an escape: this is the fifth time today
        # a backslash was eaten between the shell, the heredoc and the file.
        src = "abc" + chr(10) + "de&&f" + chr(10)
        self.assertEqual(gm.line_col(src, 6), (2, 3))   # first &
        self.assertEqual(gm.line_col(src, 7), (2, 4))   # second &

    def test_no_survivors_passes(self):
        self.assertEqual(gm.verdict(survivors=[], allowed={}), 0)

    def test_the_allowlist_on_disk_parses_and_every_reason_is_real(self):
        allowed = gm.load_allowlist()
        for key, reason in allowed.items():
            self.assertGreater(len(reason.strip()), 20,
                               f"{key} is allowed without an argument")


class TestItReportsWhenItSampled(unittest.TestCase):
    """Sampling is a cost trade-off, not a smaller exhaustive run. A reader who
    takes a sampled clean sweep for a proof has been misled by the output."""

    def test_the_sample_is_deterministic(self):
        sites = list(range(100))
        self.assertEqual(gm.sample(sites, 7), gm.sample(sites, 7))

    def test_it_takes_the_whole_set_when_under_the_cap(self):
        self.assertEqual(gm.sample([1, 2, 3], 10), [1, 2, 3])

    def test_the_sample_spans_the_file(self):
        """Taking the first N would test the imports and the top of the file
        and call it a module."""
        picked = gm.sample(list(range(100)), 5)
        self.assertLess(picked[0], 20)
        self.assertGreater(picked[-1], 79)


class TestItRunsEndToEndOnARealModule(unittest.TestCase):
    """The mechanism's own falsifiability check, and the reason this task
    exists: run it against a module with a KNOWN hole and require it to say so.
    A mutation runner that reports a clean sweep over `harness-root.ts` is the
    fifth instance of the class it was built to end."""

    @unittest.skipUnless(shutil.which("node"), "node required")
    def test_a_planted_untested_branch_survives(self):
        with tempfile.TemporaryDirectory() as d:
            mod = os.path.join(d, "planted.ts")
            with open(mod, "w", encoding="utf-8") as f:
                f.write("export function f(a, b) {\n"
                        "  if (a === 1 && b === 2) return 'both';\n"
                        "  return 'no';\n"
                        "}\n")
            test = os.path.join(d, "test_planted.py")
            with open(test, "w", encoding="utf-8") as f:
                f.write(textwrap.dedent("""
                    import unittest
                    class T(unittest.TestCase):
                        def test_nothing_about_the_branch(self):
                            self.assertTrue(True)
                """))
            survivors = gm.run_module(mod, [test], cap=99, cwd=d)
            self.assertTrue(survivors,
                            "a module whose tests assert nothing must report survivors")


if __name__ == "__main__":
    unittest.main()
