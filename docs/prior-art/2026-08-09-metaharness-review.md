# metaharness 實作層審視 — 2026-08-09

`research/metaharness`(1.9 GB)· `ruvnet/agent-harness-generator` 的 ADR 集。

## 先更正我自己

**我在建變異檢查時引用過它的 ADR-010 當根據**,而那時我只讀了那一個檔案。
現在逐項查證:

* **ADR-010 的 `Status` 是 `Proposed`,不是 `Accepted`。** 我把一個提案當成已確立的決定引用。
* 引文本身逐字正確(「No mutation testing in v1.0 … perf cost … A later ADR can add it
  if we measure that it would have caught real bugs」),**反轉條件也確實寫在裡面**,
  所以我的推論方向不受影響 —— 但**權威性被我高估了一級**。

223 個 ADR 裡,`Accepted` 系列約 42 個,其餘多為 `Proposed`。
**「這個 repo 說過 X」在這裡不是一句安全的話,要先看狀態欄。**

## 採用:量測噪音底線,再解讀差異(ADR-138)

`ADR-138 — the micro-evolve fitness noise floor, quantified`(`Accepted (measured)`)
把「單次 run 不可靠」從斷言變成數字,並給出可直接套用的算法:

> 要分辨相差 Δ 的兩個條件,標準誤要小於 Δ/2,即 **n ≳ (sd / (Δ/2))²**。
> 實測 sd ≈ 0.45、Δ ≈ 0.5 → **n ≈ 4–5**。而他們的演化實驗跑在 **n=1**,
> 「貪婪爬山追著雜訊爬進局部最佳解」。

**這直接指出我的方法缺口。** 我用 **n=2** 對二元結果下判定,
而且**從未量過本機模型的 run 間變異**:

| 嘗試 | 「認領前成功搜尋 = 0」的 run |
|---|---|
| 第二次(4 輪) | 1/2 |
| 第三次(8 輪) | 2/2 |

**若真實成功率是 50%,2/2 出現的機率是 25%。** 我事先寫下「n=2 只能否證」是對的,
但那是直覺;ADR-138 給出**為什麼**,以及要多少樣本才夠。

**待辦(已進 roadmap)**:先量本機模型在同一設定下的 run 間變異,再談任何條件比較。

## 採用:狀態詞彙區分「已決定」與「已量測」

`Accepted` / `Accepted (measured)` / `Accepted (implemented + measured)` 是三個不同的狀態。

本 repo 的 `docs/measurements/` 全是量測、`docs/case/` 全是結論,
**但兩者之間沒有一個欄位說「這個決定有沒有證據」** —— 只能靠讀者自己追連結。
**低成本、高價值,值得抄。**

## 明確不採用

| 項目 | 理由 |
|---|---|
| Darwin Mode 整套演化機制(ADR-093 ~ 152) | 遺傳演算法演化 harness 基因組、SWE-bench 語料、模型路由。**規模與目的都不同**:我們是單機、單模型、面對一個真實使用者的日常流程 |
| 223 個 ADR 的文件密度 | 我們的 `docs/` 已經有漂移問題(roadmap 一天漂一次)。**再加一層編號文件會讓沒人讀的東西變多** |
| 三環測試分層(ADR-010) | 我們已有等價物(單元 / bridge handler / 真實 session),而且是實測驅動的 |

## 一句話

**這次審視最有價值的產出,是它指出我方法上的錯誤,而不是給我新功能。**
而我第一件查的事就是我自己對它的引用 —— 那個引用高估了一級。
