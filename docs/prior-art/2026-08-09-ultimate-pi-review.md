# ultimate-pi 實作層審視 — 2026-08-09

`research/ultimate-pi`(1.1 GB)· `aryaniyaps/ultimate-pi` · 第一層最後一個

## 出處性質

**已出貨的 npm 套件**(`pi install npm:ultimate-pi`),有 CHANGELOG、biome、lefthook。
同樣建在 Pi 之上,且**流程與我們幾乎同構**:

> 以證據規劃 → 只能對著**已核准的 PlanPacket** 執行 → 合併前跑一道**獨立審查閘**。

| ultimate-pi | 我們 |
|---|---|
| Plan → `plan-packet.yaml` | `planning.md` + `## Self-Review` |
| Run(只執行已核准的計畫) | 階段閘 PLAN:無計畫不得寫交付物 |
| Review(獨立審查閘) | C.A.S.E. §1 雙軌 / §7 Path A |
| **Steer** | **沒有對應物** ← 見下 |

## 採用一:`Steer` —— 拒絕之後的修補必須有界

> `/harness-steer`:**只修被核准的那個缺口,不擴大範圍**。輸出:更新後的實作 + 新的一輪審查。

**我們沒有這個階段。** Checker 拒絕時,協定是「寫 `feedback.md`、狀態回 `PENDING`/`IN_PROGRESS`」——
之後模型可以做任何事,包括重寫整個交付物。

**這是本 repo 已知疤痕的另一面**:我們花了很多力氣讓「開始」有界(階段閘),
**卻沒讓「重做」有界**。而重做正是最容易夾帶範圍蔓延的地方。

**待移植的是形狀,不是指令**:拒絕時記錄的是**具體缺口**,而下一輪只被允許修那個缺口。

## 採用二:風險分級決定儀式深度

> `--risk low|med|high` 改變規劃與審查的細節量;`--quick` 改變深度,**但不改變流程必須正確**。

**我們對所有東西套用同樣的儀式** —— 每個任務都要 role/recipe/planning/output/retro/action_log。
研究型 run 要 20–40 分鐘,而其中一部分是儀式成本。

**這條與本 repo 的價值觀有張力,要小心**:我們的疤是「省掉步驟就出事」。
但 ultimate-pi 的寫法保留了那個底線 —— **深度可調,流程不可省**。
**待評估**,而且要先量:目前沒有資料說明哪些儀式對小任務是浪費。

## 其他值得記的形狀(未採用)

* `/harness-abort` —— 清掉進行中的工作並**鎖住變更**。我們的「放棄」目前是狀態改 `ESCALATED`,沒有鎖。
* `/harness-incident --trigger` —— 把失敗寫成產物。我們寫在 retro 裡,沒有獨立的事故紀錄型別。
* `/harness-clear` —— 清理歷史 run 目錄,**保留進行中的**,且需確認。
  我們的 `advancer-*` 暫存目錄目前無人清理(這次量測留下十幾個)。

## 明確不採用

| 項目 | 理由 |
|---|---|
| 整套 `/harness-*` 指令族 | 我們的介面是 bridge 與擋阻,不是斜線指令;而且擁有者要的是「不用記得觸發」 |
| `plan-packet.yaml` 取代 `planning.md` | 協定已定義 `planning.md`;換格式會與 C.A.S.E. 打架,收益是零 |
| Sentrux steward / graph bootstrap | 依賴我們沒有的架構圖層與工具鏈 |

## 第一層審視結束,依停止規則停在這裡

四個第一層來源全部審視完(metaharness、harness-engineering、the-last-harness、ultimate-pi),
**待移植清單累積到 7 項,而一項都還沒實作**。

依 `CLAUDE.md` 剛寫下的停止規則:**下一步是實作,不是繼續讀。**
