# 技能管理最佳實務

## 📋 目錄

1. [技能載入機制](#技能載入機制)
2. [全域與本地技能](#全域與本地技能)
3. [衝突處理](#衝突處理)
4. [維護最佳實務](#維護最佳實務)
5. [除錯指南](#除錯指南)

---

## 技能載入機制

### 多路徑 Discovery

Pi Agent 啟動時會在以下路徑依序 discovery 技能：

1. **本地子模組** (`external/`)
   - `D:\MyProject\CKs_PI_Code_Agent_Harness\external\taste-skill\skills`
   - `D:\MyProject\CKs_PI_Code_Agent_Harness\external\superpowers\skills`
   - `D:\MyProject\CKs_PI_Code_Agent_Harness\external\graphify\skills`

2. **全域安裝** (`~/.pi/agent/skills`)
   - 透過 `pi install <pkg>` 安裝的技能

3. **Submodule 目錄**
   - `~/.pi/agent/git/github.com/obra/superpowers/skills`
   - 其他 Git Submodule 路徑

### 載入優先順序

1. **Temp 路徑**（預先建立）：本專案管理的路徑
2. **全域目錄**：使用者手動安裝的技能
3. **Submodule**：Git Submodule 路徑

> ✅ **最佳實務**：本專案透過 `restore.py` 確保本地子模組優先載入，避免版本錯位。

---

## 全域與本地技能

### 全域技能 (Global Skills)

- **位置**: `~/.pi/agent/skills/`
- **安裝方式**: `pi install <pkg>`
- **特點**:
  - 跨專案共享
  - 使用者自訂為主
  - 易受手動更新影響

### 本地技能 (Local Skills)

- **位置**: `external/*/skills` 或 `pi-skills/*/`
- **管理方式**: Git Submodule + `restore.py`
- **特點**:
  - 專案特定版本
  - 透過腳本自動維護
  - 避免全域衝突

### 技能命名規則

**推薦格式**:
```yaml
# SKILL.md frontmatter
name: "domain-subdomain-skill-name"
```

**範例**:
- ✅ `design-taste-frontend` (正確：含領域 + 子域 + 名稱)
- ⚠️ `frontend` (可能重複)
- ❌ `frontend-design` (與 `design-taste-frontend` 衝突)

---

## 衝突處理

### 已知衝突清單

本專案在 `scripts/restore.py` 中維護以下衝突清單：

```python
PRUNE_GLOBAL_SKILLS = {
    # Taste-skill (external/taste-skill)
    "brandkit",
    "design-taste-frontend",
    "design-taste-frontend-v1",
    "full-output-enforcement",
    "gpt-taste",
    "high-end-visual-design",
    "image-to-code",
    "imagegen-frontend-mobile",
    "imagegen-frontend-web",
    "industrial-brutalist-ui",
    "minimalist-ui",
    "redesign-existing-projects",
    "stitch-design-taste",
    
    # Superpowers (external/superpowers)
    "brainstorming",
    "dispatching-parallel-agents",
    "executing-plans",
    "finishing-a-development-branch",
    "receiving-code-review",
    "requesting-code-review",
    "subagent-driven-development",
    "systematic-debugging",
    "test-driven-development",
    "using-git-worktrees",
    "using-superpowers",
    "verification-before-completion",
    "writing-plans",
    "writing-skills",
    
    # Graphify (pi-skills/graphify)
    "graphify",
    
    # Core skills (pi-skills/core)
    "hello-reflect",
    "planning-with-files",
}
```

### 清理機制

#### 1. **自動清理**
執行 `restore.py` 時自動執行：

```bash
python scripts/restore.py --auto
```

#### 2. **清理邏輯**
- 掃描全域技能目錄
- 比對 `PRUNE_GLOBAL_SKILLS` 清單
- 移除重複技能目錄（保留 `SKILL.md`）
- 記錄清理日誌

#### 3. **日誌輸出**
```
[RESTORE] Pruning conflicting global skill: design-taste-frontend
[RESTORE] Pruned 29 conflicting global skills.
```

### 為什麼保留 SKILL.md？

保留 `SKILL.md` 的原因：
- **追溯性**: 方便後續了解哪些技能曾被安裝
- **文檔留存**: 技能描述與使用方式保留
- **非執行檔案**: 純文檔，不影響載入邏輯

---

## 維護最佳實務

### 1. 定期執行 Restore

**頻率**: 每次專案更新或團隊協作前

**命令**:
```bash
python scripts/restore.py --auto
```

**檢查清單**:
- [ ] 無 `[Skill conflicts]` 警告
- [ ] 所有預期技能已載入
- [ ] 全域目錄無重複檔案

### 2. 手動清理步驟

如需手動清理（例如 `--auto` 失敗）：

#### Step 1: 檢查全域目錄
```bash
ls ~/.pi/agent/skills/
```

#### Step 2: 移除重複目錄
```bash
# 針對每個衝突名稱
rm -rf ~/.pi/agent/skills/design-taste-frontend/
```

#### Step 3: 保留文檔
```bash
# 只保留 SKILL.md
mv ~/.pi/agent/skills/design-taste-frontend/SKILL.md ./
rm -rf ~/.pi/agent/skills/design-taste-frontend/
```

### 3. 新增衝突技能

若發現新的衝突技能，需更新 `scripts/restore.py`：

```python
PRUNE_GLOBAL_SKILLS = {
    # 新增衝突名稱
    "new-skill-name",
    # ... 其他清單
}
```

### 4. 測試驗證

#### 乾淨狀態檢查
```bash
# 1. 執行 restore
python scripts/restore.py --auto

# 2. 檢查日誌
grep "Pruned" output.log

# 3. 驗證技能載入
pi skills list
```

---

## 除錯指南

### 常見問題

#### Q1: `[Skill conflicts]` 警告持續出現？

**原因**:
- `PRUNE_GLOBAL_SKILLS` 清單未包含新衝突
- 清理腳本執行失敗

**解法**:
1. 檢查日誌確認哪些技能仍在衝突
2. 新增到 `PRUNE_GLOBAL_SKILLS` 清單
3. 重新執行 `restore.py --auto`

#### Q2: 全域目錄清理後，技能未載入？

**原因**:
- 本地子模組路徑錯誤
- Submodule 未初始化

**解法**:
```bash
# 1. 檢查 Submodule
git submodule status

# 2. 重新初始化
git submodule update --init --recursive

# 3. 執行 restore
python scripts/restore.py --auto
```

#### Q3: 手動安裝的技能被清理後想恢復？

**方法**:
```bash
# 1. 從全域目錄移回
mv ~/.pi/agent/skills/design-taste-frontend ./backup/

# 2. 重新安裝
pi install design-taste-frontend

# 3. 手動移動至專案路徑（可选）
cp -r ~/backup/design-taste-frontend external/
```

### 進階除錯

#### 檢查技能載入順序
```bash
# 啟用詳細日誌
export PI_DEBUG=1
pi skills list
```

#### 手動清理全域目錄
```bash
# Windows (PowerShell)
Get-ChildItem ~/.pi/agent/skills | Where-Object {
    $_.Name -in @("design-taste-frontend", "brainstorming")
} | Remove-Item -Recurse -Force

# Linux/macOS
for skill in design-taste-frontend brainstorming; do
    rm -rf ~/.pi/agent/skills/$skill
done
```

---

## 📚 相關文件

- **核心腳本**: `scripts/restore.py`
- **衝突清單定義**: `scripts/restore.py#PRUNE_GLOBAL_SKILLS`
- **復盤文檔**: [docs/decisions/2026-07-19-skill-conflicts-fix.md](../decisions/2026-07-19-skill-conflicts-fix.md)
- **已知問題**: [docs/KNOWN_ISSUES.md](KNOWN_ISSUES.md)

---

## 🎯 快速參考

| 操作 | 命令 | 說明 |
|------|------|------|
| **預覽**修復 (Dry Run) | `python scripts/restore.py --dry-run` | 預覽將清理的檔案（不含實際執行） |
| 自動修復衝突 | `python scripts/restore.py --auto` | 清理全域重複技能 |
| 檢查技能清單 | `pi skills list` | 列出已載入技能 |
| 安裝全局技能 | `pi install <pkg>` | 手動安裝技能 |
| 初始化子模組 | `git submodule update --init --recursive` | 更新外部倉庫 |

### Dry Run 模式說明

執行 `--dry-run` 可在不實際修改任何檔案的情況下，預覽清理與還原的動作：

```bash
python scripts/restore.py --dry-run
```

**輸出範例**：
```
[RESTORE] Dry run: Would prune 29 conflicting global skills:
[RESTORE]   - design-taste-frontend (in ~/.pi/agent/skills)
[RESTORE]   - brainstorming (in ~/.pi/agent/skills)
[RESTORE]   ...
```

**優點**：
- ✅ 安全預覽：確認要清理的檔案再執行
- ✅ 除錯用：檢視腳本行為而不影響現狀
- ✅ 教育用：了解清理機制運作方式

---

**版本**: v1.0  
**最後更新**: 2026-07-19  
**維護者**: CK (Chiakai Chang)
