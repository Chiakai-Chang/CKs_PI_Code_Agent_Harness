# 已知問題 (Known Issues)

記錄目前已知、且根因不在本專案可直接修復範圍內的問題。每項均附影響評估與處理方式。

## 1. Pi 啟動時的 `[Skill conflicts]` 名稱不符警告（僅舊版 pi；≥0.74.1 已消失）

**現象**：`pi` 0.73.x 及更舊版本啟動時列出多條 `name "X" does not match parent directory "Y"` 警告，來源為 `external/` 子模組（ECC、taste-skill、evolver、Local-Agent-Workspace、planning-with-files）。

**根因**：這些上游專案的 `SKILL.md` frontmatter `name` 與資料夾名稱不一致。Pi 舊版對此發出警告但照常載入。

**影響**：純視覺噪音。技能實際以 frontmatter 名稱正常載入。

**處理**：**執行 `pi update` 即可**——pi 0.74.1 起已移除此警告（pi-mono #4534）。已實測 0.80.3 啟動不再出現。

## 2. ECC `loop-design-check` 技能載入失敗（上游 YAML 錯誤）

**現象**：啟動警告 `Nested mappings are not allowed in compact mappings at line 2, column 14`，該技能未載入。

**根因**：上游 `affaan-m/ECC` 的 `skills/loop-design-check/SKILL.md` 中，`description:` 的值是未加引號的純量、內含 `: `（如 `Two actions: (1) WRITE`），為無效 YAML。上游 HEAD（截至 2026-07-08）仍存在此問題。

**影響**：僅此一個 ECC 技能無法使用，其餘 ECC 技能正常。

**處理**：`scripts/restore.py` 已改為逐一註冊 ECC 技能並跳過 `ECC_BROKEN_SKILLS` 清單中的損壞項目（不修改子模組內容），啟動時不再出現此錯誤。執行更新流程（README「更新與升級」）即生效。待上游修正 YAML 後（一行修正：description 值加引號），自 `ECC_BROKEN_SKILLS` 移除該項即可恢復載入。

## 3. npm 安裝時的 deprecated 警告

**現象**：安裝時出現 `@mariozechner/pi-* deprecated: please use @earendil-works/pi-*`。

**根因**：Pi 官方將 npm scope 從 `@mariozechner` 遷移至 `@earendil-works`；舊 scope 凍結在 0.73.1。

**處理**：本專案 `setup.py` 全新安裝已改用 `@earendil-works/pi-coding-agent`。既有安裝執行 `pi update` 即自動遷移（0.73.1 起的自我更新支援改名，會移除舊全域套件並安裝新套件）。
