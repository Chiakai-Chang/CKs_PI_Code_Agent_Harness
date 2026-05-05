# 🚀 CK's Pi Code Agent Harness

> 幫你一鍵架設 AI 程式開發助手（Pi）的配置套件 — 換電腦不手軟

這是一個「可攜式 Pi 配置」，讓你在任何一台電腦上，都能快速重建相同的 AI 開發環境：
不用手動拷貝設定、不用重頭調整 skills 與 rules，跑一支指令即可還原。

特色：

- 一鍵檢查與設定環境（Windows 為主，macOS / Linux 皆可）
- 自動偵測本地 LLM（Ollama / LMStudio / llama.cpp 等），讓使用者選擇模型
- 自動寫入 shellPath（Windows Git Bash）
- 內建 skills：程式開發、UI/UX 設計、文件撰寫、除錯流程等
- 內建 rules：Git 工作流程、程式碼風格、安全規範、測試標準
- 與 Pi 核心解耦：Pi 可自行更新，不受本 repo 限制
- 不需要 pi-mono 原始碼

本 repo 負責：
- ~/.pi/agent 下的配置（skills、rules、extensions、settings、config）

Pi 本身：
- 由 npm 安裝，由你自己決定版本與更新時機

## 📦 環境需求

- Windows / macOS / Linux
- Git
- Python（建議 3.10+）
- Node.js ≥ 18（推薦 LTS）
- Pi（由腳本協助安裝或更新）

## 🔌 版本建議與相容

- 建議 Pi 版本：>= 0.73.0
- 本 repo 的配置格式可能隨 Pi 版本演進調整：
  - 若 Pi 升級後行為異常，建議：
    - 先執行 pi update
    - 再 git pull 本專案
    - 重新執行 bash scripts/restore.sh
- 若 Pi 官方文件格式變更，本 repo 將隨之更新，不會強制綁死特定版本。

## 🛡️ 安全與信任

- 本套件目前版本（截至 2025/11）：
  - 不收集使用資料
  - 不呼叫任何外部 API（除你選用的本地 LLM / 模型外）
  - 不追蹤設備資訊
- restore.sh 與 setup.py 會修改：
  - ~/.pi/agent/settings.json
  - ~/.pi/agent/config.json
  - ~/.pi/agent/skills
  - ~/.pi/agent/rules
  - ~/.pi/agent/extensions
  - ~/.pi/agent/git/.gitignore
- 在覆蓋前，restore.sh 會自動備份至：
  - ~/.pi/agent.backup.<timestamp>
- 若你信任本 repo，才可放心執行。

## 🧭 快速上手（手把手教學）

### Windows 用戶

1. 安裝 Git 與 Python（若尚未安裝）

   打開「PowerShell」或「命令提示字元」，執行：

   - winget install Git.Git
   - winget install Python.Python.3.12

   完成後，請「重新開啟終端機」。

2. 克隆本專案

   - git clone git@github.com:Chiakai-Chang/CKs_PI_Code_Agent_Harness.git
   - cd CKs_PI_Code_Agent_Harness

3. 執行一鍵安裝

   - .\install.bat

   安裝程式會：

   - 檢查 Git / Python / Node/npm
   - 若缺少 Node：提示你安裝 nvm-windows 並重新執行
   - 自動安裝 / 更新 Pi（若你同意）
   - 掃描 Ollama / LMStudio 等本地 LLM 服務，列出可用模型
   - 讓你選擇模型，並寫入 pi-config/settings.json 與 model.json
   - 偵測 Git Bash 路徑並寫入 shellPath
   - 詢問是否還原配置到 ~/.pi/agent

   依照畫面提示操作即可。

4. 開啟 Pi

   - pi

   確認：
   - Skills 正常載入
   - Extensions 正常載入
   - 模型設定符合你的需求

### macOS / Linux 用戶

1. 安裝 Git 與 Python

   - macOS（Homebrew）:
     - brew install git python
   - Ubuntu/Debian:
     - sudo apt update
     - sudo apt install -y git python3

2. 克隆本專案

   - git clone git@github.com:Chiakai-Chang/CKs_PI_Code_Agent_Harness.git
   - cd CKs_PI_Code_Agent_Harness

3. 執行一鍵安裝

   - bash install.sh

   流程與 Windows 類似：
   - 檢查依賴
   - 安裝 / 更新 Pi
   - 掃描本地 LLM
   - 讓你選擇模型
   - 還原配置

4. 開啟 Pi

   - pi

   確認 Skills / Extensions 正常即可。

## 📁 專案結構

- install.bat / install.sh
  - 各平台一鍵入口，呼叫 scripts/setup.py

- scripts/
  - setup.py：環境檢查與設定主程式
  - restore.sh：一鍵還原 Pi 配置
  - restore-commands.md：手動還原步驟

- pi-config/
  - settings.json：Pi 基本設定（模型、套件等）
  - model.json：當前選擇的本地模型
  - config.json：自訂 skills/agents 路徑
  - git/.gitignore：Git 忽略設定

- pi-skills/
  - 分為：
    - core/（核心）：程式開發、測試、除錯、Git 流程、規劃、code review、understand 系列
    - optional/（可選）：較重的設計與 UI 技能，例如 design、ui-styling、ui-ux-pro-max、slides、brand
  - 還原時會：
    - 自動套用 core
    - 詢問是否套用 optional（可依需求跳過，讓環境更輕量）

- pi-rules/
  - 開發規範與工作流程：
    - Git 工作流、程式碼風格、安全、效能、測試等

- pi-extensions/
  - 自訂 extensions，例如 planning-with-files 橋接

## 🔄 換電腦流程（簡明版）

在新電腦上：

1. 安裝 Git、Python
2. 克隆本專案
3. 執行：
   - Windows: .\install.bat
   - macOS/Linux: bash install.sh
4. 依照提示完成：
   - 安裝 Node（若無）
   - 安裝 / 更新 Pi
   - 選擇本地模型
   - 還原配置
5. 開啟 Pi 並確認環境正常

## 🛠️ 更新 Pi 與本專案（分離管理）

Pi 與本配置是獨立維護的：

- 更新 Pi（核心版本）：
  - npm update -g @mariozechner/pi-coding-agent
  - pi update

- 更新本專案的配置（skills / rules / extensions）：
  - 在本 repo 資料夾中：
    - git pull
  - 重新套用配置：
    - bash scripts/restore.sh

這樣可確保：
- Pi 可獨立升級到最新版
- 你的 skills 與 rules 也能同步更新

## ⚠️ 注意事項

- 部分安裝指令（如 npm install -g 或 winget / apt）可能需要：
  - 以「系統管理員」身分開啟終端機
- 本 repo 的 config.json 中有部分路徑會參考本機目錄：
  - 還原腳本會自動替換部分佔位字串
  - 若有額外外部路徑（如 everything-claude-code），
    請手動編輯 ~/.pi/agent/config.json 調整
- 若出現 skill 命名警告，確認已使用本 repo 最新配置並重新還原

## 🛠️ 常見問題與除錯

如果你在使用時卡住，可依症狀快速檢查：

1) 「pi 指令找不到」
- 確認 Pi 已安裝：
  - 執行: pi --help
- 若找不到，請安裝：
  - npm install -g @mariozechner/pi-coding-agent
- 若剛安裝完 pi 仍找不到：
  - 關閉所有終端機後重新開啟（讓 PATH 生效）
  - 或重新執行: install.bat / install.sh

2) 「npm install -g 權限不足」（Windows 常見）
- 現象：安裝 Pi 失敗，出現 EACCES / 權限錯誤。
- 解法：
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
  - LMStudio / llama.cpp: 1234、8080、5000（視你設定）

4) 「restore.sh 無法執行」（Windows 沒有 bash）
- 解法：
  - 安裝 Git（含 Git Bash）
  - 或使用 Python 版還原（不依賴 bash）：
    - python scripts/restore.py

5) 「模型設定好像沒生效」
- 檢查：
  - pi-config/settings.json 中 defaultProvider / defaultModel 是否正確。
  - 在 Pi 內確認當前使用的模型，必要時重新開啟 Pi。

6) 「Skill 命名衝突」
- 若出現 skill name 錯誤：
  - 確認使用的是本 repo 最新配置。
  - 執行: git pull
  - 重新執行: bash scripts/restore.sh（或 python scripts/restore.py）

7) 如何取得除錯日誌
- 本工具輸出會使用前綴：
  - [SETUP] 環境檢查與安裝
  - [RESTORE] 配置還原
- 若需要請他人協助：
  - 複製包含 [SETUP]/[RESTORE] 的完整輸出
  - 附註：作業系統、Pi 版本（pi --version）

## 🙏 授權

本專案使用 MIT 授權（可自由修改與使用）。
