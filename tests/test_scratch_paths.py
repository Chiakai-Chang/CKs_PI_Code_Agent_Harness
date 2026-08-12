"""No test may write a fixed-name scratch file into `tests/`.

Thirty-six test modules each wrote their node driver to a hard-coded name —
`.tmp_bashc_driver.mjs` and friends. Sequentially that is invisible. Two suite
processes at once (which happens the moment a slow suite gets backgrounded and
another starts) and their `finally` blocks delete each other's files: measured
2026-08-12, two concurrent runs of one module gave `failures=25, errors=5` and
`failures=42, errors=9`, none of them real and none naming the cause. The run
after that was green.

A red that turns green on a retry is the most expensive signal this repo can
produce, because the lesson it teaches is "reds are noise". This check keeps the
fix from eroding one convenient hard-coded path at a time.
"""

import io
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = os.path.join(ROOT, "tests")

# `os.path.join(ROOT, "tests", ".tmp_whatever")` — the shape that was replaced.
FIXED = re.compile(r'os\.path\.join\(\s*ROOT\s*,\s*"tests"\s*,\s*"\.tmp_')
# The pathlib spelling of the same thing: `ROOT / "tests" / ".tmp_x.mjs"`. It
# was missed by the first sweep and two concurrent suites found it immediately —
# 5 errors in one, 4 in the other, all inside `finally: driver.unlink()`.
PATHLIB = re.compile(r'ROOT\s*/\s*"tests"\s*/\s*"\.tmp_')
# A repo-relative literal handed to a guard, e.g. "tests/.tmp_big_fixture.txt".
LITERAL = re.compile(r'"tests/\.tmp_')


class TestNoFixedScratchNames(unittest.TestCase):
    def _sources(self):
        for name in sorted(os.listdir(TESTS)):
            if name.startswith("test_") and name.endswith(".py"):
                path = os.path.join(TESTS, name)
                with io.open(path, encoding="utf-8") as f:
                    yield name, f.read()

    def test_no_module_builds_a_fixed_tmp_path(self):
        # This file names the pattern in order to search for it, so it matches
        # itself. Excluding it is not a loophole — `test_the_patterns_match`
        # below proves both regexes still catch the real shape.
        offenders = [n for n, src in self._sources()
                     if (FIXED.search(src) or PATHLIB.search(src))
                     and n != os.path.basename(__file__)]
        self.assertEqual(offenders, [], "use scratch() from tests/_scratch.py: %s" % offenders)

    def test_no_module_hardcodes_the_relative_form(self):
        offenders = [n for n, src in self._sources()
                     if LITERAL.search(src) and n != os.path.basename(__file__)]
        self.assertEqual(offenders, [], "use scratch_rel(): %s" % offenders)

    def test_the_patterns_match_the_shape_they_are_meant_to_catch(self):
        """A check nobody has seen fail is a check nobody should trust — and
        both regexes here are exclusion-based, so a typo would make them pass
        forever on an empty match set."""
        self.assertTrue(FIXED.search(
            'driver = os.path.join(ROOT, "tests", ".tmp_bashc_driver.mjs")'))
        self.assertTrue(LITERAL.search(
            '{"path": "tests/.tmp_big_fixture.txt"}'))
        self.assertTrue(PATHLIB.search(
            'driver = ROOT / "tests" / ".tmp_task_context.mjs"'))
        self.assertIsNone(FIXED.search(
            'driver = scratch(".tmp_bashc_driver.mjs")'))
        self.assertIsNone(PATHLIB.search(
            'driver = Path(scratch(".tmp_task_context.mjs"))'))

    def test_the_helper_makes_names_unique_per_process(self):
        import sys as _sys
        _sys.path.insert(0, TESTS)
        from _scratch import scratch, scratch_rel
        got = scratch(".tmp_probe.mjs")
        self.assertIn(str(os.getpid()), os.path.basename(got))
        # The suffix has to survive: node picks its parser from `.mjs`, so a pid
        # appended after the extension would silently change how it loads.
        self.assertTrue(got.endswith(".mjs"), got)
        self.assertEqual(os.path.dirname(got), TESTS)
        self.assertEqual(scratch_rel(".tmp_probe.mjs"),
                         "tests/" + os.path.basename(got))

    def test_two_processes_would_not_collide(self):
        """The property that actually matters, stated as a test rather than as a
        comment: the name is a function of the pid, so no two live processes can
        produce the same one."""
        import sys as _sys
        _sys.path.insert(0, TESTS)
        from _scratch import scratch
        mine = scratch(".tmp_probe.mjs")
        theirs = mine.replace(".%d." % os.getpid(), ".%d." % (os.getpid() + 1))
        self.assertNotEqual(mine, theirs)


if __name__ == "__main__":
    unittest.main()
