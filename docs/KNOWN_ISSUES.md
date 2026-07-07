# 已知問題 (Known Issues)

記錄目前已知、且根因不在本專案可直接修復範圍內的問題。每項均附影響評估與處理方式。

## 1. Pi 啟動時的 `[Skill conflicts]` 名稱不符警告（無害）

**現象**：`pi` 啟動時列出多條 `name "X" does not match parent directory "Y"` 警告，來源為 `external/` 子模組（ECC、taste-skill、evolver、Local-Agent-Workspace、planning-with-files）。

**根因**：這些上游專案的 `SKILL.md` frontmatter `name` 與資料夾名稱不一致，違反 [Agent Skills 標準](https://agentskills.io/specification)的命名規則。Pi 對此「警告但照常載入」（見 pi docs/skills.md Validation 一節）。

**影響**：純視覺噪音。技能實際以 frontmatter 名稱正常載入（可在 `[Skills]` 清單中確認）。

**處理**：不在本地修改子模組內容（違反 Submodule Respect 原則）。正確解法是向各上游回報／提交 PR 修正命名。若上游修正，執行更新流程（見 README「更新與升級」）即可消除。

## 2. ECC `loop-design-check` 技能載入失敗（上游 YAML 錯誤）

**現象**：啟動警告 `Nested mappings are not allowed in compact mappings at line 2, column 14`，該技能未載入。

**根因**：上游 `affaan-m/ECC` 的 `skills/loop-design-check/SKILL.md` 中，`description:` 的值是未加引號的純量、內含 `: `（如 `Two actions: (1) WRITE`），為無效 YAML。上游 HEAD（截至 2026-07-08）仍存在此問題。

**影響**：僅此一個 ECC 技能無法使用，其餘 ECC 技能正常。

**處理**：已確認升級子模組無法解決（上游未修）。待上游修正後透過子模組更新自然解決；亦可向上游回報（一行修正：description 值加引號）。

## 3. npm 安裝時的 deprecated 警告

**現象**：安裝時出現 `@mariozechner/pi-* deprecated: please use @earendil-works/pi-*`。

**根因**：Pi 官方將 npm scope 從 `@mariozechner` 遷移至 `@earendil-works`；舊 scope 凍結在 0.73.1。

**處理**：本專案 `setup.py` 全新安裝已改用 `@earendil-works/pi-coding-agent`。既有安裝執行 `pi update` 即自動遷移（0.73.1 起的自我更新支援改名，會移除舊全域套件並安裝新套件）。
