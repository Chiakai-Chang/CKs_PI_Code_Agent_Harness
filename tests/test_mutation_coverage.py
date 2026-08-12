"""Every pure module is either swept or excluded with a reason.

T1b started from a number nobody was maintaining: 33 of 48 pure modules had
never been touched by the mutation sweep, and nothing in the repo said so.
Adding two of them immediately produced 22 survivors, ten of them in a file
edited that same day — so the coverage of the sweep, not the wording of the
assertions, is the lever.

A one-off sweep does not keep that. This does: a module that appears in
`pi-extensions/` and in neither list fails here, so the next module to arrive
cannot be silently unswept the way these were. It is the same guard the
`uninstall.py` / `restore.py` drift earned — one list managed five bridges while
the other managed eleven, and seven kept loading forever.

`index.ts` is out of scope on purpose: it opens with `require.resolve`, which
exists only under Pi's shim, so no test can import it and no mutant could be
killed. That is the reason the logic worth sweeping keeps being moved OUT of
index.ts into its own module — `calibration.ts`, `notice.ts`, `plan.ts` are all
that shape.
"""

import io
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCANNER = os.path.join(ROOT, "scripts", "check-guard-mutations.py")
EXTENSIONS = os.path.join(ROOT, "pi-extensions")


def scanner_source():
    return io.open(SCANNER, encoding="utf-8").read()


def declared(block_name):
    """Module paths listed in one of the scanner's two dicts."""
    src = scanner_source()
    start = src.index(block_name)
    end = src.index("\n}", start)
    return set(re.findall(r'"(pi-extensions/[^"]+\.ts)"', src[start:end]))


def pure_modules():
    """Every .ts in pi-extensions that a test could drive.

    Excludes `index.ts` (not importable, see the module docstring) and `*.test.ts`
    (they are the tests).
    """
    out = set()
    for dirpath, _dirs, files in os.walk(EXTENSIONS):
        if "node_modules" in dirpath.replace("\\", "/"):
            continue
        for name in files:
            if not name.endswith(".ts") or name.endswith(".test.ts") or name == "index.ts":
                continue
            rel = os.path.relpath(os.path.join(dirpath, name), ROOT)
            out.add(rel.replace("\\", "/"))
    return out


class TestEveryModuleIsAccountedFor(unittest.TestCase):
    def setUp(self):
        self.modules = pure_modules()
        self.swept = declared("GUARD_MODULES = {")
        self.excluded = declared("UNSWEPT_WITH_REASON = {")

    def test_the_inventory_is_not_empty(self):
        """A walk that found nothing would make every assertion below pass by
        accident — the shape of failure this repo keeps meeting."""
        self.assertGreater(len(self.modules), 20, sorted(self.modules))

    def test_no_module_is_unaccounted_for(self):
        missing = sorted(self.modules - self.swept - self.excluded)
        self.assertEqual(missing, [], "neither swept nor excluded with a reason: %s"
                                      % missing)

    def test_nothing_is_in_both_lists(self):
        both = sorted(self.swept & self.excluded)
        self.assertEqual(both, [], "listed as swept AND excluded: %s" % both)

    def test_the_lists_name_files_that_exist(self):
        gone = sorted(p for p in (self.swept | self.excluded)
                      if not os.path.isfile(os.path.join(ROOT, p)))
        self.assertEqual(gone, [], "listed but absent from disk: %s" % gone)

    def test_every_exclusion_carries_a_known_reason(self):
        """A blank or invented reason is how an exclusion list becomes a place
        to put things nobody wants to test."""
        src = scanner_source()
        start = src.index("UNSWEPT_WITH_REASON = {")
        end = src.index("\n}", start)
        reasons = set(re.findall(r'"pi-extensions/[^"]+\.ts":\s*"([^"]*)"',
                                 src[start:end]))
        known = set(re.findall(r'UNSWEPT_REASONS = \{([^}]*)\}', src)[0].split(","))
        known = {k.strip().strip('"').strip("'") for k in known if k.strip()}
        self.assertTrue(reasons, "no exclusions parsed — the format changed")
        self.assertEqual(reasons - known, set(),
                         "exclusion reasons with no explanation block: %s"
                         % sorted(reasons - known))




class TestALeakedMutationStopsTheNextRun(unittest.TestCase):
    """A sweep killed mid-mutation leaves the source file wrong on disk.

    Measured 2026-08-12: a 2-minute command timeout killed a sweep and left
    `readability.ts` holding `index + 2`. `mutated_file`'s `finally` restores on
    every exception, but SIGTERM is not an exception — the process is gone before
    it runs. The unit tests caught the mutant minutes later, which is the system
    working; a mutation left in the tree can still be committed, and
    `setup.py --mode restore` would install it into ~/.pi and run it live.

    Signals that can be caught are now turned into exceptions. SIGKILL cannot be,
    so a marker file records which file is mutated and the next run refuses.
    """

    def setUp(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("guard_mutations", SCANNER)
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)

    def test_a_marker_makes_the_next_run_refuse(self):
        marker = self.mod.MUTATION_MARKER
        self.assertFalse(os.path.exists(marker), "a marker is present right now — "
                                                 "a sweep may have died; check it")
        with io.open(marker, "w", encoding="utf-8") as f:
            f.write("pi-extensions/somewhere/left-mutated.ts")
        try:
            with self.assertRaises(SystemExit) as caught:
                self.mod.refuse_if_a_mutation_leaked()
            self.assertIn("left-mutated.ts", str(caught.exception))
        finally:
            os.remove(marker)

    def test_no_marker_means_no_complaint(self):
        self.assertIsNone(self.mod.refuse_if_a_mutation_leaked())

    def test_the_catchable_signals_are_turned_into_exceptions(self):
        """SIGINT already raises; SIGTERM is the one a command timeout sends."""
        import signal
        self.mod.install_signal_restore()
        handler = signal.getsignal(signal.SIGTERM)
        self.assertTrue(callable(handler),
                        "SIGTERM still has its default disposition: a timeout "
                        "would kill the sweep without restoring the file")


if __name__ == "__main__":
    unittest.main()
