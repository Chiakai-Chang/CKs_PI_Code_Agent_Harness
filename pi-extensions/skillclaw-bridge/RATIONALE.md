# 🧠 決策紀錄 (Rationale) - SkillClaw Bridge

## 1. 為什麼要引進 SkillClaw？
當前開發者的 AI Agent 環境存在一個根本痛點：**技能的「孤島效應」**（不同機器、不同 Agent 或不同開發者各自累積的經驗無法複用，導致同一個 Bug 會被重複踩坑，或者相同的技能被重複開發）。
引進 `AMAP-ML/SkillClaw` 是為了解決：
*   **集體技能演進 (Collective Skill Evolution)**：整合來自多個 session、多個設備或多個使用者的軌跡（Trajectories），將其進行合併、去重與最佳化。
*   **結構化歷史帳本 (Version History Ledger)**：每次技能修改前，強制閱讀歷史變更紀錄，避免發生功能退化（Regression）。
*   **雙向驗證門檻 (Verification Gate)**：技能被批准發布前，必須提供本地的冒煙測試（Smoke test）或靜態模擬佐證。

---

## 2. 為什麼選擇「子模組導入」與「主要流程智慧蒸餾」？
根據 `DISTILLATION_GUIDE.md`：
*   **ST/WO 交叉策略**：`SkillClaw` 包含了極其厚重的 Python Proxy、Nacos 服務與 S3 快取。若直接在用戶主機運行，會帶來嚴重的依賴污染風險。
*   **解決方案**：
    1.  **原生映射 (Path 1 - Submodule)**：將 `SkillClaw` 作為子模組引入，主要提取並註冊其核心進化手冊 [EVOLVE_AGENTS.md](file:///D:/Myproject/CKs_PI_Code_Agent_Harness/external/SkillClaw/evolve_server/engines/EVOLVE_AGENTS.md)。
    2.  **智慧蒸餾 (Path 3)**：提取其 **集體演進 SOP（Summarize -> Aggregate -> Decide -> Validate -> History Ledger）** 寫入 [AGENTS.md](file:///D:/Myproject/CKs_PI_Code_Agent_Harness/pi-rules/AGENTS.md)，做為本地規則直接引導 Agent。
