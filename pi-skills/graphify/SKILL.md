---
name: graphify
description: "Use for analyzing codebase structure, AST relationships, module calls, or to query the codebase graph (specifically if graphify-out/ exists). Provides tools to build, update, and query the code graph."
---

# 🔍 AST 程式碼結構圖譜 (Graphify)

`graphify` 是一個使用 Tree-sitter 與 AST（抽象語法樹）分析程式碼調用關係、引用與導航的工具。它能為超大型程式庫建立語法圖譜，大幅節省 LLM 檢索程式碼時的 API Token 消耗。

## ⚙️ 核心指令

在終端機中，你可以透過以下方式執行 Graphify（將自動偵測並調用本地的 python/pip 依賴）：

```bash
# 在目前目錄下分析並建立代碼圖譜
python -m graphify

# 增量更新圖譜（僅重新提取變更的檔案）
python -m graphify . --update

# 使用自然語言查詢已建立的圖譜（BFS 寬度搜尋，節省 Token）
python -m graphify query "如何進行使用者驗證？"

# 尋找兩個模組／類別之間的最短調用路徑
python -m graphify path "AuthModule" "Database"

# 解釋特定的模組或節點
python -m graphify explain "SwinTransformer"
```

## 🧭 執行準則

1.  **優先使用既有圖譜**：每次收到關於 codebase 架構的問題（例如：「有哪些模組調用了 X？」、「追蹤 Y 的資料流向」），請先檢查 `graphify-out/graph.json` 是否存在。
2.  **查詢圖譜**：若圖譜已存在且不是重建請求，請直接使用 `python -m graphify query "<你的問題>"`。這能精確返回相關的 AST 調用關係，避免你用 `read_file` 盲目閱讀大量原始碼，節省 token。
3.  **增量更新**：如果程式碼發生了重大變更，請執行 `python -m graphify . --update` 保持圖譜最新。
4.  **零依賴保護**：若執行時提示缺少依賴，請引導使用者執行 `pip install graphifyy` 或 `uv tool install graphifyy` 進行安裝。
