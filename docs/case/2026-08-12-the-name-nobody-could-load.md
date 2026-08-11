# 一個載不到的名字,和一個五天前的檔案(2026-08-12)

**來源:擁有者隨手開的一個真實 session**,`D:/MyProject/DiscoverTurth`,
問題是一個十項的調查請求。不是實驗、不是探針、沒有事先安排。

挖出來的呼叫序列只有五步,而它把這個 harness 最核心的承諾整條打斷:

```
1 read  ~/.pi/agent/skills/research-task-routing/SKILL.md
2 read  ...\external\superpowers\skills\planning-with-files\SKILL.md   ← ENOENT
3 web_search 2025年7月 台灣 重大社會事件 新聞
4 web_search 2025年7月 中國 重大事件 政策
5 web_search 2025年7月 香港 社會事件

injections: none
refusals:   none
```

**模型完全照著指示做。** 是指示本身壞的。

---

## 缺陷一:我們自己叫了一個不存在的名字

`research-task-routing` 說「Load `planning-with-files`」,`pi-rules/AGENTS.md` §4/§10
說了三次,`CLAUDE.md` 說了一次。而真正註冊的名字是 **`pi-planning-with-files`** ——
外部 submodule 在自己的 frontmatter 裡這樣宣告,`restore.py` 也刻意讓本地版讓位給它。

於是 Pi 拿著 `planning-with-files` 這個名字,在已註冊的技能根目錄底下找,
找到 `external/superpowers/skills/planning-with-files/SKILL.md` —— 不存在。

**loader 沒有壞,是這個 harness 的每一條方法論路由都指向一個載不到的名字**,
而且失敗的時間點正好是方法論該開始運作的那一刻。

修法不只是改字。加了 `tests/test_skill_names_resolve.py`:
**指示裡叫得出的每一個技能名,都必須是註冊清單裡真的存在的名字** ——
兩邊任一邊改名都會有東西變紅,而不是讓方法論安靜地關掉。

## 缺陷二:一個五天前的檔案讓路由器閉嘴

路由器把這個請求分類得**完全正確**:

```
classify   -> {"multiStep": true, "deliverables": 10}
hasAnyPlan -> true          ← task_plan.md,寫於 2026-08-06
isCase     -> false
```

然後它讓位了,因為「已經有計畫了」。那份計畫是五天前另一件工作留下的,
**對剛剛送進來的請求一個字都沒說**。

修法**不是**加一個「幾天算過期」的門檻 —— 那是校準,而且是憑感覺挑的。
bridge 本來就知道 session 什麼時候開始,那才是誠實的界線:

* 計畫的 mtime **在 session 開始之後** → 模型正在規劃,再講一次是噪音,讓位
* 更早 → 那是歷史,照常給建議

不給時間參數時行為不變,所以三個共用這個判斷的 bridge 之間的 parity 測試不受影響。

## 缺陷三:每次啟動都印一則對的檔案的警告

```
Warning: [skill-namespace-guard] Skipping unsafe skill name ""yes"" from
...\external\yes.md\skills\yes\SKILL.md (must match [A-Za-z0-9._-]+);
registering as-is.
```

檔案是對的。`name: "yes"` 加引號是上游**不得不**加的:YAML 1.1 會把裸的 `yes`
讀成布林 `true`。我們用正則讀 name 卻沒有把引號脫掉,於是拿引號去比對自己的安全樣式。

**一則每次啟動都出現、而且針對一個正確檔案的警告,是噪音;而噪音正是讓警告不再被讀的原因。**
脫引號只脫**成對**的:`"yes` 這種不成對的維持原狀,否則會把壞掉的檔案偽裝成正常的。

---

## 這一天真正的教訓

**九個我自己安排的 run,沒有一個發現這三件事。** 它們全部跑在 `PiTaskLab` ——
一個 C.A.S.E. 專案,`isCaseProject` 為真,路由器與 `planning-with-files` 這條路
**在那裡本來就會讓位**。三個缺陷全部躲在我的量測場地的盲區裡。

擁有者隨手開的一個 session,五步就撞到全部三個。

> **自己安排的場地會遺傳自己的假設。** 要找缺陷,真實使用勝過受控實驗 ——
> 這與「控制變因是為了量測效果,不是為了找缺陷」是同一條規則的另一面。
