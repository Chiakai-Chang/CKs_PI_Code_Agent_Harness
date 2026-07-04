# 🧠 決策紀錄 (Rationale) - MECE-Autopilot Bridge

## 1. SWOT 分析與 TOWS 交叉決策

為了評估將 `MECE-Autopilot` 推理標準導入本 Harness 的合適性，我們進行以下技術評估：

### SWOT 分析 (Technical SWOT)
*   **優勢 (Strengths)**：
    *   **互斥且窮盡 (MECE)** 的多角色辯論思維，能強迫 AI (特別是本地 LLM) 跳出單一思維盲點。
    *   **上下文隔離**：協調器將多輪辯論切分為獨立的檔案儲存，避免將超長對話擠在同一個 Context 中，適合本地模型有限的上下文空間。
    *   **輕量化設計**：腳本為零依賴的 Node.js 檔案，符合 Harness 追求的零依賴部署原則。
*   **劣勢 (Weaknesses)**：
    *   **Token 消耗顯著增加**：但由於本專案以本地模型為主（免 API 費用），因此對 Token 消耗不敏感。
    *   **路徑調用依賴**：原專案依賴系統 PATH 中的 `mece-autopilot` 指令，AI 在不同機器上不易直接執行。
*   **機會 (Opportunities)**：
    *   與本專案的 `C.A.S.E. 框架`、`LLM Wiki` 高度契合。辯論產出的 ADR (Architecture Decision Record) 可做為專案長期記憶的沉澱載體。
*   **威脅 (Threats)**：
    *   本地模型可能在多角色扮演中產生「自我認同混淆」或「盲目同意」（可透過 Devil's Advocate 及收斂門檻檢驗解決）。

### TOWS 交叉決策
*   **SO 策略 (發揮優勢/利用機會)** → **採路徑 1 (Native Mapping)**：將該專案以 Git Submodule 形式引入至 `external/mece-autopilot`，直接映射其 `SKILL.md`，享有上游最新決策標準的更新。
*   **WO 策略 (克服弱點/利用機會)** → **採路徑 2 (Thin Bridge)**：建立 `mece-autopilot-bridge`，動態解析並注入協調器的**絕對路徑**到 Pi 的系統提示詞中，使 AI 能無縫透過 `node "<abs_path>"` 啟動並步進狀態機，繞過全域環境變數依賴。

---

## 2. 核心價值：本地推理自適應

MECE-Autopilot 為本地模型引入了「決策與收斂」的閉環。本地模型不需要追求極致省 Token，而是需要透過「左右互搏」的思維衝突，逼出潛在的系統安全威脅或架構瑕疵。

---

## 3. 維護計畫
*   將 `external/mece-autopilot` 作為 Git Submodule 管理，定期同步上游更新。
*   使用 `mece-autopilot-bridge` 自動向 AI 宣告調用指令與路徑，確保跨平台零阻力運作。

---
**本文件依據 docs/core/DISTILLATION_GUIDE.md 建立。**
