# 🏗️ 軟體架構文件 (SAD) - Universal Harness v4.0

## 1. 架構概述
本架構採用 **「適配器模式 (Adapter Pattern)」**。核心邏輯 (Core Logic) 保持獨立，透過不同平台的適配器 (Bridges) 進行投影。

## 2. 目錄結構提案 (Refactored Directory Structure)

```text
CKs_PI_Code_Agent_Harness/
├── core/                   # 核心規則與技能 (平台無關)
│   ├── rules/              # 演算法、性能、安全規則
│   └── skills/             # 蒸餾後的 Markdown 技能檔案
├── bridges/                # 平台適配器
│   ├── gemini/             # 生成 .gemini/ 配置與 toml 指令
│   ├── claude/             # 生成 .claude/ 技能與 Agent 定義
│   └── codex/              # 生成 .codex/ 相關配置
├── external/               # 大師級資產 (Git Submodules)
├── scripts/                # 自動化核心
│   ├── detector.py         # 環境嗅探器 (Detects CLI platforms)
│   ├── generator.py        # 投影生成器 (Generates platform-specific manifests)
│   └── mapper.py           # 智慧路徑映射器
└── setup.py                # 單一入口
```

## 3. 關鍵技術決策 (Design Decisions)

### 3.1 指令映射 (Command Mapping)
*   **決策**：在 `core/` 下定義一份 `manifest.json`，描述每個指令對應的技能檔案路徑。
*   **實作**：`generator.py` 會讀取此 JSON，為 Gemini 產生 `.toml`，為 Claude 產生 `.claude/commands/` 下的 Markdown。

### 3.2 工具轉譯 (Tool Abstraction)
*   **決策**：在所有核心技能的 Prompt 中使用 **「中性工具名」**（如 `{{TOOL:READ}}`）。
*   **實作**：在投影至特定平台時，`generator.py` 會自動將變數替換為 `read_file` 或 `Read`。

## 4. 資料流 (Data Flow)
`setup.py` -> `detector.py` (獲取環境) -> `generator.py` (處理適配) -> `mapper.py` (建立 Symlinks) -> **萬能裝束就緒**。

---
**版本：Flagship v4.0-Draft**
