# Task_018 — Path A 一直都在協定裡,是我們把它關掉了

**狀態:REVIEW**

## 起因

擁有者指出:C.A.S.E. 的 review 部分要求 **AI 陪同說明與驗收、用輕鬆的選項**,
而不是讓人自己去看。去讀原文,他是對的。

## 原文(逐字,非印象)

**`references/for_agents.md` §7:**

> **Path A — Human-in-the-Loop (default for supervised/interactive deployments)**:
> Checkers and Humans communicate approval or rejection via natural language in the
> chat session. The AI Agent translates these statements to state changes:
> **APPROVE** (Human responds with approval phrases like "pass", "looks good",
> "approved", "OK"): transitions `status.txt` to `DONE`.

**`references/for_humans.md` 步驟三:**

> 當 AI 自我檢驗 100% 通過後,才會**在對話中向人類回報成果**。人類只需以大白話與 AI 對話,
> **不需要手動修改任何 `status.txt` 檔案或逐項勾選**。

**§1 只說:** `A Worker MUST NOT **self-approve** its own output as final.`

## 根因:一句話被讀錯

**把「Worker 不可自我核可」讀成「必須換一個 session」。**

Path A 裡的 Checker **是人**。人在對話裡說「通過」,雙軌就成立 —— §1 沒有一個字要求換 session。
**只有 Path B(無人值守)要求 fresh context**,而我們把它寫成唯一路徑。

三處後果,皆已對照原始碼確認:

| 位置 | 原本 | 現在 |
|---|---|---|
| `queue-advancer.ts` 終端訊息 | 「核可必須由**另一個 session** 進行…請告訴使用者可以開新 session」 | 要求模型逐條回報 DoD、明講驗不了的、給 A/B/C 三個選項 |
| `task-queue-guard.ts` 自我核可 | 認領過的 session **一律**不准寫 DONE(Path A 無法執行) | 有**真實使用者核可憑據**時放行;沒有仍然擋 |
| 擋阻理由 | 「開新 session,自己去對照 DoD」 | 明列兩條路,並說明不允許的只有「用自己的話結案」 |

## 憑據只能是使用者真的打的字

`before_agent_start` 的型別逐字寫著 `prompt` 是
"The raw user prompt text (after expansion)" —— **bridge 自己看到的**。

模型說的一律不算。理由是量過的:`blocked-claim` 抓到一次 run 對著被擋下的呼叫回報「已執行完畢」。
**一個接受「模型說使用者同意了」的守衛,比沒有守衛更糟,因為它看起來像取得了同意。**

四道關卡,順序是刻意的 —— **否決與疑問句先判,核可最後判**:

1. 我方注入(`[C.A.S.E.]` / `[SYSTEM]` 開頭)一律不算
2. 超過 40 字不算 —— 核可是簡短而刻意的動作
3. 疑問句不算(`可以通過了嗎?` 是在問,不是在決定)
4. 要求修改不算(`這裡改一下`、`not approved`)

憑據**用過即清**,`session_start` 也清。否則一句 OK 會結掉後面每一個任務 ——
與 `blocked-claim` 的輪次邊界是同一類錯誤。

## 過程中自己踩到的兩件事

**一、否決清單太寬,吃掉了協定自己的核可語。**
`問題` 原本在否決清單裡,結果 `沒問題` 被判為否決 —— 而那正是 `for_humans.md` 舉的核可範例。
**一份寬到吞掉協定核可語的否決清單,會用另一種方式再把 Path A 關掉一次。**

**二、中文不需要分隔符,而第一版要求了。**
`可以通過` 判不出來,因為 `通` 前面是 `以`、沒有空格 —— 那就是中文的樣子。

## 更大的教訓

**今天早上我跟擁有者要了「授權自我核可」。協定本來就有這條路。**
我不需要特別授權,我需要的是**把結果好好講給他聽,然後他說一句 OK**。
是我先把那條路擋住,再回頭跟他要鑰匙。

**讀協定要讀完整條,不要讀關鍵字。** §1 的 "self-approve" 與 §7 的 Path A 相隔六節,
只讀 §1 會得到一個看起來嚴謹、實際上把預設路徑關掉的實作。
