# 🧠 決策紀錄 (Rationale) - Best Practices Bridge

## 1. 為什麼要引進 agents-best-practices？
在設計和除錯 Agent Harness 時，開發者常常面臨模型決策與執行層邊界不清、Context 過載、或沙盒控制不嚴的架構隱憂。
引進 `DenisSergeevitch/agents-best-practices` 是為了解決：
*   **架構中立規範 (Provider-Neutral Standards)**：提供適用於 OpenAI/Anthropic/Gemini 的通用控制面（Control Plane）設計範式。
*   **環境回饋自適應 (Agent-Legible Feedback Loops)**：確保環境的反饋、測試報告與系統錯誤是「Agent 易讀（Legible）」的，避免機械故障般的無窮嘗試。
*   **最小可行產品生成 (MVP Builder Mode)**：為不同的業務場景（研究、金融、 legal 等）快速 scaffold 出高安全性的 MVP Agent 設計藍圖。

---

## 2. 為什麼選擇「原生映射 (Native Mapping)」+「輕量橋接」？
根據 `DISTILLATION_GUIDE.md`：
*   **SO 策略 (發揮優勢/利用機會)**：該專案的所有優良架構說明與實踐指南皆以標準 Markdown (SKILL.md) 形式組織，完全零依賴。因此最適策略為 **Submodule 原生映射（Path 1）**。
*   **橋接整合**：在 `pi-extensions/best-practices-bridge` 中建立極簡的映射 JSON 設定，將 `harness-best-practices` 技能註冊進 Pi Engine，確保開發者能隨時查詢最佳架構檢核表。
