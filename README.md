# 🚀 CK's Pi Code Agent Harness

> 一鍵還原你的 Pi 開發環境 — 換電腦不手軟

CK's Pi Code Agent Harness 是一套「可攜式 Pi 配置」，
讓你在任何一台電腦上都能快速重建相同的 Pi 開發環境。

特色：

- 一鍵還原配置：bash scripts/restore.sh
- 內建 skills：程式開發、UI/UX 設計、文件撰寫、除錯流程等
- 內建 rules：Git 工作流程、程式碼風格、安全規範、測試標準
- 支援本地模型：可指定 Ollama / LM Studio / 自架 API
- 與 Pi 核心解耦：Pi 可自行更新，不受本 repo 限制
- 跨平台友善：Windows (Git Bash)、macOS、Linux 皆可

本 repo 負責：
- ~/.pi/agent 下的配置（skills、rules、extensions、settings、config）

Pi 本身：
- 由 npm 安裝，由你自己決定版本與更新時機

## 📦 環境需求

- Node.js ≥ 18（推薦 LTS）
- Git
- Pi（透過 npm 安裝）

## 🧭 快速上手（手把手教學）

### 第一步：安裝 Pi

在本機先安裝 Pi（獨立於本 repo）：

- npm install -g @mariozechner/pi-coding-agent

確認已安裝：

- pi --help

（若出現說明，代表 Pi 已安裝成功）

### 第二步：克隆本專案

- git clone git@github.com:Chiakai-Chang/CKs_PI_Code_Agent_Harness.git
- cd CKs_PI_Code_Agent_Harness

### 第三步：（選填）設定本地模型

如果你想搭配本地模型（如 Ollama / LM Studio）：

1. 開啟 pi-config/settings.json
2. 調整 defaultProvider 與 defaultModel，例如：

   - 使用 Ollama：
     - "defaultProvider": "ollama",
       "defaultModel": "llama3.1"
   - 使用自架 OpenAI 相容 API：
     - "defaultProvider": "custom-openai-compatible",
       "defaultModel": "your-model"

若暫時不想調整，也可以先保留預設值，之後在 Pi 中再修改。

### 第四步：一鍵還原配置

執行還原指令：

- bash scripts/restore.sh

此指令會自動：

- 建立 ~/.pi 與 ~/.pi/agent 相關目錄
- 複製 config、skills、rules、extensions
- 替換路徑佔位字串（TODO_NEW_MACHINE）
- 自動備份既有配置到 .backup.<timestamp>（方便復原）

### 第五步：更新 Pi 並確認

- pi update
- pi

開啟 Pi 後，確認：

- Skills 正常載入，無衝突
- Extensions 正常載入
- 模型設定符合你的需求

完成後，你的 Pi 就與本仓库配置一致。

## 📁 專案結構

- pi-config/
  - settings.json：Pi 基本設定（模型、套件等）
  - config.json：自訂 skills/agents 路徑
  - git/.gitignore：Git 忽略設定

- pi-skills/
  - 包含所有 Pi skills，例如：
    - 程式碼：test-driven-development、systematic-debugging
    - 規劃與文件：planning-with-files、writing-plans
    - 設計與 UI：design、ui-styling、ui-ux-pro-max
    - 理解與分析：understand 系列
  - 已修正命名衝突（移除 ckm: 前綴）

- pi-rules/
  - 開發規範與工作流程：
    - Git 工作流、程式碼風格、安全、效能、測試等

- pi-extensions/
  - 自訂 extensions，例如 planning-with-files 橋接

- scripts/
  - restore.sh：一鍵還原配置
  - restore-commands.md：手動還原步驟（若無法執行腳本）

## 🔄 換電腦流程（簡明版）

在新電腦上：

1. 安裝 Node.js、Git
2. 安裝 Pi：
   - npm install -g @mariozechner/pi-coding-agent
3. 克隆本專案：
   - git clone git@github.com:Chiakai-Chang/CKs_PI_Code_Agent_Harness.git
   - cd CKs_PI_Code_Agent_Harness
4. 若有使用本地模型，先編輯 pi-config/settings.json
5. 執行：
   - bash scripts/restore.sh
6. 更新並啟動：
   - pi update
   - pi

即可直接使用。

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

- 本 repo 的 config.json 中有部分路徑會參考本機目錄（例如 D:/MyProject/...）：
  - 還原腳本會自動替換部分佔位字串
  - 若你有用到額外外部路徑（如 everything-claude-code），
    請手動編輯 ~/.pi/agent/config.json 調整
- 若出現 skill 命名警告，確認已使用本 repo 最新配置並重新還原

## 🙏 授權

本專案使用 MIT 授權（可自由修改與使用）。
