# 復盤：「回報了」不等於「收到了」（2026-08-04）

起點是使用者的一句話。他在另一個專案的 Pi session 裡看到這行提示：

```
💡 偵測到提交操作，但尚未建立 task_plan.md。建議使用 /plan 以強化任務追蹤。
```

然後問：**「好像有顯示但沒發揮作用，對嗎?」**

對。而且比「沒發揮作用」嚴重得多——那行字從來沒有到過模型面前，`/plan` 這個指令不存在，偵測邏輯還會對存在的計畫誤報。三層各自失效，而每一層背後都還有更大的同型問題。

最後查出 11 個缺陷。但這份文件要記的不是缺陷清單，是那個**貫穿兩邊的推理瑕疵**：

> **一個機制「回報了」，不代表接收方「收到了」。而我用來確認「收到了」的工具，可能回答的是另一個問題。**

橋接程式犯這個錯犯了很久。我在同一個 session 裡犯了三次。

---

## 一、harness 這邊：對著沒有人在聽的頻道講話

`ecc-hooks-bridge` 有七處、`planning-with-files-bridge` 有一處，把發現交給 `ctx.ui.notify`。它只畫終端機。

契約查已安裝的 `@earendil-works/pi-coding-agent@0.83.0`（**不是** `reference/oh-my-pi/`，理由見第二節）：

```ts
// dist/core/extensions/types.d.ts:778
export interface ToolCallEventResult { block?: boolean; reason?: string; }   // 沒有第二個出口

// dist/core/extensions/types.d.ts:876
on(event: "turn_end", handler: ExtensionHandler<TurnEndEvent>): void;        // 沒有回傳型別

// @earendil-works/pi-agent-core dist/types.d.ts:310
export interface AgentToolResult<T> {
  content: (TextContent | ImageContent)[];  // "returned to the model"
  details: T;                               // "for logs or UI rendering"
}
```

所以能送到模型的只有兩條路：`tool_result` 回 `{ content }`、`before_agent_start` 回 `{ systemPrompt }`。

最貴的兩個受害者：

* **`post:quality-gate`**——模型改壞了程式碼，檢查跑了、抓到了，結果送去終端機。模型繼續往那個壞掉的編輯上疊。
* **`stop:format-typecheck`**——同樣，而且它在 `turn_end`，那裡連回傳值都沒有。發現必須先入佇列，等下一個有通道的事件。

`planning-with-files-bridge` 的版本更幽微。它回傳 `{ details: { planningReminder } }`，而原始碼註解寫著：

```ts
// Non-intrusive: just log for model awareness via system prompt pattern
```

那是一句願望，不是機制。`details` 是給 log 跟 UI 的。這個提醒從上線到現在，沒有任何模型讀過。

---

## 二、我這邊：三次，工具回答的是另一個問題

### 第一次——讀了一份不在跑的契約

查 `BeforeAgentStartEventResult` 時我讀 `reference/oh-my-pi/`，看到只有 `message?`，於是判定 `planning-with-files-bridge:228` 回傳 `systemPrompt` 是缺陷。

改查已安裝的 0.83.0：

```ts
// dist/core/extensions/types.d.ts:800
export interface BeforeAgentStartEventResult {
    message?: Pick<CustomMessage, ...>;
    systemPrompt?: string;   // fork 裡沒有
}
```

那段程式碼是**對的**。`reference/oh-my-pi/` 是 gitignored 的 0.73 世代 fork 副本（`.gitignore:28`），不是 npm 全域裝的那個 Pi。差一步就把正確的程式碼報成缺陷。

### 第二次——單元測試綠著，功能沒送達

11 個測試通過，`advisory.ts` 的佇列、策略、預算、格式全部驗證過。實測一跑，session log 裡什麼都沒有。

原因：`appendAdvisory` 回傳的是 content **陣列**，而 handler 必須回傳 `{ content: 陣列 }`。Pi 收到型別不符的東西，靜默丟棄。

測試測的是 helper 本身，不是 helper 在 handler 裡被怎麼用。**測試綠 ≠ 送達。** 唯一抓到的是這個：

```
$ python - <session.jsonl>
=== toolResult content blocks: 2
---
[master 7c9c6f8] third commit
---
[ecc-hooks] advisory (not command output):
You are committing with no task_plan.md in this project. ...
```

而該次 session 的模型自己在結論裡寫：「(hooks 提醒這則 commit 沒有附 `task_plan.md`，這是單次一次性修改，直接帶過即可。)」——它讀到了，而且照建議裡「一次性改動就說明並繼續」做了。

### 第三次——量測工具不跟隨它要量的東西

我回報「`~/.pi/agent/skills/` 有 15 個 0 檔案的空目錄，restore 跑完仍是 15 個」，並據此寫了清理程式。

它們不是空目錄。它們是 **Windows junction**，指向 `~/.agents/skills/`：

```
st_reparse_tag: 0xa0000003    # IO_REPARSE_TAG_MOUNT_POINT
st_file_attributes: 0x410     # DIRECTORY | REPARSE_POINT
```

`find -type f` 和 `os.walk()` 預設都不跟隨 junction，所以整棵樹讀成 0 檔案。更糟的是 `os.path.islink()` 對 junction 回傳 **False**（它只認 IO_REPARSE_TAG_SYMLINK），所以任何用 `islink` 分支的 Python 都把 junction 當普通目錄。

我寫的 prune「清了 15 個」，實際只成功 1 個——整份撤回。

---

## 三、第三次的錯誤反而挖出最嚴重的缺陷

`delete_path` 的 docstring 寫著「Safely delete a file, directory, symlink or **junction**」。它刪不掉 junction，而且刪不掉時什麼都不說：

```python
shutil.rmtree(path, onexc=remove_readonly)   # CPython 拒絕 rmtree 一個 link
# 但 onexc 一旦提供，那個拒絕會被導向 handler 然後 return，不會 raise
# 於是底下那段註解寫著 "Fallback for junctions" 的程式碼，永遠不執行
```

後果不只是空殼：`~/.pi/agent/skills/` 每一個項目都是 junction，而 `planning-with-files` 在 `managed_skills` 清單裡——**任何一次 restore 都從來沒能把它換掉過。**

`clear_dir` 有兩份同構的複製，而且是更危險的形狀：它在決定要不要遞迴前檢查 `islink`，對 junction 為 False，於是會 `os.listdir` **穿透連結，把目標目錄的內容刪光**。測試證實目標端的 `keep.md` 真的被刪了。那些連結指向 `~/.agents/skills/`——別的工具的資料。

這條是**提交前讀 diff 才發現的**，前面所有測試都沒碰到。

---

## 四、什麼是驗證過的，什麼不是

誠實區分，避免這份文件本身犯同樣的錯：

**實測觀察過（session log 為證）**
* 無計畫 + `git commit` → tool result 2 個 content block，第二個是建議，模型讀了並回應。
* 計畫在 `.planning/plan-1/task_plan.md`（非根目錄，正是舊 root-only 檢查必誤報的佈局）→ 1 個 block，正確不觸發。

**只證明了機制，沒有觀察到端到端**
八個生產端裡，只有 `plan-missing` 一個被實際觸發過。`quality-gate`、`format-typecheck`、`console-warn`、`suggest-compact`、`gateguard`、`hello-reflect` 都依賴 ECC hook 腳本吐出 stderr，這次沒有製造那些條件。**佇列與送達路徑是共用的，但那六個的觸發條件本身未經田野驗證。**

**刻意弄壞驗證過會紅的守衛**
* parity 測試：退回 root-only → `plan_via_active_plan_pointer` 等 2 個佈局變紅。（第一次它只因 `plan.ts` 不存在而紅，那只證明 import 接上了，不證明它抓得到分歧。）
* `isGitCommit`：退回 `includes("git commit")` → 6 個誤判案例變紅。
* catalog freshness：移掉一個項目 → `1 failure(s) found`；把 catalog 移走 → `skipped`，0 failures（CI 全新 checkout 安全）。
* junction 刪除：修之前 `test_a_junction_is_actually_removed` 紅；`clear_dir` 穿透那條在修之前真的刪掉了目標檔案。

---

## 五、順帶查出的三處「無人守的重複」

這次一口氣出現三組同樣的問題——兩份邏輯做同一件事，沒人比對：

1. **兩個 bridge 對「有沒有計畫」的定義不同**。ecc 只看 repo 根目錄，pwf 的 `resolvePlanDir()` 還認 `.planning/.active_plan` 與 `.planning/<id>/task_plan.md`。→ 加了 parity 測試，兩邊分岔就紅。
2. **catalog 產物 vs 產生規則**。`restore.py` 會把不在 `skillTiers.core` 的本地 skill 降級進 catalog，但沒人檢查產物有沒有跟上。實測：18 個該進、0 個在裡面——`hello-reflect`、`thinking-frameworks`、`grilling-protocol`、`camofox-stealth` 全部無路可及，而 README 與 CORE_CONCEPTS 把它們寫成運作中的功能。→ `validate-config.py` 加了 freshness 檢查。
3. **`delete_path` 與 `clear_dir` 兩份同構程式碼**。→ 直接消除重複，`clear_dir` 委派給 `delete_path`。

第三種處理方式最好：**能消掉重複就消掉，消不掉才加守衛。**

還有一組沒動但要知道：`CLAUDE.md` 與 `pi-rules/AGENTS.md` §9 是同一套 Evidence 規則的兩份鏡像，且**已經有內容分岔**（AGENTS.md 有「不捏造不存在的東西」那條，CLAUDE.md 沒有）。這次兩邊都補了，但這對鏡像本身沒有守衛。

---

## 六、生命週期：拆完之後，誰在看著？

`advisories` 佇列建在 extension 的 default export 裡。Pi 每個 **process** 呼叫一次 default export，每個 **session** 觸發一次 `session_start`——所以 `/new` 之後同一個佇列還在，`once` 策略的建議在該 process 剩餘生命裡永遠不會再發，而上一個 session 的發現會被當成當前的交出去。

加了 `reset()` 掛在 `session_start`。這條是自審時想起 `lifecycle-tests-find-what-units-cannot` 那道疤才問出來的：**每次有東西被拆掉或替換，就問一次「現在誰在看著它？」**

---

## 七、未解

* `~/.pi/agent/skills/` 剩 15 個 junction 指向 `~/.agents/skills/`，不歸本 harness 管，正確地留著。其中 `brandkit`、`design-*` 等**目標端本身是空的**——那是建立它們的那個工具的問題。`agents-best-practices`（25 檔）與 `darwin-skill`（36 檔）是有內容的，透過 junction 正常運作。
* 因此 `~/.agents/skills/` 實際上是**第三個 skill 來源**。`docs/superpowers/specs/2026-07-21-skill-namespace-isolation-design.md` 明文寫「不掃描 `~/.agents/skills/`（YAGNI）」，但由於 `~/.pi/agent/skills/` 底下都是指過去的 junction，namespace guard 其實一直都在讀那邊的內容。決策的前提與現況不符，值得複查。
* 上述六個未經田野驗證的 advisory 生產端。

---

## 八、落地成規則

`CLAUDE.md` 與 `pi-rules/AGENTS.md` §9 同步新增：

* **Pi 跑的是安裝副本**：改完 `pi-extensions/` 或 `pi-skills/` 先跑 `python scripts/setup.py --mode restore`，否則量的是上一版。
* **單元測試綠了不等於送達**：bridge 注入給模型的東西，要在 `~/.pi/agent/sessions/**.jsonl` 裡找到那段文字才算數。
* **API 契約查已安裝的套件**，不查 `reference/oh-my-pi/`；並附上「只有兩條路到得了模型」的完整清單。

不寫進規則的（放記憶與本文即可）：Windows junction 的量測陷阱太窄，不值得佔用每輪注入的 prompt 預算。
