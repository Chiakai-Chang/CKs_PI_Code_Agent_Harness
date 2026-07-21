# 技能管理最佳實務

## 📋 目錄

1. [技能載入機制](#技能載入機制)
2. [全域與本地技能](#全域與本地技能)
3. [撞名處理](#撞名處理)
4. [維護最佳實務](#維護最佳實務)
5. [除錯指南](#除錯指南)

---

## 技能載入機制

### 多路徑 Discovery

Pi Agent 啟動時會在以下路徑 discovery 技能：

1. **本地子模組** (`external/`)
   - `external/superpowers/skills`、`external/taste-skill/skills`、`external/graphify` 等
2. **全域安裝** (`~/.pi/agent/skills/`)
   - 透過 `pi install <pkg>` 安裝的技能，或本專案 `restore.py` staged 的隔離副本
3. **Submodule 目錄**
   - `~/.pi/agent/git/github.com/obra/superpowers/skills`

### 兩種技能來源，兩種管理方式

- **`pi-skills/core/*`**（本專案自己 author 的技能）：`restore.py` 直接物理複製進 `~/.pi/agent/skills/`，用固定的 `managed_skills` 允許清單管理，安全、無撞名疑慮。
- **`external/*`**（submodule 帶進來的技能，名字是上游取的，泛用名如 `brainstorming`、`graphify`、`agents-best-practices`）：這批**不再**由 `restore.py` 直接寫進 `settings.json`。改由 `restore.py` 把路徑寫進 `pi-config/external-skills-manifest.json` 清單，交給 `pi-extensions/skill-namespace-guard` 這個 extension 在**每次 Pi 啟動**時即時決定要不要用、要不要隔離——見下方〈撞名處理〉。

---

## 全域與本地技能

### 全域技能 (Global Skills)

- **位置**: `~/.pi/agent/skills/`
- **安裝方式**: `pi install <pkg>`（使用者自己裝的）或 `skill-namespace-guard` staged 的 `harness-<name>` 隔離副本
- **特點**: 跨專案共享；使用者自訂為主

### 本地技能 (Local Skills)

- **位置**: `external/*/skills` 或 `pi-skills/*/`
- **管理方式**: Git Submodule（`external/*`）或直接複製（`pi-skills/core`）
- **特點**: 專案特定版本，透過 `restore.py` 自動維護

---

## 撞名處理

> ⚠️ 本節取代 2026-07-19 版的做法（`PRUNE_GLOBAL_SKILLS` 清單 + 強制清空同名全域目錄）。舊做法**不比對內容**，任何使用者自己裝的同名技能都會被無聲整個清空——這跟「harness 是基礎建設、使用者能自由安裝其他東西不受影響」的目標直接衝突，已於 2026-07-21 移除。歷史記錄見 [docs/decisions/2026-07-19-skill-conflicts-fix.md](../decisions/2026-07-19-skill-conflicts-fix.md)（**已被取代，不反映目前程式碼行為**）。

### 現行機制：`skill-namespace-guard`（即時、非破壞性）

每次 Pi 啟動（`resources_discover` 事件），對 manifest 裡每一個 `external/*` 技能：

1. **`~/.pi/agent/skills/<name>/` 不存在** → 沒撞名，直接用原始路徑，行為跟以前一樣。
2. **存在，內容比對後相同**（正規化換行、去頭尾空白後算 hash）→ 判定是同一套東西重複裝，**跳過**、不重複註冊，不動使用者那份，也不多佔 context。
3. **存在，內容不同**（純粹巧合撞名、使用者裝了不同功能但剛好同名的東西）→ 把 harness 這份物理複製、改名成 `harness-<name>`（改寫 frontmatter `name:`），兩份並存，**完全不動使用者原本的版本**。

不會刪除、不會清空任何使用者自己的技能內容——這是跟舊機制最根本的差異。

設計細節見 [docs/superpowers/specs/2026-07-21-skill-namespace-isolation-design.md](../superpowers/specs/2026-07-21-skill-namespace-isolation-design.md)，實作在 `pi-extensions/skill-namespace-guard/index.ts`。

### 為什麼不用清單、不用刪除？

- **內容比對比名單可靠**：靜態清單需要人工維護、會漏；內容 hash 比對自動判斷「是不是同一套東西」，不需要猜。
- **每次啟動都重新檢查，不是安裝當下判斷一次**：使用者隨時 `pi install` 新東西，下次開 Pi 就會被抓到，不會凍結在 harness 安裝當下的快照。
- **絕不刪除使用者內容**：隔離（改名雙存）而非清空，任何情況都不會讓使用者不明不白丟失自己裝的技能。

---

## 維護最佳實務

### 1. 定期執行 Restore

```bash
python scripts/restore.py --auto
```

**檢查清單**：
- [ ] `pi-config/external-skills-manifest.json` 有更新（`restore.py` 每次都會重寫）
- [ ] 所有預期技能已載入（`pi skills list`）

### 2. 新增 external/* 子模組

不需要手動維護撞名清單——`skill-namespace-guard` 在執行期自動判斷。只要在 `restore.py` 的 `profile_skills` 加入新子模組的路徑（走 `ext_root` 開頭的既有慣例），撞名偵測自動生效，不需要額外設定。

### 3. 測試驗證

```bash
# 1. 執行 restore
python scripts/restore.py --auto

# 2. 確認 manifest 已寫出
cat pi-config/external-skills-manifest.json

# 3. 驗證技能載入
pi skills list
```

---

## 除錯指南

### 常見問題

#### Q1: `[Skill conflicts]` 警告持續出現？

Pi 自己的 `[Skill conflicts]` 訊息是 Pi 核心對「同名保留先找到那個」規則的提示，`skill-namespace-guard` 是解決「先找到贏、使用者裝的永遠輸」這個根本問題，但不會讓 Pi 自己的提示訊息完全消失（隔離出的 `harness-<name>` 版本名字不同，不會再跟使用者版本撞名）。若警告持續出現在非 `external/*` 來源的技能上，那是另一個獨立問題，不在本機制處理範圍。

#### Q2: 想知道某個技能是不是被 `skill-namespace-guard` 隔離改名了？

```bash
ls ~/.pi/agent/skills/ | grep '^harness-'
```

看到 `harness-<name>` 就代表 `<name>` 這個技能名字曾經撞到你自己裝的、內容不同的東西，兩份都保留著，你自己那份完全沒被動過。

#### Q3: 全域目錄的技能沒有正常載入？

**原因**：本地子模組路徑錯誤、或 Submodule 未初始化。

**解法**：
```bash
git submodule status
git submodule update --init --recursive
python scripts/restore.py --auto
```

**不要手動用 `rm -rf` 清空 `~/.pi/agent/skills/` 底下的任何目錄**——若目錄是 `harness-<name>` 開頭，下次 `resources_discover` 會自動重建；若不是，那是你自己安裝的技能，手動刪除沒有任何自動復原機制。

---

## 📚 相關文件

- **核心腳本**: `scripts/restore.py`
- **即時撞名判斷**: `pi-extensions/skill-namespace-guard/index.ts`
- **設計文件**: [docs/superpowers/specs/2026-07-21-skill-namespace-isolation-design.md](../superpowers/specs/2026-07-21-skill-namespace-isolation-design.md)
- **已知問題**: [docs/KNOWN_ISSUES.md](../KNOWN_ISSUES.md)
- **舊機制歷史記錄（已取代）**: [docs/decisions/2026-07-19-skill-conflicts-fix.md](../decisions/2026-07-19-skill-conflicts-fix.md)

---

## 🎯 快速參考

| 操作 | 命令 | 說明 |
|------|------|------|
| 同步/更新 | `python scripts/restore.py --auto` | 同步 manifest，`skill-namespace-guard` 下次 Pi 啟動即時判斷撞名 |
| 檢查技能清單 | `pi skills list` | 列出已載入技能 |
| 檢查隔離副本 | `ls ~/.pi/agent/skills/ \| grep '^harness-'` | 看哪些技能名字撞過名、被隔離雙存 |
| 安裝全域技能 | `pi install <pkg>` | 手動安裝技能，撞名由 `skill-namespace-guard` 自動處理 |
| 初始化子模組 | `git submodule update --init --recursive` | 更新外部倉庫 |

---

**版本**: v2.0
**最後更新**: 2026-07-21
**維護者**: CK (Chiakai Chang)
