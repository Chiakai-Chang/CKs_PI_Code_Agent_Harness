# pi-until-done 學習復盤：核心收穫與適用性評估

> 綜合 `01` 至 `05` 的復盤。pi-until-done 的定位是「Pi 擴充套件」非 harness，但其將開發原則轉化為可執行機制的模式對本 harness 有高度啟發。

## 最高價值收穫（可直接改善本專案）

### 1. Compaction 生存套件設計（來源：compaction-context.ts）
pi-until-done 用 verbatim preservation 區塊 + session_compact hook 確保 lossy compaction 不丟失關鍵信號。我們的 compact-continuation-bridge 解決相同問題但策略粗糙 — 重新注入指導但無「哪些不可丟棄」的明確標記、無最近證據/學習的精簡保留。
**適用性：高** — 可直接引入 verbatim preservation 區塊概念到 compact-continuation-bridge。

### 2. Verifiability Block 注入（來源：verifiability.ts + before_agent_start hook）
pi-until-done 將 verifiability discipline 濃縮為 HARD 條文經 hook 每輪注入 system prompt。我們的 CLAUDE.md「實測有證據」是同等重要的原則但只在開發者指南中 — agent 執行時無此紀律提醒。
**適用性：高** — 可將核心條文濃縮為 verifiability block，透過 planning-with-files-bridge 的 before_agent_start hook 注入（僅在規劃/自治任務 active 時）。

### 3. Hook 使用紀律文件化（來源：README Runtime Contract）
pi-until-done 用五條規則明確定義 hook 組合紀律（append never replace、agent_settled owns continuation、uninvolved return undefined...）。我們的 bridge 用多個 hooks 但無此紀律文件。
**適用性：高** — 應在 pi-rules/ 或 extensions/ 層級文件化 hook 使用原則，含 hook 選擇理由。

### 4. Bridge API import 來源統一（來源：pi-until-done 的統一 @earendil-works/pi-* 依賴）
二次復盤已發現 bridge 分用兩套件（@mariozechner vs @earendil-works），pi-until-done 統一鎖定精確版本。
**適用性：高** — 需確認兩套件 API 是否真分歧，然後統一來源並加版本鎖定。

### 5. 有界執行與空轉保護概念（來源：agent_settled 狀態機）
compact-continuation-bridge 無 turn budget、spin guard、使用者插話暫停。pi-until-done 的完整狀態機不適用 harness 層，但「自治延續必須有停止條件」的原則通用。
**適用性：中** — 至少引入明確的停止條件與預算概念；完整 spin guard 需 Pi hook 支援（progress signal tracking）。

## 中長期概念借鑑

- **Session-native state with reducer replay**：harness 跨回合狀態（若未來需要）的參考模式
- **Judge 分離驗證原則**：完成聲明的驗證獨立於執行者 — 影響 harness 工具的設計哲學
- **Fail open with visible warning**：外部服務失敗時不靜默放行，適用所有 bridge
- **Operating contract 繼承**：CLAUDE.md 原則的分發模式參考

## 不適用的設計（明確排除）

- 完整 judge 系統、Ralph loop 實現、Pi 工具註冊 — 均為 agent 擴充套件層職責，harness 不實作 competing goal pursuit system
- pi-config operating contract 倉庫模式 — 當前 harness 規模不需跨專案合約繼承
- mise 自動化體系 — 與本專案開發流程無關

## 適用性總結

| 收穫 | 適用性 | 緊急度 | 實作難度 |
|---|---:|---:|---:|
| Compaction 生存套件設計 | 高 | 高 | 低 |
| Verifiability block 注入 | 高 | 中 | 低 |
| Hook 紀律文件化 | 高 | 中 | 低 |
| Bridge API import 統一 | 高 | 高 | 中 |
| 有界執行概念引入 | 中 | 低 | 中 |
| Session-native state / Judge 分離 / Fail open | 概念 | — | — |
