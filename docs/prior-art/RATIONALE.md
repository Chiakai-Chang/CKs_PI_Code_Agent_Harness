# 研究決策紀錄 (Research Rationale)

記錄每次參考研究的來源、評估結果、與導入決策。

> **格式取自 [OmniHeal](https://github.com/Chiakai-Chang/OmniHeal) 的 `reference/RATIONALE.md`。**
> 那份文件用 14 個來源證明了一件事:**「放棄項目」欄比「採用項目」欄更值錢** ——
> 沒有寫下來的否決,會被下一個人原封不動重做一次。本專案 2026-08-06 就付了這個代價
> (見下方 pi-until-done 條目)。
>
> 索引與強制檢查在 [REGISTER.md](REGISTER.md);**這份是逐次研究的正文**。
> 一個來源在 REGISTER 標為「已審視」的前提,是這裡有它的條目。

---

## 2026-08-06 — srinitude/pi-until-done(**重讀,非首次**)

**來源**:https://github.com/srinitude/pi-until-done(`reference/pi-until-done`)
**研究目的**:本專案的佇列推進器連續三次量測都以 ESCALATED 收場,重讀其續跑迴圈的實作,
確認是參數問題還是地基問題。
**完整對照**:[2026-08-06-pi-until-done-loop-reference.md](2026-08-06-pi-until-done-loop-reference.md)

### 核心發現

**四項都是地基,不是參數。** 逐行讀 `extensions/lib/`(非讀我們自己的摘要):

1. 續跑掛 **`agent_settled`**(`hooks/agent.ts:62`),`turn_end` 只用來記最後一段文字。
2. 停滯的判準是**這一輪做了什麼**:`tool_call` 加權計分(edit/write 3、bash 2、
   read/grep/find/ls 1、其他工具 2),`=== 0` 才算空轉(`hooks/tools.ts:65`)。
3. 自動化放棄時**只把自己設成 `paused` / `blocked`**(`hooks/agent-end-helpers.ts:13`),
   **從不去動被執行任務的狀態**。
4. 續跑用 `sendUserMessage(..., { deliverAs: "followUp" })`,**沒有** `triggerTurn`。

### 採用項目(待移植,列為 `Task_015_advancer_settled_loop`)

| # | 移植什麼 | 取代本專案的什麼 |
|---|---|---|
| 1 | 續跑改掛 `agent_settled` | `turn_end` 每輪注入 —— 實測「正常進行中的步驟被判停滯」的直接成因 |
| 2 | 加權 progress signal,`=== 0` 才算停滯 | 數注入次數(數的是「我說了幾次」而非「你做了什麼」) |
| 3 | **自動化放棄 = 暫停自己,不寫 `status.txt`** | 要求模型寫 `ESCALATED` —— 五次 run 三次 ESCALATED,至少兩次是我們自己造的假失敗 |
| 4 | 終端步驟不計時 | 「交還使用者核可」這個設計上不會再變的狀態被判成卡住 |

### 放棄項目

| 項目 | 放棄原因 |
|------|---------|
| 直接安裝 `pi-until-done` | 它鎖 Pi `0.81.1`,本機是 `0.83.0`;lockstep 設計,不可跨版 |
| turn budget 的對話框確認 | 本專案量測以 `--print` 為主,無 UI 可確認 |
| YAML 狀態檔與 widget UI | TUI 專屬,模型收不到(本專案已知:只有兩個通道到得了模型) |
| `mise` 綁定的驗證指令路由 | 本專案不使用 mise |

### 被推翻的舊決定

`docs/superpowers/pi-until-done-learnings/07-optimization-plan.md` 曾把
**「Judge 系統、Ralph loop」列為不實作 —— 擴充層職責**。

2026-08-06 的 Task_001/008 做了 Ralph loop,Task_010/011 做了一個以詞表與結構規則
判斷「回覆是否謊報完成」的 `blocked-claim` —— **那就是一個很弱的 judge**。
**那條排除事實上已被推翻,只是沒有人寫下來。** 現重新列為待決事項。

---

## 2026-08-06 — Chiakai-Chang/OmniHeal

**來源**:https://github.com/Chiakai-Chang/OmniHeal(`research/OmniHeal`)
**研究目的**:它是擁有者自己的專案,且以 14 個 repo 的蒸餾為設計基礎 ——
評估其研究紀錄方法與可轉用的機制。

### 核心發現

**`reference/RATIONALE.md` 886 行,14 個來源,每個都有「採用項目」與「放棄項目 + 原因」。**
本專案缺的正是這個:13 個 research clone 蒸餾成 13 個技能,而 9 個來源在
`docs/` 與 `pi-skills/` 裡出現 0 次,技能檔也不寫來源。

**它解決的是同一個問題,而且早就解決了。**

### 採用項目

**1. RATIONALE 格式本身** → 就是本檔。日期 / 來源 / 研究目的 / 核心發現 / 採用 / 放棄。
**2. 「放棄項目」為必填欄** → 已寫進 `REGISTER.md` 的使用說明與 `CLAUDE.md` 的 Prior Art First。
**3. Task Queue 的恢復點定義**(恢復點 = queue 第一個未完成任務,**不依賴 Agent 記憶力**)
→ 與 C.A.S.E. 的佇列一致,可作為 `Task_015` 的設計佐證:狀態在檔案裡,不在迴圈裡。
**4. 3-Strike Protocol 的分層**(第 1 次換方式、第 2 次再換、第 3 次記錄永久跳過並繼續)
→ 本專案的守衛退場是「擋滿 3 次就讓路」,**沒有「換一種方式」這一層**,值得補。

### 放棄項目

| 項目 | 放棄原因 |
|------|---------|
| 零安裝 / 純 stdlib 的硬約束 | 本專案是 Pi extension harness,本來就依賴 Pi 與 Node |
| `skill_code_lint` / `log_parse` / `text_align` 三個技能 | 領域不同(專案健檢 vs agent 行為約束) |
| SWOT+TOWS 產出 `action_plan.md` | 本專案已有 `docs/mece/rounds/` 等效流程 |
| Phase 0/1/1.5 的掃描階段模型 | 本專案的工作單位是任務包,不是掃描 |

### 附帶價值

OmniHeal 的 14 個來源中,**有 5 個與本專案重疊**(planning-with-files、llm-wiki-plugin、
ECC、evolver、yes.md、karpathy-skills)。它們的「放棄理由」多半來自 OmniHeal 的零安裝約束,
不直接適用於本專案 —— 但**它已經替我們讀過一遍**,再讀時可以從它的核心發現開始,而不是從零。

---

## 2026-08-06 — romiluz13/auto-pi

**來源**:https://github.com/romiluz13/auto-pi(`research/auto-pi`)
**研究目的**:它是 `workflow-os-guide` 的蒸餾來源,而本專案卡在「模型不先規劃就開始動手」。
先讀它怎麼做階段門控,再決定 Task_015 的設計。

### 核心發現

**它把「先規劃」變成模型做不到別的事,而不是變成一段建議。**

`extensions/loop.ts:1020` 的 phase tool gate 在 **`tool_call`** 上依當前階段擋工具:

```
PLAN   階段:唯讀 —— 不准 write/edit,不准會改東西的 bash
VERIFY 階段:read/bash/lsp only —— 驗證者不准自己改東西
```

擋阻理由直接寫「tool "X" is not in the phase allowlist」。

`extensions/workflow-gate-logic.ts` 另一層:**把操作綁在技能上**。

| 操作 | 必須已載入的技能 |
|---|---|
| commit | `verification-before-completion` |
| push | `commit` |
| 寫入**原始碼**檔(測試檔不算) | `tdd` |
| review | `code-review` |

技能沒載入 → 操作被擋。**這是「技能裝了卻從來沒被觸發」的直接解法** ——
不是提醒模型用技能,是讓不用技能就做不了那件事。

第三層 `loop.ts:1339` 的 **RED guard**:輸出裡出現 `RED` / 測試失敗 / 非 0 exit 就
**不算完成**,回送一段補救提示(「A failing test is never completion」),
並有上限(`maxIterations`);另有 plateau 偵測。

### 採用項目

| # | 採用什麼 | 對應本專案的什麼 |
|---|---|---|
| 1 | **階段工具白名單,在 `tool_call` 擋** | 本專案 Task_008 的判定寫著「推進器在 `turn_end` 追不上第一輪就搜完的行為,只有 `tool_call` 擋得到」—— auto-pi 就是那個實作 |
| 2 | **操作綁技能**(沒載入就擋) | 直接對應擁有者的原始抱怨:Superpowers / C.A.S.E. / MECE 裝著沒被用 |
| 3 | RED guard:失敗輸出不算完成,回送補救提示並設上限 | 本專案的 `blocked-claim` 只看「回覆有沒有謊報」,不看**工具輸出裡的失敗證據** |
| 4 | 純邏輯與 runtime 分離(`workflow-gate-logic.ts` vs `workflow-gate.ts`) | 本專案已部分如此(`bash-containment.ts`),值得成為慣例 |

### 放棄項目

| 項目 | 放棄原因 |
|------|---------|
| 整套安裝(`install.sh`、`mise`、`jq`、`gh` 依賴) | 本專案自有 `setup.py` 部署鏈,且不引入 mise |
| 六個預設 workflow 與 slash palette | 領域不同;本專案的工作單位是 C.A.S.E. 任務包 |
| `loop.ts` 單檔 1557 行的形狀 | 本專案的守衛以小模組 + 平權測試為慣例,不採此規模 |
| 全自主模式 | 本專案明確要求人類核可(C.A.S.E. §1 雙軌驗證) |

### 這一則改變了工作順序

**階段門控比推進器更直接命中擁有者的抱怨。** 推進器在事後推,階段門控在事前擋;
而本專案自己的量測已經證明「事後推」追不上。因此新增
`Task_016_phase_tool_gate`,與 `Task_015` 並列,並排在它前面。

---

## 2026-08-06 — Forward-Future/loopy

**來源**:https://github.com/Forward-Future/loopy(`external/loopy`,submodule)
**研究目的**:確認它是否有可移植的迴圈控制機制(與 Task_015 同題)。

### 核心發現

**它不是程式,是一個技能 + 一個線上 loop 目錄。** 可移植的是一句定義:

> Treat a loop as a feedback system with **terminal states**, not as permission
> for endless autonomy.

以及它的 loop 審計面向:**弱檢查(weak checks)** 與 **不安全的授權(unsafe authority)**。

### 採用項目

**1. 終端狀態是迴圈定義的一部分,不是例外。**
本專案的推進器沒有終端狀態的概念,於是「交還使用者核可」這個**正確且穩定**的狀態
被計時器判成卡住並升級 —— Task_008 逐字重現過。已列入 Task_015 的移植項第 4 條,
並已作為回饋送往 C.A.S.E. 上游(要求協定標明哪些狀態是 terminal)。

**2. 「弱檢查」是一個可審計的類別。**
本專案有現成的實例:`blocked-claim` 曾經有 12 條綠測試而**在真實 session 裡從未響過**。
值得把「這個守衛真的響過嗎」做成定期審計,而不是等下一次疤。

### 放棄項目

| 項目 | 放棄原因 |
|------|---------|
| Loop Library 網站與 catalog | 外部服務,本專案離線優先 |
| 把 loop 發佈到公開目錄的流程 | 不適用 |
| Loopy 的 discover/craft 互動流程 | 與本專案的 MECE-Autopilot + brainstorming 重疊 |

---

## 待辦:尚未寫入本檔的來源

`scripts/check-prior-art.py` 在寫入當下回報 **23 個未審視**。優先序依「壓在當前卡點上」排:

| 優先 | 來源 | 壓在哪個卡點 |
|---|---|---|
| ~~1~~ ✅ | ~~auto-pi~~ | 已完成 —— 直接改變了工作順序,見上 |
| ~~2~~ ✅ | ~~loopy~~ | 已完成 |
| 3 | agentic-harness.pi | `detect → parse → review` 生命週期合約 —— 對應守衛的通道選擇 |
| 4 | harness-engineering | grilling 一問一答門控 —— 對應「不先釐清就動手」 |
| 5 | pi-browser-harness | 研究型 session 的實作(本專案最痛的場景) |
| 6 | pi-superagents / pi-tool-repair-layer / 其餘 | 依需要 |

## 2026-08-08 — prime-agent(Prime Intellect)

**來源**:`research/prime-agent`(shallow,592 MB)· https://github.com/PrimeIntellect-ai/prime-agent
**研究目的**:擁有者指出它也是基於 Pi 的研究型 harness,問能否強化本專案。

**核心發現**:**它不是 Pi 的擴充,是 pi-mono 的 fork**(自帶 `packages/coding-agent`,
釘 `pi-coding-agent ^0.7.1`,我們跑 0.83)。所以問題不是「能不能裝」,是「哪些設計可以移植」。

**採用項目(待移植,尚未動工)**
* **local / global 分域,預設 local** —— 直接對應我們「量測時全域旗標會騷擾其他專案」的已知問題。
* **refinement 事件 append-only + `rollbackOf` 回滾**;`refinement.ts:396` 的韌性做法可直接抄。
* **supplemental-only 提示層,base 由 `validateEdit()` 真的擋下**(`refinement.ts:672`)。

**放棄項目**
* 整套 RLM / 常駐 IPython runtime —— 換執行模型,不是加功能。
* 換底座到它的 fork —— `reference/oh-my-pi` 的疤:對著舊型別找缺陷會找到不存在的問題。
* daemon / agent 互傳 / autonomous mode —— 迴圈都還沒關好,先加自主性只會放大問題。
* **它的「evidence-backed」** —— `evidence: proposal.rationale`(`:787`),值就是模型自己寫的理由,
  沒有核對。名字叫 evidence,行為是 opinion。移植時證據必須綁真實產物,這是我們該做得比它嚴的地方。

**完整記錄**:[2026-08-08-prime-agent-review.md](2026-08-08-prime-agent-review.md)

## 2026-08-09 — metaharness(`ruvnet/agent-harness-generator` ADR 集)

**來源**:`research/metaharness`(1.9 GB,223 個 ADR)
**研究目的**:第一層未審視來源的第一個;同時查證我先前對它 ADR-010 的引用。

**核心發現**:**我的引用高估了一級。** ADR-010 的狀態是 `Proposed` 而非 `Accepted`;
引文逐字正確、反轉條件確實存在,但那是提案不是決定。
223 個 ADR 裡 `Accepted` 系列僅約 42 個 —— **「這個 repo 說過 X」在這裡不是安全的話。**

**採用項目**
* **量測噪音底線再解讀差異**(ADR-138,`Accepted (measured)`):`n ≳ (sd/(Δ/2))²`。
  **直接指出我的方法缺口** —— 我用 n=2 對二元結果下判定,從未量過本機模型的 run 間變異。
  已排進 roadmap 成為所有條件比較的前置。
* **狀態詞彙區分 `Accepted` 與 `Accepted (measured)`**:我們的 `docs/case/` 沒有欄位說明
  「這個決定有沒有證據」,只能靠讀者追連結。低成本高價值。

**放棄項目**
* Darwin Mode 整套演化機制(ADR-093~152)—— 遺傳演算法、SWE-bench 語料、模型路由:
  規模與目的都與我們不同(單機、單模型、一個真實使用者的日常流程)。
* 223 個 ADR 的文件密度 —— 我們的 roadmap 一天漂一次,再加一層編號文件只會讓沒人讀的東西變多。
* 三環測試分層(ADR-010)—— 已有實測驅動的等價物。

**完整記錄**:[2026-08-09-metaharness-review.md](2026-08-09-metaharness-review.md)

## 2026-08-09 — 被引用卻未審視的兩個來源

**起因**:審視 `metaharness` 時先查自己的引用,發現把 `Proposed` 的 ADR 當成決定。
於是問「還有沒有別的」—— 有兩個,而且是**兩種不同的債**。

**新增機制**:`check-prior-art.py` 現在會找出「我們自己的程式碼或筆記引用了它、
而登記表仍寫未審視」的來源。已證明會紅也會綠(2 → 1 → 2)。

**`pi-tool-repair-layer`** —— 真的只讀了一份文件。那份 `testing-strategy.md`
是 **AI 生成**、mutation 欄位**全是目標值而非實測**。我當時「分層採用、百分比不採用」
剛好正確,**但那是運氣**。
其核心能力(依欄位名修復畸形 tool call)**現在不採用**:
我們實測 35/35 正確 tool call,**沒有量到這個問題**。
**觸發條件已寫下**:若日後量到畸形 tool call,這是移植來源。

**`pi-browser-harness`** —— **審視做過了,只是沒登記**。
`stealth-web-bridge` 的註解指名檔案、說明採用 `inBoilerplate`、
明確拒絕密度啟發式並給理由、附真實失敗證據(維基百科 fixture 回傳「Donate」)。
比多數登記條目更完整。

**教訓**:「被引用」不等於「被理解」,也不等於「沒被理解」。
檢查抓的是**紀錄缺席**,而缺席的原因可能完全不同 ——
所以它報告的是「去看一眼」,不是「你錯了」。

**完整記錄**:[2026-08-09-cited-but-unreviewed.md](2026-08-09-cited-but-unreviewed.md)

## 2026-08-09 — harness-engineering

**來源**:`research/harness-engineering`(116 MB)· `vinicius91carvalho/harness-engineering`
**出處性質**:**已出貨**(semver 發布、安裝腳本指向 release tag 而非 `main`),
與 metaharness 那種以 `Proposed` 為主的 ADR 集不同性質。

**核心發現**:它的 ADR-0001 一句話讓我去打開一個從沒看過的檔案 ——
> 防止「一個不完整的佇列僅因為它所有的旗標都為真,就宣告成功」。

依此檢查 `01_Roadmap/global_dod.md`,發現三重問題:**沒人讀、還是未填樣板、
而唯一填了的第 1 條正是那個謬誤**(「所有任務 DONE」)。已依實測紀錄改寫成七條帶數字的標準。

**採用項目**
* ADR-0001 專案目標即完成權威 → 已改寫 `global_dod.md`(機制缺口:仍無人讀,列為後續)
* **待移植** ADR-0014 證據產物不可變:create-only、覆寫即硬失敗、以 digest 引用。
  我們的 `docs/measurements/` 是可任意改寫的普通檔案 —— 我今天就事後追加過下注文件。
  與 prime-agent 的 refinement journal 同族,**一起設計而非各做一半**。

**放棄項目**
* plugin marketplace 與多 host 路由 —— 我們是單一 host、單一本機模型。
* `roles.json` 依階段路由到有序模型候選 —— 同上,且我們只有一個模型可用。
* Supervisor / lease / fence / beacon 車隊治理 —— 我們一次跑一個 run,
  而且剛被兩個孤兒行程教過:先把單機行程樹管好再談車隊。
* 常駐背景 worker —— 同上。
* **記下觸發條件**:ADR-0018 的 fail-closed + 持久 Input Request,
  若出現「因缺少某能力而反覆產出不可驗證的結論」,再移植。

**這次最該記住的**:審視外部來源的收益,有一部分是**它逼你檢查自己有什麼**。

**完整記錄**:[2026-08-09-harness-engineering-review.md](2026-08-09-harness-engineering-review.md)

## 2026-08-09 — the-last-harness

**來源**:`research/the-last-harness`(218 MB)· `diegopetrucci/the-last-harness`
**出處性質**:已出貨且活躍(CI、Releases 下載計數),並有一份專門定義「怎樣才算驗證過」的 `VALIDATING.md`。
**與我們最可比** —— 同樣建在 Pi 之上。

**核心發現**:它的第二條主張是對我們現狀的批評 ——
> 你不該當保姆:若你需要手動呼叫工具、下指令,**harness 已經辜負你了**。
> 你不該發現自己在想「啊,我忘了觸發 `/review`」。

今天符合這個定義的有三次,**其中一次是我自己忘了用剛做好的 Path A**(Task_020 卡在 REVIEW)。

**採用項目(待移植)**
* **旗標在 `session_start` 快照,不即時讀取。** 我們的 `resolveFlag` 每次呼叫都讀檔,
  所以量測跑到一半改設定會當場改變行為、而紀錄看不出來;「這次 run 用哪個設定」現在無法事後回答。
  **直接打在我們最弱的地方(量測可信度),成本低。**
* **待評估**:封閉的子代理/動作允許清單。tlh 把 `contrarian`、`oracle` 放進執行期封閉清單,
  而我們量過同名的 Layer 1 技能全躺在 catalog 層、詞彙上到不了。
  要移植的是「角色是封閉集合、由政策指派」這個形狀,不是照抄子代理機制。
* **長期標準**:「使用者忘了觸發某件事」= harness 的失敗,不是使用者的疏忽。

**放棄項目**
* architect → 自動接手的整套編排 —— 假設多個可靠子代理與充足 token 預算;
  我們是單一本機模型,連並行五個 tool call 都會把守衛額度用光。
* 使用者自訂 embedded subagents —— 內建角色都還沒有。
* `/experimental` 指令族 —— 形狀記下,現在不做:旗標只有一個半,做 UX 是為不存在的規模建設施。

**完整記錄**:[2026-08-09-the-last-harness-review.md](2026-08-09-the-last-harness-review.md)

