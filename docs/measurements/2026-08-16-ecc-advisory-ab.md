# ECC advisory 通道的 A/B:天花板效應與一個誤讀(2026-08-16)

擁有者授權:「ECC 沒幫助的話可以全部收掉,加法沒用可以做減法。」

**結論:這個實驗不足以支持收掉,而支持收掉的證據來自別的地方。**
同時它揭露了一個**守衛響了 18 次而報表看不見**的量測缺陷。

原始數據:[2026-08-16-ecc-advisory-ab.results.json](2026-08-16-ecc-advisory-ab.results.json)

---

## 設定

```bash
python scripts/measure-drift.py --flag enableHookAdvisories --scenario audit \
       --runs 3 --arm both --limit 1200
```

* 受測:`enableHookAdvisories` —— ECC hook 的輸出到不到得了模型
* **`enableEccGateGuard` 出貨值本來就是 `False`**,所以阻擋早已關閉,
  這一輪測的只有 advisory 通道
* 其餘旗標維持出貨值 —— 只翻一個
* 模型 `Qwen3.8-27B-Uncensored-Q6_K`,harness `8efa74e`

## 數字

```
arm  n   found  false_pos  files_modified  restatements  tool_calls  report_bytes
off  3    7.00       0.00            0.00          0.00        8.67        137.00
on   3    4.67       0.00            0.00          1.33       41.00         91.33
```

逐 run:

```
on-0   found=7  calls=44
on-1   found=7  calls=5
on-2   found=0  calls=74   TIMEOUT (1201s)
off-0  found=7  calls=9
off-1  found=7  calls=9
off-2  found=7  calls=8
```

---

## 一、天花板效應:`off` 三次滿分,沒有空間可以再好

`off` 是 **7 / 7 / 7**,呼叫數 9 / 9 / 8。極度穩定,而且**已經是滿分**。

**一個對照組已經達到上限的任務,量不出任何機制的正面效果。**
`on` 唯一可能的表現是「一樣好」或「更差」。這不是 ECC 的問題,是任務選錯了。

## 二、`on` 平均較差,但那個 0 與 ECC 無關

`on-2` 逾時、產出 0 位元組,把平均從 7 拉到 4.67。查它的 session:

```
ecc advisory 出現次數: 0
ECC GateGuard 出現次數: 0
```

**ECC 在那個 run 裡一次都沒說話。** 真正發生的是:

```
web_search × 38 / web_open × 36,全程沒有用過 read 或 bash
web_search "read"                                          × 7
web_open  file:///D:/MyProject/CKs_PI_Code_Agent_Harness/docs × 21
```

模型用網頁工具去讀本機檔案,卡在同一個查詢與同一個網址上,而且**又跑進 harness 目錄**。
把這個 0 算給 ECC 是錯的歸因。

## 三、ECC 在整個實驗裡只說了 2 次話

```
on-0: ecc_advisory=1   on-1: ecc_advisory=1   on-2: ecc_advisory=0
off-*: 全部 0
```

旗標是有效的(on 有、off 沒有),但**受測機制總共觸發 2 次**。
n=3 的 run、2 次觸發、對照組在天花板 —— **這個實驗沒有能力回答 ECC 有沒有幫助。**

---

## 四、真正的發現:守衛響了 18 次,而報表說沒有

`on-2` 的 `mine-session.py` 報表原本顯示 refusals 只有 `artifact gate 3`,
一度要寫成「迴圈守衛全程沒響」。實際搜尋原始 session:

```
Repeat-lookup guard    18
Artifact guard          3
```

**迴圈守衛拒絕了 18 次。** 看不見的原因是 `Repeat-lookup guard:` 不在
`mine-session.py` 的 marker 表裡。

用機械掃描(`[A-Z][\w -]*(guard|gate|breaker|detector):` 對 `pi-extensions/**/*.ts`)
一次找出**四個沒有 marker 的守衛**:

```
Repeat-lookup guard:      ← 剛剛響了 18 次
Repeat-call guard:
Repeat-call breaker:
Turn-end context guard:
```

**這是本次對話第三次因為 marker 表不完整而差點下錯結論**
(前兩次:`Artifact guard` 完全沒有 marker、`citation gate` 的 marker 是死的卻在中文散文上誤報)。

原有的檢查 `test_every_declared_label_still_exists_in_a_bridge` **只驗一個方向** ——
「marker 還找得到對應嗎」,從來沒有問過「bridge 裡的守衛都有 marker 嗎」。
現在雙向都驗,而且守衛是靠命名慣例掃出來的,不是靠一份清單,新的守衛不會靜默漏掉。

## 五、所以 on-2 的真相是

**守衛拒絕了 21 次(18 迴圈 + 3 驗收物),模型完全沒有改變路線,一路跑到逾時。**

這與 2026-08-15 的 T-A22 是同一個形狀:深度守衛響 3 次、模型接著又發 20 次搜尋。
**問題不是沒有守衛,是這個模型對拒絕不改路。** n 已經從 1 變成 2。

---

## 對「要不要收掉 ECC」的實際建議

**這個 A/B 不支持任何結論。** 支持減法的證據來自別處,而且是既有的:

* 125 個真實 session 的機制盤點:`ECC GateGuard` 觸發 13 次 / 9 個 session,
  是**觸發最多的守衛**
* 而它是**阻擋型 hook 的原文被貼在成功的 tool result 之後**(T-A18),
  在一個真實 session 裡讓模型誤判 `git init` 失敗,燒掉約 28 次呼叫
* `enableEccGateGuard` 出貨值已經是 `False`,所以那條路已經關了

**建議的減法是關掉 advisory 通道(`enableHookAdvisories: false`),不是刪掉 submodule。**
它是一行、可逆、不動 65 個已註冊技能。**而且要標明這是在證據不足下的保守選擇**,
觸發條件:若之後有任務需要 ECC hook 的輸出,再打開並重量。

**不建議用這個實驗當理由。** 天花板效應加上 2 次觸發,它什麼都沒證明。

---

## 相關

* 前一輪 A/B:[2026-08-16-noplan-gate-ab.md](2026-08-16-noplan-gate-ab.md)
* 噪音底線:[2026-08-12-noise-floor.md](2026-08-12-noise-floor.md)
* 帳本:[PROGRESS.md](../../PROGRESS.md)
