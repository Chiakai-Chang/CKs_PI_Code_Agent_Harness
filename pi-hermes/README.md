# 🚀 Hermes 增強框架集成指南

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