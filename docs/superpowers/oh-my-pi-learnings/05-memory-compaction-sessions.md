# oh-my-pi 學習筆記：自主記憶、壓縮与会話樹

> 來源：`reference/oh-my-pi/docs/memory.md`、`docs/compaction.md`、`docs/session.md`、`docs/tree.md`

## 自主記憶（Autonomous Memory）

兩階段背景管道，會話啟動時運行：

- **Phase 1 提取**：對每個自上次處理後有變動的過去會話，模型讀取歷史並提取持久訊號（技術決策、約束、已解決的失敗、重複工作流）。有年齡/閒置/數量上限。
- **Phase 2 整合**：第二個模型回合讀取所有提取，產生三份寫入磁碟的輸出：
  - `MEMORY.md` — 策展的長期記憶文件
  - `memory_summary.md` — 開場注入的簡潔摘要（5000 token 上限）
  - `skills/` — 可重用的程序 playbook
- 整合使用租約和心跳防多重執行，輸出寫入前對常見 secret/token 模式做脫敏

記憶作為啟發性情境注入：優先信任當前 repo 狀態和使用者的指示，衝突時視記憶為過期。

## 壓縮策略（Compaction）

oh-my-pi 的壓縮不僅是摘要：

- **CompactionEntry**：一級會話條目，含 `firstKeptEntryId`（壓縮邊界）、`tokensBefore`、可選 `preserveData`
- **重建邏輯**：最新壓縮轉為一條 summary 訊息 → 從 `firstKeptEntryId` 到壓縮點的 kept entries 重新包含 → 後續條目附加
- **觸發條件**：手動 `/compact`、上下文溢位錯誤、`stopReason === "length"` 不完整輸出、超過閾值、閒置維護
- **Snapcompact**（實驗性）：將歷史歸檔為密集 bitmap 影像，極端壓縮

## 會話樹（Session Tree）

- 會話檔案為 JSONL，條目 append-only；分支導航移動 `leafId` 指標而非 mutate 現有條目
- `/tree` 命令開啟互動式樹選擇器，可跳到任何條目繼續
- 切換分支時可選產生 **BranchSummaryEntry** — 放棄的分支內容被摘要化保留

## 對本專案的啟發

### 直接可用
- **記憶注入品質**：oh-my-pi 的記憶注入有明確的「信任等級」指引（啟發性、非權威、衝突時以 repo 狀態為準）。我們的 `hello-reflect` skill 蒸餾自 claude-reflect，但缺少這種信任等級框架 — 可能導致 agent 過度信任陳舊記憶。
- **壓縮邊界保留**：oh-my-pi 的 `firstKeptEntryId` + kept entries 重新包含，確保關鍵決策上下文不會被壓縮丟失。我們的 `compact-continuation-bridge` 可借鑑此設計。
- **分支摘要**：Pi 支援會話分支，但我們缺少對「放棄分支」內容的保存機制。

### 概念借鑑
- **租約防多重執行**：記憶整合的租約/心跳模式，適合我們的 `setup.py` / `restore.py` — 避免多個終端同時執行還原時衝突。
- **脫敏寫入**：記憶輸出在寫入磁碟前脫敏 secret/token，這是我們 `pi-config/auth.json` 等敏感檔案管理應有的防護意識。

### 改善空間（oh-my-pi 自身）
- 記憶管道跳過 subagent 和未持久化的會話 — subagent 的決策可能同樣重要。
- snapcompact 將歷史轉為影像，模型無法直接檢索細節，是壓縮率與可用性的權衡。
