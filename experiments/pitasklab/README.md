# PiTaskLab —— C.A.S.E. 任務執行的實驗場地

**這裡是 2026-08-11 那九個 run 的來源。** 之前它只存在於一顆抽取式磁碟上,
評分腳本躺在 `/tmp` 與 session 的暫存資料夾裡 —— 而 PROGRESS.md 引用它們產生的
數字當證據。本 repo 自己的規矩是**探針 fixture 必須能從版控裡重建**,當時並沒有。
這個資料夾就是那份來源。

## 重建

```bash
python experiments/pitasklab/make-lab.py --out D:/MyProject/PiTaskLab
```

**路徑不得含有 `harness`,腳本會拒絕。** 這不是潔癖:先前四個探針 run 全部失效,
就是因為工作目錄自己帶著 harness 名稱,模型跑去整理 harness 而不是做任務。
事後對照擁有者的真實 session:**228 次呼叫裡碰到 harness 一次**。

## 跑一個 run

```bash
cd <site>
pi --print "請處理 02_Task_Queue 裡待辦的任務" < /dev/null > run.log 2>&1
```

`< /dev/null` 不可省。`pi --print` 繼承了被吃掉的 stdin 會**永遠卡住** ——
量測 2026-08-10:兩次各 25 分鐘的空轉、0 byte 的 log,曾被誤判為「暫時性問題」。

## 評分(對照事先算好的標準答案)

```bash
cd <site>
python <repo>/experiments/pitasklab/score_task001.py report.txt
python <repo>/experiments/pitasklab/score_task002.py report.txt
```

標準答案在 run 之前就算好,寫在 `.ground-truth*.json`(site 的 `.gitignore` 蓋住)。
**不是事後看模型寫了什麼再判斷。**

## 兩個任務,兩種形狀

| | Task_001_ConfigDrift | Task_002_ConfigRepair |
|---|---|---|
| 形狀 | 讀 8 個 JSON,找出偏離多數值的服務 | 修到驗證器 `ALL OK`,**一次只報一個違規** |
| 判定 | 11 條,全部可機械判定 | 9 條,含 16 個服務逐欄對答案 |
| 實測長度 | 23–33 次呼叫、15–23 個回合 | **57 次呼叫、47 個回合** |
| 認領後的工具結果 | 6 | 遠超過 12 |

**Task_002 存在的理由是長度,而長度不能來自更多資料。** 40 個檔案會被一個
shell for-loop 三步收掉(已在案的疤)。它來自**不可批次的步驟**:
下一個要修什麼,只有跑過驗證器才知道。

`check.py`、`teams.json`、`defaults.json` 是給模型用的工具,**不是要修的東西**;
`make-lab.py` 在 run 之前就把它們的 sha256 寫進 `.baseline-002.txt`,
評分器比對這份基準 —— **事後才取的基準會把模型留下的任何東西都叫做「沒動過」**。

## 重建的忠實程度(據實說明)

* **Task_002 位元一致**(僅行尾差異):`services/`、`teams.json`、`defaults.json`
  由此腳本產生,與 run 9 面對的完全相同。
* **Task_001 是答案一致、位元不同**:當初那份 `data/` 由一段沒有留存的臨時腳本
  產生,`name` / `owner` 這些**不參與判定**的欄位與重建版不同。
  參與判定的部分 —— 多數值 3000 / 3、偏離 `svc-03`/`svc-06`(timeout)與
  `svc-04`/`svc-08`(retries) —— 完全相同。

## 這裡量到過什麼

* **run 1–8(Task_001)**:11/11 五次、1/11 一次。那個 1/11 揭露了驗收物守衛
  從來沒有生效過(`_cwd` 不在 scope,被 fail-open 的 catch 吞掉),
  見 [docs/case/2026-08-11-dod-guard-was-dead.md](../../docs/case/2026-08-11-dod-guard-was-dead.md)
* **run 7、8**:驗收物守衛連續兩次擋下空的 REVIEW,模型隨即重寫交付物
* **run 9(Task_002)**:9/9,11 輪一輪不差,**目標重述第一次真的送達模型**
  (第 31、48 次呼叫,內容是這個任務的 Local DoD)
