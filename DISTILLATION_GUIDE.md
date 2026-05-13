# 🧪 功能蒸餾指南 (Distillation Guide) v3.0

這份文件記錄了本專案如何將外部 AI 代理功能「蒸餾」至 `Pi` 平台，並確保其具備 **「環境自適應 (Environment Agnostic)」** 的通用能力。

---

## 核心設計理念：硬體與軟體的契約 (The Contract)
為了讓 Harness 能適應不特定的用戶設備（從 8GB 筆電到 128GB 工作站），所有蒸餾工作必須遵循 **「動態縮放」** 原則：
*   **不假設環境**：嚴禁在腳本或代理中硬編碼 Context Window、線程數或記憶體分配。
*   **資源意識**：功能模組必須具備「先偵測、後啟動」的意識。
*   **優雅降級**：當硬體不足以支撐「全量功能」時，必須自動切換至「核心模式」。

---

## 蒸餾標準流程 (Adaptive Distillation SOP)

### 第一步：能力分層定義 (Tiering)
在解構外部專案時，必須將其能力劃分為三個等級並定義門檻：
1.  **Tier 1: 核心生存 (Minimal)** —— 僅需 8GB RAM，提供基礎指令響應。
2.  **Tier 2: 深度分析 (Standard)** —— 需 16GB+ RAM / 8GB+ VRAM，支援多檔案邏輯分析。
3.  **Tier 3: 極限模式 (Extreme)** —— 需旗艦硬體，支援 128k+ 長文本與全專案圖譜生成。

### 第二步：橋接器的環境偵測 (Resource Probing)
擴充功能的 `index.ts` 不僅是翻譯，更是「導航員」：
*   **主動探針**：利用 `setup.py` 注入的 `PI_HARNESS_ROOT` 讀取硬體概況。
*   **參數對接**：根據偵測到的 VRAM/RAM，動態將對應的參數（如 `num_ctx`）傳遞給外部腳本。
*   **範例**：若偵測到用戶使用 CPU 推論，自動在調用 `/understand` 時加入 `--depth 1` 的限制。

### 第三步：人格的環境適應性 (Prompt Scalability)
實體化 `.md` 代理人格時，加入環境分支指令：
> *"If the current system report shows low memory, focus on individual files instead of attempting codebase-wide relationship mapping."*

---

## 環境自癒與提權：通用安全準則
*   **提權隔離**：確保以管理員/root 權限執行的操作僅限於「安裝本體」。所有生成的設定檔必須具備正確的 User Space 讀寫權限。
*   **編碼統一**：強制 UTF-8 是所有跨環境工具的最低底線，必須在所有 Batch/Shell 進入點強制執行。

---

## 蒸餾後檢核表 (Post-Distillation Validation)
- [ ] **低配環境模擬**：手動將 `models.json` 的 Context 設為 4096，測試功能是否會崩潰或能自動簡化任務。
- [ ] **高配環境釋放**：確認在強大硬體下，功能是否能自動解鎖（如自動跳轉至 192k 以上）。
- [ ] **全域路徑穩定性**：在系統不同分區 (C:/D:/E:) 下啟動 `pi`，驗證絕對路徑注入是否依然精準。
- [ ] **權限淨化**：確認安裝後，非管理員帳號是否能正常使用所有功能。

---

## 實戰心得：研究與分發的平衡
*   **開發者研究用**：可以在本地隨意調整參數進行極限測試。
*   **分發給他人用**：必須提供 `.example` 配置，並在 `setup.py` 中實作「硬體感知偵測」。
*   **保持腳本「零依賴」**：減少使用者安裝外部環境（如 pnpm）的負擔，這對於通用性至關重要。

---
**本指南由 CK's Pi Code Agent Harness 核心團隊維護，旨在構建最具適應力的 AI 開發環境。**
