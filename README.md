# 🚀 CK's Pi Code Agent Harness

> 幫你「一鍵架設 AI 程式開發助手（Pi）」的配置套件 — 換電腦不手軟

這是一個可攜式 Pi 配置，讓你在任何一台電腦上，都能快速重建相同的 AI 開發環境。
不用手動拷貝設定、不用重頭調整 skills 與 rules，跑一支指令即可完成。

### 核心特色

- 一鍵安裝與還原（Windows 為主，macOS / Linux 亦可）
- 自動檢查必要環境（Git / Python / Node / Pi），缺什麼會引導你裝
- 自動偵測本地 LLM（Ollama / LMStudio / llama.cpp 等），讓你直接選模型
- 內建開發 skills、rules 與 extensions，支援程式開發、測試、除錯、Git 流程

## 🧭 快速上手（3 步完成）

1) 克隆本專案

   - git clone git@github.com:Chiakai-Chang/CKs_PI_Code_Agent_Harness.git
   - cd CKs_PI_Code_Agent_Harness

2) 執行一鍵安裝

   - Windows:
     - .\install.bat
   - macOS / Linux:
     - bash install.sh

   安裝程式會：
   - 自動檢查 Git / Python / Node / Pi
   - 若缺少必要套件：
     - 會顯示安裝指令（例如 winget / brew / apt）
     - 或直接打開下載頁面（如 nvm-windows）
     - 必要時提醒你重開終端機或以管理員執行
   - 若尚未安裝 Pi：
     - 會詢問你是否要自動安裝（npm install -g）
   - 掃描你電腦上的本地 LLM 服務與可用模型，讓你選擇
   - 自動寫入 shellPath（Windows Git Bash）
   - 自動還原 skills / rules / extensions 到 ~/.pi/agent

   依照畫面提示操作即可。

3) 開啟 Pi 並確認

   - pi

   確認：
   - Skills 正常載入
   - Extensions 正常載入
   - 模型設定符合你的需求

如果你要更詳細的說明，可以展開下方內容。

<details>
<summary><strong>📦 環境需求</strong></summary>

- Windows / macOS / Linux
- Git
- Python（建議 3.10+）
- Node.js ≥ 18（推薦 LTS）
- Pi（由腳本協助安裝或更新）

本工具會自動檢測以上套件，若缺漏會引導你安裝。

</details>

<details>
<summary><strong>📁 專案結構</strong></summary>

- install.bat / install.sh
  - 各平台一鍵入口，呼叫 scripts/setup.py

- scripts/
  - setup.py：環境檢查與設定主程式
  - restore.sh：Bash 版一鍵還原 Pi 配置
  - restore.py：Python 版還原（不依賴 bash）
  - restore-commands.md：手動還原步驟

- pi-config/
  - settings.json：Pi 基本設定（模型、套件等）
  - model.json：當前選擇的本地模型
  - config.json：自訂 skills/agents 路徑
  - harness-config.json：本套件版本與建議 Pi 版本
  - git/.gitignore：Git 忽略設定

- pi-skills/
  - core/：核心技能（程式開發、測試、除錯、Git 流程、code review、understand 系列）
  - optional/：可選的設計與 UI 技能（例如 design、ui-styling、ui-ux-pro-max、slides、brand）
  - 還原時會自動套用 core，並詢問是否套用 optional

- pi-rules/
  - 開發規範與工作流程（Git 流程、程式碼風格、安全、效能、測試等）

- pi-extensions/
  - 自訂 extensions，例如 planning-with-files 橋接

</details>

<details>
<summary><strong>🔄 換電腦流程（簡明版）</strong></summary>

在新電腦上：

1. 安裝 Git 與 Python（若尚未安裝）
2. 克隆本專案
3. 執行：
   - Windows: .\install.bat
   - macOS / Linux: bash install.sh
4. 依照提示完成：
   - 安裝 Node（若無）
   - 安裝 / 更新 Pi
   - 選擇本地模型
   - 還原配置
5. 開啟 Pi 並確認環境正常

</details>

<details>
<summary><strong>🛠️ 更新 Pi 與本專案（分離管理）</strong></summary>

Pi 與本配置是獨立維護的：

- 更新 Pi（核心版本）：
  - npm update -g @mariozechner/pi-coding-agent
  - pi update

- 更新本專案的配置（skills / rules / extensions）：
  - 在本 repo 資料夾中：
    - git pull
  - 重新套用配置：
    - bash scripts/restore.sh
    - 或 python scripts/restore.py

</details>

<details>
<summary><strong>🔌 版本建議與相容</strong></summary>

- 建議 Pi 版本：>= 0.73.0
- 若 Pi 升級後行為異常，建議：
  - 先執行 pi update
  - 再 git pull 本專案
  - 重新執行 restore 腳本
- 若 Pi 官方文件格式變更，本 repo 將隨之更新，不會強制綁死特定版本。

</details>

<details>
<summary><strong>🛡️ 安全與信任</strong></summary>

- 目前版本（截至 2025/11）：
  - 不收集使用資料
  - 不呼叫任何外部 API（除你選用的本地 LLM 外）
  - 不追蹤設備資訊
- 腳本會修改：
  - ~/.pi/agent/settings.json
  - ~/.pi/agent/config.json
  - ~/.pi/agent/skills
  - ~/.pi/agent/rules
  - ~/.pi/agent/extensions
  - ~/.pi/agent/git/.gitignore
- 在覆蓋前會自動備份至：
  - ~/.pi/agent.backup.<timestamp>
- 若你信任本 repo，才可放心執行。

</details>

<details>
<summary><strong>🐞 常見問題與除錯</strong></summary>

1) 「pi 指令找不到」
   - 確認 Pi 已安裝：
     - 執行: pi --help
   - 若找不到，請安裝：
     - npm install -g @mariozechner/pi-coding-agent
   - 若剛安裝完仍找不到：
     - 關閉所有終端機後重新開啟（讓 PATH 生效）
     - 或重新執行: .\install.bat / bash install.sh

2) 「npm install -g 權限不足」（Windows 常見）
   - 右鍵 install.bat → 以系統管理員身分執行。
   - 或手動：
     - 以管理員開啟終端機
     - 再執行: npm install -g @mariozechner/pi-coding-agent

3) 「找不到 Ollama / LMStudio / 本地模型」
   - 確認服務已啟動：
     - Ollama: 瀏覽器開啟 http://localhost:11434/api/tags
     - LMStudio: 確認已啟動且啟用 local server
   - 若服務在跑但仍未偵測到：
     - 手動編輯 pi-config/settings.json，填入對應 provider 與 model。
   - 常見 port：
     - Ollama: 11434
     - LMStudio / llama.cpp: 1234、8080、5000

4) 「restore.sh 無法執行」（Windows 沒有 bash）
   - 安裝 Git（含 Git Bash）
   - 或使用 Python 版還原（不依賴 bash）：
     - python scripts/restore.py

5) 「模型設定好像沒生效」
   - 檢查 pi-config/settings.json 中 defaultProvider / defaultModel 是否正確
   - 在 Pi 內確認當前使用的模型，必要時重新開啟 Pi

6) 「Skill 命名衝突」
   - 確認使用的是本 repo 最新配置
   - 執行: git pull
   - 重新執行: bash scripts/restore.sh（或 python scripts/restore.py）

7) 如何取得除錯日誌
   - 本工具輸出會使用前綴：
     - [SETUP] 環境檢查與安裝
     - [RESTORE] 配置還原
   - 若要請他人協助：
     - 複製包含 [SETUP]/[RESTORE] 的完整輸出
     - 附註：作業系統、Pi 版本（pi --version）

</details>

## 🙏 授權

本專案使用 MIT 授權（可自由修改與使用）。
