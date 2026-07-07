# 🧪 功能蒸餾指南 (Distillation Guide) v3.0

這份文件記錄了本專案如何將外部 AI 代理功能「蒸餾」至 `Pi` 平台，並確保其具備 **「環境自適應 (Environment Agnostic)」** 的通用能力。

---

## 核心設計理念：智慧嫁接與價值判準 (The Wisdom of Choice)
本專案的目標是做一個 **「輕量但選集精良」** 的開發框架。我們不進行盲目的「搬運」，而是根據以下原則進行智慧整合：

### 核心原則 (Key Principles)
*   **價值優先 (Capability-First)**：移植的唯一理由是該功能能顯著提升開發效率。
*   **高保真移植 (High-Fidelity)**：一旦決定移植，必須確保核心邏輯的完整性。我們追求的是「邏輯的精煉」而非「功能的閹割」。
*   **果斷放棄 (The Power of No)**：並非所有強大功能都適合本專案。如果一個功能的代價是讓環境變得臃腫、緩慢或難以維護，我們應拒絕移植，而非勉強蒸餾。
*   **維護性優先 (Maintainability)**：優先考慮能享有上游更新的整合方式，避免產生一次性的技術債。

### 整合路徑優先級 (Priority of Integration)
在引進外部功能時，必須按以下順序評估路徑：
1.  **原生映射 (Native Mapping) - 首選**：如果原專案結構相容，優先使用 `git submodule` 並直接映射路徑。這能確保我們 **100% 享有上游的持續更新**。
2.  **輕量橋接 (Thin Bridge)**：僅在需要對接 Pi 的特殊事件（如 Hooks）或修復跨平台路徑時，才撰寫極簡的橋接程式碼。
3.  **智慧蒸餾 (Smart Refactor) - 最後手段**：僅在原專案過於臃腫、依賴過重或無法直接執行時，才提取其核心 Prompt 邏輯改寫為本地 Skills。這是一次性的，應謹慎使用。

---

## 智慧移植流程 (Smart Grafting SOP)

### 第一步：戰略評估與決策分析 (Strategic Evaluation)
在動手前，必須進行深度「戰略分析」，不只是看功能好壞，更要看「代價與長遠價值」。建議使用以下工具進行分析：

#### 1. 技術 SWOT 分析 (Technical SWOT)
分析該外部專案對本 Harness 的意義：
*   **優勢 (Strengths)**：移植後能獲得什麼 Pi 原生沒有的神力？(如：192k 圖譜分析)。
*   **劣勢 (Weaknesses)**：移植會帶來什麼副作用？(如：增加 200MB 磁碟佔用、啟動延遲)。
*   **機會 (Opportunities)**：是否能藉此統一某種開發標準？或吸引特定語言的用戶？
*   **威脅 (Threats)**：上游專案是否已停止維護？其核心邏輯是否與未來 AI 趨勢衝突？

#### 2. 技術 TOWS 交叉決策矩陣
根據 SWOT 結果推演「最適路徑」：
*   **SO 策略 (發揮優勢/利用機會)** → **採路徑 1 (Native Mapping)**：功能強大且結構完美，直接 Submodule 引進，同步享受上游更新。
*   **WO 策略 (克服弱點/利用機會)** → **採路徑 3 (Smart Refactor)**：功能有價值但代價太高(重型依賴)，我們只「脫水」提取核心 Prompt 邏輯，徹底消滅弱點。
*   **ST 策略 (發揮優勢/迴避威脅)** → **採路徑 2 (Thin Bridge)**：上游更新頻繁但結構不穩，我們用「輕量橋接」隔絕影響，保留隨時切換的靈活性。
*   **WT 策略 (最小化弱點/迴避威脅)** → **果斷放棄 (The Power of No)**：如果維護成本高於獲得的戰力，這就是一個「負資產」。

### 第二步：決策存檔與脈絡保存 (Rationale Documentation)
一旦確定路徑，必須在該 Skill 目錄下建立 `RATIONALE.md`，記錄以下抉擇理由：
1.  **為什麼要選這個路徑？** (基於上面的 TOWS 分析)。
2.  **核心解決了什麼問題？** (User Case)。
3.  **未來的維護計畫是什麼？** (定期更新 Submodule 或 永久維持本地快照)。

### 第三步：邏輯重構與精煉 (Logic Adaptation)
確認要移植後，採取的策略是「轉換」而非「刪減」：
*   **人格轉換 (Persona Mapping)**：將外部專案原本複雜的代碼流，重新構思為 Pi 易於理解的「專家代理人格 (.md)」。
*   **工具對接**：精準對應外部工具與 Pi 原生工具。若有缺失，考慮以輕量的 TypeScript Extension 進行「能力補完」。
*   **配置解耦**：所有 machine-specific 的設定必須透過 `setup.py` 動態生成，嚴禁將開發者的本地設定硬編碼進 Skills。

### 第四步：環境自癒 (Zero-Friction Implementation)
*   **絕對路徑注入**：確保擴充功能在全域環境下依然具備「尋址能力」，這是全域穩定的底線。
*   **零依賴原則**：優先使用系統原生指令（curl, wmic, powershell），保持 Harness 倉庫的純淨與秒速安裝特質。

### 第五步：嚴謹驗證與閉環 (The Verification Loop)
功能移植完成後，必須進入「閉環驗證」階段，確保智慧沒有在蒸餾過程中喪失：
1.  **基準功能對照 (Functional Parity)**：
    *   **做法**：選取一個標準測試案例，分別在「原始專案」與「本 Harness」中執行。
    *   **目標**：確保兩者產出的關鍵決策與邏輯路徑一致，無核心價值遺失。
2.  **跨環境路徑壓力測試 (Path Resilience)**：
    *   **做法**：在不同的磁碟分區、包含特殊字元的資料夾、以及非管理員權限下啟動 `pi`。
    *   **目標**：驗證 `PI_HARNESS_ROOT` 的注入與 `Bridge Extension` 的調用是否百分之百穩定。
3.  **AI 人格自我審核 (Persona Fidelity Audit)**：
    *   **做法**：直接詢問被移植的 AI 代理其行為準則，檢查是否偏離了原始設計初衷。
    *   **目標**：確保 distilled agent 依然具備其原有的「專業靈魂」。

### 第六步：研究隔離與防汙染 (Research Isolation)
在深入研究外部專案時，建議將其完整代碼 Clone 到本地進行分析，但必須嚴格遵守「隔離原則」：
1.  **專屬研究目錄**：建議在本專案根目錄下建立 `research/` 資料夾，專門用來存放 `git clone` 回來的外部原始碼。
2.  **嚴禁提交原始碼**：絕對不要將外部專案的原始程式碼直接 Git Add 到本專案。我們只需要其「蒸餾後的精華」。
3.  **Git Ignore 保護**：確保 `research/` 或任何臨時存放外部檔案的目錄已列入 `.gitignore`，防止任何 machine-specific 或非專案資產被意外上傳，維持 Harness 倉庫的純淨度。

---

## 嚴禁行為 (Forbidden Bloat)
*   [ ] **嚴禁硬要**：禁止在破壞外部功能核心價值的前提下，強行進行「殘廢式」移植。
*   [ ] **嚴禁重型依賴**：禁止引入需要複雜編譯環境的二進位檔。
*   [ ] **嚴禁黑箱操作**：所有移植的 Skills 必須保持透明可讀，讓用戶知道 AI 到底在做什麼。

---

## 移植後驗證清單 (Final Validation Checklist)
- [ ] **功能保真度**：移植後的功能是否依然能解決原本它在原專案中所解決的問題？
- [ ] **路徑防禦力**：在系統不同分區 (C:/D:/E:) 下啟動，所有 Hook 與 Bridge 是否依然精準？
- [ ] **權限淨化度**：確認普通使用者權限是否能無礙執行所有移植過來的核心指令？
- [ ] **運作可行性**：在當前用戶設定的資源（如 32k Context）下，該功能是否提供了具備實際開發價值的輸出？
- [ ] **邏輯純粹性**：這個技能是否真的增加了開發力，還是只是多餘的裝飾？

---

## 🧠 脈絡復盤與防誤區指南 (Lessons Learned & Anti-Patterns)

專案在發展過程中曾經歷多次「非實證性設計」與「虛浮配置」的痛點。為了貫徹自我進化精神，以下記錄核心復盤脈絡，未來之 AI 代理與開發者必須嚴格遵守：

### 1. 拒絕「過度宣稱與吹牛」 (Anti-Bragging)
*   **歷史痛點**：過去的文檔曾出現「整合 GitHub 15+ 個頂尖開源倉庫」、「大師級資產」等無嚴謹實證的浮誇論述。這不僅對開發者無實質助益，更降低了開源專案的誠信度。
*   **進化規則**：所有文檔必須直白、論述客觀。我們只說明**「選集原因」**（Why we chose it）與**「遷移做法」**（How we migrated it）。專案為實驗性質，不保證一定比原生好，只保證「盡量選集、實事求是」。

### 2. 拒絕「空殼配置」 (No Passive/Zombie Configs)
*   **歷史痛點**：在遷移過程中，為了應付配置模板，曾在 `settings.json` 中塞入許多「尚未實現或完全是空殼」的 TypeScript Extensions（如 `open-design-bridge`、`open-pua-bridge`）。這導致 `pi` 啟動時拋出無謂的載入警告，對系統穩定性造成隱患。
*   **進化規則**：**嚴禁註冊空殼 Extension**。如果該模組僅有 Skills（純 Markdown 提示詞）而無實質的 TypeScript Hook 邏輯，應將其從 `settings.json` 的 `extensions` 列表中移除，直接將 Skills 目錄映射至 Pi 的 `skills` 中載入即可。每行註冊的配置都必須是「有代碼、有實質功用、經過測試」的。

### 3. 避免「硬編碼跨平台衝突」 (Platform-Agnostic Defaults)
*   **歷史痛點**：在共享的配置模板 `pi-config/settings.json` 中寫死了 Windows 特有的 Shell 路徑（`C:\\Program Files\\Git\\bin\\bash.exe`），導致 macOS / Linux 使用者複製專案後啟動即崩潰。
*   **進化規則**：共享配置文件必須保持**平台無關性**。任何 OS-specific 的配置（如 Shell、路徑、環境變數）必須在運行期由 `setup.py` 動態偵測並寫入使用者的本地 `.pi/settings.json` 中，絕不應編碼進受版本控制的模板檔中。

### 4. 嚴格執行「功能性審計」而非「文檔糊弄」 (Verify over Documenting)
*   **歷史痛點**：當被質疑功能是否可用時，代碼代理人容易「僅修改 README 敷衍」，而忽略了代碼底層的真實狀態。
*   **進化規則**：在宣稱任何功能（如 Hooks / 雙軌驗證）可用之前，必須撰寫獨立的腳本或直接審計全域安裝包（如 `node_modules/@earendil-works/pi-coding-agent` 的 `loader` 與 `runner`）來確認其支援的 Event API（例如 `before_agent_start`, `tool_call` 等）與虛擬別名機制（如虛擬映射 `@mariozechner/pi-coding-agent` 的別名），確保功能是真的「開箱即用」。

### 5. 脈絡的可追溯性 (Canonical Links)
*   **進化規則**：所有客製化的框架與理念（如 C.A.S.E. 框架），其跳轉連結必須指向精準、權威且擁有者持有的 Canonical URL（例如指向 [Chiakai-Chang/Local-Agent-Workspace](https://github.com/Chiakai-Chang/Local-Agent-Workspace/tree/main/C.A.S.E._Framework)），絕不能使用模糊的搜尋結果或第三方無關 Repo 連結。

### 6. 子模組與橋接代碼的徹底清理 (Dead Bridge Purging)
*   **歷史痛點**：在對專案 submodule 進行修剪與刪除時，若只刪除了外部子模組，而未清理其在本地的橋接程式碼（如 `understand-framework`、`*-bridge`）與 `restore.py` 的路徑註冊，會導致新環境還原時拋出錯誤甚至啟動崩潰。
*   **進化規則**：每次移除 Submodule 後，必須立刻在 [scripts/restore.py](../../scripts/restore.py) 的註冊列表、`pi-extensions/` 橋接器與對應的架構文檔中進行「全鍊條清理」。

### 7. 設計與測試的版本解耦 (Version-Agnostic File Naming)
*   **歷史痛點**：設計規格（如 `specs/harness-setup-v3.7.2`）與測試套件（如 `tests/test_v372_setup.py`）如果帶有寫死的具體版本號，會導致工具迭代時，文檔命名與實際代碼進度發生漂移，徒增維護負擔。
*   **進化規則**：文檔與測試檔案應使用**版本無關**的通用命名（如 [specs/harness-setup/](../../specs/harness-setup/) 與 [tests/test_setup.py](../../tests/test_setup.py)），並將具體版本作為文檔內部的元數據管理。

### 8. 多供應商模型引導的智慧解耦 (Smart Multi-Provider Model Wizard)
*   **歷史痛點**：原本的 setup 腳本只支援本地 LLM 偵測，若無本地執行中的 Ollama/Llama.cpp 則直接跳過模型配置，這限制了採用雲端 API 的開發者。
*   **進化規則**：模型配置嚮導必須涵蓋本地（如動態查詢 Ollama 標籤）與雲端供應商（Anthropic, Google, OpenAI, OpenRouter, 自訂端點）的互動式引導。若設定非本地模型，需自動清除 settings.json 中的 `apiBase` 配置，防止 AI 行為混淆。

### 9. 啟動腳本與 Onboarding 合規性 (Bootstrap Script Compliance)
*   **歷史痛點**：初始化腳本（`install.bat` / `install.sh`）若過於簡化，容易因缺乏授權聲明、確認提示與進度標記，而無法通過專案合規測試。
*   **進化規則**：確保所有引導腳本均包含明確的步驟進度提示、開源 MIT 授權聲明，以及使用者二次確認機制。

---

## 實戰心得：研究與分發的平衡
*   **開發者研究用**：可以在本地隨意調整參數進行極限測試。
*   **分發給他人用**：必須提供 `.example` 配置，並在 `setup.py` 中實作「硬體感知偵測」。
*   **保持腳本「零依賴」**：減少使用者安裝外部環境（如 pnpm）的負擔，這對於通用性至關重要。

---
**本指南由 CK's Pi Code Agent Harness 核心團隊維護，旨在構建最具適應力的 AI 開發環境。**
