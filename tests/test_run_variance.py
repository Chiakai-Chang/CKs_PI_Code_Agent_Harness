"""How many runs before a difference means anything.

`research/metaharness` ADR-138 (Accepted (measured)) turns "single runs are
unreliable" into a rule: to separate two conditions Δ apart the standard error
must be under Δ/2, so n ≳ (sd/(Δ/2))². They measured sd ≈ 0.45 against Δ ≈ 0.5
and concluded four to five averaged runs; their evolution had been running at
n=1, which is why greedy search chased noise into a local optimum.

Every verdict in this project so far rests on n=2, and the run-to-run variance
of this model has never been measured. Attempt 2 of the CLAIM budget gave 1/2
and attempt 3 gave 2/2 - and if the true rate were 50%, two in a row happen a
quarter of the time.

The trap is pooling. Those attempts ran against different code: the status
validity check landed between them, and the phase notice landed before that.
Averaging across them would be the exact mistake this file exists to prevent,
so variance is only ever computed within one configuration, and the
configuration each run used is recorded with it.
"""

import importlib.util
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "measure_advancer", os.path.join(ROOT, "scripts", "measure-advancer.py"))
ma = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ma)


def runs(config, values, metric="pre_claim_ok"):
    return [{"config": config, metric: v} for v in values]


class TestItRefusesToPoolDifferentConfigurations(unittest.TestCase):
    """The mistake this whole file guards against."""

    def test_two_configurations_are_two_groups(self):
        rows = runs({"caseClaimRefusalTurns": 4}, [0, 24]) + \
               runs({"caseClaimRefusalTurns": 8}, [0, 0])
        groups = ma.variance_report(rows, ["pre_claim_ok"])
        self.assertEqual(len(groups), 2, "different settings are different experiments")

    def test_the_same_configuration_written_differently_is_one_group(self):
        """Key order in a JSON object is not a configuration difference."""
        rows = [{"config": {"a": 1, "b": 2}, "pre_claim_ok": 0},
                {"config": {"b": 2, "a": 1}, "pre_claim_ok": 1}]
        self.assertEqual(len(ma.variance_report(rows, ["pre_claim_ok"])), 1)


class TestAnUnrecordedConfigurationIsNotAnEmptyOne(unittest.TestCase):
    """Caught by running the tool on real files, where it silently pooled four
    runs from two different experiments.

    Result files written before the config field existed have no config, and
    treating that as `{}` let an 8-turn run average with a 4-turn one — the
    exact mistake this analysis was built to prevent, committed by the analysis
    itself. Same shape as "unreadable" and "empty" being one answer, which cost
    a run earlier the same day."""

    def test_runs_with_no_recorded_config_form_their_own_group(self):
        rows = [{"pre_claim_ok": 0}, {"config": {}, "pre_claim_ok": 1}]
        groups = ma.variance_report(rows, ["pre_claim_ok"])
        self.assertEqual(len(groups), 2,
                         "an unrecorded configuration is unknown, not empty")

    def test_the_unknown_group_says_so(self):
        groups = ma.variance_report([{"pre_claim_ok": 0}], ["pre_claim_ok"])
        self.assertIn("unknown", groups[0]["config"].lower())


class TestWhatItReports(unittest.TestCase):
    def test_mean_and_sd_of_a_known_set(self):
        g = ma.variance_report(runs({"x": 1}, [2, 2, 2, 1, 2]), ["pre_claim_ok"])[0]
        stat = g["metrics"]["pre_claim_ok"]
        self.assertEqual(stat["n"], 5)
        self.assertAlmostEqual(stat["mean"], 1.8, places=6)
        self.assertAlmostEqual(stat["sd"], 0.4, places=6)

    def test_required_n_uses_the_adr_138_rule(self):
        """n ≳ (sd/(Δ/2))². sd 0.45 against Δ 0.5 is the worked example, and it
        comes out at the four-to-five they concluded."""
        self.assertEqual(ma.required_n(sd=0.45, delta=0.5), 4)
        self.assertEqual(ma.required_n(sd=0.5, delta=0.5), 4)
        self.assertEqual(ma.required_n(sd=1.0, delta=0.5), 16)

    def test_a_delta_of_zero_is_not_answerable(self):
        """"How many runs to detect no difference" has no number, and returning
        one would invite quoting it."""
        self.assertIsNone(ma.required_n(sd=0.4, delta=0))

    def test_no_variance_still_needs_more_than_one_run(self):
        """Identical results are not proof of zero variance at n=2 — they are
        the most likely outcome of a coin landing the same way twice."""
        self.assertGreaterEqual(ma.required_n(sd=0.0, delta=0.5), 1)


class TestSmallSamplesAreLabelled(unittest.TestCase):
    """An sd from two runs is a number, not an estimate. Printing it without
    saying so is how n=2 became a verdict in the first place."""

    def test_under_three_runs_is_marked_unreliable(self):
        g = ma.variance_report(runs({"x": 1}, [0, 0]), ["pre_claim_ok"])[0]
        self.assertTrue(g["metrics"]["pre_claim_ok"]["unreliable"])

    def test_five_runs_is_not(self):
        g = ma.variance_report(runs({"x": 1}, [0, 1, 0, 2, 1]), ["pre_claim_ok"])[0]
        self.assertFalse(g["metrics"]["pre_claim_ok"]["unreliable"])

    def test_a_single_run_reports_no_sd_at_all(self):
        g = ma.variance_report(runs({"x": 1}, [3]), ["pre_claim_ok"])[0]
        self.assertIsNone(g["metrics"]["pre_claim_ok"]["sd"])


class TestMissingMetricsDoNotBecomeZero(unittest.TestCase):
    def test_a_run_without_the_metric_is_skipped_not_counted_as_zero(self):
        rows = [{"config": {"x": 1}, "pre_claim_ok": 4},
                {"config": {"x": 1}}]
        stat = ma.variance_report(rows, ["pre_claim_ok"])[0]["metrics"]["pre_claim_ok"]
        self.assertEqual(stat["n"], 1, "an absent measurement is absent, not zero")


if __name__ == "__main__":
    unittest.main()
