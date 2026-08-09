# 被引用卻未審視的來源 — 2026-08-09

## 起因

審視 `metaharness` 時,第一件查的事是**我自己對它的引用**,結果發現我把一個
`Proposed` 的 ADR 當成已確立的決定。於是問下一個問題:**還有沒有別的?**

有兩個。而且它們是**兩種不同的債**,這正好說明為什麼要做成檢查而不是靠紀律。

## 新增的檢查

`scripts/check-prior-art.py` 現在會掃 `scripts/`、`pi-extensions/`、`tests/`、
`docs/case/`、`docs/measurements/`、`CLAUDE.md`,找出提到 `research/<名稱>` 或
`reference/<名稱>` 而登記表仍寫「未審視」的來源。

`REGISTER.md`、`RATIONALE.md`、`README.md`、`external-manifest.json` **豁免** ——
它們的工作就是列出所有來源(含未審視的),在那裡出現不算引用。

**證明它會失敗也會通過**:目前 2 個 → 暫時把其中一個標為已審視 → 1 個 → 還原 → 2 個。

## 債一:`pi-tool-repair-layer` —— 真的只讀了一份文件

`scripts/check-guard-mutations.py:25` 引用它的 mutation-score 分層當設計依據。

查證後:

* 那些百分比是**目標值,不是實測分數**。文件裡有覆蓋率的實測結果,**沒有任何一個 mutation 分數**。
* 該文件 frontmatter 寫著 `generated_by: cali-testing-ai-code` —— **AI 生成**,
  內文還混著葡萄牙文。

我當時寫「分層採用、百分比不採用」**剛好是對的,但那是運氣** ——
我沒有查它是什麼文件。**同一個教訓第二次:引用之前要看那份文件的性質。**

### 它真正的價值,以及為什麼現在不採用

核心主張直指我們的處境:

> 「開源模型不擅長 tool calling」幾乎總是 harness 問題 ——
> 一組有限的、可組合的失敗模式在各模型間重複出現。

修復依**欄位名稱**進行(模型寫 `dir` 而不是 `path` 之類),與模型無關。

**不採用,理由是我們沒有量到這個問題。** 本 repo 的實測是
**35/35 正確的 tool call、0 次守衛誤觸**(見 `harness-is-not-the-blocker`)。

**觸發條件寫下來**:若日後量到畸形的 tool call(錯誤欄位名、參數包錯層),
**這是要移植的來源**,不必重新找。

## 債二:`pi-browser-harness` —— 審視做過了,只是沒登記

`stealth-web-bridge/readability.ts` 與 `truncate.ts` 的引用其實是紮實的實作層審視:

* 指名具體檔案(`src/domains/readpage/readability.ts` —— 已驗證存在)
* 說明**採用什麼**:`inBoilerplate` 旗標(該檔第 20、51 行,已驗證)
* 說明**明確不採用什麼**:它以文字/連結密度猜測正文的啟發式。
  我們拿到的是無障礙樹,每個節點自帶語意角色,按角色過濾**更簡單也更可靠**,
  且不需注入頁內腳本、不會被惡意頁面破壞
* 附**真實失敗證據**:第一次跑維基百科 fixture 回傳「Donate、Create account、Log in」

**這比多數登記表條目更完整,只是從來沒進登記表。**

## 兩種債,一個結論

| | `pi-tool-repair-layer` | `pi-browser-harness` |
|---|---|---|
| 實際讀了什麼 | 一份 AI 生成的策略文件 | 具體實作檔案 |
| 有沒有採用/拒絕的判斷 | 有,但憑運氣正確 | 有,含理由與證據 |
| 缺什麼 | **審視本身** | **只缺登記** |

**「被引用」不等於「被理解」,也不等於「沒被理解」。** 檢查抓的是**沒有紀錄**,
而紀錄缺席的原因可能完全不同 —— 所以檢查報告的是「去看一眼」,不是「你錯了」。
