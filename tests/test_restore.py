import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import restore


class TestMergeSettings(unittest.TestCase):
    def test_real_incoming_overrides_managed_keys(self):
        """切換模型後，harness 管理鍵必須以 pi-config/settings.json 的新值為準。"""
        existing = {
            "defaultModel": "llama3.2",
            "defaultProvider": "ollama",
            "apiBase": "http://127.0.0.1:11434",
            "theme": "dark",
        }
        incoming = {"defaultModel": "claude-sonnet-5", "defaultProvider": "anthropic"}
        merged = restore.merge_settings(existing, incoming, incoming_is_real=True)
        self.assertEqual(merged["defaultModel"], "claude-sonnet-5")
        self.assertEqual(merged["defaultProvider"], "anthropic")

    def test_stale_api_base_removed_when_switching_to_cloud(self):
        """incoming（真實設定檔）沒有 apiBase 時，必須清除殘留的 apiBase。"""
        existing = {"defaultModel": "llama3.2", "apiBase": "http://127.0.0.1:11434"}
        incoming = {"defaultModel": "gemini-2.5-pro", "defaultProvider": "google"}
        merged = restore.merge_settings(existing, incoming, incoming_is_real=True)
        self.assertNotIn("apiBase", merged)

    def test_user_custom_keys_preserved(self):
        existing = {"theme": "dark", "defaultModel": "old"}
        incoming = {"defaultModel": "new"}
        merged = restore.merge_settings(existing, incoming, incoming_is_real=True)
        self.assertEqual(merged["theme"], "dark")

    def test_example_fallback_does_not_override_user_choice(self):
        """settings.json 不存在（僅 .example 回退）時，不得覆蓋使用者既有選擇。"""
        existing = {"defaultModel": "claude-sonnet-5", "defaultProvider": "anthropic"}
        incoming = {"defaultModel": "llama3.2", "defaultProvider": "ollama",
                    "apiBase": "http://localhost:11434"}
        merged = restore.merge_settings(existing, incoming, incoming_is_real=False)
        self.assertEqual(merged["defaultModel"], "claude-sonnet-5")
        self.assertEqual(merged["defaultProvider"], "anthropic")
        self.assertNotIn("apiBase", merged)

    def test_list_values_merge_without_duplicates(self):
        existing = {"packages": ["npm:context-mode", "npm:my-own"]}
        incoming = {"packages": ["npm:context-mode", "npm:@tintinweb/pi-tasks"]}
        merged = restore.merge_settings(existing, incoming, incoming_is_real=True)
        self.assertEqual(
            merged["packages"],
            ["npm:context-mode", "npm:my-own", "npm:@tintinweb/pi-tasks"],
        )


class TestMergeModels(unittest.TestCase):
    def test_other_providers_preserved(self):
        """同步 models.json 不得抹掉使用者其他自訂 provider。"""
        existing = {"providers": {"my-vllm": {"baseUrl": "http://10.0.0.2:8000"}}}
        incoming = {"providers": {"ollama": {"baseUrl": "http://127.0.0.1:11434"}}}
        merged = restore.merge_models(existing, incoming)
        self.assertIn("my-vllm", merged["providers"])
        self.assertIn("ollama", merged["providers"])

    def test_same_provider_updated(self):
        existing = {"providers": {"ollama": {"models": [{"id": "llama3.2"}]}}}
        incoming = {"providers": {"ollama": {"models": [{"id": "qwen3"}]}}}
        merged = restore.merge_models(existing, incoming)
        self.assertEqual(merged["providers"]["ollama"]["models"][0]["id"], "qwen3")

    def test_empty_existing(self):
        merged = restore.merge_models({}, {"providers": {"ollama": {}}})
        self.assertIn("ollama", merged["providers"])


if __name__ == "__main__":
    unittest.main()
