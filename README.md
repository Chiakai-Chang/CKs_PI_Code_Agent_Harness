# 🚀 CK's Pi Code Agent Harness

> **一鍵重建頂級 AI 開發環境** —— 為你的 Pi 助手注入來自開源社群的強大「靈魂」。

`CK's Pi Code Agent Harness` 是一個專為 [Pi Coding Agent](https://github.com/badlogic/pi-mono) 設計的可攜式配置套件。它將散落在 GitHub 各處的強大 Skills、Rules 與 Extensions 整合為一個「一鍵式」的安裝流程，讓你無論在換電腦、切換工作環境時，都能在 3 分鐘內恢復完整的戰鬥力。

---

## 🌟 為什麼要使用這個 Harness？

不僅僅是配置拷貝，我們透過 **橋接技術 (Bridge Extension)** 深度整合了社群頂尖資源：

*   **🛡️ 紀律強化 (ECC)**：自動觸發品質門檻 (Quality Gate)、配置保護與專業 Git 工作流。
*   **🧠 專業直覺 (Superpowers)**：賦予 AI 「主動思考」與「工具自選」的專家行為準則。
*   **🔍 深度解讀 (Understand-Anything)**：讓 AI 具備「圖論級」的代碼庫解讀能力，快速啃食大型專案。
*   **🎨 美感注入 (UI-UX-Pro-Max)**：內建過百種專業設計規範與配色方案，讓 AI 寫出的介面更具質感。
*   **🦖 極簡溝通 (Caveman)**：支援超壓縮溝通模式，在複雜任務中為你節省 50% 以上的 Token 消耗。

---

## 🚀 快速上手 (Quick Start)

### 1. 取得專案
```bash
git clone https://github.com/Chiakai-Chang/CKs_PI_Code_Agent_Harness.git
cd CKs_PI_Code_Agent_Harness
```

### 2. 執行安裝
*   **Windows**: 雙擊執行 `install.bat`（建議右鍵「以管理員身分執行」以獲得最佳體驗）。
*   **macOS / Linux**: 執行 `bash install.sh`。

> 安裝程式會自動檢查 Git/Python/Node 補全環境，並偵測您電腦上的 **Ollama** 或 **LMStudio** 模型。

### 3. 開始開發
安裝完成後，直接在終端機輸入：
```bash
pi
```

---

## 🛠️ 核心特色

*   **⚡ 全自動化安裝**：自動處理環境補全，缺什麼裝什麼，不再為 PATH 設定煩惱。
*   **🕵️ 智慧模型配置 (Smart Detection)**：
    *   **真值偵測**：深度對接 Ollama API 與 llama.cpp `/props`，自動擷取精準的 Context Window。
    *   **硬體感知**：自動掃描系統 RAM 與 NVIDIA VRAM，根據硬體體質給出最佳參數建議。
    *   **Enter-Centric UI**：一路按 Enter 即可完成專業配置，同時保留手動微調空間。
*   **🔄 持久化計畫 (Manus-style)**：內建 `planning-with-files`，讓 AI 在多輪對話中擁有「外部硬碟級」的記憶力。
*   **🌐 跨平台支援**：完美支援 Windows (Git Bash)、macOS 與 Linux。

---

## 📂 技能包與生態系 (Integrated Ecosystem)

本專案透過整合以下開源專案，構建了目前最完整的 `pi` 技能圖譜：

| 領域 | 參考來源 / 專案 | 核心功能 |
| :--- | :--- | :--- |
| **工作流管理** | [Everything Claude Code](https://github.com/affaan-m/everything-claude-code) | Hooks 橋接、品質檢查點、`/tdd`、`/plan`。 |
| **行為強化** | [Superpowers](https://github.com/obra/superpowers) | 強迫 AI 在每一動之前尋找最佳專業技能。 |
| **代碼解讀** | [Understand-Anything](https://github.com/Lum1104/Understand-Anything) | `/understand-onboard` 生成專案知識圖譜。 |
| **視覺設計** | [UI-UX-Pro-Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | 專業配色、字體配對與 UI 審查清單。 |
| **瀏覽器自動化** | [dev-browser](https://github.com/SawyerHood/dev-browser) | 讓 AI 具備操作 Chrome 進行網頁驗證的能力。 |
| **提示工程** | [prompt-master](https://github.com/nidhinjs/prompt-master) | 自動優化發送給其他 AI 模型的提示詞。 |

---

## 📁 專案結構速覽

```text
├── install.bat / install.sh   # 多平台一鍵安裝入口
├── pi-config/                 # 預設設定檔 (models.json, settings.json)
├── pi-skills/                 # 核心技能 (Core) 與可選 UI 技能 (Optional)
├── pi-extensions/             # 關鍵橋接擴充 (ECC Bridge, Planning Bridge)
├── pi-rules/                  # 開發規範與工作流程指南
├── scripts/                   # 底層安裝與還原邏輯 (setup.py, restore.py)
└── external/                  # ECC 核心組件 (Git Submodule)
```

---

## ✅ 隱私、安全與信任

*   **完全開源**：所有安裝代碼透明可查，杜絕後門。
*   **0 資料收集**：本套件不收集、不追蹤任何用戶行為。
*   **本地優先**：優先支持本地 LLM (Ollama)，隱私資料不出門。
*   **自動備份**：執行 `restore` 前會自動將您的 `~/.pi/agent` 備份。

---

## ❓ 常見問題 (FAQ)

<details>
<summary><strong>如何更新 Harness 到最新版本？</strong></summary>
在本資料夾執行：
1. `git pull`
2. `git submodule update --remote`
3. `python scripts/restore.py`
</details>

<details>
<summary><strong>安裝時出現權限錯誤？</strong></summary>
Windows 用戶請確保以「系統管理員」身分執行終端機或 `install.bat`。
</details>

<details>
<summary><strong>找不到本地 Ollama 模型？</strong></summary>
請確保 Ollama 已啟動並在瀏覽器輸入 `http://localhost:11434` 確認服務正常運作，然後重新執行安裝腳本。
</details>

---

## 🙏 感謝與授權

*   本專案採用 **MIT 授權**。
*   特別感謝 [badlogic/pi-mono](https://github.com/badlogic/pi-mono) 提供的強大基座。
*   向所有在 **「技能來源」** 列表中出現的開源貢獻者致敬。

---
**由 [CK (Chiakai Chang)](https://github.com/Chiakai-Chang) 維護與優化。**
