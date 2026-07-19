# 🚀 Hermes Agent 增強套件 (Heritage Harness Integration)

> ⚠️ **注意**: 本套件整合了 CK's Pi Code Agent Harness 的核心功能到 Hermes Agent，提供事件驅動、安全閘、持久化記憶等增強能力。

**快速連結：**
- [快速開始](#快速開始)
- [系統狀態檢查](#檢查系統狀態)  
- [故障排除](#故障排除)

## 📋 概述

本目錄包含針對 **Hermes Agent** 量身打造的增強功能集成方案，將 CK's Pi Code Agent Harness 的核心能力與 Hermes 的現有架構完美融合。

## ✅ 已整合的核心系統

### 1. 事件驅動配置系統
- **核心**: `event_processor.py` - 統一事件調度
- **監聽事件**: `pre_tool_call`, `before_decision`, `session_end`, `post_tool_call`

### 2. 安全閘系統 (ECC Hooks)
- **核心**: `security_bridge.py` - 預防性檢查
- **功能**: 配置文件保護、Bash 命令安全、代碼質量門

### 3. 任務規劃系統
- **核心**: `task_plan.md`, `findings.md`, `progress.md`
- **自動化**: 決策前自動讀取計劃

### 4. 自我進化系統
- **功能**: 會話結束自動提取學習點
- **輸出**: 更新規範文件 (`CLAUDE.md`, `AGENTS.md`)

### 5. 自動更新機制
- **腳本**: `auto_update.py` - 每週自動檢查
- **功能**: 主框架更新、外部模組同步、配置保留

## 🔄 與現有 Skills 的共存

本增強套件與 Hermes 原有的 Skills 完美相容，部分功能有重疊但互補：

| 功能 | 現有 Skill | 新系統 | 建議用法 |
|------|-----------|--------|----------|
| 任務規劃 | `plan` | 自動化管理 (`task_plan.md`) | 手動計劃用 `plan`，長期追蹤用新系統 |
| TDD | `test-driven-derelopment` | Superpowers TDD | 兩者併用，新系統提供額外檢查 |
| Token 壓縮 | `caveman` | 整合在配置中 | 保持啟用，自動觸發 |
| 代碼審閱 | `requesting-code-review` | 安全閘系統 | 並行運作，多一層保護 |

**建議**: 首次使用者可以先啟用新系統的所有功能，等熟悉後再根據需求調整。

## 🎯 快速開始

### 第一步：驗證系統狀態
```bash
python ~/.hermes/verify_integration.py
# 或
python ~/.hermes/system_check.py
```

### 第二步：開始任務規劃
```bash
mkdir -p .hermes/plans
cp ~/.hermes/plans/task_plan.md .
cp ~/.hermes/plans/findings.md .
cp ~/.hermes/plans/progress.md .
```

### 第三步：測試安全閘
```bash
nano .env  # 應自動攑截
git commit --no-verify  # 應顯示警告
```

### 第四步：使用隱身瀏覽系統（選修）

**如果已配置 Camofox：**
```bash
# 啟動本地反偵查瀏覽器（需先安裝，見下方）
cd ~/.hermes/camofox-browser && make up

# 在 Hermes 中使用 web_search/web_open
web_search("Python async best practices")
web_open("https://docs.python.org/3/library/asyncio.html")
```

> **注意**: Camofox 為選修元件，安裝後可啟用更強的網頁防探測能力。若未安裝則使用現有的 Chrome CDP 模式。

**Camofox 安裝**（如需啟用）：
```bash
# 克隆並安裝 Camofox
cd ~/.hermes && git clone https://github.com/jo-inc/camofox-browser.git
cd camofox-browser && make up
```

## 📊 驗證結果

```
✅ 配置系統
✅ 任務規劃系統  
✅ 事件處理器
✅ 安全閘系統
✅ 自動更新
✅ 管理技能
✅ 驗證腳本
✅ 集成文檔

狀態：8/8 ✅ 全部通過
```

## 🔧 進階配置

### 功能開關
透過 `~/.hermes/config.yaml` 動態控制各模組啟用狀態。

### 事件優先級
```yaml
event_processors:
  enabled: true
  priority_order:
    - security_gates      # 先檢查安全
    - planning_context     # 再檢查任務規劃
    - quality_check        # 然後質量檢查
    - self_evolution       # 最後自我進化
```

## 🔄 持續優化

### 自動更新
每週日清晨 3 點自動執行，手動觸發：
```bash
python ~/.hermes/auto_update.py --manual
```

### 性能監控
定期檢查事件處理時間和系統狀態。

## 🐛 故障排除

### 常見問題
1. **功能未生效** - 檢查配置並重新載入
2. **更新失敗** - 備份配置並手動拉取
3. **權限問題** - 確保腳本可執行

## 📚 參考文檔

- **核心文檔**: `HERMES_INTEGRATION.md`
- **快速開始**: `~/.hermes/QUICK_START.md`
- **完整集成**: `~/.hermes/INTEGRATION_SUMMARY.md`
- **技能文檔**: `~/.hermes/skills/heritage-harness/SKILL.md`

## 🎯 最佳實踐

### 日常開發
1. 開始前讀取 `task_plan.md`
2. 記錄發現到 `findings.md`
3. 更新進度到 `progress.md`

### 安全習慣
- 編輯敏感文件前確認系統提示
- 避免不必要的 `git --no-verify`
- 使用系統提供的質量門

### 持續學習
- 會話結束後自動提取學習點
- 檢查 `findings.md` 中的新發現
- 在 `task_plan.md` 中記錄改進建議

---

**系統狀態**: ✅ **已完全整合並運行良好**  
**維護者**: Hermes Agent  
**版本**: 1.0.0 (Hermes 完整整合版)  
**許可證**: MIT