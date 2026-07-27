# 📘 知識資產：Agent 無限循環根因分析與防護指引 (Infinite Loop Prevention Guide)

> **版本**: v1.0.0  
> **建立日期**: 2026-07-27  
> **適用範圍**: CK's Pi Code Agent Harness 核心架構、Bridge Extensions 開發與安全護欄。

---

## 🎯 1. 背景與故障摘要

在 AI Agent（特別是具備自主多 Turn 驅動的 Coding Agent）長時間運行過程中，常見的一類極高風險崩潰為 **死循環（Infinite Loop）**。

在本次 Harness 健檢中，診斷出兩大相互耦合的深層缺陷：

1. **SystemPrompt 全域覆寫 (Context Wipeout)**：
   - 擴充套件（如 `taste-bridge`）在實作 `before_agent_start` 鉤子時，誤將傳入的 `event.systemPrompt` 直接替換為特定引導 Prompt。
   - **後果**：抹除了系統層級的 `AGENTS.md`、`CLAUDE.md` 及 native 工具結構說明，導致 LLM 在缺乏格式約束下輸出純文字標籤（如 `<bash>command</bash>`）。

2. **自回饋警告死循環 (Self-Reinforced Warning Loop)**：
   - 護欄套件（如 `yes-hooks-bridge`）在偵測到假工具標籤時發送警告，但警告訊息中含有未轉義的 `<invoke>`, `<bash>` 標籤。
   - **後果**：LLM 在下一 Turn 引述警告時再度觸發正則檢測，被誤判為連續違規；且 Strike 3 將違規次數歸零並繼續發送 `deliverAs: "nextTurn"`，形成 `1 -> 2 -> 3 -> 1` 的無限自驅動死循環。

---

## 🛡️ 2. 不可變三大開發鐵律 (Immutable Rules for Harness Extensions)

為徹底防範類似故障重演，所有本 Harness 內的 Extension Bridges 必須嚴格遵照以下鐵律：

### 📌 鐵律一：SystemPrompt 必須採不可變疊加 (Immutable Concatenation)
所有 `before_agent_start` 鉤子在回傳結果時，必須使用 `append` 模式：
```typescript
// ❌ 錯誤示範（會抹除全域規則與工具聲明）
return { systemPrompt: "[My-Extension] Custom instructions..." };

// ✅ 正確示範（保留上游 prompt 與工具宣告）
return {
  systemPrompt: (event.systemPrompt ?? "") + "\n\n[My-Extension] Custom instructions..."
};
```

### 📌 鐵律二：系統警告標籤必須實施轉義 (Tag Escaping Discipline)
在系統向 LLM 發送警告、Prompt 注入或錯誤提示時，**禁止直接出現 raw HTML/XML 工具標籤**（如 `<invoke>`, `<bash>`, `<read-file>`）。一律使用中括號或等效轉義符替換：
```typescript
// ❌ 錯誤示範（LLM 覆述時會再次觸發 FAKE_TOOL_CALL_PATTERN）
const warning = "Do not output raw <bash>command</bash> tags!";

// ✅ 正確示範（避免混淆正則比對）
const warning = "Do not output raw [bash]command[/bash] tags!";
```

### 📌 鐵律三：Strike 3 斷路器必須回歸人類控制權 (Human Circuit Breaker)
在達到最大違規或重試上限（如 Strike 3）時，**禁止清空次數後繼續發送 `deliverAs: "nextTurn"`**。必須使用 `deliverAs: "followUp"` 將控制權主動交還給人類使用者：
```typescript
// ❌ 錯誤示範（死循環驅動器）
this.strikeCount = 0;
return { sendMessage: { text: warning, deliverAs: "nextTurn" } };

// ✅ 正確示範（人類斷路器介入）
this.strikeCount = 0;
return { sendMessage: { text: warning + " Pausing for human guidance.", deliverAs: "followUp" } };
```

---

## 🧪 3. 測試與驗證規範 (Contract Testing Requirement)

1. **契約測試覆蓋**：任何新增或改動的 Bridge Extension，必須於 `tests/test_<bridge_name>.py` 中加入單元測試。
2. **斷言檢驗點**：
   - 驗證 `before_agent_start` 在傳入原始 `systemPrompt` 時，傳出結果精準包含 `(event.systemPrompt ?? "")` 前綴。
   - 驗證極限違規（Strike 3）當下 `deliverAs` 值為 `"followUp"` 而非 `"nextTurn"`。

---

*本知識資產已收錄於專案核心文檔庫 `docs/core/` 中。*
