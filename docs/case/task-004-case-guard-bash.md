# Task_004_case_guard_bash — 結論與上游回饋

任務包在 `02_Task_Queue/Task_004_case_guard_bash/`(gitignore),本檔是結論摘錄。

## 修了什麼

`task-queue-guard.ts` 現在看得到 `bash`。落在任務包內的 shell 寫入:
`status.txt` 擋下並要求改用 `write`;其他檔案走既有 boundary 規則;任務包外不受影響。

**這不是新規則。** 協定兩處明文禁止,`SKILL.md:122` 的反例一字不差就是觀察到的行為:

```
**NEVER** run host shell redirection commands (e.g. `echo "IN_PROGRESS" > status.txt`)
```

`for_agents.md:424` 的例外(「除非高階工具完全不可用」)由既有的擋滿 3 次退場承接。

## 為什麼不解析 bash 寫入的內容

`printf "DONE" >` 抽得出,`cat > f << EOF`、`echo $VAR >`、`sed -i` 抽不出。
**部分可解析比完全不解析更危險** —— 它會讓人以為轉換檢查在 bash 上生效,而實際上
只在某些寫法生效,且沒有任何地方顯示是哪些。

## 破壞測試 5/5,其中一項是平權測試抓到的

把抽取器改成不認 `cp`/`mv`,**平權測試立刻紅** —— 它正是為了「兩份複製會漂移」而存在。

## 給 C.A.S.E. 上游的兩條回饋

**一、協定沒有「暫緩」轉換。** `IN_PROGRESS → PENDING` 不在 §4 表裡,但實務上一定發生:
任務被降優先序,既不是被 Checker 退回,也不是卡住。本任務規劃時就撞到了。

**二、Tool-First 規則值得從散文升格為可強制。** 它現在只寫在 §4 與 SKILL.md 的文字裡,
而本次證明:不強制的話,五條狀態規則會被一行 `printf >` 全部繞過 ——
包括 §1 標明不可協商的雙軌驗證。建議 `verify.py` 加一項:`action_log.jsonl` 若記錄到
對 `status.txt` 的 shell 寫入,即判定為協定違規。

## 最該記住的一條

**同一個洞今天出現兩次,而我修第一次時沒有去找第二個。**

早上補了目錄圍堵的 bash 洞,當時完全具備推廣的資訊 ——「守衛掛在 `write`/`edit` 就會被
bash 穿過」是通則,不是那個守衛的特例。代價是具體的:五條 C.A.S.E. 守衛在真實使用中
裸奔一整天,其中一條是協定的不可協商公理。

**修好一個洞之後,要問「這個形狀還在哪裡」。**
