# 📜 OmniHeal Project Constitution (治理憲法)

> **目標專案**: CK's Pi Code Agent Harness (`CKs_PI_Code_Agent_Harness`)  
> **生成時間**: 2026-07-27  
> **預設領域**: AI Agent 框架 / 開發工具 (Cross-Platform CLI & Extension Infrastructure)  

---

## 🏛️ 專案核心治理原則 (Project Core Principles)

1. **反誇大宣傳 (Anti-Bragging)**
   - 拒絕使用缺乏功能實證的宣傳性形容詞或主張，所有發現與改善必須立足於客觀實驗與代碼事實。

2. **組態衛生 (Config Hygiene)**
   - 嚴禁在 `settings.json` 模板中註冊空殼或佔位符 TypeScript 擴充功能；每個 registered extension 必須有對應實作。

3. **跨平台動態安全性 (Cross-Platform Safety)**
   - `pi-config/` 下的文件嚴禁硬編碼 Windows 絕對路徑（如 `C:\...`）。所有平台相關路徑必須在 `scripts/setup.py` / `scripts/restore.py` 安裝時動態探測與注入。

4. **C.A.S.E. 框架對齊 (C.A.S.E. Alignment)**
   - 擴充套件設計必須完全符合 C.A.S.E. (Constitution, Architecture, State, Execution) 框架原則。

5. **Shell 與原生執行相容性 (Shell & Execution Discipline)**
   - 所有腳本、橋接 Hook 與指令必須相容於 `bash` 語法，防止在 Windows 環境下因 CMD/PowerShell 差異造成執行失敗。

6. **深層實測驗證 (Deep Verification & Rigorous Audit)**
   - 嚴禁未讀原始碼即做推斷；所有修復必須經由自動化測試（`python -m unittest discover -s tests`）與驗證腳本（`verify-bridges.py`, `validate-config.py`）驗證。

---

## 🔒 絕不容忍之致命問題 (Zero Tolerance Patterns)

- **SystemPrompt Wipeout**: 在 Bridge Extensions 的 `before_agent_start` 中未拼接 `(event.systemPrompt ?? "")` 導致全局提示詞遭覆寫。
- **Unbounded Auto-Turn Loops**: 在灰牌或錯訊處理中盲目觸發 `deliverAs: "nextTurn"` 導致 LLM 陷入無限自驅動循環。
- **Zombie Configs**: 在配置文件或模組登錄中保留已移除或無效的擴充元件參照。
- **Hardcoded Absolute Paths**: 將開發者個人電腦路徑硬編碼入提交程式碼中。
