# 🚀 Hermes Agent 完整整合指南

## 📋 系統概覽

本目錄包含針對 **Hermes Agent** 量身打造的增強功能集成方案，將 CK's Pi Code Agent Harness 的核心能力與 Hermes 的現有架構完美融合。

## ✅ 已部署的核心系統

### 1. 事件驅動配置系統
- **文件**: `~/.hermes/event_processor.py`
- **功能**: 統一的事件調度與優先級管理
- **監聽事件**:
  - `pre_tool_call` - 工具調用前檢查
  - `before_decision` - 決策前上下文注入
  - `session_end` - 會話結束學習提取
  - `post_tool_call` - 質量檢查

### 2. 安全閘系統 (ECC Hooks)
- **文件**: `~/.hermes/security_bridge.py`
- **功能**: 預防性安全檢查
- **檢查項目**:
  - 配置文件保護 (`.env`, `config.yml`)
  - Bash 命令安全 (`git --no-verify`)
  - 代碼質量門 (括號平衡)
  - 敏感路徑檢測

### 3. 任務規劃系統
- **文件**: `~/.hermes/plans/`
- **核心文件**:
  - `task_plan.md` - 階段性任務追蹤
  - `findings.md` - 研究發現記錄
  - `progress.md` - 會話進度日誌
- **自動化**: 每次決策前自動讀取計劃

### 4. 自我進化系統
- **功能**: 會話結束自動提取學習點
- **輸出**: 更新規範文件 (`CLAUDE.md`, `AGENTS.md`)
- **策略**: 從失敗中學習，避免重複錯誤

### 5. 自動更新機制
- **腳本**: `~/.hermes/auto_update.py`
- **頻率**: 每週自動檢查 (已配置 cron)
- **功能**: 
  - 主框架更新
  - 外部模組同步
  - 配置保留
  - 緩存清理

## 🎯 快速開始

### 第一步：驗證系統狀態

```bash
# 完整驗證
python ~/.hermes/verify_integration.py

# 快速檢查
python ~/.hermes/system_check.py
```

### 第二步：開始任務規劃

```bash
# 在專案目錄中
mkdir -p .hermes/plans
cp ~/.hermes/plans/task_plan.md .
cp ~/.hermes/plans/findings.md .
cp ~/.hermes/plans/progress.md .

# 開始編輯任務計劃
nano task_plan.md
```

### 第三步：測試安全閘

```bash
# 嘗試編輯敏感文件（應自動攔截）
nano .env

# 檢查 Bash 命令
git commit --no-verify
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

透過 `~/.hermes/config.yaml` 動態控制：

```yaml
# 安全閘系統
security_gates:
  enabled: true
  strict_mode: false
  config_protection: true
  prevent_bash_no_verify: true

# 任務規劃系統
planning_with_files:
  enabled: true
  auto_init: true

# 自我進化系統
self_evolution:
  enabled: true
  session_end_capture: true
```

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

## 🔄 自動更新

### 手動觸發

```bash
python ~/.hermes/auto_update.py --manual
```

### 自動排程 (已配置)

每週日清晨 3 點自動執行：
```bash
0 3 * * 0 python ~/.hermes/auto_update.py --manual
```

## 🐛 故障排除

### 常見問題

#### 1. 功能未生效

**檢查配置**:
```bash
cat ~/.hermes/config.yaml
```

**重新載入**:
```bash
source ~/.hermes/event_processor.py
```

#### 2. 更新失敗

**備份配置**:
```bash
cp ~/.hermes/config.yaml ~/.hermes/config_backup.yaml
```

**手動拉取**:
```bash
cd ~/.hermes/harness && git pull --recurse_submodules
```

#### 3. 權限問題

**確保腳本可執行**:
```bash
chmod +x ~/.hermes/*.sh
chmod +x ~/.hermes/*.py
```

## 📚 參考文檔

### 核心文件位置

| 文件 | 用途 |
|------|------|
| `~/.hermes/config.yaml` | 系統配置 |
| `~/.hermes/event_processor.py` | 事件驅動核心 |
| `~/.hermes/security_bridge.py` | 安全閘系統 |
| `~/.hermes/plans/task_plan.md` | 任務規劃模板 |
| `~/.hermes/auto_update.py` | 自動更新腳本 |

### 技能文檔

- **Heritage Harness**: `~/.hermes/skills/heritage-harness/SKILL.md`
- **管理技能**: `~/.hermes/skills/manage-heritage-harness/SKILL.md`

### 完整文檔

- **集成總結**: `~/.hermes/INTEGRATION_SUMMARY.md`
- **快速開始**: `~/.hermes/QUICK_START.md`

## 🎯 最佳實踐

### 1. 日常開發工作流

```bash
# 開始新任務前
1. 讀取 task_plan.md 確認目標
2. 檢查 progress.md 了解當前狀態
3. 在 findings.md 記錄新發現

# 每個主要階段
1. 更新 task_plan.md 的進度
2. 記錄關鍵決策到 findings.md
3. 標記已完成階段
```

### 2. 安全習慣

```bash
# 編輯配置前
- 系統自動檢查並給出提示
- 確認是否確實需要修改

# Bash 命令
- 避免不必要的 `git --no-verify`
- 使用系統提供的質量門
```

### 3. 持續學習

```bash
# 會話結束後
- 自動提取學習點並更新規範
- 檢查 findings.md 中的新發現
- 在 task_plan.md 中記錄改進建議
```

## 🚀 下一步建議

### 立即開始

1. **在專案中創建任務規劃**
   ```bash
   mkdir -p .hermes/plans
   cp ~/.hermes/plans/task_plan.md .
   # 開始編輯你的任務計劃
   ```

2. **測試安全閘系統**
   ```bash
   # 嘗試編輯一個敏感文件
   nano .env
   # 觀察系統提示
   ```

3. **啟用隱身瀏覽（可選）**
   ```bash
   # 啟動 Camofox（如果需要）
   cd ~/.hermes/camofox-browser && make up
   ```

### 深度定制

1. **自定義安全規則**
   - 編輯 `~/.hermes/security_bridge.py`
   - 添加特定的檢查邏輯

2. **擴展事件處理器**
   - 在 `~/.hermes/event_processor.py` 中添加新處理器
   - 註冊到 `self.event_handlers`

3. **調整更新策略**
   - 修改 `~/.hermes/auto_update.py` 的排程
   - 配置特定的更新源

---

**系統狀態**: ✅ **已完全整合並運行良好**  
**維護者**: Hermes Agent  
**版本**: 1.0.0 (Hermes 完整整合版)  
**許可證**: MIT