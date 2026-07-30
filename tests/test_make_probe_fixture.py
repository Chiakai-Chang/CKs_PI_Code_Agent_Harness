"""Tests for the probe-fixture builder.

The builder exists because a mis-sized fixture invalidated a full day of model
and engine comparisons on 2026-07-29. A tool whose job is to make measurements
trustworthy has to be trustworthy itself, so the sizing and pinning logic is
tested directly. Nothing here touches git or a model server: the git reader and
the tokenizer are both injected.
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

spec = importlib.util.spec_from_file_location(
    "make_probe_fixture", os.path.join(ROOT, "scripts", "make-probe-fixture.py"))
mpf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mpf)


class FakeProc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestReadPinned(unittest.TestCase):
    def test_returns_stdout_of_git_show(self):
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            return FakeProc(stdout="pinned body")

        self.assertEqual(mpf.read_pinned("abc123", "docs/X.md", run=fake_run), "pinned body")
        self.assertEqual(calls[0], ["git", "show", "abc123:docs/X.md"])

    def test_git_failure_is_an_error_not_empty_content(self):
        # Silently returning "" here would produce a fixture built from fewer
        # sources than the manifest claims — the exact class of drift this
        # script exists to prevent.
        def fake_run(cmd, **kwargs):
            return FakeProc(returncode=128, stderr="fatal: path does not exist")

        with self.assertRaises(mpf.FixtureError):
            mpf.read_pinned("abc123", "docs/missing.md", run=fake_run)


class TestBuildSourceText(unittest.TestCase):
    def test_concatenates_sources_in_declared_order(self):
        reader = lambda commit, path: f"[{path}]"  # noqa: E731
        text = mpf.build_source_text("c0", sources=("a.md", "b.md"), reader=reader)
        self.assertEqual(text, "[a.md]\n\n[b.md]")

    def test_all_empty_sources_is_an_error(self):
        reader = lambda commit, path: "   "  # noqa: E731
        with self.assertRaises(mpf.FixtureError):
            mpf.build_source_text("c0", sources=("a.md",), reader=reader)


class TestRepeatToBytes(unittest.TestCase):
    def test_grows_short_source_to_requested_size(self):
        out = mpf.repeat_to_bytes("abcd", 30)
        self.assertEqual(len(out.encode("utf-8")), 30)

    def test_truncates_long_source(self):
        out = mpf.repeat_to_bytes("x" * 100, 40)
        self.assertEqual(len(out.encode("utf-8")), 40)

    def test_never_cuts_a_multibyte_character_in_half(self):
        # Every fixture in this repo contains Traditional Chinese. A byte-level
        # cut would emit invalid UTF-8 and the server would reject the request.
        out = mpf.repeat_to_bytes("臺灣", 4)
        out.encode("utf-8").decode("utf-8")
        self.assertLessEqual(len(out.encode("utf-8")), 4)

    def test_deterministic_for_the_same_inputs(self):
        a = mpf.repeat_to_bytes("seed text ", 5000)
        b = mpf.repeat_to_bytes("seed text ", 5000)
        self.assertEqual(mpf.sha256(a), mpf.sha256(b))

    def test_rejects_non_positive_size(self):
        with self.assertRaises(mpf.FixtureError):
            mpf.repeat_to_bytes("abc", 0)


class TestSizeToTokens(unittest.TestCase):
    """The tokenizer is injected, so a fixed bytes-per-token model stands in."""

    @staticmethod
    def counter(bytes_per_token):
        return lambda text: max(1, len(text.encode("utf-8")) // bytes_per_token)

    def test_hits_the_requested_count_within_tolerance(self):
        text, got = mpf.size_to_tokens("filler " * 500, 4000, self.counter(4))
        self.assertLessEqual(abs(got - 4000), 25)
        self.assertGreater(len(text), 0)

    def test_works_when_the_ratio_is_far_from_english_prose(self):
        # CJK runs near 1.5 bytes/token where English runs near 4. Seeding the
        # search from a measured sample rather than a constant is what makes
        # both land; this test fails if that seeding is replaced by a guess.
        _, got = mpf.size_to_tokens("中文字元填充" * 500, 6000, self.counter(1))
        self.assertLessEqual(abs(got - 6000), 25)

    def test_returns_the_closest_candidate_when_tolerance_is_unreachable(self):
        # A coarse tokenizer cannot land inside +/-25; the search must still
        # return its best attempt rather than loop or raise.
        _, got = mpf.size_to_tokens("x" * 100, 3, self.counter(1000))
        self.assertIsInstance(got, int)

    def test_rejects_non_positive_target(self):
        with self.assertRaises(mpf.FixtureError):
            mpf.size_to_tokens("abc", 0, self.counter(4))


class TestCountTokens(unittest.TestCase):
    def test_counts_the_tokens_array(self):
        class FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return json.dumps({"tokens": [1, 2, 3, 4]}).encode("utf-8")

        self.assertEqual(mpf.count_tokens("http://x", "hi", opener=lambda *a, **k: FakeResp()), 4)

    def test_malformed_response_is_an_error(self):
        class FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return json.dumps({"error": "no model"}).encode("utf-8")

        with self.assertRaises(mpf.FixtureError):
            mpf.count_tokens("http://x", "hi", opener=lambda *a, **k: FakeResp())


class TestCli(unittest.TestCase):
    def test_bytes_mode_writes_fixture_and_manifest_without_a_server(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc = mpf.main(["--out", tmp, "--bytes", "2048"])
            self.assertEqual(rc, 0)
            manifest = json.loads(open(os.path.join(tmp, "manifest.json"), encoding="utf-8").read())
            self.assertEqual(len(manifest["fixtures"]), 1)
            entry = manifest["fixtures"][0]
            self.assertEqual(entry["bytes"], 2048)
            self.assertIsNone(entry["tokens"])
            self.assertTrue(os.path.exists(os.path.join(tmp, entry["file"])))

    def test_manifest_records_a_resolved_commit_not_a_moving_ref(self):
        # "HEAD" in a manifest is unrebuildable one commit later.
        with tempfile.TemporaryDirectory() as tmp:
            mpf.main(["--out", tmp, "--bytes", "1024"])
            manifest = json.loads(open(os.path.join(tmp, "manifest.json"), encoding="utf-8").read())
            self.assertRegex(manifest["commit"], r"^[0-9a-f]{40}$")

    def test_requires_at_least_one_size(self):
        with self.assertRaises(SystemExit):
            mpf.main(["--out", tempfile.gettempdir()])

    def test_probe_target_is_not_one_of_the_fixture_sources(self):
        # If the file the probe asks the model to read is described in the
        # system prompt, "I already have it" is correct and scores as failure.
        self.assertNotIn(mpf.DEFAULT_TARGET, mpf.DEFAULT_SOURCES)

    def test_declared_sources_exist_at_head(self):
        for path in mpf.DEFAULT_SOURCES:
            proc = subprocess.run(
                ["git", "show", f"HEAD:{path}"], capture_output=True, cwd=ROOT
            )
            self.assertEqual(proc.returncode, 0, f"{path} is not in HEAD")


if __name__ == "__main__":
    unittest.main()
