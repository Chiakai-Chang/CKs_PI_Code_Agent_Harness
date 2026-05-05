# 🚀 CK's Pi Code Agent Harness

> 一鍵還原你的 Pi 開發環境 — 換電腦不手軟

CK's Pi Code Agent Harness 是一套可攜式 Pi（程式碼代理工具）環境配置，
讓你可以：

- 換電腦後快速重建一模一樣的 Pi 環境
- 套用統一的 skills、rules、extensions
- 搭配本地模型（如 Ollama / LM Studio）或雲端模型
- 不需手動調整一堆設定檔

特色：

- 一鍵還原：bash scripts/restore.sh
- 內建 skills：程式開發、UI/UX 設計、文件撰寫、除錯流程等
- 內建 rules：Git 工作流程、程式碼風格、安全規範、測試標準
- 支援本地模型：可指定 Ollama / 自架 API
- 不需要 pi-mono 原始碼

不需要 pi-mono 或任何原始碼，只要 Node.js + Git + Pi 即可。

## 📦 環境需求

- Node.js ≥ 18（推薦 LTS）
- Git
- Pi（透過 npm 安裝）

## 🧭 快速上手（一鍵啟動）

1. 安裝依賴

   - 安裝 Node.js：
     - https://nodejs.org
   - 安裝 Git：
     - https://git-scm.com
   - 安裝 Pi：
     - npm install -g @mariozechner/pi-coding-agent

2. 取得本專案

   - git clone git@github.com:Chiakai-Chang/CKs_PI_Code_Agent_Harness.git
   - cd CKs_PI_Code_Agent_Harness

3. （選填）設定本地模型位置

   如果你想搭配本地模型使用：

   - 開啟 pi-config/settings.json
   - 找到 defaultProvider / defaultModel，例如：

     - 使用 Ollama：
       - "defaultProvider": "ollama",
         "defaultModel": "llama3.1"

     - 或使用自架 API：
       - "defaultProvider": "custom-openai-compatible",
         "defaultModel": "your-model"

   若目前不想調整，也可以先保留預設值，之後在 Pi 內再修改。

4. 執行還原指令

   - bash scripts/restore.sh

   此指令會自動：
   - 建立 ~/.pi 相關目錄
   - 複製 config、skills、rules、extensions
   - 替換路徑佔位字串

5. 更新 Pi

   - pi update

6. 開啟 Pi 並確認

   - 執行 pi
   - 檢查：
     - Skills 有正常載入且無衝突
     - Extensions 有正常載入

完成後，你的 Pi 就與本仓库配置一致。

## 📁 專案結構

- pi-config/
  - settings.json：Pi 基本設定（模型、套件等）
  - config.json：自訂 skills/agents 路徑
  - git/.gitignore：Git 忽略設定

- pi-skills/
  - 包含所有 Pi skills，例如：
    - 程式碼相關：test-driven-development、systematic-debugging
    - 文件與規劃：planning-with-files、writing-plans
    - 設計與 UI：design、ui-styling、ui-ux-pro-max
    - 理解與分析：understand 系列
  - 已修正命名衝突（移除 ckm: 前綴）

- pi-rules/
  - 包含開發規範與工作流程：
    - Git 工作流、程式碼風格、安全、效能、測試等

- pi-extensions/
  - 自訂 extensions，例如 planning-with-files 橋接

- scripts/
  - restore.sh：一鍵還原指令
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

## ⚠️ 注意事項

- config.json 中有部分路徑會參考本機目錄（例如 D:/MyProject/...）：
  - 還原腳本會自動替換部分佔位字串
  - 若你有用到額外外部路徑（如 everything-claude-code），
    請手動編輯 ~/.pi/agent/config.json 調整
- 若出現 skill 命名警告，確認已使用本 repo 最新配置並重新還原

## 🙏 授權

本專案使用 MIT 授權（可自由修改與使用）。
