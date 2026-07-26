# pi-until-done 學習後優化計畫

> 基於 `06-review-and-findings` 的適用性評估，聚焦高適用性 + 高/中緊急度項目。

## 工作清單

### A. Compaction 生存套件升級（高適用性 / 高緊急度）
**目標**：compact-continuation-bridge 的 compaction 策略從「重新注入指導」升級為 pi-until-done 式的 verbatim preservation 區塊。

- [ ] A1. 重構 compact-continuation-bridge：compaction annotation 改為標記 `preserve verbatim` 區塊，精簡保留關鍵信號（當前任務狀態、實測有證據原則摘要、最近進展），非完整指導副本
- [ ] A2. 在 RATIONALE.md 文件化 hook 選擇理由（為何用 session_compact 不用 session_before_compact）

**pi-until-done 借鑑點**：compaction-context.ts 的 survival kit 設計 — lossy compaction 只保留壓縮後最需要的信號。

### B. Verifiability Block 注入（高適用性 / 中緊急度）
**目標**：將 CLAUDE.md「實測有證據」原則轉化為 agent 執行時可見的紀律提醒。

- [ ] B1. 濃縮 CLAUDE.md §4 核心條文為 verifiability block（~4 行 HARD discipline 文字）
- [ ] B2. 透過 planning-with-files-bridge 的 before_agent_start hook 注入（僅在規劃任務 active 時附加到 system prompt，永不替換）

**pi-until-done 借鑑點**：verifiability.ts 的代理信號拒絕清單 + per-turn injection。

### C. Hook 使用紀律文件化（高適用性 / 中緊急度）
**目標**：bridge hook 使用有明確紀律與選擇理由，避免 ad hoc hook 註冊。

- [ ] C1. 新增 pi-rules/extension-hook-discipline.md：hook 組合原則（append never replace、uninvolved return undefined）、各 bridge 的 hook 選擇理由、已知陷阱（ctx.newSession 在 event handler deadlock）

**pi-until-done 借鑑點**：README Runtime Contract 五條規則 + nunorralves 文章的 API 限制警告。

### D. Bridge API import 來源統一與版本鎖定（高適用性 / 高緊急度）
**目標**：消除 bridge 分用兩套 Pi 套件的隱蔽分歧風險。

- [ ] D1. 確認 @mariozechner/pi-coding-agent vs @earendil-works/pi-coding-agent 的 ExtensionAPI 是否真分歧（查 npm 版本與型別定義）
- [ ] D2. 統一來源並加 peerDependency 版本鎖定，記錄於 bridge-manifest.json

## 不實作的項目（明確排除）

- Judge 系統、Ralph loop、Pi 工具註冊 — agent 擴充套件層職責
- Session-native state reducer replay — 當前 harness 無跨回合狀態需求
- pi-config operating contract 倉庫模式 — 規模不需

## 驗證策略

遵循 CLAUDE.md「實測有證據」：所有 hook 行為聲明需實際 Pi session 測試驗證；API 分歧確認需引用實際 npm 型別定義差異，不推測。
