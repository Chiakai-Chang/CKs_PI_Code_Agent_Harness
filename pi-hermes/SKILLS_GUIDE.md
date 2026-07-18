# 🎯 Hermes Agent 技能使用指南

## 📋 概覽

本指南說明如何最佳使用整合到 Hermes Agent 中的各項增強技能，確保發揮最大效能。

## ✅ 已部署的技能清單

### 🔐 核心安全與品質

#### 1. **事件處理器 (event_processor.py)**
- **功能**: 統一的事件調度與優先級管理
- **監聽事件**:
  - `pre_tool_call` - 工具調用前檢查
  - `before_decision` - 決策前上下文注入
  - `session_end` - 會話結束學習提取
  - `post_tool_call` - 質量檢查

#### 2. **安全閘系統 (security_bridge.py)**
- **功能**: 預防性安全檢查
- **檢查項目**:
  - 配置文件保護 (`.env`, `config.yml`)
  - Bash 命令安全 (`git --no-verify`)
  - 代碼質量門 (括號平衡)
  - 敏感路徑檢測

### 📝 任務與記憶

#### 3. **任務規劃系統**
- **核心文件**:
  - `task_plan.md` - 階段性任務追蹤
  - `findings.md` - 研究發現記錄
  - `progress.md` - 會話進度日誌
- **自動化**: 每次決策前自動讀取計劃

### 🧠 自我進化

#### 4. **自我進化系統**
- **功能**: 會話結束自動提取學習點
- **輸出**: 更新規範文件 (`CLAUDE.md`, `AGENTS.md`)
- **策略**: 從失敗中學習，避免重複錯誤

### 🔄 持續優化

#### 5. **自動更新機制**
- **腳本**: `~/.hermes/auto_update.py`
- **頻率**: 每週自動檢查
- **功能**: 主框架更新、外部模組同步、配置保留

## 🚀 使用策略

### 1. 事件驅動架構的最佳實踐

```bash
# 查看當前監聽的事件
python -c "from hermes.event_processor import event_processor; print(event_processor.event_handlers.keys())"

# 檢查啟用狀態
python -c "from hermes.event_processor import event_processor; print(event_processor.get_active_features())"
```

### 2. 安全閘檢查流程

**工具調用前 (pre_tool_call)**:
1. 配置文件保護檢查
2. Bash no-verify 檢查
3. 敏感路徑檢查
4. 代碼質量門

**工具調叫後 (post_tool_call)**:
1. 質量檢查
2. 變更日誌記錄

### 3. 任務規劃自動化

系統會在每次決策前自動讀取：
- `task_plan.md` - 任務目標和進度
- `findings.md` - 研究發現和決策
- `progress.md` - 會話進度記錄

## 📊 技能映射與整合

### 重疊技能處理

| Hermes 原有 Skill | 整合版本 | 建議 |
|-------------------|----------|------|
| `plan` | 任務規劃系統 | 使用 heritage 版本，功能更強大 |
| `test-driven-development` | Superpowers TDD | 整合進事件處理器 |
| `requesting-code-review` | 安全閘系統 | 作為質量門的一部分 |
| `systematic-debugging` | 事件處理器 | 在 `post_tool_call` 中執行 |
| `caveman` | Token 壓縮 | 已整合，保持啟用 |

### 避免衝突策略

1. **事件解耦**: 每個處理器獨立，不直接調用彼此
2. **可選啟用**: 透過配置控制哪些功能啟用
3. **優先級管理**: 高優先級檢查先執行
4. **後備機制**: 如果一個處理器失敗，其他仍可運作

## 🔄 持續優化流程

### 1. 監控系統狀態

```bash
# 定期檢查功能狀態
python ~/.hermes/verify_integration.py

# 查看啟用列表
python -c "from hermes.event_processor import event_processor; print(event_processor.get_active_features())"
```

### 2. 性能分析

```bash
# 記錄事件處理時間
cat ~/.hermes/logs/event_processor.log | grep "execution_time"
```

### 3. 故障排除

#### 常見問題

1. **功能未生效**
   ```bash
   # 檢查配置
   cat ~/.hermes/config.yaml
   
   # 重新載入事件處理器
   source ~/.hermes/event_processor.py
   ```

2. **衝突檢測**
   ```bash
   # 檢查重複的 skill
   python -c "from hermes.skills_list import skills; print([s['name'] for s in skills if 'plan' in s['name']])"
   ```

3. **性能問題**
   ```bash
   # 查看事件處理時間
   tail -n 100 ~/.hermes/logs/event_processor.log
   
   # 分析瓶頸
   python ~/.hermes/diagnostics.py --profile
   ```

## 🎯 最佳實踐清單

### ✅ 每日開發
- [ ] 開始前讀取 `task_plan.md`
- [ ] 檢查 `findings.md` 的新發現
- [ ] 更新 `progress.md` 的進度
- [ ] 留意安全閘的提示

### ✅ 每週優化
- [ ] 運行自動更新 (`auto_update.py`)
- [ ] 檢查系統狀態 (`verify_integration.py`)
- [ ] 清理舊的日誌檔案
- [ ] 回顧 `findings.md` 中的學習點

### ✅ 每月審查
- [ ] 評估功能開關設置
- [ ] 優化事件優先級
- [ ] 更新任務規劃模板
- [ ] 備份重要配置

## 📚 補充文檔

- **快速開始**: `~/.hermes/QUICK_START.md`
- **完整集成**: `~/.hermes/INTEGRATION_SUMMARY.md`
- **技能文檔**: `~/.hermes/skills/heritage-harness/SKILL.md`
- **管理技能**: `~/.hermes/skills/manage-heritage-harness/SKILL.md`

---

**維護者**: Hermes Agent  
**版本**: 1.0.0 (技能使用指南)  
**許可證**: MIT