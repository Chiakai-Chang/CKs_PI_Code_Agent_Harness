# 「14 個從未觸發的守衛」錯了三次,正確答案是 4,而且一個都不該刪(2026-08-16)

擁有者說「請刪那 14 個從未觸發的守衛」。**那個數字是我給的,而它錯了三次。**
逐一查證之後,真正在任何地方都沒觸發過的是 **4 個**,
而**這 4 個沒有一個是「接錯了」** —— 它們是升級層與罕見條件。

**這份文件記錄的是一個差點執行的錯誤刪除,以及它為什麼會發生。**

---

## 從 14 到 4

| 步驟 | 數字 | 錯在哪 |
|---|---|---|
| 我最初回報 | **14** | — |
| 修掉 `harness-status.py` 漏算 sendMessage 通道 | 13 | `blocked-claim` 走 `custom_message`,而掃描只走 `message` |
| 把「探針 session」也算進去 | 7 | `harness-root hint`(4)、`artifact gate`(2)、`repeat-lookup`(1)**都會動**,只是沒在真實專案裡出現 |
| 撤掉兩個**不可能出現在 session 裡**的 marker | **4** | 見下 |

### 撤掉的那兩個 marker

**`Turn-end context guard:` 根本不是守衛。**
它是 `pi-extensions/stealth-web-bridge/index.ts:295` 的一句**註解**。
我用機械掃描補 marker 時,那次探索性查詢**沒有濾掉註解** ——
而同一天寫的覆蓋檢查是有濾的。工具比我嚴謹。

**`Repeat-call breaker:` 是 `ctx.ui.notify`。**
它只畫 TUI,**結構上不可能出現在 session 紀錄裡**,所以它永遠報 0。
**一個不可能觸發的 marker,不是關於守衛的證據,是關於 marker 的證據。**

覆蓋檢查隨即反過來要求「這個 notify 也要有 marker」——
那個要求本身是錯的,所以檢查也修了:`ui.notify(` 附近的字串豁免。

---

## 剩下 4 個,逐一判定

```
status value      C.A.S.E. 的 status.txt 值域守衛
one-at-a-time     C.A.S.E. 的一次只認領一個任務
loop guard        重複呼叫三振之後,交還控制權給使用者
discarded call    一輪撞到輸出上限,Pi 丟掉了那個工具呼叫
```

**沒有一個是接錯了。** 分類:

| 守衛 | 為什麼沒觸發 | 刪掉會失去什麼 |
|---|---|---|
| `loop guard` | **升級層**:`repeat-call` 有觸發過(1),但沒有累積到三振 | **停止鍵**。觀察到的那次迴圈跑了 70 分鐘,沒有東西讓它停 |
| `discarded call` | **罕見條件**:輸出上限截斷工具呼叫,尚未發生 | 一個安靜失敗的解釋 —— 模型會以為呼叫送出了 |
| `status value` | C.A.S.E. 專屬,而真實工作幾乎不走 C.A.S.E. | 見下 |
| `one-at-a-time` | 同上 | 見下 |

**「從未觸發」與「該刪除」是兩件事,而且中間有三種可能:**

1. **接錯了/條件不可能** → 刪
2. **升級層還沒被觸及** → 留(刪掉等於拿掉停止鍵)
3. **罕見但嚴重的條件** → 留

**這一輪 4 個全部落在 2 和 3。**

---

## C.A.S.E. 的那一群,答案是搬不是刪

真實 session 沒觸發的 11 個裡,**6 個屬於 case-bridge**:

```
status value, transition, one-at-a-time, retrospective, dual-track, tool-first
```

它們沒觸發的原因不是壞掉,是**真實工作幾乎不在 C.A.S.E. 專案裡**
(`isCaseProject` 為假時,整條路本來就讓位)。

**擁有者在同一則訊息裡說了答案**:
「我想要分開,CASE 跟 PI harness 放在一起感覺不會有結果,CASE 研究成通用的好了」。

**這 6 個該跟著 C.A.S.E. 走,不是刪掉。** 刪除線與拆分線恰好重合。

---

## 這次為什麼會差點刪錯

**三個錯誤都出在量測儀器,不在守衛。**

1. **`harness-status.py` 漏了一整條通道。** 它只從 `message` 累積文字,
   而 `pi.sendMessage` 是 `type: "custom_message"`。
   **session miner 修過完全相同的 bug,而我寫新腳本時原樣重犯。**
2. **「排除探針」濾掉了唯一證明三個守衛會動的資料。**
   排除探針是對的規矩(探針路徑會製造假象),
   但**「沒有在真實專案觸發」不等於「不會觸發」**,而我把兩者當成同一件事報出去。
3. **機械掃描抓到了註解與 notify。** 掃描很好,它找出了四個真的沒有 marker 的守衛;
   但它同時抓進兩個不可能觸發的字串,而我沒有逐一驗證就當成守衛。

**共同形狀:我用一個剛做好、沒有被質疑過的量測工具,產出了一個要刪東西的建議。**
這個 repo 的規矩是「先證明檢查會失敗」,而我對 `harness-status.py` 只證明了它會跑。

---

## 已經做的

* `harness-status.py` 補上 `custom_message` 通道,並加測試
* 撤掉兩個不可能觸發的 marker,理由寫在 `mine-session.py` 的表裡
* 覆蓋檢查豁免 `ui.notify(` 附近的字串
* **沒有刪掉任何守衛**

## 沒有做的,以及觸發條件

* **`loop guard` / `discarded call`**:留著。觸發條件 —— 若累積 ≥50 個真實 session
  仍為 0,且期間發生過它們該擋的失效卻沒擋到,才視為接錯並移除
* **6 個 C.A.S.E. 守衛**:隨 C.A.S.E. 拆分一起移出,見帳本的拆分任務

---

## 相關

* 現況頁:`python scripts/harness-status.py`
* [Round 18](../mece/rounds/2026-08-16_round18_擁有者看不懂就是缺陷.md)
* 帳本:[PROGRESS.md](../../PROGRESS.md)
