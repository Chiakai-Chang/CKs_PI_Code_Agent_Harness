# prime-agent(Prime Intellect)實作層審視 — 2026-08-08

`research/prime-agent`(shallow clone,592 MB)。
`https://github.com/PrimeIntellect-ai/prime-agent`

## 一句話定位:它不是 Pi 的擴充,是 pi-mono 的 fork

`packages/` 底下是 `agent` / `ai` / `coding-agent` / `tui` —— **就是 pi-mono 的套件結構**,
而 `package.json` 釘的是 `@earendil-works/pi-coding-agent ^0.7.1`(我們跑 0.83)。

**所以「採用」在這裡不是安裝一個擴充,是換底座。** 與登記表裡的 `oh-my-pi` 同一類。
本次審視的目標因此定為:**哪些設計可以移植成我們的 bridge,而不是能不能裝。**

## 三個值得移植的設計(附行號)

### 一、supplemental-only 提示層,而且 base 真的擋得住

`refinement.ts:672`:

```ts
if (edit.kind === "prompt" && (edit.id === "base_system_prompt" || computedId === "base_system_prompt")) {
    return "base system prompt is not editable";
}
```

系統提示分成**不可變的 base** 與**可增修的 supplemental notes**,而不可變是由 `validateEdit()`
回傳拒絕字串**真的擋下來**的,不是寫在文件裡的約定(`refinement.ts:135`、`:451` 兩處把這句話
同時寫進給模型看的提示)。

**對我們的意義**:我們的 bridge 目前是「注入或不注入」,沒有分層概念。
若要讓 harness 能累積自己的經驗(這正是擁有者反覆要求的「不要看過就忘」),
**分層 + 不可變 base + 真守衛**是比「再加一段注入」更穩的地基。

### 二、refinement 事件是 append-only,且可回滾

`refinements.jsonl`,每筆帶 `id` / `trigger` / `changes` / `evidence` / `outcome`,
回滾以 `rollbackOf` 指向被撤銷的那一筆(`:100`、`:804` `rollbackProposal()`)。

`refinement.ts:396` 的註解值得抄:

> `// Skip malformed lines so a single bad append cannot break rollback.`

**對我們的意義**:我們已有 `action_log.jsonl` 的先例,格式與韌性做法可直接借。
而「自我改進必須可回滾」是我們目前**完全沒有**的一層 —— 今天的 `/refine` 類機制若要上,
先有回滾再有改進。

### 三、local / global 分域,預設 local

harness 狀態預設寫**本次 session 的 local**,只有「跨 session 的持久教訓」才升 global
(`:974` 的判準逐字:*"Prefer local harness edits for current task progress, temporary blockers,
and current-run coordination. Ask for global refinement only for durable cross-session lessons"*)。

**對我們的意義**:直接呼應本 repo 的「不得汙染不知情使用者的目錄」與 zombie config 禁令。
我們的 `enableCaseAdvancer` 是全域旗標,量測時會騷擾其他專案 —— 這個分域模型是現成解法。

## 明確不採用,以及為什麼(不寫下來就會被下一個人重做)

| 項目 | 不採用理由 |
|---|---|
| 整套 RLM / 常駐 IPython runtime | 模型把 context 當變數、以 `rlm(...)` 呼叫子代理,前提是一個常駐 Python 控制環境。這是**換執行模型**,不是加功能;而我們的地端弱模型連並行五個 tool call 都會把守衛額度用光,再加一層程式化間接只會更難觀測 |
| 換底座到它的 fork | 它釘 `^0.7.1`,我們在 0.83。`reference/oh-my-pi` 的疤已經記過:對著 fork 的舊型別找缺陷,會「找到」根本不存在的問題 |
| daemon 常駐 / agent 互相傳訊 / autonomous mode | 我們連「推進器預設要不要開」都還沒有實測依據(見 4b)。在沒關好的迴圈上加自主性,是把有反應沒結果的東西放大 |
| **它的「evidence-backed」** | **這一項要特別記** —— 見下 |

## 最重要的一個發現:它的「證據」是自陳的

README 與提示文案反覆強調 *small, evidence-backed updates*。但 `refinement.ts:787`:

```ts
evidence: proposal.rationale,
```

**`evidence` 欄位的值,就是模型自己寫的 `rationale`。** 沒有任何東西去核對那段話對應到
trajectory 裡真實發生過的事;而決定要不要 refine 的 `shouldRefine`(`:974`)也是另一個模型判斷。

這正是本 repo 量了一整天的那條線:
**`blocked-claim` 抓到過模型對著被擋下的呼叫回報「已執行完畢」。**
一個把模型自陳當成證據的欄位,在名字上叫 evidence,在行為上是 opinion。

**所以移植這套機制時,`evidence` 必須綁到真實產物** —— session log 的行號、跑過的指令與輸出、
守衛的擋阻紀錄 —— 而不是綁到模型的說明。**這是我們可以做得比它嚴謹的地方,不是抄它的地方。**

## 建議的後續(依價值排序,尚未執行)

1. **local/global 分域**:先用在 `enableCaseAdvancer` 這類旗標上,解決「量測會騷擾其他專案」。
2. **refinement 事件 + rollback**:在有回滾之前,不要讓 harness 自我改進。
3. **supplemental-only 提示層**:等前兩項成立再談,因為它會改變注入的形狀。
4. 讀 Continual Harness 論文(arXiv 2605.09998),確認上面三項是否還有前提沒抄到。

**四項都還沒動工,本文只記審視結果。**
