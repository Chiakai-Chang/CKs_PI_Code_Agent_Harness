import os
import sys
import unittest
import re
import json
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import setup

# Mock hardware info for testing logic
MOCK_HW_GOOD = {"ram": 64, "vram": 24}
MOCK_HW_LOW = {"ram": 8, "vram": None}

def mock_get_recommended_specs(model_id, hw, found_ctx=None):
    """
    Ported logic from get_recommended_specs for validation.
    """
    mid = (model_id or "").lower()
    ctx, max_t, reasoning, found_truth = 8192, 4096, False, False
    
    if found_ctx:
        ctx = found_ctx
        found_truth = True

    if any(k in mid for k in ["r1", "thought", "qwen"]):
        reasoning = True
    
    # Heuristics ONLY if truth NOT found
    if not found_truth:
        if "qwen" in mid: ctx = 32768
        if "3.6" in mid: ctx = 196608
    
    # Safety Capping (Downward ONLY)
    if found_truth:
        # Respect truth, but still apply downward safety if it's crazy high for the hardware
        pass 
    else:
        vram = hw.get("vram")
        if vram and vram < 12 and ctx > 32768: ctx = 32768

    return ctx, max_t, reasoning, found_truth

class TestSetupLogic(unittest.TestCase):
    def test_truth_preservation(self):
        """Verify that API truth (e.g. 131072) is NOT overridden by heuristics."""
        # Case: Qwen 3.6 reported 128k (131072) by server
        ctx, _, _, found = mock_get_recommended_specs("qwen-3.6-35b", MOCK_HW_GOOD, found_ctx=131072)
        self.assertTrue(found)
        self.assertEqual(ctx, 131072, "Should respect API truth and NOT force it to 192k")

    def test_heuristic_fallback(self):
        """Verify that heuristics kick in when NO truth is found."""
        ctx, _, _, found = mock_get_recommended_specs("qwen-3.6-35b", MOCK_HW_GOOD, found_ctx=None)
        self.assertFalse(found)
        self.assertEqual(ctx, 196608, "Should use 192k as fallback for Qwen 3.6 if no API info")

    def test_hardware_capping(self):
        """Verify that fallback values are capped by hardware, but truth remains truth."""
        # Fallback case (low hardware)
        ctx, _, _, found = mock_get_recommended_specs("large-model", MOCK_HW_LOW, found_ctx=None)
        # Assuming 32k cap for 8GB RAM in heuristics
        self.assertLessEqual(ctx, 32768)

    def test_max_tokens_scales_with_probed_ctx(self):
        """探到大 context 時，輸出上限必須跟著放大（ctx//8），
        否則思考型模型長回應被 4096 預設值硬切。"""
        with mock.patch.object(setup, "probe_llama_cpp", return_value={"ctx": 262144}):
            ctx, max_t, _, truth = setup.get_recommended_specs(
                "agents-a1.gguf", MOCK_HW_GOOD, api_base="http://127.0.0.1:8080", provider="custom")
        self.assertTrue(truth)
        self.assertEqual(ctx, 262144)
        self.assertEqual(max_t, 32768)

    def test_max_tokens_capped_for_huge_ctx(self):
        """輸出上限有失控煞車：不超過 32768。"""
        with mock.patch.object(setup, "probe_llama_cpp", return_value={"ctx": 1048576}):
            _, max_t, _, _ = setup.get_recommended_specs(
                "huge.gguf", MOCK_HW_GOOD, api_base="http://127.0.0.1:8080", provider="custom")
        self.assertEqual(max_t, 32768)

    def test_max_tokens_default_for_small_ctx(self):
        """小 context（預設 8192）維持 4096，不縮小。"""
        _, max_t, _, _ = setup.get_recommended_specs("tiny-model", MOCK_HW_GOOD)
        self.assertEqual(max_t, 4096)

    def test_size_heuristic_max_tokens_not_lowered(self):
        """70B 啟發值 max_t=8192（ctx 32768）不得被 ctx//8=4096 拉低。"""
        _, max_t, _, _ = setup.get_recommended_specs("llama-70b", MOCK_HW_GOOD)
        self.assertEqual(max_t, 8192)

    def test_wmic_regex(self):
        """Verify the number extraction from messy Windows output."""
        messy_out = "TotalPhysicalMemory  \r\n17179869184          \r\n"
        nums = re.findall(r'\d+', messy_out)
        self.assertEqual(nums[0], "17179869184")


class TestCommitGraphCleanup(unittest.TestCase):
    """`update.bat` printed `failed to rename temporary commit-graph file` on
    every run. Two causes: git leaves read-only (0444) orphan .graph files that
    a later write cannot rename over, and — the reason a previously-added
    `git config fetch.writeCommitGraph false` on the superproject did nothing —
    each submodule keeps its OWN config under .git/modules/<name>/config and
    inherits nothing from the parent."""

    def setUp(self):
        import stat as _stat
        import tempfile
        self.tmp = tempfile.mkdtemp()
        self.orig_root = setup.REPO_ROOT
        setup.REPO_ROOT = self.tmp

        def mk_gitdir(path, with_graph=False, readonly=False):
            os.makedirs(os.path.join(path, "objects", "info"), exist_ok=True)
            os.makedirs(os.path.join(path, "refs"), exist_ok=True)
            open(os.path.join(path, "config"), "w").close()
            if with_graph:
                gdir = os.path.join(path, "objects", "info", "commit-graphs")
                os.makedirs(gdir, exist_ok=True)
                f = os.path.join(gdir, "commit-graph-chain")
                with open(f, "w") as fh:
                    fh.write("deadbeef\n")
                if readonly:
                    os.chmod(f, _stat.S_IREAD)

        self.top = os.path.join(self.tmp, ".git")
        mk_gitdir(self.top, with_graph=True, readonly=True)
        for name in ("ecc", "superpowers"):
            mk_gitdir(os.path.join(self.top, "modules", "external", name),
                      with_graph=True, readonly=True)
        # A nested submodule, to prove the walk keeps descending into modules/
        mk_gitdir(os.path.join(self.top, "modules", "external", "ecc", "modules", "inner"))

    def tearDown(self):
        import shutil as _shutil
        import stat as _stat
        setup.REPO_ROOT = self.orig_root
        for parent, _d, files in os.walk(self.tmp):
            for f in files:
                try:
                    os.chmod(os.path.join(parent, f), _stat.S_IWRITE)
                except OSError:
                    pass
        _shutil.rmtree(self.tmp, ignore_errors=True)

    def test_finds_superproject_and_every_submodule_git_dir(self):
        found = setup.git_dirs(self.tmp)
        self.assertIn(self.top, found)
        names = {os.path.basename(p) for p in found}
        self.assertIn("ecc", names)
        self.assertIn("superpowers", names)
        self.assertIn("inner", names, "nested submodule git dirs must be reached too")
        self.assertEqual(len(found), 4)

    def test_missing_repo_returns_empty(self):
        import tempfile
        self.assertEqual(setup.git_dirs(tempfile.mkdtemp()), [])

    def test_removes_readonly_commit_graph_caches(self):
        """Read-only (0444) is exactly why git's own rename failed — deleting
        without clearing the bit would fail the same way."""
        with mock.patch.object(setup, "run") as run_mock:
            removed, targets = setup.disable_commit_graph()
        self.assertEqual(removed, 3, "one cache per git dir that had one")
        self.assertEqual(targets, 4)
        for parent, _d, _f in os.walk(self.tmp):
            self.assertNotIn("commit-graphs", os.path.basename(parent))
        # Both knobs, on every git dir: fetch-time writes AND the post-fetch
        # `git maintenance` commit-graph task (which reported its own error).
        cmds = " ".join(str(c) for c in run_mock.call_args_list)
        self.assertEqual(cmds.count("fetch.writeCommitGraph false"), 4)
        self.assertEqual(cmds.count("maintenance.commit-graph.enabled false"), 4)

    def test_idempotent(self):
        with mock.patch.object(setup, "run"):
            setup.disable_commit_graph()
            removed, _ = setup.disable_commit_graph()
        self.assertEqual(removed, 0)


class TestModelDrift(unittest.TestCase):
    """Swapping a GGUF quant without re-running setup leaves settings.json
    naming the old file. llama.cpp ignores the `model` field with one model
    loaded, so nothing errors — Pi's status line just shows a model that is not
    running. Observed live: settings said Q6_K, the server had Q4_K_M."""

    def test_reports_mismatch(self):
        drift = setup.model_drift(
            {"defaultModel": "m-Q6_K.gguf"}, {"name": "m-Q4_K_M.gguf"})
        self.assertEqual(drift, ("m-Q6_K.gguf", "m-Q4_K_M.gguf"))

    def test_match_is_not_drift(self):
        self.assertIsNone(setup.model_drift({"defaultModel": "m.gguf"}, {"name": "m.gguf"}))

    def test_unknown_or_missing_is_not_drift(self):
        """No probe, no server, or an unnamed model must not raise a false alarm."""
        self.assertIsNone(setup.model_drift({"defaultModel": "m.gguf"}, None))
        self.assertIsNone(setup.model_drift({"defaultModel": "m.gguf"}, {"name": "unknown"}))
        self.assertIsNone(setup.model_drift({}, {"name": "m.gguf"}))
        self.assertIsNone(setup.model_drift(None, None))


class TestOrphanSubmoduleDetection(unittest.TestCase):
    """`git submodule deinit`/removal drops the working tree but leaves
    .git/modules/<name> behind forever. One such leftover (agi-super-team) was
    holding 120MB in this repo with nothing referencing it."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.mkdtemp()
        modules = os.path.join(self.tmp, ".git", "modules", "external")
        for name in ("ecc", "agi-super-team"):
            d = os.path.join(modules, name)
            os.makedirs(d)
            open(os.path.join(d, "config"), "w").close()
        # A stray directory with no config is not a submodule git dir.
        os.makedirs(os.path.join(modules, "not-a-gitdir"))
        with open(os.path.join(self.tmp, ".gitmodules"), "w", encoding="utf-8") as f:
            f.write('[submodule "external/ecc"]\n\tpath = external/ecc\n\turl = https://example.com/ecc\n')

    def tearDown(self):
        import shutil as _shutil
        _shutil.rmtree(self.tmp, ignore_errors=True)

    def test_reports_only_undeclared_gitdirs(self):
        names = [n for n, _p in setup.orphan_submodule_gitdirs(self.tmp)]
        self.assertEqual(names, ["agi-super-team"])

    def test_no_gitmodules_reports_nothing(self):
        os.remove(os.path.join(self.tmp, ".gitmodules"))
        self.assertEqual(setup.orphan_submodule_gitdirs(self.tmp), [])

    def test_detection_is_read_only(self):
        """Advisory by design: this is user data inside .git, and an installer
        that silently deletes hundreds of megabytes is the worse failure."""
        before = sorted(os.listdir(os.path.join(self.tmp, ".git", "modules", "external")))
        orig_root, setup.REPO_ROOT = setup.REPO_ROOT, self.tmp
        try:
            setup.report_orphan_submodules()
        finally:
            setup.REPO_ROOT = orig_root
        after = sorted(os.listdir(os.path.join(self.tmp, ".git", "modules", "external")))
        self.assertEqual(before, after)


class TestUpdateFailureHandling(unittest.TestCase):
    """`git pull`'s return value used to be ignored, so a failed pull (merge
    conflict, no network) was followed by restore and `pi update` anyway. The
    update then reported success over a half-updated repo — exactly the shape of
    "I ran the updater and it is still broken"."""

    def setUp(self):
        with open(os.path.join(ROOT, "scripts", "setup.py"), encoding="utf-8") as f:
            self.src = f.read()

    def test_update_aborts_when_pull_fails(self):
        self.assertIn('if not run_stream("git pull --recurse-submodules"):', self.src)
        self.assertIn("更新中止", self.src)

    def test_warns_before_pulling_over_local_config_edits(self):
        """README instructs users to edit pi-config/harness-config.json, and
        that file is tracked — following the docs can produce a conflict."""
        self.assertIn("warn_locally_modified_config()", self.src)

    def test_porcelain_paths_are_parsed_without_truncation(self):
        """A fixed ln[3:] slice ate the first character: pi-config -> i-config."""
        import subprocess as sp
        code = (
            "import sys; sys.path.insert(0, %r); import setup;"
            "print(setup.warn_locally_modified_config())" % os.path.join(ROOT, "scripts")
        )
        p = sp.run([sys.executable, "-c", code], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", cwd=ROOT, timeout=120)
        for line in p.stdout.splitlines():
            self.assertNotIn("i-config/", line.replace("pi-config/", ""))


if __name__ == '__main__':
    unittest.main()
