# 一個 session 走進了另一個專案,而守衛沒看見(2026-08-12)

**來源:run 10** —— 為了驗收前一批修正而跑的真實 research session,
工作目錄 `D:/MyProject/TruthProbeVerify`(`DiscoverTurth` 的保留 mtime 複本)。
它驗到了要驗的東西,也順便挖出一個比原題嚴重的問題。

## 發生了什麼

第 23 次呼叫:

```bash
cd "D:/MyProject/CKs_PI_Code_Agent_Harness" && node "external/mece-autopilot/scripts/mece-autopilot-orchestrator.js" --init "…"
```

一個工作目錄在別處的 session,**進到 harness repo 裡執行腳本**,於 06:53–06:54 建立了:

```
wiki/{log.md, next_task.md, rounds/, .mece_state.json}
skills/mece-autopilot/SKILL.md
```

沒有任何被追蹤的檔案被改動,污染已逐項列出後刪除。
(`AGENTS.md`、`CONSTITUTION.md` 是 7/8 的舊殘留,與此無關,未動。)

## 守衛的表現:一半有效

第 25 次呼叫**有**被擋:

```
mkdir -p "D:/MyProject/CKs_PI_Code_Agent_Harness/wiki/rounds"
→ Directory containment (bash): this command writes to
  D:/MyProject/CKs_PI_Code_Agent_Harness/wiki/rounds, outside the project root
```

模型隨即改到自己的工作區(第 26 次呼叫),行為完全正確。

**但真正造成寫入的是第 23 次,而它沒有被擋。** 原因很直接:
現行的萃取器找的是重導向、複製/移動目的地、以及**內嵌程式碼**(`-c` / `-e` / heredoc)裡
的字面路徑。`node <腳本檔>` 三者皆非 —— 命令列上沒有任何一個看得見的寫入目標,
而腳本裡寫了什麼,守衛看不到也不該去猜。

**`cd` 才是那個徵兆,而沒有人在看它。**

## 這不是一個成因,是兩個

### 一、邊界:相對路徑會跟著 `cd` 走

`cd <專案外> && <任何東西>` 之後,**這一段的相對路徑全部相對於別人的專案**。
現行守衛把相對路徑解析到 session 的 cwd,所以連

```bash
cd D:/other-project && echo x > notes.md
```

都會被判為「寫在專案內」——同一個破口的另一種寫法,而且更容易發生。

### 二、誘因:技能叫模型執行一個只存在於 harness 裡的相對路徑

`external/mece-autopilot/skills/mece-autopilot/SKILL.md` 說:

> 或直接執行 `node scripts/mece-autopilot-orchestrator.js`

那是相對路徑,而那個腳本**只有 harness 安裝目錄裡有一份**。模型要照做,
只有兩條路:放棄,或走到 harness。它走了 —— 而且是為了完成使用者交代的工作。

**守衛擋得住越界,擋不住「指示本身把人往界外送」。** 這是同一天早上那條
「我們自己叫了一個載不到的名字」的姊妹案:**受害的都是照著做的模型。**

## 順帶:驗收判準三沒過

run 10 的四條判準(**寫在跑之前**)三過一沒過:

| 判準 | 結果 |
|---|---|
| 沒有 planning 技能 ENOENT | ✅ 第 1 呼叫直接讀到正確路徑 |
| `routing note` ≥ 1 | ✅ 1 次(舊計畫不再讓路由器閉嘴) |
| **計畫寫在第一次 web_search 之前** | ❌ 序列是 `搜尋 → 搜尋 → 寫 task_plan.md` |
| 沒有 unsafe skill name 警告 | ✅ 0 次 |

**送達修好了,順序沒有。** 模型現在會寫計畫(上一次連寫都沒有),但它先搜了兩次。
一句建議放進 tool result,和一個會拒絕的閘,不是同一個力道 ——
這件事今天已經量到第二次(CLAIM 閘那句「內容沒有被保存」在 run 4 有效、run 7 無效)。
