# 🛡️ OmniHeal 專案健檢審計快照 (Audit Summary)

**掃描時間**: 2026-07-27
**目標專案**: CK's Pi Code Agent Harness (`CKs_PI_Code_Agent_Harness`)
**測試驗證狀態**: 176 / 176 測試通過 (100% PASS) | 0 橋接錯誤 | 0 配置合規警告

---

## 📊 健檢指標與風險概覽

| 檢查範疇 | 掃描結果 | 關鍵亮點 / 風險評級 |
| :--- | :--- | :--- |
| **無窮迴圈 bug (Infinite Repetition)** | 🔴 已排除根因 (High Severity) | `taste-bridge` 過去無預警抹除全域 systemPrompt，觸發 `yes-hooks-bridge` `loopGuard` 循環。已完成修復與單元測試。 |
| **研究隔離性 (Research Containment)** | 🟢 優良 (Low Severity) | `research/OmniHeal` 成功 Clone 並已受 `.gitignore` 純淨性保護。 |
| **橋接擴充架構 (Bridge Extensions)** | 🟢 9 大橋接全數健康 | `ecc-hooks`, `planning-with-files`, `case`, `taste`, `mece-autopilot`, `stealth-web`, `yes-hooks`, `skill-namespace-guard`, `compact-continuation` 通過 `verify-bridges.py`。 |
| **全域組態衛生 (Config Hygiene)** | 🟢 零 Zombie Config | 無死節點或空殼 TypeScript Extensions 註冊於 `settings.json` 模板。 |
| **跨平台相容性 (Cross-Platform Safety)** | 🟢 動態注入安全 | 無 Windows 絕對路徑硬編碼於 `pi-config/`。全部經由 `scripts/setup.py` 與 `scripts/restore.py` 動態探測。 |

---

## 🔍 關鍵發現詳情 (Verified Findings)

### Finding 1: `taste-bridge/index.ts` SystemPrompt Overwrite [✓ VERIFIED]
- **權責/位置**: `pi-extensions/taste-bridge/index.ts:26-28`
- **問題類型**: 致命系統提示詞覆蓋 (Catastrophic Prompt Erasure)
- **現象**: 舊寫法直接回傳 `{ systemPrompt: "[Taste-Engine]..." }`，抹除了包含 `AGENTS.md`、`CLAUDE.md` 與原生工具格式在內的所有系統提示詞，導致模型無法正常調用工具而輸出純文字標籤。
- **處置結果**: 已更新為 `(event.systemPrompt ?? "") + "\n\n" + ...` 並增加 `tests/test_taste_bridge.py` 契約測試。

### Finding 2: `yes-hooks-bridge/index.ts` `loopGuard` Self-Feedback Cycle [✓ VERIFIED]
- **權責/位置**: `pi-extensions/yes-hooks-bridge/index.ts:161-180`
- **問題類型**: 灰牌邏輯自迴圈引擎 (Auto-Turn Loop Engine)
- **現象**: 
  1. `loop-guard` 警告訊息本身包含未轉義的 `<invoke>`, `<read-file>`, `<bash>` 標籤，導致模型引述警告時重新觸發 `FAKE_TOOL_CALL_PATTERN`。
  2. 第 3 灰牌（strike 3）重設為 0 時仍發送 `{ deliverAs: "nextTurn" }`，導致 1->2->3->1 無窮自動驅動對話。
- **處置結果**: 標籤轉義為 `[invoke]`, `[read-file]`, `[bash]`，且第 3 灰牌改為 `{ deliverAs: "followUp" }`，強制停下等待人類用戶指示。

---

## 📈 測試與驗證數據

- `python -m unittest discover -s tests`: **Ran 176 tests in 0.035s, OK (skipped=7)**
- `python scripts/verify-bridges.py`: **9 bridges checked, 0 failure(s) found**
- `python scripts/validate-config.py`: **0 failure(s) found**
