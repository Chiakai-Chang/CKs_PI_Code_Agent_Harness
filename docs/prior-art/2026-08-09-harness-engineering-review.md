# harness-engineering 實作層審視 — 2026-08-09

`research/harness-engineering`(116 MB)· `vinicius91carvalho/harness-engineering`

## 出處性質(照程序,先查這個)

**已出貨,不是提案。** semver 發布、`install.sh` 明確指向 release tag 而非 `main`
(README 有一段解釋為什麼:否則每次遠端安裝都會追著移動中的 `main`)。
與 metaharness 的 223 個 ADR(多數 `Proposed`)是不同性質的來源。

它的定位與我們高度重疊:**「harness 擁有完成政策」**、**「Done means evidence」**。

## 採用一:專案目標才是完成權威(ADR-0001)—— 當場抓到一個殭屍產物

> 防止「一個不完整的佇列僅因為它所有的旗標都為真,就宣告成功」。

**這句話描述的就是我們的失效模式。** 我們遇過任務走到 `REVIEW` 卻沒有 `output.md`,
修了那個個案 —— 但結構性問題更深:**沒有專案層級的目標驗收。**

依此檢查 `01_Roadmap/global_dod.md`,結果三重問題:

1. **沒有任何 bridge 或腳本讀它** —— 我們自己禁止的殭屍產物
2. **還是未填寫的樣板**,第 2–4 條全是 `[Project-specific criterion — e.g., ...]`
3. **唯一填了的第 1 條正是那個謬誤**:「所有任務 `DONE` 且經 Checker 驗證」

**已改寫**:七條驗收標準,每一條帶實測數字或明列缺口(其中兩條是 ❌)。
**已明列的機制缺口**:仍然沒人讀它,那是後續工作。

## 採用二:證據產物不可變(ADR-0014)

> Evidence Artifacts are create-only … **Overwrite of an existing path is a hard failure** …
> referenced by **digest** from Workflow Journals and Defect Reports.

我們的 `docs/measurements/` 是普通檔案,**我今天就在事後追加修改過下注文件**
(有標示為追加,但沒有任何東西**阻止**默默改寫)。
「以 digest 引用證據」會讓「這個結論的依據」變成可驗證的。

**待移植,未實作。** 與 prime-agent 的 refinement journal(append-only + 回滾)是同一族,
應該一起設計而不是各做一半 —— 已在 roadmap 第 3 項。

## 採用三:能力不足時 fail closed 並發出持久請求(ADR-0018)

> 當需要 `http`/`browser` 而候選池中沒有合格的強 host,Supervisor 會**升起一個持久的
> Input Request(fail closed)**,而不是放行弱 host 或靜默等待。

我們的對應處境:**驗不了的東西目前只寫成散文**(「明列未達成」)。
`fail closed + 持久請求`比「在報告裡寫一句」強 —— 它會**擋住流程**,而散文不會。

**未採用,但記下觸發條件**:若出現「因為缺少某能力而反覆產出不可驗證的結論」,
這是要移植的形狀。目前我們的規模還撐得住人工判讀。

## 明確不採用

| 項目 | 理由 |
|---|---|
| plugin marketplace / 多 host 路由(Claude Code / Codex / Cursor / OpenCode / Pi) | 我們是**單一 host、單一本機模型**。多 host 路由解的是我們沒有的問題 |
| `.harness/roles.json` 依階段路由到有序的模型候選 | 同上;跨模型 Checker 是 C.A.S.E. §17 的既有議題,但我們只有一個模型可用 |
| Supervisor / lease / fence / beacon 這一整層(ADR-0009/0012/0015/0019) | 那是**車隊規模**的併發治理。我們一次跑一個 run,而且已經被兩個孤兒行程教過:先把單機的行程樹管好,再談車隊 |
| 背景 worker 常駐 | 同上,且我們剛量到「常駐但沒人管的行程會污染量測」 |

## 這次審視最該記住的

**它的價值不在於給我新機制,而在於它的一句話讓我去看一個我從沒打開過的檔案。**
`global_dod.md` 在 repo 裡躺了很久,是樣板、沒人讀、而且唯一填了的一條是錯的判準。

**審視外部來源的收益,有一部分是它逼你檢查自己有什麼。**
