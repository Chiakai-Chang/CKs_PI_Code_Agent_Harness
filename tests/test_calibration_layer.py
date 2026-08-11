"""Calibration lives in the config file, not in enforcement code (T-A2).

Three numbers in this harness were measured against one model on one day:
the CLAIM gate's refusal budget (8 turns), the goal-restatement threshold (12
results) and the pending-task listing cap (5). Written as constants they swap
models in silence — no error, just a gate that lets go too early or a reminder
that never arrives. Harness-Bench (arXiv 2605.27922) states the general form:
capability is a property of the model–harness configuration, so the numbers
calibrated to a configuration belong where the configuration is declared.

Every test here drives the reader against a FIXTURE root. That matters more than
it looks: the shipped value and the code fallback are the same number for all
three, so a test that only exercised the shipped case could not tell a wired
reader from a dead one. That is exactly how a guard sat dead through 1287 green
tests on the morning of the same day.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATE = os.path.join(ROOT, "pi-extensions", "case-bridge", "phase-gate.ts")
CONFIG = os.path.join(ROOT, "pi-config", "harness-config.json")


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


def run_js(module, script):
    driver = os.path.join(ROOT, "tests", ".tmp_calibration_driver.mjs")
    url = "file:///" + module.replace("\\", "/")
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


def fixture_root(values):
    """A harness root carrying just a config file."""
    tmp = tempfile.mkdtemp()
    os.makedirs(os.path.join(tmp, "pi-config"))
    with open(os.path.join(tmp, "pi-config", "harness-config.json"),
              "w", encoding="utf-8") as f:
        json.dump(values, f)
    return tmp


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheListingCapComesFromConfig(unittest.TestCase):
    def cap(self, root):
        queue = os.path.join(root, "02_Task_Queue")
        return run_js(GATE, "process.stdout.write(JSON.stringify("
                            "m.listingCap(%s, %s)));"
                            % (json.dumps(queue), json.dumps(root)))

    def test_the_configured_value_is_used(self):
        root = fixture_root({"queueListingCap": 2})
        self.addCleanup(shutil.rmtree, root, True)
        self.assertEqual(self.cap(root), 2)

    def test_a_missing_config_keeps_the_shipped_cap(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, True)
        self.assertEqual(self.cap(root), 5)

    def test_a_nonsense_value_keeps_the_shipped_cap(self):
        """Zero is the one that matters: a cap of zero prints an empty listing,
        and the whole point of that rung is to show the model the real paths
        instead of reciting a template at it."""
        for bad in [0, -3, "5", True, 2.5, None]:
            with self.subTest(bad=bad):
                root = fixture_root({"queueListingCap": bad})
                self.addCleanup(shutil.rmtree, root, True)
                self.assertEqual(self.cap(root), 5)


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheShippedConfigDeclaresTheCalibration(unittest.TestCase):
    """The point of the task is that these numbers are declared somewhere a
    person swapping models will look. A wired reader with nothing to read is
    only half the change."""

    def setUp(self):
        with open(CONFIG, encoding="utf-8") as f:
            self.cfg = json.load(f)

    def test_every_calibrated_number_is_present_and_documented(self):
        for key, shipped in [("caseClaimRefusalTurns", 8),
                             ("goalRestateThreshold", 12),
                             ("goalRestateMax", 2),
                             ("queueListingCap", 5)]:
            with self.subTest(key=key):
                self.assertIn(key, self.cfg)
                self.assertEqual(self.cfg[key], shipped,
                                 "config disagrees with the code fallback for %s" % key)
                self.assertIn("_" + key, self.cfg,
                              "%s has no documentation key saying what it calibrates" % key)

    def test_the_group_says_what_calibration_means(self):
        self.assertIn("_calibration", self.cfg)
        self.assertIn("Harness-Bench", self.cfg["_calibration"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheClaimBudgetReachesTheSessionSnapshot(unittest.TestCase):
    """The gate reads its budget from the session snapshot, and the snapshot is
    taken with the harness root in hand. Before T-A2 the global file carried no
    such key, so the snapshot always came back empty and the constant in
    `phase-gate.ts` was the only value that could ever be used."""

    SCOPE = os.path.join(ROOT, "pi-extensions", "case-bridge", "harness-scope.ts")

    def snapshot(self, cwd, root):
        return run_js(self.SCOPE,
                      "const s = new m.ScopeSnapshot();\n"
                      "s.take(%s, %s);\n"
                      "process.stdout.write(JSON.stringify("
                      "s.get('caseClaimRefusalTurns') ?? null));"
                      % (json.dumps(cwd), json.dumps(root)))

    def test_the_global_value_reaches_the_snapshot(self):
        root = fixture_root({"caseClaimRefusalTurns": 10})
        self.addCleanup(shutil.rmtree, root, True)
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, True)
        self.assertEqual(self.snapshot(project, root), 10)

    def test_the_shipped_config_is_what_a_real_session_reads(self):
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, True)
        self.assertEqual(self.snapshot(project, ROOT), 8)

    def test_a_project_may_tighten_within_bounds(self):
        """The trust boundary is unchanged by T-A2: the project file may still
        only move this number inside 8-12."""
        root = fixture_root({"caseClaimRefusalTurns": 10})
        self.addCleanup(shutil.rmtree, root, True)
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, True)
        for value, expected in [(9, 9), (1, 10), (99, 10)]:
            with self.subTest(value=value):
                with open(os.path.join(project, ".pi-harness.json"),
                          "w", encoding="utf-8") as f:
                    json.dump({"caseClaimRefusalTurns": value}, f)
                self.assertEqual(self.snapshot(project, root), expected)


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheListingItselfHonoursTheCap(unittest.TestCase):
    """Through `check()`, not through the helper.

    The first version of this file tested `listingCap()` alone. Putting
    `slice(0, 5)` back into the call site left all of it green — the helper was
    right and nobody called it. That is the same defect, in the same repo, on
    the same day, as the DoD guard that never ran."""

    def refusal(self, root, pending, cap):
        queue = os.path.join(root, "02_Task_Queue")
        os.makedirs(queue, exist_ok=True)
        for i in range(pending):
            d = os.path.join(queue, "Task_%03d_Fixture" % (i + 1))
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "status.txt"), "w", encoding="utf-8") as f:
                f.write("PENDING\n")
        return run_js(GATE,
                      "m.useHarnessRoot(%s);\n" % json.dumps(root) +
                      "const g = new m.PhaseGate();\n"
                      # Third rung: the one that prints the listing. Two turns
                      # of refusals get us there.
                      "let out = null;\n"
                      "for (let i = 0; i < 3; i++) {\n"
                      "  out = g.check(%s, 'web_search', { query: 'x' });\n" % json.dumps(queue) +
                      "  g.turnEnded();\n"
                      "}\n"
                      "process.stdout.write(JSON.stringify(out === null ? null : out.reason));")

    def lines(self, text):
        return [l for l in (text or "").splitlines() if "->" in l and "status.txt" in l]

    def test_the_configured_cap_is_what_the_listing_prints(self):
        root = fixture_root({"queueListingCap": 2})
        self.addCleanup(shutil.rmtree, root, True)
        text = self.refusal(root, 7, 2)
        self.assertIsNotNone(text, "the third rung did not refuse")
        self.assertEqual(len(self.lines(text)), 2, text)
        self.assertIn("5", text.split("另外還有", 1)[1][:4],
                      "the remainder count does not follow the cap: %s" % text)

    def test_the_shipped_cap_prints_five(self):
        root = fixture_root({})
        self.addCleanup(shutil.rmtree, root, True)
        text = self.refusal(root, 7, 5)
        self.assertEqual(len(self.lines(text)), 5, text)
