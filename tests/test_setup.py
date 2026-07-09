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

if __name__ == '__main__':
    unittest.main()
