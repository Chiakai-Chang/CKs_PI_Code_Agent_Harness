# 已知問題 (Known Issues)

記錄目前已知、且根因不在本專案可直接修復範圍內的問題。每項均附影響評估與處理方式。

## 1. 全域技能名稱重複導致的 `[Skill conflicts]` 警告（已修復）

**現象**：執行 `scripts/restore.py` 時出現大量 `Skill conflicts` 警告，提示全域目錄 (`~/.pi/agent/skills`) 與本地子模組存在相同名稱的技能（如 `design-taste-frontend`、`brainstorming` 等）。

**根因**：
- 本專案透過 Git Submodule 整合外部倉庫（taste-skill、superpowers、graphify 等）
- 使用者可能透過 `pi install <pkg>` 將相同名稱的技能安裝到全域目錄
- Pi Agent 啟動時在多個路徑 discovery 技能，重複名稱觸發警告

**影響**：
- **輕度**：技能仍能正常載入（優先使用 temp 路徑）
- **維護成本**：累積警告可能造成困擾
- **潛在風險**：版本錯位可能導致行為差異

**處理**：**已在本專案 `scripts/restore.py` 中自動修復**
- 新增 `PRUNE_GLOBAL_SKILLS` 清單，主動清理衝突全域目錄
- 每次執行 `restore.py --auto` 時自動清理重複技能（保留 SKILL.md）
- 詳見 [docs/decisions/2026-07-19-skill-conflicts-fix.md](docs/decisions/2026-07-19-skill-conflicts-fix.md)

## 2. Pi 啟動時的 `[Skill conflicts]` 名稱不符警告（僅舊版 pi；≥0.74.1 已消失）

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

## 4. stealth-recon 後端首次自動安裝（~300MB）

`camofox-stealth` 技能的後端 `@askjo/camofox-browser@1.11.2` **會自動安裝，不需手動架設**：`recon.sh` 以 `npx -y` 取得套件，camofox-browser 首次啟動時再自動下載 Camoufox（~300MB 到 `~/.camofox`，一次性，不含在 repo）。第一次啟動會顯示下載提示並延長等待逾時（預設 600 秒）；之後啟動為秒級。也可在 `setup.py` 完整安裝時選擇預先下載。最硬的 Akamai/Datadome 頂層可能仍需 residential proxy（本技能預設不掛 proxy，不在支援範圍）。
