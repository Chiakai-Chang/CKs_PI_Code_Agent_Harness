"""The budget behind 「📝 偵測到新學習點 (1)。這個一直出現,只有提示沒有意義。」

The owner reported the symptom directly. Measured on session 019ffbdd (122
turns, 6.5 hours): the notice had no dedupe while the advisory beside it was
already "once", so it fired on every turn_end — 122 times — and each firing
spawned a python process and walked the whole of ~/.pi/agent/sessions, 20
workspace directories on that machine.

Why this is a separate module at all: `ecc-hooks-bridge` cannot be imported
under bare node (Pi-only dependencies) and `tests/test_bridge_handlers_run.py`
lists it as such, so nothing in this suite can drive its handlers. An undeclared
variable inside a bridge handler once survived 774 tests, three checks and a
byte-identical install for exactly that reason. Logic that can be wrong is moved
somewhere a test can call it.
"""

import json
import os
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import sys as _sys
_sys.path.insert(0, os.path.join(ROOT, "tests"))
from _scratch import scratch  # noqa: E402

MOD = os.path.join(ROOT, "pi-extensions", "ecc-hooks-bridge", "reflect-budget.ts")
IDX = os.path.join(ROOT, "pi-extensions", "ecc-hooks-bridge", "index.ts")


def node_ok():
    try:
        out = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=30)
        return out.returncode == 0 and int(out.stdout.strip().lstrip("v").split(".")[0]) >= 22
    except Exception:
        return False


NODE_OK = node_ok()


@unittest.skipUnless(NODE_OK, "node >= 22 required for native TypeScript type stripping")
class TestTheBudget(unittest.TestCase):
    DRIVER = r"""
import { readFileSync } from "node:fs";
import { ReflectBudget } from %(mod)s;
const cases = JSON.parse(readFileSync(process.argv[2], "utf-8"));
const out = [];
for (const c of cases) {
  const b = new ReflectBudget(...(c.ctor ?? []));
  const scans = (c.sizes ?? []).map((s) => b.claimScan(s));
  const notices = [];
  for (let i = 0; i < (c.notices ?? 0); i++) notices.push(b.claimNotice());
  out.push({ scans, notices, stats: b.stats() });
}
process.stdout.write(JSON.stringify(out));
"""

    def _run(self, cases):
        driver = scratch(".tmp_reflect_driver.mjs")
        payload = scratch(".tmp_reflect_input.json")
        with open(driver, "w", encoding="utf-8") as f:
            f.write(self.DRIVER % {"mod": json.dumps("file:///" + MOD.replace("\\", "/"))})
        with open(payload, "w", encoding="utf-8") as f:
            json.dump(cases, f)
        try:
            p = subprocess.run(["node", driver, payload], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", cwd=ROOT, timeout=120)
            if p.returncode != 0:
                raise AssertionError("node driver failed:\n%s\n%s" % (p.stdout, p.stderr))
            return json.loads(p.stdout)
        finally:
            for x in (driver, payload):
                if os.path.exists(x):
                    os.remove(x)

    def test_the_measured_session_scans_three_times_not_one_hundred_and_twenty_two(self):
        """122 turn_ends on a transcript that keeps growing. The old code ran a
        python process on every one of them."""
        sizes = [1000 * (i + 1) for i in range(122)]
        (r,) = self._run([{"sizes": sizes}])
        self.assertEqual(sum(r["scans"]), 3)

    def test_the_notice_fires_once_however_often_it_is_claimed(self):
        (r,) = self._run([{"notices": 50}])
        self.assertEqual(r["notices"].count(True), 1)
        self.assertEqual(r["notices"][0], True, "the first claim must be the one that speaks")

    def test_a_transcript_that_is_not_growing_is_not_rescanned(self):
        """The reason this is a growth gate and not a turn counter: a session
        that has stopped producing has nothing new to find, and scanning it again
        costs a process to learn that."""
        (r,) = self._run([{"sizes": [50_000, 50_000, 50_001, 55_000]}])
        self.assertEqual(r["scans"], [True, False, False, False])

    def test_growth_past_the_threshold_earns_the_next_scan(self):
        """And the reason it is not simply "run once": a scan on turn two reads a
        transcript with nothing in it yet. The original ran every turn precisely
        so it would eventually see a long one."""
        (r,) = self._run([{"sizes": [20_000, 40_000, 60_000]}])
        self.assertEqual(r["scans"], [True, True, True])

    def test_the_run_cap_holds_even_on_a_very_long_session(self):
        (r,) = self._run([{"sizes": [100_000 * (i + 1) for i in range(20)]}])
        self.assertEqual(sum(r["scans"]), 3)
        self.assertEqual(r["stats"]["runs"], 3)

    def test_a_resumed_session_that_is_already_large_still_gets_its_first_scan(self):
        """Nothing here should assume the transcript started at zero this
        process."""
        (r,) = self._run([{"sizes": [4_000_000]}])
        self.assertEqual(r["scans"], [True])

    def test_a_nonsense_size_is_refused_rather_than_counted(self):
        """`statSync().size` is the caller's input and this runs inside a
        try/catch that swallows everything. A NaN silently burning the budget
        would look exactly like a session with no learnings."""
        (r,) = self._run([{"sizes": [-1, "x", None, 30_000]}])
        self.assertEqual(r["scans"], [False, False, False, True])
        self.assertEqual(r["stats"]["runs"], 1)

    def test_zero_is_a_size_and_only_negatives_are_nonsense(self):
        """From the mutation sweep: `size < 0` weakened to `size < 1` is
        invisible at the default threshold, because an empty transcript fails the
        growth gate one line later anyway. It is not invisible at a zero
        threshold, and the contract is the point — a real file of zero bytes is a
        size, a negative one is a bad reading."""
        (r,) = self._run([{"ctor": [3, 0], "sizes": [0]}])
        self.assertEqual(r["scans"], [True])
        (r2,) = self._run([{"ctor": [3, 0], "sizes": [-1]}])
        self.assertEqual(r2["scans"], [False])

    def test_the_bounds_are_settable_so_they_can_be_calibrated(self):
        """These are calibration numbers, not protocol — the repo's own rule is
        that such values must be movable without editing the mechanism."""
        (r,) = self._run([{"ctor": [1, 5], "sizes": [10, 20, 30]}])
        self.assertEqual(r["scans"], [True, False, False],
                         "maxRuns=1 must stop after the first scan")
        (r2,) = self._run([{"ctor": [5, 1_000_000], "sizes": [10, 20, 30]}])
        self.assertEqual(r2["scans"], [False, False, False],
                         "a growth threshold above the transcript blocks every scan")


class TestItIsActuallyWiredIn(unittest.TestCase):
    """The extraction only helps if the handler uses it. index.ts cannot be
    imported here, so this reads the source — which is a weaker check than the
    ones above and is why the LOGIC lives in the module they can drive."""

    def setUp(self):
        with open(IDX, encoding="utf-8") as f:
            self.src = f.read()

    def test_the_handler_uses_the_budget(self):
        self.assertIn("new ReflectBudget()", self.src)
        self.assertIn("reflect.claimScan(", self.src)
        self.assertIn("reflect.claimNotice()", self.src)

    def test_the_session_file_comes_from_pi_not_from_an_mtime_scan(self):
        """The attribution defect: it picked the globally newest .jsonl under
        ~/.pi/agent/sessions, which with two Pi instances is another project's
        transcript. `getSessionFile()` answers the question directly."""
        self.assertIn("getSessionFile", self.src)
        self.assertNotIn("readdirSync", self.src.split("import ")[-1])

    def test_the_recursive_sessions_walk_is_gone(self):
        self.assertNotIn("const traverse =", self.src)
        self.assertNotIn("latestTime", self.src)


if __name__ == "__main__":
    unittest.main()
