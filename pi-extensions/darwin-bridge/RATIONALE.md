# 🧠 決策紀錄 (Rationale) - Darwin Skill Bridge

## 1. 為什麼要引進 darwin-skill？
隨著專案技能與提示詞數量增加，手動維護和修改 `SKILL.md` 的成本極高，且容易因修改導致「性能漂移（Performance Drift）」。
引進 `darwin-skill` 是為了解決：
*   **定性化評分 (SkillLens Rubric)**：基於微軟 SkillLens 9 维定量指標，為 SKILL.md 提供非樂觀偏差的客觀結構性評分。
*   **棘輪保護機制 (Git Ratchet)**：基於版本控制，優化後的分數必須「嚴格高於」舊版才被接受，否則自動回滾。
*   **跨 Runtime 相容性檢測**：主動掃描並清除綁定特定平台（如 Claude Code 專用詞）的紅燈描述，確保技能的通用度。

---

## 2. 為什麼選擇「原生映射 (Native Mapping)」+「輕量橋接」？
根據 `DISTILLATION_GUIDE.md`：
*   **SO 策略 (發揮優勢/利用機會)**：`darwin-skill` 核心是純標準 Markdown（`SKILL.md`），不含任何必須編譯的二進制重型依賴。因此最適路徑是 **Submodule 直接原生映射（Path 1）**。
*   **橋接整合**：在 `pi-extensions/darwin-bridge` 中建立極簡的映射 JSON 設定，將 `/darwin:score` 與 `/darwin:optimize` 註冊進 Pi Engine，確保無縫調用且享有上游更新。

---

## 3. 未來維護計畫
*   定期執行 `git submodule update --remote` 獲取最新的優化診斷指標與 Ontario/SkillLens 論文更新的 Rubric 標準。
