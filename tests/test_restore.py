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


class TestEccSkillPaths(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.mkdtemp()
        for name in ["good-skill", "loop-design-check", "another-skill"]:
            d = os.path.join(self.tmp, name)
            os.makedirs(d)
            with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as f:
                f.write("---\nname: x\ndescription: y\n---\n")
        os.makedirs(os.path.join(self.tmp, "not-a-skill"))  # no SKILL.md

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_broken_skills_excluded(self):
        """Known-broken upstream skills must not be registered (docs/KNOWN_ISSUES.md)."""
        paths = restore.ecc_skill_paths(self.tmp)
        names = [os.path.basename(p) for p in paths]
        self.assertIn("good-skill", names)
        self.assertIn("another-skill", names)
        self.assertNotIn("loop-design-check", names)
        self.assertNotIn("not-a-skill", names)

    def test_missing_root_returns_root_fallback(self):
        """Uninitialized submodule: fall back to registering the root dir."""
        missing = os.path.join(self.tmp, "does-not-exist")
        self.assertEqual(restore.ecc_skill_paths(missing), [missing.replace("\\", "/")])


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


class TestHealMaxTokens(unittest.TestCase):
    """舊版 setup.py 對大 context 模型仍寫入預設 maxTokens=4096，導致長回應
    被硬切（maximum output token limit）。restore 時必須自動治癒該組合。"""

    def _models(self, ctx, max_t):
        return {"providers": {"local-server": {"models": [
            {"id": "big.gguf", "contextWindow": ctx, "maxTokens": max_t}
        ]}}}

    def test_legacy_default_on_large_ctx_raised(self):
        models = self._models(262144, 4096)
        healed = restore.heal_max_tokens(models)
        self.assertEqual(
            models["providers"]["local-server"]["models"][0]["maxTokens"], 32768)
        self.assertEqual(healed, ["big.gguf"])

    def test_huge_ctx_capped_at_32768(self):
        """思考型模型需要大輸出額度，但仍須有失控煞車：上限 32768。"""
        models = self._models(1048576, 4096)
        restore.heal_max_tokens(models)
        self.assertEqual(
            models["providers"]["local-server"]["models"][0]["maxTokens"], 32768)

    def test_user_chosen_value_untouched(self):
        """非 4096 的值視為使用者自選，不得覆蓋。"""
        models = self._models(262144, 5000)
        healed = restore.heal_max_tokens(models)
        self.assertEqual(
            models["providers"]["local-server"]["models"][0]["maxTokens"], 5000)
        self.assertEqual(healed, [])

    def test_small_ctx_untouched(self):
        """ctx 32768 以下，4096 已是合理比例（ctx//8），不動。"""
        models = self._models(32768, 4096)
        healed = restore.heal_max_tokens(models)
        self.assertEqual(
            models["providers"]["local-server"]["models"][0]["maxTokens"], 4096)
        self.assertEqual(healed, [])

    def test_mid_ctx_scaled_not_capped(self):
        models = self._models(65536, 4096)
        restore.heal_max_tokens(models)
        self.assertEqual(
            models["providers"]["local-server"]["models"][0]["maxTokens"], 8192)

    def test_empty_or_malformed_no_crash(self):
        self.assertEqual(restore.heal_max_tokens({}), [])
        self.assertEqual(restore.heal_max_tokens({"providers": {"x": {}}}), [])
        self.assertEqual(
            restore.heal_max_tokens({"providers": {"x": {"models": [{}]}}}), [])


class TestCheckModelsAgainstServer(unittest.TestCase):
    """設定檔是快照，server 重啟參數會變（例如 -np 2 把 262144 平分成
    2×131072）。restore 時必須拿 live 真值核對，錯配要警告。"""

    def _models(self, ctx, max_t, base="http://127.0.0.1:8080"):
        return {"providers": {"local-server": {"baseUrl": base, "models": [
            {"id": "big.gguf", "contextWindow": ctx, "maxTokens": max_t}
        ]}}}

    def test_declared_ctx_exceeds_live_ctx_warns(self):
        """實例：models.json 262144，server 每 slot 只有 131072。"""
        probe = lambda url: {"name": "big.gguf", "ctx": 131072}
        warnings = restore.check_models_against_server(
            self._models(262144, 32768), probe=probe)
        self.assertEqual(len(warnings), 1)
        self.assertIn("262144", warnings[0])
        self.assertIn("131072", warnings[0])

    def test_matching_ctx_no_warning(self):
        probe = lambda url: {"name": "big.gguf", "ctx": 131072}
        self.assertEqual(restore.check_models_against_server(
            self._models(131072, 16384), probe=probe), [])

    def test_declared_ctx_below_live_is_fine(self):
        """聲明值較小只是保守，不是錯誤。"""
        probe = lambda url: {"name": "big.gguf", "ctx": 262144}
        self.assertEqual(restore.check_models_against_server(
            self._models(131072, 16384), probe=probe), [])

    def test_server_down_silent(self):
        """離線／沒跑 server 是正常情境，不得警告或當掉。"""
        probe = lambda url: None
        self.assertEqual(restore.check_models_against_server(
            self._models(262144, 32768), probe=probe), [])

    def test_remote_base_url_not_probed(self):
        """只探本機 server；雲端 provider 一律跳過。"""
        calls = []
        def probe(url):
            calls.append(url)
            return {"name": "x", "ctx": 1}
        restore.check_models_against_server(
            self._models(262144, 32768, base="https://api.example.com"), probe=probe)
        self.assertEqual(calls, [])

    def test_no_base_url_skipped(self):
        models = {"providers": {"p": {"models": [{"id": "m", "contextWindow": 999}]}}}
        self.assertEqual(
            restore.check_models_against_server(models, probe=lambda u: {"ctx": 1}), [])


if __name__ == "__main__":
    unittest.main()
