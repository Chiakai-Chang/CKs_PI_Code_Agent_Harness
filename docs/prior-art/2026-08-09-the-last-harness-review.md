# the-last-harness 實作層審視 — 2026-08-09

`research/the-last-harness`(218 MB)· `diegopetrucci/the-last-harness`

## 出處性質

**已出貨且活躍**:CI badge、GitHub Releases 有下載計數、`node >= 22.19`。
`VALIDATING.md` 是一份**專門定義「怎樣才算驗證過」**的文件。

**而且它是整個登記表裡與我們最可比的來源** —— `tlh` 同樣是建在 Pi 之上的 harness。
同底座、同問題空間。

## 它的第二條核心主張,是對我們現狀的批評

> **你不該當保姆**:如果你需要手動呼叫工具、下指令,**harness 已經辜負你了**。
> 你不該發現自己在想「啊,我忘了觸發 `/review`」。

對照今天這一整天,擁有者被要求做的事:

* 開新 session 當 Checker(直到 Path A 修好)
* 自己下指令
* **當孤兒行程的偵測器** —— 兩次是他先發現「模型還在跑但 shell 沒東西」
* 而 `Task_020` 卡在 `REVIEW`,**正是因為我忘了用自己剛做的 Path A**

**「我忘了觸發」這件事,tlh 直接把它列為 harness 的失敗。** 這條標準值得長期掛著。

## 採用一:旗標在明確邊界快照,不即時讀取

> runtime 在 session 開始或明確 `/reload` 時快照 `tlh.experimental`;
> 啟用或停用旗標**在那之前不會影響執行中的 runtime**。

**我們的 `resolveFlag` 每次呼叫都讀檔。** 後果:

* 量測跑到一半若設定檔變動,**行為會當場改變而紀錄上看不出來**
* 「這次 run 用的是哪個設定」不是一個可以事後回答的問題

這正好打在我們目前最弱的地方(量測可信度)。**待移植:在 `session_start` 快照,
並把快照值寫進紀錄。** 成本低,直接提升每一次量測的可複驗性。

## 採用二:封閉的子代理與動作允許清單

```js
ALLOWED_SUBAGENTS = ["developer","code-reviewer","repo-scout","diff-summarizer",
                     "librarian","web-scout","oracle","contrarian"]
SAFE_SUBAGENT_ACTIONS = ["list","get","models","status","interrupt","doctor","resume"]
```

兩個都是 `Object.freeze` 的封閉集合。

**與我們的處境對照**:我們量過 Layer 1 的 `contrarian-review` / `adversary-review` /
`grilling-protocol` **全都躺在 catalog 層、沒有描述、詞彙上到不了**。
tlh 把 `contrarian` 和 `oracle` 放進**執行期的封閉允許清單**,而不是放進一堆技能裡等模型自己想到。

**這是「政策決定」對上「等模型提議」的又一個實例** —— 與我們第 9–10 輪的結論同向。
**待評估**,不是照抄:我們沒有子代理機制,要移植的是「角色是封閉集合、由政策指派」這個形狀。

## 明確不採用

| 項目 | 理由 |
|---|---|
| 整套 architect → 自動接手的編排 | 它假設有多個可靠的子代理與充足 token 預算(「slow by default, token-expensive」)。我們是**單一本機模型**,而它連並行五個 tool call 都會把守衛額度用光 |
| embedded subagents(使用者自訂 markdown 子代理) | 我們連內建角色都還沒有;先有封閉集合再談使用者擴充 |
| `/experimental` 指令族 | **形狀值得記,現在不做**:我們的旗標目前只有一個半,做 UX 是為不存在的規模建設施 |

## 這次審視對我們最直接的一句

**它把「使用者忘了觸發某件事」定義成 harness 的失敗,而不是使用者的疏忽。**
我們今天有三次符合這個定義 —— 而且其中一次是我自己忘了用剛做好的機制。
