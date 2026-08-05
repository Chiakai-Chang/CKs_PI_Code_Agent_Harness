# Task-Shape Router Design（2026-08-05）

## 問題（實測，非推測）

Harness 主人的實際回報:請 Pi 做市場調查,它直接 `web_search` 十幾次然後給結論——而 Superpowers、planning-with-files、MECE-Autopilot、C.A.S.E. 都裝著。

量化(`scripts/measure-triggers.py`,本機模型,隔離 session、中性 cwd,repeats=3):

```
debug-methodology         2/3   67%
multi-step-methodology    0/3    0%
      run1 no methodology skill loaded (read: none)
      run2 no methodology skill loaded (read: none)
      run3 no methodology skill loaded (read: none)
```

## 不是什麼（先排除）

**不是可及性問題。** 倒出真實 system prompt(`PI_HARNESS_DUMP_PROMPT`)：39,980 chars ≈ 9,995 tok，`skillTiers.core` 的 **21 個方法論 skill 全部在裡面**，含 `<available_skills>` 與各自的 description，由 `skill-namespace-guard` 在 `resources_discover` 執行時註冊。

（查 `~/.pi/agent/settings.json` 與 `~/.pi/agent/skills/` 會得到「19/21 不存在」的錯誤結論——執行時註冊不落在那兩處。這個誤判在本次調查中真的發生過一次。）

**不是 catalog description 缺失。** 122 個目錄化 skill 確實只有 name+path，但方法論那 21 個不在其中。

## 是什麼

**description 的語域對不上請求的語域。**

`debug-methodology` 有 67%，因為請求字面上就落在 `systematic-debugging` 的描述領域（bug、測試失敗）。`multi-step-methodology` 是 0%，因為「做市場調查」撞不到任何描述——`brainstorming` 寫的是 *creating features, building components*，`planning-with-files` 寫的是 *complex multi-step task*。**這些描述是為軟體工作寫的，而使用者的真實任務有一大半是研究與分析。**

而那些 skill 位於 `external/superpowers` 等 submodule，**不能改**。

## 外部證據

| 來源 | 數據 | 對本設計的意義 |
|---|---|---|
| Vercel agent evals | skills 在 56% 案例中從未被叫用 | 觸發不可靠是普遍現象，不是本 harness 獨有 |
| [Routine, arXiv 2507.14447](https://arxiv.org/abs/2507.14447) | 多步工具呼叫正確率 GPT-4o 41.1%→96.3%；**Qwen3-14B 32.6%→83.3%** | 增益對小模型更大，而本 harness 正是跑小模型 |
| 同上 | 增益來自**餵給模型一份結構化 routine 腳本** | 關鍵：不是叫它自己從清單挑 |
| Plan Mode 實務 | 「harness state with enforced tooling」vs「asking the agent is **just a chat message**」 | 機制 > 勸說，與本 repo 三次實證一致 |
| 同上 | 跳過規劃 → 約 40% 任務要重做 | 成本面的理由 |
| Anthropic 官方 | description 就是觸發器 | 我們改不了 submodule 的 description，只能在自己這側補 |

## 設計

### 機制:形狀路由 + routine 投遞

**不是**在 session 開頭遞一張 122 項菜單。**是**在模型即將走捷徑的那一刻，給它一份具體腳本。

```
before_agent_start   →  判斷請求形狀，符合條件則「上膛」
first broad tool_call →  投遞 routine（走已驗證的 advisory 管線）
```

三個判斷條件同時成立才上膛：

1. **形狀是多步**——請求含多個可交付項（「競爭者、定價、哪些區隔沒被滿足」＝3 項）、或含研究/調查/比較/盤點類動詞
2. **沒有既存計畫**——沿用 `hasAnyPlan()`（本 session 已做過 parity 測試的那個）
3. **第一個動作是廣域工具**——`web_search` / `deep_research` / `bash`

### 投遞內容

一份具體腳本，點名可載入的 skill，並留下逃生口:

```
[harness] This request has 3 separate deliverables. Before searching, take one of two paths:

  A. If the scope is clear: load the `planning-with-files` skill, write task_plan.md
     with one phase per deliverable, then work one phase at a time and verify each
     before starting the next.
  B. If the scope is not clear: load the `brainstorming` skill and settle the open
     questions with the user first.

If this really is a single lookup, say so in one sentence and carry on.
```

三個設計理由:

* **點名 skill**——Routine 的核心是給腳本，不是給選單。
* **保留「說明理由後繼續」**——與 plan-missing advisory 同樣的形狀。硬擋在 `--print` 模式沒有人可以按確認。
* **每 session 一次**（`once` 策略）——重複投遞會變成壁紙。

### 位置

新 bridge `pi-extensions/task-shape-bridge/`，而非塞進既有 bridge。理由:職責獨立、可獨立開關、可獨立量測；且 `ecc-hooks-bridge` 已經是本 repo 最大的一個。

`tool_call` 多處理器的組合方式已查證（`runner.js:705`）:

```js
for (const handler of handlers) {
  const r = await handler(event, ctx);
  if (r) { result = r; if (r.block) return result; }   // 第一個 block 勝出並短路
}
```

共存安全。本 bridge 預設不 block，所以不會搶在 `yes-hooks-bridge` 的安全攔截之前。

### 開關

`enableTaskShapeRouter`，**預設 true**，fail-open。

與 `enableEccGateGuard`（預設 false、fail-closed）的差異是刻意的:GateGuard 會**擋**，這個只會**說**。一個從未跑過的攔截器不該預設硬擋；一個只加一段文字的提示可以預設開。

## 不做（連同理由）

* **不裝 `@bacnh85/pi-plan`**——功能完整且活躍（v0.9.2，2026-08-04），但它 hard-block bash 寫入，與 `yes-hooks-bridge` 職責重疊；OWASP AST10 點名 skill/plugin 執行層風險最高；v0.9.x 未達 1.0。**借它與官方範例的設計，不借相依。**
* **不做 HITL 硬閘**——`pi --print` 情境沒有人可以確認。
* **不改 submodule 的 skill description**——`external/*` 不歸我們，且 `yes-hooks-bridge` 本來就擋寫入。
* **不給 122 個 catalog 條目全加 description**——實算 +7,516 tok/turn。方法論那 21 個本來就有描述，加了也不解決語域問題。

## 驗收（DoD）

| 層級 | 判準 |
|---|---|
| 單元 | 形狀判斷的純函式測試，含**負向**案例:單一查詢不得上膛 |
| 守衛 | 刻意弄壞一次確認會紅 |
| 整合 | 不與既有 11 個 `tool_call` 攔截點衝突（全套測試綠） |
| **實測** | `measure-triggers.py --only multi-step-methodology --repeats 3`：**基線 0/3**，目標 ≥ 2/3 |
| 負向實測 | `single-lookup-stays-cheap` 不得退步 |

最後一列是這份設計成立與否的唯一判準。單元測試綠不算數——本 session 已經證明過兩次。
