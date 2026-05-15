# 📝 實施計畫 (Implementation Tasks) - Universal Harness v4.0

## 第一波：基礎設施重構 (Scaffolding)
- [ ] **Task 1.1**: 建立新目錄結構：`core/`, `bridges/`。
- [ ] **Task 1.2**: 遷移現有 `pi-rules/` 至 `core/rules/`。
- [ ] **Task 1.3**: 遷移現有 `pi-skills/` 至 `core/skills/` (暫時保留 Pi 專屬名稱，待轉譯層完成)。
- [ ] **Task 1.4**: 建立 `scripts/detector.py` 並實作 `claude`/`pi` 偵測邏輯。

## 第二波：統一描述層與生成器 (Unified Manifest)
- [ ] **Task 2.1**: 定義 `core/manifest.json` 結構。
- [ ] **Task 2.2**: 實作 `scripts/generator.py`：
    - 支援為 Gemini 產生 `gemini-extension.json`。
    - 支援為 Claude 產生 `.claude/` 技能目錄結構。
- [ ] **Task 2.3**: 實作「中性工具名」替換邏輯（Regex-based）。

## 第三波：驗證與閉環 (Verification)
- [ ] **Task 3.1**: 撰寫 TDD 測試：驗證 `detector.py` 在模擬環境下的回傳值。
- [ ] **Task 3.2**: 實施 BDD 驗收：在模擬的 Claude Code 工作區執行 `setup.py`，檢查是否正確生成 `.claude/`。
- [ ] **Task 3.3**: 最終整合驗收：確保全平台指令行為一致。

---
**本計畫遵循「每次一個小動作」原則，確保每一步都經過驗證。**
