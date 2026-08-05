# Task-Shape Router Implementation Plan（2026-08-05）

設計見 [`../specs/2026-08-05-task-shape-router-design.md`](../specs/2026-08-05-task-shape-router-design.md)。

一句話:多步請求走到第一個廣域工具呼叫時，投遞一份具體的執行腳本，而不是在 session 開頭遞一張 122 項菜單。基線 `multi-step-methodology 0/3`。

## Constitution（不可違反的約束）

沿用本 repo `CLAUDE.md` 與 `pi-rules/AGENTS.md` §9，加上本次特有的:

* **不寫入 `external/*`**——submodule，`yes-hooks-bridge` 也會擋。
* **改完 bridge 必跑 `python scripts/setup.py --mode restore`** 才算測到新版。
* **送達要在 session JSONL 找到字串**才算數。
* **預設不 block**——只加文字，不改變模型可用的工具集。
* **數字一律下筆當下實跑。**

## 狀態機

每個 Task:`PENDING → IN_PROGRESS → REVIEW → DONE`，`REVIEW` 需通過該 Task 的驗收判準才可進 `DONE`。任一 Task 連續失敗 3 次 → `ESCALATED`，停下來問人。

## 雙軌驗證

* **Worker 軌**:單元測試（形狀判斷純函式）
* **Checker 軌**:live session log。兩軌都綠才算 `DONE`。

本 session 已經兩次出現「Worker 軌全綠、Checker 軌空白」（advisory 回傳裸陣列、ECC 欄位名不符），所以這條不是形式。

---

### Task 1 · `shape.ts` — 請求形狀判斷 `DONE`

純函式 `classifyRequest(prompt) -> { multiStep: boolean, deliverables: number, reason: string }`。

**正向**（應判為多步）
* 「competitors, how they price, and which segments are underserved」→ 3 項
* 「幫我調查 X 的市場、技術、UI/UX」→ 3 項
* 「compare A versus B on licensing, pricing and self-hosting」→ 3 項
* 研究/調查/盤點/比較類動詞 + 名詞清單

**負向**（不得判為多步——比正向更重要）
* 「What is the latest released version of Zig?」單一查詢
* 「fix this typo」
* 「read foo.ts and tell me what it does」
* 空字串 / 只有標點

判斷只用便宜的字面啟發式:可交付項計數（連接詞與逗號分隔的名詞片語）、研究類動詞、長度下限。**不呼叫模型**——這條路徑在每個 turn 的最前面，代價必須接近零。

**驗收**:負向案例全過；`classifyRequest("")` 不丟例外。

### Task 2 · `routine.ts` — 腳本產生 `DONE`

`buildRoutine(shape) -> string`。點名 `planning-with-files` 與 `brainstorming`，保留「說明理由後繼續」的出口，字數上限沿用 `DEFAULT_DRAIN_BUDGET` 的量級。

**驗收**:輸出含兩個 skill 名、含逃生口句、長度 < 700 chars。

### Task 3 · bridge 接線 `DONE`

`pi-extensions/task-shape-bridge/index.ts`

* `before_agent_start`:`classifyRequest(event.prompt)`，多步 && `!hasAnyPlan(ctx.cwd)` → 上膛
* `tool_call`:若已上膛且工具屬 `web_search` / `deep_research` / `bash` → 走 advisory 佇列投遞，解除上膛，**不 block**
* `tool_result`:drain（沿用 `advisoryResult`）
* `session_start`:重置（沿用本 session 學到的生命週期教訓）

`hasAnyPlan` 與 advisory 佇列從 `ecc-hooks-bridge` 複製而非跨 bridge 匯入——安裝後各 bridge 是獨立目錄，跨目錄匯入會斷。**複製 + parity 測試**，與 `plan.ts` 同樣的處理方式。

**驗收**:`verify-bridges.py` 綠（含本 session 新增的同層模組檢查）；全套測試綠。

### Task 4 · `enableTaskShapeRouter` 開關 `DONE`

預設 **true**、fail-open。與 `enableEccGateGuard`（false、fail-closed）的差異寫進 `_` 說明鍵。

**驗收**:通過 `test_no_zombie_harness_config_keys`；關閉時不投遞。

### Task 5 · 註冊與安裝 `DONE`

`bridge-manifest.json`、`package.json#pi.extensions`、`restore.py` 的 bridge 清單、`uninstall.py` 的 `MANAGED_BRIDGES`（有 `TestManagedBridgesConsistency` 鎖著，漏了會紅）。

**驗收**:`verify-bridges.py` 報 13 bridges、0 failures。

### Task 6 · Live 驗收 `DONE`

```bash
python scripts/setup.py --mode restore
python scripts/measure-triggers.py --only multi-step-methodology,single-lookup-stays-cheap \
    --repeats 3 --report docs/measurements/trigger-baseline.jsonl
```

* **主判準**:`multi-step-methodology` 從 **0/3** 升到 **≥ 2/3**
* **負向判準**:`single-lookup-stays-cheap` 不得退步
* 另需一次真實 session，在 JSONL 中找到投遞的 routine 文字

**達不到 2/3 就不算 DONE**——退回 Task 1/2 調整形狀判斷或腳本措辭，最多 3 輪，之後 `ESCALATED`。

### Task 7 · 知識資產 `DONE`

* `docs/retro/` 新增一篇:本輪的方法收穫（第四次「儀器回答了另一個問題」、外部數據對照、Routine 的小模型增益）
* `docs/measurements/trigger-baseline.jsonl` 保留前後對照
* `docs/KNOWN_ISSUES.md`:若 2/3 達不到，如實記錄殘餘缺口

## Self-Review Notes

* **Task 1 的負向案例比正向重要**。誤判成多步 → 每個單一查詢都被塞一段腳本，那就從「沒觸發」變成「到處觸發」，比現況更糟。
* **Task 6 是唯一真正的判準**。前五個 Task 全綠而 Task 6 停在 0/3 是完全可能的結果——那代表「投遞腳本」這個假設本身錯了，該回到設計而不是繼續調措辭。這種情況要誠實記錄，不要調參數硬湊到 2/3。
* **基線只有 3 次執行**。本機模型 temperature 0.6，3 次的解析度很粗。0/3 → 2/3 的差異夠大所以可用，但若結果落在 1/3 就不能宣稱有效，要加跑 repeats。


---

## 結果（2026-08-05）

```
                              基線    第一版    第二版
multi-step-methodology         0/3      0/3      3/3
single-lookup-stays-cheap       —       3/3      3/3
```

**第一版 0/3，且原因已查明**：腳本確實送達（session log 為證，出現在第一次
`web_search` 的 tool result），模型在 17 次工具呼叫裡完全無視。`ToolCallEventResult`
是 `{block, reason}`，tool_call 階段無法加文字只能擋——所以「動作當下建議」其實是
「動作之後建議」，模型已投入、資料已到手。

**第二版 3/3**，兩處改動：

1. **動作前也投遞**——`before_agent_start.systemPrompt`。這條路一直都在，是我在第一版
   宣稱「Pi 只給 block 一條路」時沒有去數。模型注意力呈 U 形、重要指令應出現在多處。
2. **`research-task-routing` 本地 skill**——description 涵蓋 market survey／競品分析／
   可行性等語域，補上 submodule skill 描述裡沒有的詞。必須列入 `skillTiers.core`，
   否則降級進 catalog 會丟掉 description。

`block + reason`（Task 說明中的 T2）**未實作，也不需要**。最重的手段留著沒用上。

Task 7 的知識資產見 `docs/retro/2026-08-05-the-note-arrived-after-the-decision.md`——
那一篇記的是第一版為什麼失敗，比這一版為什麼成功更值得留。
