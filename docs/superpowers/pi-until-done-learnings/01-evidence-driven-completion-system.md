# 收穫一：證據驅動完成系統 — 將「實測有證據」從口號變成可執行機制

> 來源：pi-until-done 的 judge 工具鏈與 verifiability discipline 注入。
> 對應本專案：CLAUDE.md「Evidence-Based Completion」章節目前只是開發者指南中的 prose guidance。

## pi-until-done 的設計

**核心機制**：LLM judge 把關完成聲明，執行者不能自己說服自己「完成了」。

### Judge 架構
- **分離執行與驗證**：judge 只看 goal + doneCriteria + verifyCommand + executor 引用的證據，不看執行過程。交叉模型審判為預設（executor 用模型 A，judge 用模型 B），防 Ralph loop 震盪。
- **嚴格 JSON 裁決**：judge 必須回傳 `{ "verdict": "done" | "continue", "reason": "..." }`；解析失敗（parse_error）或基礎設施不可用（unavailable）時**fail open with visible warning**，無使用者可見的「無 judge 旁路」。
- **證據累積審計軌跡**：每次 `until_done_complete` 的證據追加到 state.evidence 陣列，裁決註記也寫入 — 完整歷史可查。
- **拒絕完成的明確指導**：judge reject 時回傳 `refused()` 工具結果：「Judge rejected completion: {reason}. Address the gap and call until_done_complete again with stronger evidence.」

### Verifiability Block（每輪注入）
```
Verifiability discipline (HARD):
  • Do NOT accept proxy signals. "It compiled", "the test I added passes",
    "lint is clean" — none of these prove the goal is done. Only the
    verifyCommand passing counts.
  • Treat uncertainty as NOT ACHIEVED. If unsure, answer "not yet".
    Never call until_done_complete on vibes.
  • Quote command output as evidence — not a paraphrase, the bytes.
  • Cleanup before completing. Strip debug prints, scratch files, TODOs.
```
這段文字經 `before_agent_start` hook 附加到 system prompt，**每輪對話都出現**。

## 對應本專案的差距與改善空間

### 直接可用（高適用性）
1. **CLAUDE.md「實測有證據」原則的 verifiability block 版本**：我們有原則但無注入機制。可將 CLAUDE.md §4 的核心條文濃縮為一段 HARD discipline 文字，在 planning-with-files skill 的 session start 階段注入（透過 planning-with-files-bridge 的 `before_agent_start` hook），而非只靠開發者讀文件自覺遵守。
2. **Proxy signal 拒絕清單**：pi-until-done 明確列出「編譯成功、自己加的測試通過、lint 乾淨」不算完成證據 — 我們的 CLAUDE.md 有「Green on my machine is not proof」但無此具體清單。應補充到 skill 注入文字中。

### 概念借鑑（不直接移植但影響設計）
- **Judge 分離**：harness 層不適合實作完整 judge 系統（那是 pi-until-done 的職責），但可從其設計學到「完成聲明的驗證必須獨立於執行者」的原則，應用於 harness 自身工具的驗證策略。
- **Fail open with visible warning**：judge 基礎設施失敗時不靜默放行，而是產生可見警告證據行 — 此模式適用於 harness 任何依賴外部服務的 bridge（如 stealth-web-bridge 的 camofox server down 場景）。

## pi-until-done 的實作細節（供參考）
- Judge 呼叫透過 `ctx.modelRegistry` 直接呼叫 Pi 的 AI provider，不走 bash — 避免 shell 編碼問題
- `consultSelfJudge` 支援同模型 fresh-context judge（無第二模型時的妥協方案）
- `decideJudge` 在 complete 執行時決定用 cross-model 還是 self-judge，judge 選擇是 contract 一部分（northStar.judgeModel）
