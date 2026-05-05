# Contributing to CK's Pi Code Agent Harness

感謝你想貢獻！為保持清晰與可維護性，請依以下原則進行。

## 1. 貢獻範圍

本 repo 主要包含：
- pi-config/：Pi 設定與路徑配置
- pi-skills/：AI 技能（prompt、流程）
- pi-rules/：開發規範與工作流程
- pi-extensions/：自訂 extensions
- scripts/：安裝與還原腳本

## 2. 新增 Skill 規則

- 建立新目錄：pi-skills/<skill-name>/
- 放入 SKILL.md：
  - name 必須等於目錄名稱
  - 只能使用：小寫英文 a-z、數字 0-9、連字號 -
  - 不可包含 ckm: 或特殊字元
- 若使用外部授權內容，請：
  - 在該 skill 目錄或 NOTICE.md 中註明來源與授權

## 3. 修改腳本（setup.py / restore.sh / restore.py）

- 不得：
  - 收集設備或個人資訊
  - 呼叫未明確告知的外部服務
  - 隱藏行為或静默提權
- 變更需：
  - 維持跨平台可用
  - 在 PR 描述中列出影響範圍

## 4. 流程

- 建立分支
- 提交變更
- 發 Pull Request
- 描述：
  - 做了什麼
  - 為什麼要做
  - 影響哪些檔案

## 5. 已知 Pi 限制（開發者注意）

- TaskUpdate 狀態驗證問題：
  - 現象：TaskUpdate(status="completed") 驗證失敗，status 變成 "\"completed\""
  - 原因：Pi 核心與 @tintinweb/pi-tasks 的 schema / 序列化層存在 bug
  - 影響範圍：所有 Pi 用戶（非本 repo 專屬）
  - 建議做法：
    - 開發 / 測試時，若 TaskUpdate 不可靠，改用 /tasks 或文字清單
    - 避免將「TaskUpdate 一定成功」寫死在 skill 說明或自動化流程中
  - 上游修復後，本 repo 會同步更新相關指引
