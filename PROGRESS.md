# 總控:進度、收穫、脈絡

> **這份文件的用途:** 每次工作結束後在這裡留一筆 —— 做了什麼、學到什麼、詳細文件在哪。
> 它是唯一需要從頭讀的檔案;其餘文件都從這裡連出去。
>
> **它被檢查所守著:** `tests/test_progress_ledger.py` 要求 `docs/case/` 與
> `docs/measurements/` 底下每一份文件都被本檔連到。沒人讀的紀錄是這個 repo 反覆踩到的坑
> (`global_dod.md` 曾經是一份沒人讀的未填範本),所以這份索引由測試維持,不靠記得。

---

## 現在在做什麼

**上一段工作(2026-08-09 ~ 08-10):反漂移與守衛品質。**
起因是擁有者的問題:「跑到第 18 步還記得我原本要完成什麼?」

**當前認領中:** 無。T-A5 已完成(2026-08-12,n=5),等待 Path A 核可。T-A1/A2/A3/A6/A7/T1b 皆已由擁有者在對話中口頭核可(Path A)。

**下一個要動的**:**T-A18**(GateGuard 的阻擋型原文不該走 advisory 通道)。
**T-A12、T-A16、T-A13、T-A19、T-A17 已完成**,**T-A14 已上線但 live 觸發 0 次**
(2026-08-14/15,等 Path A 核可)。之後 T-A21。

> **2026-08-15 擁有者換模型至 `Qwen3.8-27B-Uncensored-Q6_K`。**
> `check-model-serving` 對它回報 0 failures,而且**這次的判準是對的**:
> template 教 `<tool_call><function=>`,活體探測回 `finish_reason: tool_calls`
> 與結構化參數 —— llama.cpp 讀得回來。
> **產生 `</atem:日>` 的那份 template 已經不在服務中**,所以 T-A14 的 live 驗證
> 在這台機器上暫時沒有機會;觸發條件留著,等哪天再遇到不可解析的方言。
不阻塞的替代:T3(反轉極性)、T6(§16 Handoff Capsule)。

> **2026-08-14 排序修正兩次,兩次都不是照原表走。**
> 原本是家族 A→B→C→D。T-A16(C)插到 B 前面,因為它有一支**已經在紅**的檢查;
> T-A13(B)插到 T-A17(C)前面,因為**壞掉的 template 當時還在 server 上跑**,
> 那個活樣本會隨著一次重開消失。**排序的依據是證據的時效,不是表格的順序。**
**明講不做的**:讓變異掃描支援 `bun`(13 個 `async-exec-bridge/*` 模組),
**這台機器的 PATH 上沒有 bun**,做了也驗不了 —— 除非擁有者裝。

> **2026-08-12 帳本自查。** 上面這行原本寫著兩個「認領中」,兩個都早就核可了;
> 底下的「舊 Task Queue」標題寫著「已被上方取代」,而它裡面有四條是活的。
> 代價是具體的:**T4 在 2026-08-11 就達成了,沒有人回來勾**,於是它在「尚未開始」裡
> 又躺了一天。這是 repo 自己那條「無人看守的清單會靜默走樣」,只是這次走樣的是計畫本身。

> **2026-08-11 重排。** [Round 14](docs/mece/rounds/2026-08-11_round14_回到起點與外部實證.md)
> 用外部實證與擁有者的真實 session 重查整條線,結論是**先前的排序建立在一個探針假象上**:
> 探針的 cwd 自己叫 `D--MyProject-CKs-PI-Code-Agent-Harness`,而真實 session 的對照是
> **228 次呼叫碰到 harness 路徑 1 次**。**T2 撤銷、技能遷移擱置(附觸發條件)。**

---

## 一眼看完:每一項現在卡在哪

> **這張表由 `tests/test_ledger_markers.py` 守著**:一個任務的 Local DoD 打勾全滿卻沒標成
> ✅、或標成 ✅ 卻還有沒打勾的框、或同時有兩個「認領中」,測試就會紅。
> 寫這條檢查的理由是它**已經發生三次**:T4 完成後兩天沒人回來勾、T-A11 上線後標題還是紅燈、
> T-A5 核可後仍寫著認領中。三次都不是判斷錯誤,是兩個地方各說各話。

| 項目 | 狀態 | **卡在什麼** |
|---|---|---|
| T-A1/A2/A3/A6/A7、T1、T1b、T1b-rest、T4、T-A5 | ✅ 完成 | — |
| T-A11 第 1 項(依工作種類點名技能) | ✅ 已上線 | 送達已證明,**效果未證明** |
| T-A11 第 2/3 項(降級 38 個技能、蒸餾技能升層) | ⏸ 暫緩 | 等 ≥5 個修後真實 session;現在做會和第 1 項的效果混在一起 |
| T-A8(先規劃再搜尋) | ⏸ 等資料 | 同上。原本的前提已被推翻(31 個 session 裡 search-first **0** 次) |
| T3(反轉極性:唯讀白名單) | ⏸ 等資料 | 需要誤擋的先驗,而先驗只能靠真實使用累積 |
| T6(§16 Handoff Capsule)、T7(learnings 注入) | ⏸ 等問題出現 | 兩者都在解 **L3 續航漂移**,而 L3 從來沒有被量到過 |
| **T-A9(路徑漂移)** | ❌ **不做** | **1 / 126** 個真實 session。觸發條件:再發生一次就實作 |
| **T-A10(捏造時間戳)** | ❌ **不做** | **2 / 126**,而且**不可機械判定** —— 合法引用的日期與捏造的日期在工具參數裡一模一樣 |
| T5(探針殘留) | 👤 你決定 | gitignored 的 `02_Task_Queue/` 裡 16 個任務包,只有 `Task_001_Inventory` 是探針留的 |
| T2 | 🚫 已撤銷 | 建立在探針假象上(Round 14),原文保留 |
| T-A12(量測儀器) | ✅ 完成 | 2026-08-14。查到的比原本記的多:3 個死 marker、1 個隱形守衛、`customType` 只認 bridge 不認機制 |
| T-A13(換模型守門員) | ✅ 完成 | 2026-08-14。⚠️ **這台機器的 server 仍是紅的** —— 修法是操作者重開,repo 不動它 |
| T-A14(殘留標籤) | 🟡 已上線 | 送達已證明,**live 觸發 0 次** —— 兩次探針模型都沒吐殘留。觸發條件已寫下 |
| T-A19(解析器) | ✅ 完成 | 2026-08-15。順帶發現這個方言連解析都進不去,以及一個「參數全空」的舊洞 |
| T-A15(20 個髒檔案) | 🚫 不做 | **2026-08-14 擁有者決定保留**:那些檔案他有用 |
| T-A16(18 個技能載不到) | ✅ 完成 | 2026-08-14。`--config-only` 是根因,已重現並修掉;套件由 `failures=2` 轉 `Ran 1465 tests / OK` |
| T-A17(learning notify) | ✅ 完成 | 2026-08-15。掃描 122→3 次、通知 122→1 次、改用 `getSessionFile()` 不再猜 |
| T-A21(點名的名字要載得到) | ⚪ 待做 | 自 T-A16 拆出。要先決定「可達」的權威定義 |
| **T-A25(L2:沒計畫就開始)** | 🟡 已上線 | **擁有者從頭在抱怨的那件事**。根因是規劃 bridge 每個 handler 都在沒計畫時 return。**live 觸發 0 次且未被測到** |
| **T-A26(結果量測解開旗標)** | 🟡 已上線 | 回答「怎麼證明有幫助」。**過去每個量測問的都是機制,不是結果**。順帶抓到 bridge 的開關在 Pi 以外全部 fail-open |
| **19 個守衛裡 10 個從未觸發** | 🔴 **下一輪要刪** | 125 個真實 session。觸發最多的是 ECC GateGuard(13 次),而它已證明會誤導模型 |
| **T-A22(遞增計數器迴圈)** | 🔴 **先查頻率** | 換模型當天第一個探針:31 次呼叫、0 次寫檔。**兩個守衛各響 3 次,模型又發了 20 次** |
| T-A23(豁免清單的鍵會過期) | ⚪ 待做 | Round 17 立案。40 條,鍵用行號,**repo 自己記過兩次會過期** |
| **T-A24(協定本體不在專案裡)** | 🔴 **先量再決定** | 其他專案 **7% 的呼叫在 harness 目錄**。修完變數後重量,分不出「設計」與「找路」就選不了邊 |
| **`$PI_HARNESS_ROOT` 是空的** | ✅ 已修 | 2026-08-16。十處指示指向空字串;三層驗證,含真實 Pi session |
| 這批工作跑過 CI 了嗎 | ✅ 跑過 | 2026-08-15 合併進 main,run `31872614550` success,`Ran 1549 / OK (skipped=28)`,28 個 skip 全部有正當理由 |
| T-A18(GateGuard 語意) | ⚪ 待做 | 不卡。界線是不動 `external/ecc/` |
| T-A20(批次崩壞) | ⏸ 等資料 | **n=1**,且 T-A13 的 template 問題本身就可能是原因 |

**為什麼「不做」也是結論。** T-A8 是從**一個現象**立的任務,做完第一步才發現那個現象在 31 個
真實 session 裡發生 **0 次**,代價是一天。現在的規矩是**先量頻率再決定做不做**,
而量頻率通常十分鐘 —— 上面兩個 ❌ 就是這樣收掉的。

**所有 ⏸ 卡在同一句話:要真實使用的資料。** 不是不想做,是現在做等於猜。

## 宏觀目標與微觀目標的對齊

**宏觀(擁有者原話):**
> 「每次專注做一件事,做完復盤,有發現就增加 task queue」
> 「他多搜幾次是好的阿?越多越好不是?**我抱怨的是他沒有先規劃就開始**」

拆成三個可判定的層次:

| 層 | 目標 | 現況(**2026-08-16 重量,n 從 6 變成 53**) |
|---|---|---|
| **L1 對齊** | Pi 在**正確的專案**裡工作 | ❌ **不成立**。其他專案 53 個 session、2832 次呼叫,**218 次(7%)碰到 harness 路徑**;單一 session 最高 18% |
| **L2 流程** | 先認領 → 先規劃 → 才產出 → 有驗收物才進 REVIEW | ⚠️ **有動,但遠未達成**。41 個有搜尋的 session:plan-first **12.2%**、no-plan **82.9%**;20+ 次呼叫卻無計畫檔 **11/18** |
| **L3 續航** | 長 cycle 裡不漂移 | ⚠️ 仍未測 |

> **⚠️ 2026-08-16:L1 那一列原本是 ✅,由 2026-08-11 的六個 run 得出。它被推翻了。**
>
> 舊結論的推理沒有錯:更早那次「五個 run 有四個跑進 harness」確實是探針假象
> (探針 cwd 自己帶著 harness 名稱)。錯在**用 6 個 run 把一整層宣告為綠**。
> n=53 給出的答案是 7%,而根因在
> [2026-08-16 量測](docs/measurements/2026-08-16-harness-root-and-skill-reach.md):
> `/case` 指令叫模型去讀 `$PI_HARNESS_ROOT/...`,而那個變數一直是空的。
> **這正是本 repo 自己的規矩(先量頻率、n 要夠)反過來咬自己的一次。**
>
> L2 的數字對照 2026-08-12 的 31 個 session(no-plan 93.5%、20+ 無計畫 10/12):
> 方向是對的(93.5% → 82.9%,83% → 61%),但 **n 小、母體也變了,只能當方向不能當結論**。
> 而且**這一週的工作沒有一件直接針對 L2** —— 見下面的「概念對齊自查」。

**L3 仍然沒有量測** —— 需要一個做不完就得換回合的任務,不是更多資料的任務
(「不能用更多資料把任務變長」 的教訓:40 個檔案被一個 for-loop 三步做完)。

### 概念對齊自查(2026-08-16)

擁有者的原話是「**我抱怨的是他沒有先規劃就開始**」。把這一週做完的七件事對上去:

| 做了什麼 | 服務哪一層 | 是擁有者提的嗎 |
|---|---|---|
| T-A12 量測儀器 marker | 工具正確性 | 否(自查發現) |
| T-A16 技能可達性 | L2 的前提 | **是**(「skills 有提示但沒真的做」) |
| T-A13 換模型守門員 | 產出完整性 | **是**(換模型後問題不少) |
| T-A19 解析器 | 產出完整性 | 否 |
| T-A14 殘留標籤 | 產出完整性 | **是**(檔案尾端垃圾) |
| T-A17 學習點通知 | 使用者體驗 | **是**(原話點名) |
| Round 17 CI / 命名空間 / TS 語法 | 我們自己的可信度 | 否 |
| `$PI_HARNESS_ROOT` | **L1** | **是**(「跨出資料夾就亂搜尋」) |

**結論:沒有跑題,但有偏斜。** 八件裡五件由擁有者實際遇到的問題驅動,
不是自己想出來的題目;剩下三件是動手時被自己的檢查抓到的。
**但沒有任何一件直接推進 L2** —— 這一週修的是水管,不是那個指標。
**這是誠實的偏斜,不是失控**:擁有者回報的缺陷確實會擋住 L2
(技能載不到、產出帶垃圾、跨專案亂跑),先修它們是對的順序。
**下一輪要把 L2 放回第一位**,否則「先規劃再開始」會一直是 82.9% 沒人動。

---

## 2026-08-12:一個真實 session 五步撞到三個缺陷

擁有者隨手在 `D:/MyProject/DiscoverTurth` 開了一個 session,問一個十項的調查請求。
五次呼叫,把這個 harness 最核心的承諾整條打斷 ——
脈絡與修法:[docs/case/2026-08-12-the-name-nobody-could-load.md](docs/case/2026-08-12-the-name-nobody-could-load.md)

```
1 read  ~/.pi/agent/skills/research-task-routing/SKILL.md
2 read  ...\external\superpowers\skills\planning-with-files\SKILL.md   ← ENOENT
3-5 web_search × 3            injections: none   refusals: none
```

| # | 缺陷 | 修法 |
|---|---|---|
| 1 | 我們自己的指示叫 `planning-with-files`,註冊的是 `pi-planning-with-files` —— **每一條方法論路由都指向載不到的名字** | 全部改成註冊名;`tests/test_skill_names_resolve.py` 從此要求「指示叫得出的名字必須註冊得到」 |
| 2 | `task_plan.md`(8/6 寫的)讓路由器對一個全新的十項請求閉嘴 | 只有 **session 開始之後**寫的計畫才算計畫;不加「幾天算過期」的門檻 |
| 3 | `name: "yes"` 被讀成含引號 → 每次啟動都警告一個正確的檔案 | frontmatter 脫**成對**引號;不成對的不脫 |

**這一天真正的教訓:我自己安排的九個 run 一個都沒發現這三件事。**
它們全部跑在 `PiTaskLab`,那是 C.A.S.E. 專案,`isCaseProject` 為真,
路由器與 `planning-with-files` 這條路**在那裡本來就會讓位** —— 三個缺陷剛好全在盲區。
**自己安排的場地會遺傳自己的假設;要找缺陷,真實使用勝過受控實驗。**

---

## 2026-08-14:換模型之後的第一個長 session,六個缺陷共用一條根因鏈

擁有者換了本機模型(`Muse-Glimmer-30B-Abliterated-Q6_K`),在
`D:/MyProject/test-20260813-cyber-patrol` 跑了一個 6.5 小時、122 turn、113 次呼叫的真實 session
(`019ffbdd`),並回報:「問題不少,而且 skills 有些有提示但沒真的做,
例如『📝 偵測到新學習點 (1)。』一直出現,只有提示沒有意義。」

量測:[docs/measurements/2026-08-14-session-019ffbdd-postmortem.md](docs/measurements/2026-08-14-session-019ffbdd-postmortem.md)
復盤:[Round 16](docs/mece/rounds/2026-08-14_round16_模板換了而清單沒有跑.md)

| # | 缺陷 | 證據 |
|---|---|---|
| 1 | `📝 偵測到新學習點` 走 `notify`(到不了模型),而它指的 `hello-reflect` **三條註冊路徑都不在** | 降級的 **14 個本地 core skill 一個都不在 catalog**;手動呼叫 `merge_into_catalog` 得 `lost []` |
| 2 | ECC GateGuard 的**阻擋型**原文被當 advisory 貼在**成功的**結果後 | 模型 thinking:`Maybe git init didn't work due to GateGuard` —— 那次 `git init` 成功了,後續約 28 次 bash 空轉 |
| 3 | server 載到的 chat template 教模型用 `<atem:*>` XML 發工具呼叫,而 Pi 走原生 `tool_calls` | `</atem:日>` 出現 **24 次**,全在 `write` 的最後一個參數尾端;**那個專案 20 個檔案帶著垃圾** |
| 4 | `universal-tag-transformer` 把 git 的**輸出回顯** `commit fe56ec6` 解析成 bash 指令 | 3 則 sendMessage,第 3 則的參數含該行 |
| 5 | `mine-session.py` 的 `loop guard` marker 是 `重複`,而全 session 的 3 次 `重複` 全來自 transformer 自己 | 報表印 `loop guard 3`,實際 **0** |
| 6 | 批次崩壞:113 次呼叫分佈在 122 個 turn(對照 `019fe72a` 的 `2/4/4/4`) | n=1,**只記錄不追** |
| 7 | **缺陷 1 的守衛早就存在,而且早就是紅的** | `Ran 1454 tests` / `FAILED (failures=2)`,兩個失敗同一缺陷,而且是 **18 個技能**不是 14 個 |

**第四個教訓(排完佇列才學到的):守衛在響,而沒有人聽。**
本輪在規劃階段一度打算「新增一支可達性檢查」——
`test_skill_catalog_staleness.py` 與 `scripts/validate-config.py` 都已經在報同一件事,
訊息裡連補救指令都寫好了。多出來的四個技能之一是 **`thinking-frameworks`**,
而 **CLAUDE.md 的方法論路由指名它**。
「先查既有再動手」這條規矩需要一個自體版本:**動手設計守衛之前,先跑自己的測試套件。**

**這一天真正的教訓:缺陷 3 是流程缺陷,不是程式缺陷。**
[2026-07-29 換模型驗收清單](docs/retro/2026-07-29-model-swap-checklist.md) §1 第一條就是
「確認 server 實際載到的 chat template」,理由原文寫著「llama.cpp 對這件事**不報錯**」。
清單早就對了,它沒有被跑 —— 因為它是一份要用眼睛讀的 markdown。
**換 bridge 有 `verify-bridges.py`、換設定有 `validate-config.py`、換提示有 `check-prompt-conflicts.py`;
換模型只有一份文件。**

**第二個教訓:一則訊息的第一個問題是「聽眾是誰」。**
GateGuard 的文字是對的,送給成功的結果就變成 28 次無用呼叫;
`📝 偵測到新學習點` 送給了看螢幕的人,而它想推動的動作只有模型能做。

**第三個:技能可達性有三層,不能混為一談** —— 載不到 / 看得到但不知何時用 / 知道卻沒人點名。
[Round 15](docs/mece/rounds/2026-08-13_round15_註冊了但沒有人叫它.md) 修的是第三層;
這次發現有 14 個卡在第一層。**本次量測自己一度也判斷錯**(用 `~/.pi/agent/skills` 的目錄內容
推論 external 技能不見了,實際上它們由 `skill-namespace-guard` 在 `resources_discover` 動態註冊)——
更正寫在量測文件裡,因為那個陷阱本身會重演。

---

## 2026-08-15:六個修法之後,誰在檢查我們

[Round 17](docs/mece/rounds/2026-08-15_round17_八個修法之後誰在檢查我們.md) 不看缺陷,看**修缺陷的過程**。
動筆前四個查詢,四個都回了東西:

| 查的 | 結果 |
|---|---|
| CI 有沒有裝 node | **沒有**。只有 python 3.12 |
| CI 什麼時候跑 | 只認 `main` 的 push / PR ——**這條分支八個 commit,零次 CI** |
| 幾個測試檔掛在 `skipUnless(NODE_OK)` | **38 個**(`test_universal_tool_parser` 一檔就 123 條) |
| constructor 參數屬性這個坑之前記過嗎 | `goal-restate.ts:130` 記過,**我今天又撞一次** |

**`skipUnless` 不會失敗,它會消失。** node 沒了或版本退了,那 38 個檔靜默跳過,
`Ran N tests, OK` 依然綠,而**沒有人在看 N**。

**這個 repo 真正的失敗模式不是不知道,是知道了沒有執行點。** 三次同一個形狀:
換模型清單 §1 寫對了沒人跑(已修成程式)、`goal-restate.ts:130` 記了沒有檢查(今天補上)、
`guard-mutation-allowlist.json` 的 `_comment` 自己寫著「鍵用行號會過期」而且**已經過期兩次**,
設計沒換過(立案,不在這一輪做)。

**已做(Round 17 的 SO,四件都便宜、都會紅、都不改行為):**

1. **CI 釘住 node 22**(`actions/setup-node@v4`)—— 38 個檔在 runner 上才真的跑
2. **`tests/test_node_is_available.py`** —— node 不在或 < 22 就**紅**,
   而不是靜默跳過;要退讓得明講 `HARNESS_ALLOW_NO_NODE=1`。
   附帶檢查 workflow 真的有裝、且版本 ≥ 22
3. **命名空間補完**。Round 16 說「一個前綴讓整套方言穿過所有偵測器」,
   而修法只做了兩處。這次逐條掃:`PARAM_TAG_PATTERN`、`<invoke name=>` fallback、
   `<tool_call>` wrapper、`<function=>` 與它的計數、Laguna 分支 —— **又補了六處**。
   **修一半比不修更危險**,因為註解讀起來像做完了。
   新增的檢查斷言的是**集合**:任何一條新的工具呼叫正則沒有前綴就紅
4. **`tests/test_bridge_ts_syntax.py`** —— constructor 參數屬性、`enum`、`namespace`、
   decorator,這些在 Node 的型別剝除下**會直接載不進去**,而載不進去的 bridge 是靜默失效的 bridge。
   範圍只收「會 fail to load」的,不做風格檢查 —— 會被關掉的檢查等於沒有

**動手時抓到的兩件事(兩次都是「檢查不會失敗」):**

* 第一版的一致性檢查用 **40 字元回看**判斷前綴在不在,而那個窗會**跨行** ——
  隔壁那條正則的前綴就能滿足它。把一條正則改回舊版,檢查**依然綠**。
  改成精確比對緊鄰字元後,同樣的改回會紅在正確的行號
* 同一條檢查第一版把**拒絕訊息裡列舉標籤的句子**當成正則,誤報三次。
  會對自己的文件開火的檢查會被關掉,所以加了字串字面值的排除

**未做,已立案:** allowlist 的鍵改用程式碼指紋而非行號(機制設計,不是一個 grep);
待驗證項目的自動重查。

**驗證:**

```
python -m unittest discover -s tests   ->  Ran 1549 tests, OK (exit 0)
verify-bridges 13 bridges 0 failures / validate-config 0 failures / prompt-conflicts 0 failures
```

**2026-08-15 已合併進 main 並跑過 CI**(run `31872614550`,`conclusion: success`):

```
Install Node ... node-version: 22
Ran 1549 tests in 79.026s
OK (skipped=28)
```

**本機 1549 / 0 skip,CI 1549 / 28 skip,總數相同。**

**這裡要更正上面的推測。** 那 28 個 skip 逐條看過,**沒有一個與 node 有關**:

```
7  external/ecc submodule is not checked out     (CI 的 checkout 不拉 submodule,已知)
6  run scripts/restore.py first
6  junctions are a Windows construct
2  yes.md guard or sh executable not available
2  the launcher/child split is a Windows problem
2  ecc submodule not initialized
1  skill-catalog.json is generated by restore.py
1  no local Pi sessions to read
1  external/yes.md is not checked out here
```

**所以 node 本來就在 runner 上,那 38 個檔一直有在跑。**
Round 17 說的是「**可能**靜默跳過」,量出來的答案是**沒有在跳**。
釘住 node 移除的是**潛在風險**,不是修好一個正在發生的故障 —— 兩者不同,
而把後者寫成前者就是這個 repo 反覆抓的那種誇大。
`test_node_is_available.py` 仍然值得留:它把「我們依賴 runner 映像檔碰巧帶什麼」
變成「我們要求它,而且少了會出聲」。

**同一次 CI 給了一個新的待辦並已修**:`actions/setup-node@v4` 被註記
「Node.js 20 is deprecated … being forced to run on Node.js 24」——
今天是強制轉移,之後會是壞掉。已改為 `@v5`。

---

## 2026-08-16:一個空變數,把每個專案的工作扯回 harness

擁有者跑了 `01a004bc`,回報三件事:跨出資料夾後 pi 不知道 C.A.S.E. 是什麼、
會回本資料夾找 `verify.py`、整體「很零碎且難以驗證有沒有幫助」。

量測:[docs/measurements/2026-08-16-harness-root-and-skill-reach.md](docs/measurements/2026-08-16-harness-root-and-skill-reach.md)

**前兩件有單一根因,而且是我們自己造成的。**
`/case` 指令的內文自己叫模型去跑 `$PI_HARNESS_ROOT/external/.../bootstrap.py`
並讀 `$PI_HARNESS_ROOT/.../SKILL.md`,而**那個變數一直是空的**:

```
call bash  echo "[$PI_HARNESS_ROOT]"
res        []
```

`restore.py:944` 寫進 `settings.env.PI_HARNESS_ROOT`,`pi-rules/AGENTS.md:21` 對讀者說
「injected by scripts/restore.py」—— **兩句都不成立**。安裝版 `Settings` 介面
(`core/settings-manager.d.ts:66-116`)**沒有 `env` 欄位**,執行期不讀它。
**十處指示指向一個空字串。**

**它為什麼活這麼久:每次稽核打開 `settings.json` 都看得到那個值,然後就停在那裡。**
配置存在 ≠ 送達 —— 這個月第四次以不同形狀出現。

**修法**:`skill-namespace-guard` 在註冊時設 `process.env.PI_HARNESS_ROOT`
(bash 工具每次呼叫都從 `process.env` 重建環境,`utils/shell.js:103`)。
輸出前驗證該路徑底下同時有 `pi-extensions/` 與 `pi-skills/` ——
`package.json` 出貨時是 `TODO_SET_BY_RESTORE`,而**錯的路徑比空字串更糟**,
兩個候選都不合格就維持不設定。不覆寫操作者自己 export 的值。
`restore.py` 改成 `settings.pop("env", None)` 清掉殭屍區塊。
`AGENTS.md` 改寫成:空值時**停下來講,不要靠猜路徑找 harness,不要離開被指派的專案**。

**三層驗證**:單元 7 條 / 安裝副本 `before "" → after "D:/..."` 且子行程讀得到 /
真實 Pi session 寫出 `root.txt` 內容正確、3 個 tool call。

> **第一次的 live 探針是無效的,記在這裡。**
> 問「echo 這個變數然後停止」,模型回了 `` `ROOT=[D:\...]` ``,而 session
> **0 個 tool call** —— **它捏造了輸出**。反斜線是識破的線索:修法路徑只產生正斜線。
> 改成「寫進檔案」才拿到真證據。**這條本身是發現:新模型會編造指令結果,回覆看起來完全正常。**

**第三件事可以量,答案不好看但明確**(125 個真實專案 session、4176 次呼叫):

| | session | tool calls | 有開過技能 | 碰到 harness 路徑 |
|---|---|---|---|---|
| harness 自己 | 72 | 1344 | 5 | 67(4%) |
| **其他專案** | **53** | **2832** | **10(19%)** | **218(7%)** |

**在別人的專案裡工作時,7% 的呼叫花在 harness 目錄**;擁有者那個 session 的 18% 是極端值不是特例。
**而 CLAUDE.md 現在還寫著「228 次呼叫碰到 harness 1 次」—— 那個基準已經過期**,
它取樣的是 `/case` 指令存在之前。

**修掉變數只解決「找不到」,沒有解決「協定本體不在專案裡」** —— 後者是設計取捨,立成 T-A24。

---

## 這一週的收穫:六條,全部是同一種形狀的變形

2026-08-14 到 08-16,八件工作、十一個 commit、兩次 CI。把它們的成因排在一起,
會看到同一個東西反覆出現:**一個機制存在、被記錄、甚至被檢查,而它的輸出沒有到達任何人。**

### 1. 配置存在 ≠ 送達(這一週出現四次)

| 東西 | 存在於 | 到不了 |
|---|---|---|
| `settings.env.PI_HARNESS_ROOT` | `~/.pi/agent/settings.json` | Pi 的 `Settings` 介面沒有 `env` 欄位 |
| `hello-reflect` advisory | 每個 session 講 5 次 | 技能三條註冊路徑都不在 |
| `📝 偵測到新學習點` | 每個 turn 一次,共 122 次 | `notify` 只畫 TUI,模型看不到 |
| ECC GateGuard 阻擋型原文 | 貼在 tool result 後 | 貼在**成功**的結果後,語意反轉 |

**共同的失敗動作:稽核時打開檔案、看到值、就停手。**
四個都是「打開 `settings.json` 看到 `PI_HARNESS_ROOT` 有值」那一類的滿足感。
**驗收要驗到接收端**,不是發送端。

### 2. 有效的補救,比沒有補救更會藏住成因

`test_skill_catalog_staleness.py` 從 2026-08-04 就是紅的,而它印的補救
「re-run restore」**真的有效**。紅了就重跑、綠了就過去,**十天沒有人問它為什麼一直回來**。
成因是 `--config-only` 的 early return 落在 catalog 折入之前 —— 兩道指令就分岔得出來。

**它把「為什麼會壞」換成了「怎麼修好」,而後者每次都成功,於是前者永遠不會被問。**

### 3. 知道了沒有執行點(三次)

* 換模型清單 §1 寫對了,沒有人跑 → 六個半小時的 session(已變成 `check-model-serving.py`)
* `goal-restate.ts:130` 記了 constructor 參數屬性會炸,沒有檢查 → 我又撞一次(已變成 `test_bridge_ts_syntax.py`)
* `guard-mutation-allowlist.json` 的 `_comment` 寫著「鍵用行號會過期」,而且**已經過期兩次**,連結論都寫了(T-A23,先量再決定)

**一條註解會變成檢查,或者變成考古。**

### 4. 修一半比不修更危險

Round 16 說「一個命名空間前綴讓整套方言穿過所有偵測器」,而修法只做了兩處。
Round 17 逐條掃,**又找到六處**。
**危險的不是漏掉,是那兩處的註解讀起來像做完了** —— 下一個人會相信它。

### 5. 綠燈也要查證據(我自己犯的)

Round 17 主張「38 個測試檔可能在 CI 上靜默跳過」。合併後第一次 CI 的答案是
`Ran 1549 / OK (skipped=28)`,28 個 skip 逐條看過**沒有一個與 node 有關** ——
node 本來就在 runner 上。**釘住它移除的是潛在風險,不是修好一個正在發生的故障。**
把後者寫成前者,就是換個方向的誇大。

### 6. 模型會捏造輸出,而回覆看起來完全正常

驗證 `$PI_HARNESS_ROOT` 的第一次 live 探針:問「echo 這個變數然後停止」,
模型回了 `` `ROOT=[D:\MyProject\CKs_PI_Code_Agent_Harness]` ``,
而 session 只有 5 筆記錄、**0 個 tool call**。
**反斜線是識破的線索** —— 修法路徑只會產生正斜線。
改成「寫進檔案」才拿到真證據(3 個 tool call,檔案內容正確)。

**推論:任何 live 驗證都要留下模型無法憑空產生的痕跡**(檔案、session 裡的 tool call),
不能只看它說了什麼。

---

## Task Queue

> **2026-08-14 新增(Round 16 TOWS)—— T-A12 ~ T-A20。**
> 家族順序 **A 儀器 → B 服務層與產出完整性 → C 可達性與通道紀律 → D 解析與待量**。
> A 無條件第一:其他三家的排序判斷都由 `mine-session.py` 讀出來,而它現在會把
> 別的機制的訊息算成 loop guard 的三次拒絕。

> **2026-08-11 起的排序原則(Round 14 TOWS):**
> SO 先做(用現成工具鏈在真實專案做乾淨實驗)→ WO 次之(校準參數移出程式碼)→
> ST 是紀律不是任務(任何 pp 宣稱必須附 model+harness 配置與樣本數)→
> WT 是排序原則(便宜且二元的先做,昂貴的量測往後)。

### ✅ T-A12 — 量測儀器在說謊(**DONE,2026-08-14;等 Path A 核可**)

* **為什麼**:`scripts/mine-session.py` 的 `REFUSALS` 表把 `loop guard` 對到 marker `重複`。
  session `019ffbdd` 裡 `重複` 只出現 3 次,**全部來自 `universal-tag-transformer` 自己那句
  「(原文不在此重複,以免你再照著寫一次。)」**。報表印 `loop guard 3`,實際是 **0**,
  而且同一批訊息已經正確地列在 `customType` 區塊 —— **同一批訊息被數了兩次,掛在兩個機制名下**
* **服務哪一層**:所有其他任務的排序判斷都由這支程式讀出來
* **不要做過頭**:不是重寫 marker 機制,是讓每個 marker 足以識別它宣稱的那個機制
* **動手後查到的比原本記的多。** 對 `pi-extensions/**/*.ts` 逐條比對 marker:
  * **3 個 marker 在任何 bridge 原始碼裡都不存在** —— `queue guard`/`C.A.S.E. 任務佇列`
    (被 per-rule 標籤取代後留下的傘狀項)、`research depth`/`研究深度`、`citation gate`/`引用`
  * **`引用` 才是真正危險的那個**:死掉的 marker 不會安靜。它對自己的守衛沉默,
    對其他所有東西大聲 —— 在一個中文 session 上它報了 2 次,全來自散文
  * **`Artifact guard` 根本沒有 marker**,所以這支程式產出過的每一份報告裡它都是隱形的
  * **`customType` 不指認機制,只指認 bridge**:`loop-guard` 這一個型別在 yes-hooks-bridge
    裡有 **7 個發送點**(重複呼叫斷路器、blocked-claim 的檔案與網路兩個分支、
    輸出上限提醒、transformer 三振交還、假工具三振)
* **所以最終設計是兩層**:型別認 bridge(擋掉跨 bridge 誤標),措辭在型別**允許的標籤集合內**分辨;
  兩者都不中的訊息只在 `custom messages` 區塊按型別記一次,不猜
* **這條檢查本來就有,只是只查了一半。** `test_every_declared_label_still_exists_in_a_bridge`
  存在,但只掃 `INJECTIONS` 不掃 `REFUSALS` —— 三個死 marker 就是從那個缺口活下來的
* **Local DoD**:
  - [x] `loop guard` 的 marker 換成迴圈守衛實際輸出的字串(`發出了完全相同的呼叫`,自原始碼取)
  - [x] 對 `019ffbdd` 重跑:`loop guard` 消失(原 3,實際 0)、`citation gate` 由 2 修正為 1、
        `tag transformer 3` 正確歸位到注入表
  - [x] 新增四條檢查:死 marker(擴到 REFUSALS)、marker 互為子字串、
        每個 bridge 宣告的 `customType` 都要被認領、允許清單裡的標籤必須真的存在
  - [x] **證明四條都會紅**:舊表的 3 個死 marker、植入 `Depth guard` 觸發子字串衝突、
        移除 `loop-guard` 觸發未認領、植入 `typo-label` 觸發不存在標籤 —— 四條各自回報非空
  - [x] `python -m unittest discover -s tests` → `Ran 1460 tests` / `FAILED (failures=2)`,
        兩個失敗都是 **T-A16 的既有缺陷**(修改前是 `Ran 1454 tests` / 同樣 2 個失敗),沒有新破的

### ✅ T-A13 — 換模型沒有守門員(**DONE,2026-08-14;等 Path A 核可**)

* **為什麼**:`</atem:日>` 24 次的根因是 server 載到的 chat template 教模型用
  `<atem:function_calls>/<atem:invoke>/<atem:parameter>` 發工具呼叫,而 Pi 走原生 `tool_calls`。
  [換模型驗收清單](docs/retro/2026-07-29-model-swap-checklist.md) §1 第一條就是查這個,
  **它沒有被跑,因為它是一份要用眼睛讀的文件**
* **外部佐證**:[llama.cpp #24189](https://github.com/ggml-org/llama.cpp/issues/24189)
  —— 有 `--mmproj` 時 llama-server **靜默忽略** `--chat-template-file`;
  本次 `/props` 回報 `"modalities":{"vision":true,"video":true}`
* **服務哪一層**:L1/L2 的前提。模板不對時,守衛全部照常綠燈而產出全部帶垃圾
* **層歸屬**:**檢查在 repo,設定在機器。** repo 不出貨任何模型預設值 ——
  這支程式報告不一致,不修改任何 server 設定
* **時效性決定了它插隊到 T-A17 前面**:壞掉的 template **當時還在 server 上跑著**,
  所以有一個活的失敗樣本可以對著寫。第一個動作是趁它還在,把 `/props` 的 `chat_template`
  釘成 fixture:`tests/fixtures/chat-template-atem.jinja`,9,532 bytes,
  sha256 `6bbce2a5b3b0f154935b89c9efb0a8caf19119a9c478b268f2359e2a0946a4b2`。
  釘 bytes 而不是描述它,因為這一整類故障就是「server 載到的東西不是任何人以為的東西」——
  照著印象寫的 fixture 會把同一個錯誤再犯一次
* **正例是真實 bytes,反例是 stock ChatML**(219 bytes,真實存在的 template,短所以直接寫出來)
* **偵測器的關鍵是前綴**:`<atem:invoke` 不匹配 `<invoke\b` —— harness 自己的
  `FAKE_TOOL_CALL_PATTERN` 就是這樣被繞過的,所以命名空間前綴寫進 pattern 而不是事後補
* **「渲染方言」與「教模型寫方言」分開**:只渲染是 WARN,教它寫才是 FAIL。
  兩者不分開,這個檢查會變成所有人繞過的閘門
* **Local DoD**:
  - [x] `scripts/check-model-serving.py`,三件事都查:
        (a) `chat_template` 的工具呼叫方言(anthropic-style XML / `<tool_call>` /
        `<function=>` / `<tools>`,含命名空間前綴);(b) `--expect-model` 比對
        `model_path` 與 `model_alias`;(c) `/v1/chat/completions` 是否 200 而非載入中的 503
  - [x] **證明它會失敗**:對釘死的真實 template →
        `FAIL: … teaches the model to emit tool calls as anthropic-style XML
        (<atem:function_calls>, <atem:invoke name=, <atem:parameter name=)`,exit **1**;
        對 ChatML → `0 failure(s), 0 warning(s)`,exit **0**;
        `--expect-model nonexistent-model` → exit **1**
  - [x] 落 `pi-config/serving-check-report.json`(已加入 `.gitignore`,機器專屬)
  - [x] server 沒開 → `SKIP: nothing answered at …`,exit **0**
  - [x] 換模型清單 §1 改成指向這支程式(手動步驟保留,說明它在看什麼);
        CLAUDE.md 指令清單已列出並標為換模型後第一件事
  - [x] 進 CI(`.github/workflows/ci.yml`),runner 上必然 SKIP ——
        目的是**讓這支程式保持跑得起來**,沒有人執行的檢查會和它取代的那份清單一樣爛掉
  - [x] 17 條測試,全部不需要 server;`python -m unittest discover -s tests` →
        **`Ran 1482 tests` / `OK`**(exit 0)

> **2026-08-15 第一次真實使用就抓到這支檢查自己的缺陷。**
> 擁有者換到 `Qwen3.8-27B-Uncensored-Q6_K`,檢查回報 0 failures —— **但理由是錯的**。
> 它說「template 沒有教模型寫方言」,而那份 template 白紙黑字寫著
> `If you choose to call a function ONLY reply in the following format` 與
> `<IMPORTANT> Function calls MUST follow the specified format`。
> `TEACHES` 那條正則只認 "you can/should/must invoke/call/use",漏了這個講法。
>
> **更重要的是判準本身錯了。** 對這份 template 送一個帶 `tools` 的真實請求:
> `finish_reason: tool_calls`、參數 `{"path":"README.md"}`、`content` 空 ——
> **llama.cpp 有 qwen/hermes 家族的解析器,把它收回成原生呼叫。**
> 所以「教方言 ⇒ 壞掉」有反例了。**教方言不是缺陷,教一個沒人讀得回來的方言才是。**
>
> 修法三件:(1) `DIALECTS` 標註每個方言**伺服器端有沒有解析器**,
> anthropic-style 是 `False`(llama.cpp 沒有),qwen/hermes 是 `True`;
> (2) 補 `TEACHES` 的講法,並明講「對散文做啟發式判斷還會再漏」;
> (3) 加**活體往返探測** —— 送一個工具,要求拿到原生 `tool_calls`,
> 並檢查回來的參數有沒有殘留。**探測的位階高於所有啟發式**,
> 因為 jinja template 是散文,而散文的啟發式已經錯過一次了。
>
> 兩份 template 現在都是 fixture:ATEM(教 + 不可解析 = FAIL)、
> QWEN(教 + 可解析 = WARN,`c3cf9e34…`)。兩者**都教**,只有一個壞 ——
> 測試明確斷言這個區分,collapse 成一個答案就是又弄丟了。

> **⚠️(已由 2026-08-15 換模型解除)這台機器當時是紅的。** `python scripts/check-model-serving.py` 對活著的 server
> 回報 1 failure + 1 warning(mmproj 已載入)。**修法是操作者重開 server**,
> repo 不出貨模型預設值,這支程式也不會去改它。
> 在那之前,這台機器上的每一次 Pi run 都還會把 `</atem:parameter>` 寫進檔案。

### 🟡 T-A14 — 殘留標籤要清掉,而且要對操作者出聲(**已上線;送達已證明,live 觸發 0 次**)

* **為什麼**:`</atem:日>` 全部落在**最後一個參數的結尾**;有一次最後一個參數是 `path`,
  於是 `ENOENT ... mkdir '…\.gitignore<'`。`yes-hooks-bridge` 的 `FAKE_TOOL_CALL_PATTERN`
  認得 `<invoke\b` 與 `<parameter\s+name=`,**但 `<atem:invoke` 不匹配** ——
  正則寫死了沒有命名空間前綴的形式,任何帶前綴的方言都會重演
* **Round 16 的約束(老魔 + 秦姐)**:**默默過濾會把根因藏起來**,重演 citation gate 的規避形狀;
  而**模型不是這則訊息的正確聽眾** —— 它改不了自己的 chat template,對它說只會浪費一輪,
  那正是 T-A18 那條缺陷的形狀。**所以:清掉,但對操作者出聲,不對模型出聲**
* **服務哪一層**:每一個被寫出去的檔案
* **`.d.ts` 說參數可以改,而 CLAUDE.md 漏了這條。** 安裝版
  `core/extensions/types.d.ts` 的 `ToolCallEventResult` 註解原文:
  `Block tool execution. To modify arguments, mutate event.input in place instead.`
  —— 所以「對模型無聲、對操作者留痕」是做得到的,不必用 block 去煩模型
* **與 runaway guard 的邊界(兩個守衛撞在一起,讓給抱怨比較好的那個)**:
  `runawayArgumentGuard` 已經會擋任何帶工具語法的參數,而對 `command` / `query`
  它的抱怨更好 ——「你越過呼叫結尾繼續生成」是模型可以修的行為;
  template 殘留不是(模型改不了自己的 template),所以 **write/edit 用修復,其餘留給它擋**。
  第一版把 `query` 也納入,直接讓 `test_universal_tool_parser.py` 三條測試轉紅,
  那三條寫著「Size is not the tell」—— 那是一個既有決定,不能默默反轉
* **Local DoD**:
  - [x] `FAKE_TOOL_CALL_PATTERN` 與 `ARG_SYNTAX_LEAK` 都認得帶命名空間前綴的形式,
        註解寫上 session id 與原因
  - [x] `write`/`edit` 的參數在其他守衛讀到之前就剝除(handler 的第一件事 ——
        `…/.gitignore</atem:日>` 這種 path 會讓 containment 與 harness-root 判斷錯的字串)
  - [x] 留痕走 `ctx.ui.notify` + `pi-config/serving-mismatch-report.json`,**不進 `tool_result`**;
        且**整個 session 只通知一次**(量到的那次會產生 24 則 —— 就是
        `📝 偵測到新學習點` 那個失敗)
  - [x] 測試用真實 session 取出的字串(`</atem:日>` 為常數,改了就紅)
  - [x] 從公開入口點 `pi.on("tool_call")` 驅動並斷言修復 + 不 block + 通知內容
  - [x] 反向也守:`</xsl:template>`、`</svg:path>`、`<w:p>` 與**標籤在字串中間**皆不動
  - [x] 進變異掃描涵蓋清單;`--only dialect-residue --all` 窮舉掃過,
        **三個存活者補成測試**(非字串輸入、8 層堆疊、殘缺 `edits` 陣列),
        只留一條豁免(迴圈上限 `8->9`,理由寫在 allowlist)
  - [ ] **live 觸發:0 次。** 兩次真實 Pi 探針(短英文一次、長中文三檔一次,
        server 仍是同一份壞 template)都是 `atem: 0` —— 模型沒吐殘留,
        守衛就沒有條件可以觸發,`serving-mismatch-report.json` 也沒產生。
        **依本 repo 的規矩,這叫未驗證,不叫可用。**
        **觸發條件(先寫下來,之後拿真實 session 對):**
        某個 session 的 `toolCall.arguments` 裡出現 `atem`,且
        `pi-config/serving-mismatch-report.json` 存在
* **順帶量到的**:殘留是**間歇性**的 —— 6.5 小時的 session 出現 24 次,
  兩個短探針一次都沒有。與本 repo 既有的「工具呼叫格式在大提示下退化」是同一族,
  也代表**短探針無法驗證這個守衛**

### 🚫 T-A15 — 已經寫壞的 20 個檔案(**2026-08-14 擁有者決定保留,不做**)

> **擁有者原話:「T-A15 留著我有用。」** 原文保留 ——
> 一個沒有寫下來的否決會被下一個人重做。
> **仍然成立的部分**:那 20 個檔案是 T-A14 修好之後的現成驗收樣本;
> 若日後要驗「新產出不再帶標籤」,對照組就在那裡。


* **為什麼**:`D:\MyProject\test-20260813-cyber-patrol\investigation_2026_taiwan_local_election\`
  底下 **20 個 `.md` 帶著 `</atem…`**(`grep -rl "</atem" … | wc -l` = 20)。
  那是擁有者真的要用的情資文件,不是測試資料。**修好 harness 不會讓已經寫壞的檔案自己乾淨**
* **Round 16 記下的規矩缺口**:本 repo 已有「探針要自己收拾殘骸」,
  但那條只涵蓋**我們跑的探針**;這次是**使用者真實 run 的殘骸**,規矩沒涵蓋,差點沒人提
* **需要擁有者決定**:那個專案不歸 harness 管,清理要不要動由擁有者說了算
* **Local DoD**:
  - [ ] 擁有者確認要清
  - [ ] 清理前先備份(該目錄有 git,確認 commit 過再動)
  - [ ] 清完重跑 `grep -rl "</atem" … | wc -l`,輸出 0,把指令與輸出貼進本檔

### ✅ T-A16 — 18 個技能載不到,而**守衛早就在響**(**DONE,2026-08-14;等 Path A 核可**)

* **為什麼**:`hello-reflect` 不在 `~/.pi/agent/skills`(restore 的 `managed_skills` 主動刪)、
  不在 `skillTiers.core`、**也不在這台機器的 `pi-config/skill-catalog.json`**。
  而 `ecc-hooks-bridge` 每個 session 叫模型「Use the hello-reflect skill」5 次
* **⚠️ 排佇列之後才跑測試套件,發現這支守衛已經存在且已經是紅的**
  (`python -m unittest discover -s tests` → `Ran 1454 tests` / `FAILED (failures=2)`):

  ```
  FAIL: test_every_demoted_local_skill_is_reachable (test_skill_catalog_staleness)
        … reachable by no route at all; re-run `python scripts/setup.py --mode restore`
  FAIL: test_repo_as_shipped_passes (test_validate_config)
        FAIL: 18 local skill(s) are neither natively registered nor in the catalogue …
  ```

  **是 18 個不是我先數的 14 個** —— 我只查了 `pi-skills/core`,檢查同時涵蓋 `optional`。
  多出來的四個是 `camofox-stealth`、`cua-commander`、`nothing-design`、**`thinking-frameworks`**
* **`thinking-frameworks` 要單獨看**:**CLAUDE.md 的方法論路由指名它**
  (「一個有取捨的決定 → `thinking-frameworks` / `mece-autopilot` / `qiushi`」)。
  專案最上層的指示叫模型去用一個載不到的技能 ——
  與 2026-08-12 的 `planning-with-files` 是同一個形狀,那次是名字不對,這次是東西不在
* **所以這一條的問題不是「沒有守衛」,是「守衛在響而沒有人聽」**,
  與 T-A13 的「清單存在而沒被跑」是同一件事換了地方發生
* **機制假說(程式路徑已證,本機觸發為推論)**:`restore.py:1035` 的 `write_catalog` 先用
  「只有 external」的清單覆寫 catalog;把本地降級那批折進去的 `merge_into_catalog` 在約 1236 行,
  而 `--config-only` 的 early return 在 **1175 行,擋在中間**。
  兩個檔案 mtime 同為 `2026-08-13 23:58:08`,catalog 缺的恰好就是本地那批。
  另有旁證:手動呼叫 `merge_into_catalog(path, tail)` 得
  `lost []` / `total 116` / `hello-reflect present: True` —— **函式沒壞,是流程沒走到它**
* **服務哪一層**:[Round 15](docs/mece/rounds/2026-08-13_round15_註冊了但沒有人叫它.md)
  的第三層之下那一層(**載不到**)
* **這是同一個缺陷的第三次**,而且 `tests/test_skill_catalog_staleness.py` 的檔頭把
  **2026-08-04** 那次寫得清清楚楚(「104 entries, all under external/*, 0 from pi-skills …
  hello-reflect, thinking-frameworks, grilling-protocol, camofox-stealth 與另外十一個
  註冊在哪裡都沒有、編目在哪裡也沒有」)。**檢查寫了,原因沒查。**
* **為什麼一個有效的補救反而藏住了缺陷**:那條檢查印的補救是「重跑 restore」,
  而重跑**真的會好**。於是每次紅了就重跑、綠了就過去,
  沒有人問它為什麼一直回來。**一個有效的補救,比沒有補救更會藏住成因。**
* **根因(已用實驗確認,可重現)**:`--config-only` 的 early return 在本地名單折入之前。
  同一台機器上依序跑:

  ```
  restore --auto --profile standard              -> 120 entries, hello-reflect: True,  validate 0 failures
  restore --auto --profile standard --config-only -> 102 entries, hello-reflect: False, validate 1 failure
  ```
* **修法**:抽出 `merged_catalog_entries()`,在 catalog 被寫出的**同一個運算式**裡
  把 external 與 local 兩批合起來。不再有先後,也就不再有 early return 能把它們拆開
* **Local DoD**:
  - [x] 跑 `python scripts/restore.py --auto --profile standard < /dev/null`(非互動)
  - [x] 兩個檢查**轉綠** → `--config-only` 假說成立;
        catalog 102 → **120**,`hello-reflect` / `thinking-frameworks` / `deep-research-guide` 皆為 True
  - [x] **決定性實驗**:修法前跑 `--config-only` 重現 102 / 1 failure;
        修法後同一道指令得 `22 core registered, 120 in catalog (18 of them local)` / **0 failures**
  - [x] 本地降級名單在 catalog 被覆寫的**同一次寫入**折進去(`merged_catalog_entries()`)
  - [x] 五條防迴歸測試,斷言對象是**決定它的那個函式**而不是磁碟上的檔案 ——
        磁碟狀態會被下一次 restore 修好,而那正是這個缺陷藏了十天的方式
  - [x] **證明會紅**:把該函式換回修法前的行為,standard 少 **18** 個、minimal 少 **14** 個;
        修法後兩者皆 0,且 external 條目仍在(反向也守)
  - [x] `python -m unittest discover -s tests` → **`Ran 1465 tests` / `OK`**(exit 0)。
        修改前是 `Ran 1454 tests` / `FAILED (failures=2)`,**兩個失敗都消失了**
  - [x] `python scripts/verify-bridges.py` → `13 bridges checked, 0 failure(s) found`
        (restore 重裝後安裝與 repo 仍相符)

> **延後、不假裝做完的部分**(移到 T-A21):
> 把 `tests/test_skill_names_resolve.py` 擴到 **CLAUDE.md 與 bridge 注入文字裡點名的技能**,
> 以及一支同時看四條可達路徑的查詢。兩者都不是本條的根因修復,
> 而且第二個要先決定「可達」的權威定義 —— 本次量測自己就先用單一路徑判斷錯過一次。

### ✅ T-A17 — `📝 偵測到新學習點` 這段程式的三個附帶缺陷(**DONE,2026-08-15;等 Path A 核可**)

* **為什麼**:`pi-extensions/ecc-hooks-bridge/index.ts:457`
  1. `notify` **沒有去重**(同段的 advisory 是 `"once"`,notify 不是)—— 122 個 turn 噴 122 次
  2. 每個 `turn_end` 都 `execSync` 起一個 python 行程,並**遞迴掃過整個 `~/.pi/agent/sessions`**
     (這台機器 20 個 workspace 目錄)。6.5 小時 = 122 次行程啟動 + 122 次全域掃描
  3. 它挑「**全域 mtime 最新**的 `.jsonl`」,**不保證是當前 session** ——
     同時開兩個 Pi 就會讀到另一個專案的紀錄。這是歸因缺陷,也是稽核問題
* **服務哪一層**:使用者實際看到的症狀 + 每輪成本
* **依賴**:第 1 點修完之後那則訊息才有意義,而「有意義」需要 T-A16 先讓技能載得到(已完成)
* **`getSessionFile()` 一直都在**:`ReadonlySessionManager` 的成員之一
  (`core/session-manager.d.ts:140`)。第 3 點根本不必用 mtime 猜 ——
  同一族的教訓:「先讀安裝版的 `.d.ts`,不要照記憶寫」
* **邏輯抽成 `reflect-budget.ts` 而不是留在 handler 裡**:
  `ecc-hooks-bridge` 在裸 node 下匯入不了(Pi-only 依賴),
  `tests/test_bridge_handlers_run.py` 明列它「not importable」,
  所以**沒有任何測試能驅動它的 handler**。這正是「一個未宣告變數撐過 774 個測試、
  三個檢查與逐位元組相同的安裝」那條疤 —— 會錯的邏輯要搬到測得到的地方
* **notify 與 advisory 分開判定,不合併**:notify 是擁有者回報的那個(只畫 TUI、到不了模型、
  122 次);advisory 是**唯一到得了模型**的一半,它的 `"once"` 是每個 drain 週期一次,
  在 019ffbdd 送達 5 次。**把模型通道砍成整個 session 只講一次是另一個決定**,
  不是這次被要求的;掃描上限本身已把它壓到最多 3 次
* **Local DoD**:
  - [x] notify 一個 session 最多一次(`ReflectBudget.claimNotice()`)
  - [x] 不再每個 turn 掃全域:改用 `ctx.sessionManager.getSessionFile()`;
        **拿不到就跳過,不退回 mtime 掃描** —— 那個退路就是歸因缺陷本身
  - [x] 不再每個 turn 起行程:上限 3 次,且兩次之間 transcript 要長 ≥20KB。
        **不是「只跑一次」** —— 第 2 個 turn 掃到的是還沒有內容的 transcript,
        原本每個 turn 都跑正是為了最後能看到一個長的
  - [x] 12 條測試驅動真實模組:122 個 turn 的尺寸序列 → **掃 3 次**(原本 122 次)、
        通知 50 次 → **只有第一次為真**、沒長大就不重掃、續接的大 session 仍有第一次掃描、
        壞掉的 size(-1 / "x" / null)不燒預算
  - [x] 窮舉變異掃描 **0 存活者**,無豁免;`test_mutation_coverage` 涵蓋清單已加入
  - [x] `python -m unittest discover -s tests` → **`Ran 1539 tests` / `OK`**;
        `verify-bridges` 13 bridges 0 failures(已 restore 安裝)
  - [x] 真實 session 跑過(31 turn / 130KB,足以跨過 20KB 門檻六次),bridge 未報錯。
        **但 notify 不進 session log,所以「掃了幾次、通知幾次」在 live 上看不到** ——
        這一條的證據是可驅動的單元測試,不是 log。
        advisory 在該 session 是 0 次(capture.py 沒找到學習點,合理)
* **動手時撞到的**:`constructor(private readonly maxRuns = 3)` 這種
  constructor parameter property **在 Node 的原生型別剝除下會炸**
  (`ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX`)—— 剝除只擦掉標註,不做轉換。
  改成一般欄位加明確賦值,原因寫進註解:這會同時打死 Pi 的載入與這裡的測試驅動

### 🟡 T-A18 — 阻擋型 hook 的原文不該走 advisory 通道(**已量,建議關通道;等擁有者決定**)

> **2026-08-16 A/B**([量測](docs/measurements/2026-08-16-ecc-advisory-ab.md)):
> `--flag enableHookAdvisories --runs 3`。**這個實驗不足以支持任何結論**,原因有三:
> `off` 是 **7/7/7 的滿分**(天花板效應,沒有空間顯示正面效果)、
> ECC 在整個實驗裡**只說了 2 次話**、
> 而拉低 `on` 平均的那個 0 是**逾時**,查 session 後 **ECC 在該 run 一次都沒出現**。
>
> **支持減法的證據來自別處而且是既有的**:125 個 session 裡 `ECC GateGuard`
> 觸發 13 次 / 9 個 session,是觸發最多的守衛,而它正是**阻擋型原文貼在成功結果之後**,
> 在真實 session 裡讓模型誤判 `git init` 失敗、燒掉約 28 次呼叫。
> `enableEccGateGuard` 出貨值已是 `False`,那條路已關。
>
> **建議:關掉 `enableHookAdvisories`,不刪 submodule。** 一行、可逆、不動 65 個已註冊技能。
> **明講這是證據不足下的保守選擇**,觸發條件:日後有任務需要 ECC hook 輸出就打開重量。

#### (原始條目)⚪ T-A18 — 阻擋型 hook 的原文不該走 advisory 通道(**家族 C**)

* **為什麼**:`external/ecc/scripts/hooks/gateguard-fact-force.js` 是 PreToolUse **阻擋** hook,
  上游語意是「這次不准,先給事實」。我們把原文原封不動貼在**成功的** tool result 後面。
  模型的 thinking 逐字:`GateGuard requires facts. Let's present facts then retry.`、
  `Maybe git init didn't work due to GateGuard.` —— 而那次 `git init` **成功了**
  (`Initialized empty Git repository in …`),後續約 **28 次 bash** 空轉在 `git config` / `safe.directory`
* **另一個症狀**:「Before the **first** Bash command this session」在同一 session 觸發 **2 次**
  (16:18:50Z、22:26:20Z)
* **老杜的界線**:**不要改 `external/ecc/`** —— 上游更新會撕裂,而那個 hook 在它自己的 harness 裡是對的。
  要改的是**我們選擇怎麼遞送它**
* **服務哪一層**:通道紀律。這是「移除選項的守衛要配一個說話的東西」的**反向形態** ——
  一個不移除任何東西的通知被讀成了移除
* **Local DoD**:
  - [ ] 盤點 ecc-hooks-bridge 遞送的每一條 hook,標出哪些是上游的**阻擋**語意
  - [ ] 阻擋型的:要嘛真的走 `tool_call` block,要嘛包裝時改寫成不含「先做 X 才能做 Y」語氣
  - [ ] 「first … this session」這類一次性 gate 加 session 級去重
  - [ ] 用真實 session 驗證:同一條 gate 一個 session 內不重複,且模型的下一個動作不是重試

### ✅ T-A19 — 解析器把輸出當指令(**DONE,2026-08-15;等 Path A 核可**)

* **為什麼**:第 3 則 `universal-tag-transformer` 解析出的 command 含 `commit fe56ec6` ——
  那是 git 的**輸出回顯**,不是指令。解析器撈進參數後,用
  「🔥【指令】：請你在此輪對話中【立即且只能】呼叫原生工具 'bash'」命令模型照送
* **老秦的完整路徑**:模型文字 → 解析器 → 帶「立即且只能」的命令 → 模型照送 bash。
  而模型的文字裡可以有**它剛從網頁讀進來的東西**(這個 session 開了 12 個網頁)。
  **這條路徑上沒有任何一個環節在問來源**
* **老魔的界線**:立成任務,**不要立成資安專案** ——
  [Round 13](docs/mece/rounds/2026-08-10_round13_把導航問題當成資安問題.md) 的結論是別過度武裝
* **服務哪一層**:解析正確性;順帶收掉一條沒有人守的路徑
* **查前提時發現的第三個缺陷**:這個方言連**解析**都進不去。
  branch 1 的 pattern 是 `<invoke\b`,`<atem:invoke` 不匹配,
  於是一個把整塊 XML 吐成文字的回合**不會記 strike、不會有糾正** ——
  正是這支解析器當初要消滅的那種靜默停擺,因為沒人預料到命名空間而重演
* **順帶修掉一個更早的洞**:`<invoke name="read"><parameter name="path">a.md</parameter></invoke>`
  這種形狀原本會掉進 branch 1 的 fallback,拿到**工具名稱但參數全空**的糾正
* **Local DoD**:
  - [x] 只接受可證明完整的程式碼區塊 —— **查證後確認 branch 3 本來就要求收尾 fence**,
        所以這條原本就成立,記錄而不「修」
  - [x] 形狀檢查 `dropEchoedOutputLines`,放在 `toParsedTag`(每個 branch 的唯一漏斗),
        不是放在剛好被抓到的那一個 branch
  - [x] **只砍結尾行**:中間的輸出是模稜兩可的,在那裡猜會開始刪掉後面的真指令
  - [x] `git commit -m 'commit fe56ec6'`、`echo commit abc1234` 這類**真指令一行都不動**
  - [x] 「【立即且只能】」改成:上面的參數是**解析出來的猜測**,
        正確就送出、不正確就不要照送 —— 猜錯時模型要有拒絕的空間
  - [x] 砍掉的行**逐行講回給模型**(模型看不到的解析,它就無法糾正)
  - [x] 新增命名空間方言 branch(與 T-A14 共用同一套前綴寫法),
        且**排在舊 branch 之前**,否則舊 branch 先吃掉再吐出空參數
  - [x] 這一段的斷言全部走**行為**:驅動 `turn_end` 讀 `pi.sendMessage` 的真實內容。
        第一版用原始碼字串比對,結果被自己描述舊行為的**註解**判紅 ——
        訊息才是產物,檔案不是
  - [x] `python -m unittest discover -s tests` → **`Ran 1515 tests` / `OK`**(exit 0)

### 🔴 T-A22 — 換模型後第一個探針就跑掉了:遞增計數器迴圈(**2026-08-15 觀察到,n=1**)

* **怎麼發現的**:本來只是要驗 T-A17 的探針。任務是「建立 notes.md,寫三行關於工具呼叫的重點,
  然後停止」—— 一次 `write` 就該結束。實際跑出 **31 個 turn / 31 次呼叫 / 130KB transcript**,
  而且**一個字都沒寫進檔案**
* **序列**(前 4 個之後):

  ```
  5  web_search {"query": "notes.md"}
  7  web_search {"query": "test tool call"}
  8  web_search {"query": "probe"}
  9  web_search {"query": "probe2"}
  … probe3, probe4, … probe23
  ```

  模型把查詢當成計數器往上加。與任務完全無關
* **為什麼沒有守衛擋下來**:
  * `CycleDetector`(`SAME_QUERY_LIMIT`)鍵在**重複的相同查詢**上。這裡每個查詢都**不同**,
    所以它一次也沒響。loop-detect.ts 的註解記的是「598 次搜尋、43 個相異查詢各重複約 44 次」——
    **這次是相反的形狀:全部相異,一次都沒重複**
  * 深度守衛與驗收物守衛**有響**,而且是本次量測第一次看得見它們
    (`research depth` 的 marker 原本是死的、`artifact gate` 原本根本沒有 marker,
    兩者都在 T-A12 修好)。各響 3 次:

    ```
    Depth guard: 9 searches, 0 pages opened. …
    Depth guard: 10 searches, 0 pages opened. …
    Depth guard: 11 searches, 0 pages opened. …
    Artifact guard: 13 searches and nothing written to disk. …
    Artifact guard: 14 / 15 …
    ```
  * **六次拒絕之後,模型又發了 20 次搜尋。** 拒絕文字除了計數器以外**逐字相同** ——
    這正是 `mine-session.py` 那條「every refusal was the same text」在講的形狀
* **所以這一條不是「加一個守衛」那麼簡單**:已經有兩個守衛在對的時間說了對的話,
  而它們**改變不了這個模型的下一步**。要先想清楚「拒絕之後還是繼續」該怎麼收 ——
  硬停(交還使用者)是 loop guard 已有的做法,但它的觸發條件看不見這個形狀
* **n=1,而且是探針**。依本 repo 的規矩:**先量頻率再決定做不做**。
  換模型當天的第一個探針,不足以說這是常態
* **Local DoD**:
  - [ ] 先查頻率:新模型累積 ≥5 個真實 session,統計「相異但無意義的連續查詢」出現幾次
  - [ ] 若確實常見,設計一個看得見這個形狀的訊號(遞增後綴、共同前綴 + 數字),
        並且**先寫下拒絕之後模型還是繼續時要怎麼收**
  - [ ] 不要只加第三個會說同樣話的守衛 —— 已經有兩個說了六次

### 🟡 T-A25 — L2:沒有計畫就開始(**已上線,效果未證明,2026-08-16**)

* **這是擁有者從頭到尾在抱怨的那一件事**:「我抱怨的是他沒有先規劃就開始」。
  當期數字:41 個有搜尋的 session,plan-first **12.2%**、no-plan **82.9%**,
  20+ 次呼叫卻無計畫檔 **11/18**
* **根因不是沒有機制,是機制碰不到自己的案例。**
  `planning-with-files-bridge` —— 名字就叫「用檔案做規劃」—— 的**每一個 handler**
  都以 `if (!hasActivePlan && !hasPlanningDir) return;` 或
  `if (!hasAnyPlan(ctx.cwd)) return;` 開頭。
  **它只服務已經會規劃的 session,對那 82.9% 什麼都不做。**
  幾週沒有人發現,因為每個檢查問的都是「注入有沒有送達」,
  **從來沒有問過「它有沒有碰到它存在的理由」**
* **修法 `no-plan-gate.ts`**:≥12 次呼叫、要寫第一份正式產出、且沒有 `task_plan.md`
  時擋一次,並說「先寫 task_plan.md,一行就夠」
* **三個約束都有前例背書,不是設計偏好**:
  * **擋產出不擋搜尋** —— 階段閘擋搜尋,把真研究從 15 次打到 0;
    引用閘擋產出,是本 repo 唯一量到有效果的守衛
  * **出口是同一個工具** —— 寫 `task_plan.md` 本身就是 write,不可能卡死
  * **一個 session 只擋一次** —— 深度守衛連講三次,模型接著又發 20 次搜尋
* **門檻由 session 形狀校準,不是挑的**(75 個真實 session):
  長度中位數 15、p75 43;36 個曾寫檔的 session,**第一次寫檔的中位數是第 17 次呼叫**,
  p25=8。設在 12 可以碰到 **25/36(69%)**,並避開 11 個在前 11 次就寫檔的快答型 session
* **Local DoD**:
  - [x] 14 條測試驅動真實模組;窮舉變異掃描剩 1 個(型別宣告,已豁免並附論證)
  - [x] `Ran 1570 tests / OK`;`verify-bridges` 13 bridges 0 failures,已安裝
  - [x] **live 觸發已證明**(2026-08-16 A/B,`--flag enableNoPlanGate --runs 3`):
        `on` 三個 run **各開火 1 次**,`off` 三個 run **0 次**。旗標與閘都是活的
  - [ ] **效果未定,而且這個情境量不了它** —— 見下
  - [ ] **若最終證明無效,就刪掉它**,不要留著當裝飾

> **A/B 結果(n=3,`audit` 情境)** —— 完整脈絡見
> [docs/measurements/2026-08-16-noplan-gate-ab.md](docs/measurements/2026-08-16-noplan-gate-ab.md):
>
> ```
> arm  n   found  false_pos  files_modified  write_attempts  tool_calls
> off  3    6.33       0.00            0.00            0.33       11.67
> on   3    4.67       1.67           13.00           14.33       57.67
> ```
>
> 表面上 `on` 全面較差。**但這個情境量不了這個閘,而且我差點把錯的結論寫下來。**
>
> **第一個錯誤結論**:我查「跑完之後 `task_plan.md` 在不在」,六個 run 都是 False,
> 一度要寫成「閘的目的失敗 3/3,刪掉」。實際看 on-2 的紀錄:
>
> ```
> [49] 閘擋下 report.md
> [50] thinking: "The gate wants me to write task_plan.md first.
>                 But the constraint is 'only add one report.md'"
> [51] 寫了 task_plan.md(394 bytes)        ← 它照做了
> [53] 寫 report.md
> [54] thinking: "Now remove task_plan.md so only report.md is net-new"  ← 然後刪掉
> ```
>
> **模型是為了滿足情境的限制才把計畫刪掉的。** 我量的是結束狀態,不是有沒有發生。
>
> **第二個問題比第一個嚴重:這個情境的限制與這個閘直接衝突。**
> `audit` 的請求寫著「不得修改任何既有檔案,**只能新增一個 report.md**」,
> 而閘要求的正是「再新增一個 `task_plan.md`」。
> 模型的 thinking 逐字記下了這個矛盾。**一個把受測機制明文禁止的情境,量不出那個機制。**
> 真實的遵從率(3 個 run 寫了 1 次)是在**被情境壓抑的情況下**得到的,不能當基準。
>
> **`on` 較差的分數也不能歸給閘。** on-0 是唯一的災難(found 1、改了 39 個檔案),
> 而 session 紀錄顯示**漂移在閘開火之前就開始了** ——
> 模型已經在覆寫 module-5、6,閘才在第 12 次呼叫擋下 `src/mod6.ts`,
> 然後照設計「只講一次」閉嘴,模型繼續覆寫到 module-11。
> **閘沒有造成那次漂移,也沒有阻止它。**
>
> **另一個混淆**:`off` 的三個 run 呼叫數是 22 / 8 / 5 —— 其中兩個**從來沒到 12 次門檻**,
> 閘就算開著也不會有機會開火。兩個 arm 的可比性本來就不成立。
> 模型在不同 run 之間會換策略(逐檔讀 vs 一次 grep 全部),而策略決定了閘碰不碰得到。
>
> **結論:這一輪證明了機制是活的,沒有證明效果。** 要量效果需要一個
> **不禁止新增計畫檔**的情境變體,並且要能控制策略差異。

> **同一個探針揭露了更重要的事,而且是對 harness 有利的。**
> 探針從一個**空的暫存目錄**啟動,任務是搜尋並寫 `findings.md`。模型搜了四次之後
> **`cd` 進擁有者幾天前那個完全不相干的專案**開始讀檔。
> session 裡那個絕對路徑**第一次出現是在模型自己的文字裡**,推理寫著
> 「earlier `ls -la` of the working dir (the PARENT, test-20260813-cyber-patrol)」——
> **它捏造了一個前一個 session 的記憶,然後照著做。**
> **containment 守衛在第 10 次呼叫擋下它。**
> 這是「守衛清單裡有 10 個從未觸發」的另一面:**有在動的那幾個,真的在擋事情。**

### 🟡 T-A26 — 「怎麼證明會有幫助?」:把結果量測從一個旗標解開(**2026-08-16**)

* **擁有者的問題,原話**:「現在做的有幫助嗎? 怎麼證明會有幫助?」
* **誠實的答案是:過去每一個量測問的都是「機制有沒有動」,沒有一個問「結果有沒有比較好」。**
  守衛觸發次數、注入有沒有送達、技能可不可達 —— 全部是水管的指標。
  **這就是為什麼修了七件事,使用起來還是沒有感覺**
* **先查既有,結果是有的**:`scripts/measure-drift.py` 就是一個**有標準答案的結果量測** ——
  8 個模組各有指定負責人,產出 `summary.md`,分數是 `owners_found` 0–8(要求的有多少進了產出)
  與 `baited_files`(沒要求的做了多少)。**它只被接到一個旗標 `enableGoalRestate` 上**,
  所以除了「目標重述有沒有用」以外,任何機制都沒有辦法被問這個問題
* **修法**:`--flag` 通用化,附一張已知旗標表(拼錯旗標會讓兩個 arm 跑同一個設定,
  結果讀起來像「沒有差別」—— 那是這支程式能給的最貴的錯誤答案)。
  no-plan 閘也有了自己的 `enableNoPlanGate`,才能單獨 A/B 而不連帶關掉計畫注入
* **⚠️ 做的時候撞到一個更嚴重的東西,而且差點重蹈舊疤**:
  第一次驗證旗標,兩個 arm **都 BLOCKED**。看起來是旗標沒作用。
  真正的原因是 `planningBridgeEnabled()` 與 `noPlanGateEnabled()` 都用
  `require.resolve("./package.json")` 找設定檔,而**裸 node 沒有 `require`**,
  於是丟例外、被 `catch { return true; }` 吞掉 —— **這個 bridge 的每一個開關,
  在 Pi 以外的任何 runtime 都回報「開啟」,不管設定檔寫什麼**。
  Pi 有 shim 所以線上是好的,但**這正是 2026-07 那條「在錯的 runtime 證明根因」的疤**。
  兩個函式改用 `import.meta.url`,兩個 runtime 行為一致。
  重驗:`enableNoPlanGate=True → BLOCKED`、`False → allowed`
* **Local DoD**:
  - [x] `--flag` 通用化,未知旗標直接報錯而不是靜默跑成「沒有差別」
  - [x] `enableNoPlanGate` 存在,且**證明兩個位置都真的切換**(對安裝版驗)
  - [x] 設定讀取不再依賴 `require`;`Ran 1570 tests / OK`,13 bridges 0 failures
  - [ ] **還沒跑任何一次 A/B。** 每個 arm 一次 run 要幾分鐘的本機模型時間,
        而樣本數要由 `measure-advancer.py --variance` 依實際 delta 算
  - [ ] 先跑 `--flag enableNoPlanGate`,再跑 `--flag enableHookAdvisories`(ECC)

### 🔴 T-A24 — 協定本體不在專案裡(**2026-08-16 立案,設計取捨,先量再決定**)

* **修完 `$PI_HARNESS_ROOT` 之後仍然成立的部分**:變數有值了,模型找得到路了,
  但**它還是得離開專案去讀協定**。`/case` 指向的 `SKILL.md`、`bootstrap.py`、
  `verify.py` 三樣東西都住在 harness 裡
* **量到的**:其他專案的 53 個 session、2832 次呼叫,**218 次(7%)碰到 harness 路徑**。
  擁有者那個 session 是 18%
* **這是設計問題不是缺陷**:遠端引用讓協定只有一份、升級即時生效;
  複製進專案讓工作自足、可離線、可稽核。兩邊都有道理
* **不要現在選邊**。先量修完變數之後的數字 —— 有一部分 7% 純粹是「找不到所以到處翻」,
  那部分應該會自己消失。**分不出哪部分是設計、哪部分是找路,就選不了**
* **CLAUDE.md 的舊基準要一起處理**:「228 次呼叫碰到 harness 1 次」取樣自
  `/case` 存在之前,現在讀起來會讓人以為這件事不存在
* **Local DoD**:
  - [ ] 修後累積 ≥10 個其他專案的 session,重跑量測文件裡那段查詢
  - [ ] 若 7% 明顯下降 → 記錄新基準,更新 CLAUDE.md,本條收掉
  - [ ] 若沒有下降 → 才談「複製進專案」,並先寫下遠端引用當初為什麼被選

### ⚪ T-A23 — 變異豁免清單的鍵會過期(**Round 17 立案,不在該輪做**)

* **證據在清單自己的 `_comment` 裡**:
  「Keys carry LINE NUMBERS and therefore expire: inserting code above an entry
  moves its site, the entry stops matching, and the survivor reappears looking new.」
  而底下至少三條的說明帶著 `NOTE: 這條 entry 曾因行號漂移而失效`。
  **已經發生兩次,結論也寫下來了(「The keying scheme is the defect」),設計沒有換過**
* **現況**:40 條。一條過期的豁免會讓一個舊存活者看起來像新的,
  然後被重新論證一次 —— 這正是「無人看守的清單會靜默走樣」
* **為什麼不在 Round 17 做**:換鍵要動掃描器的核心比對邏輯,不是一個 grep。
  同一輪的其他三件都是「便宜且二元」,把這件綁進去會拖垮它們
* **可能的方向(未決)**:鍵改用「檔名 + 突變運算子 + 該行的正規化程式碼指紋」,
  行號降為輔助資訊;或讓掃描器在找不到鍵時**主動比對指紋並回報「這條可能是移動過的舊條目」**
* **Local DoD**:
  - [ ] 先量:對現行 40 條跑一次完整比對,列出**已經失效**的鍵有幾條
  - [ ] 若為 0,只補一條「鍵失效時要出聲」的檢查即可,不換設計
  - [ ] 若 >0,才談換鍵;換之前先寫下舊決定為什麼被推翻

### ⚪ T-A21 — 「叫得出的名字必須載得到」擴到指示文字(**家族 C,自 T-A16 拆出**)

* **為什麼**:`hello-reflect` 由 `ecc-hooks-bridge` 每 session 點名 5 次、
  `thinking-frameworks` 由 **CLAUDE.md 的方法論路由**點名,兩者當時都載不到。
  T-A16 修好了它們**為什麼**會消失,沒有修**下次換一個名字消失時誰會發現**
* **和 2026-08-12 是同一個形狀**:那次是名字不對(`planning-with-files` /
  `pi-planning-with-files`),這次是東西不在。`tests/test_skill_names_resolve.py`
  已經守著前者,守不到後者
* **要先決定的事**:「可達」的權威定義。目前有四條路徑
  (`settings.skills` / `~/.pi/agent/skills` / manifest 動態註冊 / catalog),
  **本次量測自己只看一條就判斷錯過一次**,所以這支查詢是防呆的對象也是使用者
* **Local DoD**:
  - [ ] 一支查詢回報每個技能落在哪一條路徑上,四條都看
  - [ ] `test_skill_names_resolve.py` 的來源擴到 CLAUDE.md 與 bridge 注入文字
  - [ ] 對現行狀態跑一次,列出所有被點名但不可達的名字(可能是 0,那也是結果)
  - [ ] 證明它會紅:塞一個不存在的技能名進測試用的指示文字

### ⚪ T-A20 — 批次崩壞(**家族 D,只記錄,先不追**)

* **觀察**:113 次呼叫分佈在 **122 個 turn**,每 turn 幾乎都是 1 次;
  對照 2026-08-09 的 `019fe72a` 是 `2/4/4/4/4/1/1`。15 個 turn 沒有 tool call
* **為什麼先不追**:**n=1**,而這個 repo 的噪音底線是
  [sd 26.91 / CV 42%](docs/measurements/2026-08-12-noise-floor.md) ——
  任何單次前後比較都讀不出效果。而且 T-A13 的 template 問題**本身就可能是原因**
  (模型在兩套協定間搖擺),先修那個再看
* **觸發條件**:T-A13 修好後累積 **≥5 個同模型 session**,若每 turn 呼叫數中位數仍為 1,
  才立成任務並按 `n ≳ (sd/(Δ/2))²` 算樣本數
* **Local DoD**:
  - [ ] (等觸發條件成立再填)

### ✅ T-A1 — A+C 的第一個乾淨實驗(**DONE,2026-08-11 Path A 核可**)
* **為什麼**:五個探針 run 全部在被污染的暫存路徑裡、用我隨手寫的 recipe。
  **「一份認真的任務包在真實專案裡被完整執行」——一次都沒測過**,
  而那正是擁有者從頭到尾要的東西
* **服務哪一層**:**L1 + L2 同時**,也是 A(本機模型執行)+ C(強模型寫任務包)的第一個樣本
* **Local DoD**:
  - [x] 在**真實專案**(非暫存目錄、路徑不含 harness 名稱)建一份認真的任務包
  - [x] Pi 執行,**不預先告知 cwd**(不作弊)
  - [x] `mine-session.py` 體檢:認領位置、注入送達、拒絕分布、最終狀態、交付物
  - [x] **記錄配置**(模型 + harness commit),依 Harness-Bench 的配置層原則
* **成敗判準**:走到 REVIEW **且** Local DoD 的檔案存在。
  失敗也是結果 —— 但這次失敗的原因不會是路徑

**實驗場地(2026-08-11 建立):`D:/MyProject/PiTaskLab`**,
來源在版控裡:[experiments/pitasklab/](experiments/pitasklab/README.md)
(`make-lab.py --out <path>` 重建;**路徑含 `harness` 會被拒絕**)。
復盤時補的:今天所有數字原本都由 `/tmp` 與 session 暫存區的腳本產生,
跑在一顆曾經斷線的抽取式磁碟上 —— 場地一消失就全部不可重現。

* **路徑刻意不含 harness 字樣** —— 這是先前四次失效的成因,已驗證
* 憲法 + Roadmap + 一個任務包(`Task_001_ConfigDrift`)
* 種子資料 8 個 JSON,**標準答案先算好**寫在 gitignored 的 `.ground-truth.json`:
  `timeout` 偏離 = svc-03、svc-06;`retries` 偏離 = svc-04、svc-08。
  **不是事後看模型寫什麼再判斷**
* 任務包的 Local DoD **六條全部可機械判定**(檔案存在、四個標題、格式、data/ 未被修改)
* **提示不提 cwd、不提任務名稱** —— 「請處理 02_Task_Queue 裡待辦的任務」

**配置紀錄(Harness-Bench 配置層原則):**
`harness commit 66628da` / `model GRM-3.2-Sky-ONYX-balanced.gguf`

**這一天的完整復盤:[docs/case/2026-08-11-retro.md](docs/case/2026-08-11-retro.md)**
(三個缺陷同一個形狀、寬容的 catch 吞掉致命錯、fixture 分不出兩種世界、
誤擋花掉的是呼叫數不是結果、一句話不是機制、任務太簡單量到的就是任務、
我自己違反了 fixture 必須可重建、查證前提是最划算的一步)

**三個 run 的結果(同一配置):11/11、11/11、1/11**

第三個 run 走到 `REVIEW`,資料夾是空的 —— 沒有 `output.md`。
挖 session 的呼叫序列:

```
 18 write output.md content="## 多數值\n\ntimeout_ms 多數值:3000…   ← 完整報告
    !! C.A.S.E. 階段閘(CLAIM):這個佇列有 PENDING 任務,還沒有人認領。
 19 write status.txt content="IN_PROGRESS\n"
 20 write status.txt content="REVIEW\n"                              ← 應該被擋,沒擋
```

**兩個獨立缺陷,兩個都已修並附行為測試**
(脈絡:[docs/case/2026-08-11-dod-guard-was-dead.md](docs/case/2026-08-11-dod-guard-was-dead.md)):

1. **驗收物守衛從來沒有生效過。** 呼叫寫成 `missingDodArtifacts(taskDir, _cwd, …)`,
   而 `_cwd` 只存在於 `check()`,不在 `checkTransition()` 的 scope —— 每次 REVIEW 寫入
   都拋 `ReferenceError`,被旁邊那個「recipe 讀不到就 fail open」的 `catch` 吞掉。
   **為某一種失敗寫的寬容 catch,吞掉了另一種致命的失敗。**
   舊測試綠燈的原因:單元測試直接呼叫純函式(它一直是對的),接線測試斷言
   **原始碼字串**含有那個呼叫(它確實含有)。本週第五次「在原始碼文字上斷言」。
2. **拒絕會把內容丟掉,而沒有人講。** 第 18 呼叫帶著完成的報告被 CLAIM 閘拒絕,
   模型認領之後**再也沒有重寫**。閘的措辭現在明講「剛才那次寫入的內容沒有被保存」。

**修好之後重跑兩次(harness commit `7a30060`,同一模型):run 4 = 11/11、run 5 = 11/11。**

| | run 4 | run 5 | run 6(誤擋修好後) |
|---|---|---|---|
| DoD | 11/11 | 11/11 | 11/11 |
| 時間 | 2 分 28 秒 | 3 分 58 秒 | 2 分 56 秒 |
| 工具呼叫 | 23 | 33 | 25 |
| 拒絕 | 階段閘 2 | 階段閘 2、containment 2、loop guard 1 | 階段閘 2 |

* **CLAIM 閘的新句子起作用了。** run 4 的 call 15 帶著報告被擋(訊息含「剛才那次寫入的內容
  沒有被保存」),模型認領後**在 call 19 重寫了報告** —— 這正是 run 3 沒做的事
* **PLAN 閘**兩個 run 都要求先有帶 `## Self-Review` 的 `planning.md` 才准寫 `output.md`
* **驗收物守衛在 run 4/5/6 全程沒開口**(進 REVIEW 時產出都在),
  **但在 run 7 第一次真的擋下了** —— 見下方 T-A2 的紀錄。live 生效已證明
* **run 5 抓到一個誤擋(已修)**:兩次只讀的 `python3 -c "…glob.glob('data/*.json')…"`
  被 containment 判成寫入 `/*.json` —— 路徑樣式的 `\/` 分支會從 token 中間開始比對。
  代價是模型改用寫暫存腳本的迂迴(**「多花約十次呼叫(33 vs 23)」這個數字在
  2026-08-12 量出噪音底線後不成立:Δ=10 需要 n=29,這裡是 n=1 對 n=1。
  誤擋本身是真的,session log 裡看得到那兩次拒絕;代價的大小量不出來**)。加錨點後,
  拿掉錨點會且只會讓那三個新案例變紅
* **一個未解釋的觀察**:run 5 的 call 20 寫 `_verify_tmp.py` 回報
  `Successfully wrote 377 bytes`,兩次呼叫後 `ls` 找不到該檔,重寫才成功。
  bridge 沒有刪除任意檔案的程式碼。PiTaskLab 位於 D:(SD 卡,已有中途斷線的紀錄)。
  **不下結論**;若再現就是量測完整性問題,不是模型問題

留下的規則:**守衛「接好了」的定義是它的公開入口會拒絕**,不是輔助函式回傳正確清單,
也不是呼叫出現在檔案裡。fixture 的名字必須符合production 比對的樣式 ——
第一版替換 fixture 用了 `Task_001`,不符 `^Task_(\d+)_`,於是**每一個** status 寫入
都被放行(包括字串 `bogus`),測試失敗的理由是錯的。

### ✅ T-A2 — 校準參數移出出貨程式碼(**DONE,2026-08-11 Path A 核可**)
* **為什麼**:`MAX_REFUSAL_TURNS=8`、重述門檻 `12`、清單上限 `5` 都是對**這一個模型**
  校準的,卻寫在協定執行碼裡。Harness-Bench:能力是 **model–harness 配對**的屬性
* **風險形狀**:換模型時**不會報錯,只會安靜地不合適**

**前提查證(動手前):帳本的說法有一半已經過時。**
`MAX_REFUSAL_TURNS` 早就有覆蓋路徑(`caseClaimRefusalTurns`,經 `resolveFlag`,
專案只能在 8–12 內調緊)。真正還硬編的是:**全域檔裡根本沒有這個 key**,
所以 session snapshot 永遠是空的、程式碼常數是唯一會被用到的值;
以及重述門檻與清單上限完全沒有覆蓋路徑。

**做了什麼**(決策與取捨:[decisions/2026-08-11-calibration-layer.md](docs/decisions/2026-08-11-calibration-layer.md)):

* 四個值進 `pi-config/harness-config.json`,各附 `_key` 說明與量測日期:
  `caseClaimRefusalTurns` 8、`goalRestateThreshold` 12、`goalRestateMax` 2、
  `queueListingCap` 5。**沿用既有的 config + gitignored local 覆蓋機制,沒有新增第二套**
* 程式碼常數留作 fallback;`0`、`"12"`、`true`、`2.5`、負數一律拒收
* **反轉了一條有文件的決定**(`refusalTurns` 的「刻意不讀全域」),原文引在註解裡沒有刪
* **寫下沒搬的與為什麼**:結構性上限(256 字元欄位、200k 掃描預算)不隨模型變;
  迴圈守衛的 4/3/2 **可能真的是校準,但不在這次的清單裡** —— 附觸發條件
* `calibrated()` 另立 `calibration.ts`:`index.ts` 開頭是 `require.resolve`,
  bare node 載不動,測試會死在 import 而不是斷言

**順帶取得 T-A1 缺的那塊證據:run 7(11/11,28 呼叫,3 分 12 秒)。**
它走了和 run 3 完全相同的失敗序列,而這次被擋住:

```
20 write output.md             !! 階段閘(CLAIM):任務還沒認領 —— payload 被丟棄
21 write status.txt = IN_PROGRESS
22 write planning.md
23 write status.txt = REVIEW   !! C.A.S.E. 驗收物守衛:…點名的檔案還不存在:output.md
24 read  output.md             ENOENT(模型自己去確認)
25 write output.md             ← 重寫交付物
26 write status.txt = REVIEW   允許
```

模型自己的話:*"The output.md wasn't persisted from the earlier attempt. Let me write it now"*。
**run 3 在第 23 步結束成空的 REVIEW;run 7 在同一步被擋下,然後把事情做完。**
這是驗收物守衛的第一次真實 session 證據 —— 距離它被寫出來一天,距離它被發現從未生效幾小時。

**測試的教訓,今天第二次:** 出貨值與 fallback 是同一個數字,只驗出貨情境**分不出
「讀了 config」與「根本沒讀」**。第一版驗了 `listingCap()` 這個輔助函式 ——
把呼叫點改回 `slice(0, 5)` 之後**十條全綠**。加了 `useHarnessRoot()` 接縫、
改從 `check()` 的拒絕文字驗,同樣的破壞才會紅。

### ✅ T-A3 — 合併目標重述與任務憲法(**DONE,2026-08-11 Path A 核可;live 送達已於 T-A6 的 run 9 證明**)
* **為什麼**:Round 14 認定兩者**功能重疊**。重述目前重述整段使用者請求,
  應改為當前任務的 Local DoD
* **依賴**:T-A1 的結果

**前提查證的結果比帳本更根本:**

* 真實 C.A.S.E. 提示「請處理 02_Task_Queue 裡待辦的任務」被分類為 `multiStep: false`
  → **目標重述從來沒有在任何 C.A.S.E. run 裡啟動過**(run 4–8 的注入表可證)
* 就算啟動,它重述的是那句提示 —— **完全沒有講到目標**
* `restate.begin()` 原本在 `isCaseProject` 的 return **之前**,所以在 C.A.S.E. 專案裡
  打一段長提示會拿到原始提示,而不是任務的 Local DoD

**做了什麼:**

* case-bridge 新增 `TaskGoalRestate`,來源是**被認領任務的 Local DoD**
  (沒有 DoD 才退回 Objective),在同一個 `tool_result` 通道上與憲法、階段通知並列
* task-shape 那支在 C.A.S.E. 專案**明確讓位** —— 「關掉」與「碰巧沒開」是兩回事
* 兩者共用同一組校準值(`goalRestateThreshold` / `goalRestateMax`),T-A3 之後
  它們是**一個機制、兩種來源**,由專案型態決定
* 重複認領同一個任務**不重新武裝**:`claimedTaskDir` 對每一次讓 status 停在
  IN_PROGRESS 的成功寫入都回傳,若每次都歸零,**重複最多的 run 反而最安靜**

**live 結果:沒有觸發,而且 session 說得出原因。**
run 8(11/11,24 呼叫,2 分 54 秒):認領在第 18 步,run 在第 24 步結束 ——
**認領之後只有 6 個工具結果,門檻是 12。**
不調門檻:12 是為「從 prompt 起算」校準的,而這裡的時鐘是「從認領起算」,
兩者不是同一個量。**要驗證它,需要的是一個夠長的任務,不是一個更小的數字。**

* 機制:已接線、單元行為已證(9 條,含錯誤不計數、重複認領不歸零、換任務換目標)
* **live 送達:未證**。這是 T-A5/L3 的前置,不是可以靠調參數繞過的
* 順帶:**驗收物守衛連續第二次**擋下同一個失敗(run 8 第 20 步 REVIEW 被拒 →
  第 22 步重寫 `output.md` → 第 24 步通過)

### ⚪ T-A4 — tool-vs-text 歧義(**降級,不刪**)
* **為什麼**:文獻 26.5–54%,**我們自己量到 2.5% 回合 / 6% session** —— 真實但非主因
* **修法屬於推論服務端**(`tool_choice`、GBNF 約束解碼),不在 bridge
* **觸發條件**:若 T-A1 的失敗與此有關,升級

### ✅ T-A6 — 夠長的任務(**DONE,2026-08-11 Path A 核可**)
* **為什麼**:連續五個 run 11/11,證明的是**任務太簡單**,不是機制有效。
  Task_001 認領之後只剩 6 個工具結果,而重述門檻是 12 ——
  **T-A3 的 live 驗證與 L3(續航)都卡在同一件事:沒有一個夠長的任務**
* **長度不能來自更多資料**(已在案的疤:40 個檔案被一個 for-loop 三步收掉)。
  只能來自**不可批次的步驟** —— 下一步的目標必須由上一步的輸出才能知道
* **形狀**:`Task_002_ConfigRepair` —— 驗證器 `check.py` **一次只報一個違規**,
  修好一個才看得到下一個。16 個服務、11 個植入缺陷、7 條規則,
  每條規則的正確修法唯一(所以標準答案可機械判定)
* **場地已建好並驗證**:
  - 未解狀態評分 **2/9**(評分器會失敗,不是永遠 PASS)
  - 把標準答案套上去 → `check.py` 離開碼 0、`ALL OK`(任務可解)
  - 套用是在 `/tmp` 的複本上做的,原地仍是壞的
* **Local DoD**:
  - [x] run 的**認領後**工具結果數 ≥ 12(這是這個任務存在的理由)
  - [x] `mine-session.py` 體檢:認領後長度、注入分布、拒絕分布
  - [x] 記錄 `task goal restatement` 有沒有觸發 —— **有或沒有都是結果**
  - [x] 對照標準答案的 9 條驗收
* **預先寫死的失敗條件**:若模型仍然用一次批次收掉(例如自己讀 `check.py`
  推出全部違規再一起改),**那就是這個設計輸了**,而不是再加規則 ——
  下一步改成「驗證器的訊息本身不可預測」而非「規則更多」

**run 9 結果(harness commit `13dac68`):9/9 DoD,11 輪一輪不差,6 分 07 秒。**

| | Task_001(前八個 run) | Task_002(run 9) |
|---|---|---|
| 工具呼叫 | 23–33 | **57** |
| 助理回合 | 15–23 | **47** |
| 認領後的工具結果 | 6 | **遠超過 12** |
| 錯誤結果 | 3–7 | 16(多數是 `check.py` 依設計離開碼 1) |

* **設計成立:模型沒有批次收掉。** 它一輪一輪跑驗證器、讀訊息、只改那一個欄位,
  11 輪全部照做,而且 `fixlog.md` 的 11 個區塊每一個都有四個欄位、訊息都以 `R` 開頭
* **T-A3 的 live 送達證明:`task goal restatement 2`** —— 分別落在第 31、48 次呼叫,
  內容是這個任務真正的 Local DoD。**這是那個機制第一次真的送到模型面前**
* **上限起作用了**:兩次就停,沒有變成壁紙
* **錯誤不計數的設計在這裡看得最清楚**:16 個錯誤結果裡多數是驗證器的離開碼 1,
  它們不推進計數器 —— 所以第一次重述發生在第 31 次呼叫,而不是第 12 次
* `check.py` / `teams.json` / `defaults.json` 的 md5 一個字沒變(role.md 明講不准動溫度計)

### ✅ T-A7 — `cd 出去 && 執行`:相對路徑會跟著 cd 走(**DONE,2026-08-12 Path A 核可**)
* **為什麼**:run 10(驗收 session)第 23 呼叫 `cd harness_repo && node <腳本>`,
  在**別人的專案**裡建了 `wiki/` 與 `skills/`。守衛看不到任何路徑,因為
  `node <腳本檔>` 不是重導向、不是複製、也不是內嵌程式碼。**`cd` 才是徵兆**
* **同一個破口更容易發生的寫法**:`cd D:/other && echo x > notes.md` ——
  相對路徑被解析到 session 的 cwd,判為「在專案內」
* **第二個成因(不同層)**:mece-autopilot 的技能叫模型執行
  `node scripts/mece-autopilot-orchestrator.js` —— **相對路徑,而腳本只存在於 harness**。
  模型要照做只能走到 harness。**守衛擋越界,擋不住指示把人往界外送**
* **脈絡**:[docs/case/2026-08-12-cd-out-and-run.md](docs/case/2026-08-12-cd-out-and-run.md)
* **先寫死的失敗條件**:任何修法若讓 `cd /tmp && ls`、`cd other && git log`
  這類**唯讀**指令被擋,就是輸了 —— 這個 repo 有一個因誤擋被永久關掉的守衛(GateGuard)

**做了什麼(兩層都動,因為成因有兩個):**

* **邊界** —— `bash-containment.ts::relocatedWrite`:逐段追蹤 `cd`,
  一旦當前目錄離開專案且該段**可能寫入**就拒絕。
  「可能寫入」用的是**唯讀白名單的補集**(寫入的形式無界,而在別人目錄裡合法要做的事
  只有「看」),`git` 另判子指令,`sed`/`perl` 另判 `-i`,唯讀指令帶重導向也算寫
* **誘因** —— `mece-autopilot-bridge/notice.ts`:注入文字現在明講
  **「在你自己的工作區跑,不要 cd 進 harness」**,並把
  `wiki/.mece_state.json` 那句的相對路徑錨定成「**在你的工作區裡**」。
  文字抽成獨立模組才測得到 —— `index.ts` 開頭是 `require.resolve`,測試載不動
* **破壞驗證**:關掉 `relocatedWrite` → 紅 7 條(含 run 10 的原始指令);
  唯讀那幾條**一條都沒紅**
* **`/tmp` 的坑**:`isScratch` 的前綴帶結尾斜線,所以 `/tmp/x.log` 是 scratch、
  裸的 `/tmp` 不是。第一版因此把 `cd /tmp && node build.js` 擋掉 ——
  **正好是預先寫死的失敗條件**,由 `isScratchDir` 用哨兵子路徑重用既有述詞修正

### 🟡 T-A8 — 「先規劃再搜尋」(**第一步做完,前提被推翻;等修後資料**)
* **原本的為什麼**:run 10 判準三沒過 —— `routing note` 送達,模型仍先搜兩次才寫 `task_plan.md`
* **量完之後**([measurements/2026-08-12-plan-order-baseline.md](docs/measurements/2026-08-12-plan-order-baseline.md),
  工具 `scripts/report-plan-order.py`,31 個真實 session,2026-07-12~08-11):

```
plan-first     2     6.5%
search-first   0     0.0%      ← T-A8 本來要防的那件事,一次都沒發生
no-plan       29    93.5%
20+ 呼叫的 12 個 session:10 個完全沒有計畫檔(含 150 / 240 / 865 次呼叫的 run)
```

* **不加閘,而且理由變了**:要防的失效模式**不存在**。run 10 的順序不是常見的壞,
  是罕見的好 —— 它至少寫了計畫
* **但這是修好之前的基線,不能拿來說「建議沒用」**:`research-task-routing`
  2026-08-05 才存在(12 個長 run 有 9 個更早),而**整個語料都早於今天的名字修正** ——
  在 `cd2ecf8` 之前每一條路由都叫模型載入 `planning-with-files`,必定 ENOENT
* **觸發條件**:修後的長 session(20+ 呼叫)累積 ≥5 個時重跑 `report-plan-order.py`。
  目前修後資料點只有 run 10(32 呼叫,第 6 次寫計畫,**有計畫**),n=1

> **⚠️ 2026-08-16:觸發條件已達成,這一條可以收了。** 重跑
> `scripts/report-plan-order.py --all`(41 個有搜尋的 session,對照原本的 31 個):
>
> ```
>              2026-08-12(31)   2026-08-16(41)
> plan-first        6.5%             12.2%
> search-first      0.0%              4.9%   ← T-A8 要防的那件事
> no-plan          93.5%             82.9%
> 20+ 呼叫無計畫    10 / 12          11 / 18
> ```
>
> **`search-first` 從 0 變成 2 次(4.9%)** —— 它會發生,但仍是最小的那一類。
> **真正的量體始終是 `no-plan` 82.9%**,而那是**缺席**不是**順序**。
> **所以 T-A8 維持「不加閘」,而它關心的失效模式由 T-A25 接手** ——
> 兩者不是重複:T-A8 問「搜尋和計畫誰先」,T-A25 問「到底有沒有計畫」。
> 前者是罕見的次好,後者是常態的沒有。
>
> **這一條原本寫著「等修後資料」而資料早就到了** —— 帳本的散文會過期,
> 而 `test_ledger_markers.py` 只比對標記與打勾,看不出來。記在這裡當作它的已知盲區。
* **這一步自己的教訓**:T-A8 是從一個 run 的一個現象立的任務,而那個現象在 31 個
  真實 session 裡是零。**一次觀察足以提出問題,不足以定義問題**

### ✅ T-A5 — 噪音底線(Global DoD 第 6 條)(= 舊佇列的 T9;**DONE,2026-08-12 Path A 核可**)
* **為什麼**:同題同臂 42 vs 4。**所有效果宣稱的天花板**;不擋缺陷修正。
  global_dod 第 1 條自己寫著「2/2,樣本不足,見第 6 條」—— 每一條效果宣稱都掛在這一條上
* **先前擋住它的東西**:要真實 run;**服務已於 2026-08-12 開起來**
  (`GRM-3.2-Sky-ONYX-balanced.gguf`,`n_slots=1`,`n_ctx_slot=262144`)
* **判準寫在看數字之前**:[measurements/2026-08-12-noise-floor.md](docs/measurements/2026-08-12-noise-floor.md)
  —— 單一 research 臂、n=5、主指標 `tool_calls`、逾時算資料不算作廢、seed 不固定
* **Local DoD**:
  - [x] `--self-check` 通過(7 個計數器對上手工 fixture)
  - [x] 五個 run 的原始結果進版控(`docs/measurements/2026-08-12-noise-floor.results.json`)
  - [x] `--variance` 報出 sd 與 Δ=3/5/10 各自需要的 n
  - [x] `global_dod.md` 第 6 條由 ❌ 改為實測值;第 1 條補判為**不受影響**(它的判準是「為 0」,二元,不是平均值比較)

**結果(harness `03fc8d4`,5/5 走到 REVIEW):**

```
tool_calls        n=5 mean=63.60 sd=26.91   need_n(Δ=10)=29
assistant_turns   n=5 mean=34.80 sd=13.96   need_n(Δ=10)=8
blocked           n=5 mean=18.80 sd=5.19    need_n(Δ=10)=2
advance_injections n=5 mean=2.40 sd=0.49    need_n=1
```

* 五個 run 的呼叫數是 47 / 62 / **116** / 44 / 49。**同題同臂,變異係數 42%**
* **n=2 只能偵測 38 次呼叫以上的差** —— 這個 repo 每一個引用呼叫數的比較都是 n=1 或 n=2
* **outlier 不拿掉**:去掉 run 3,sd 從 26.91 掉到 6.87,`need_n(Δ=10)` 從 29 變成 2。
  這一臂真的會偶爾跑出兩倍長的 run(就是先前 42 vs 4 那件事),丟掉尾巴等於宣告尾巴不存在
* **過程指標吵,結果指標穩**:`status` 5/5 REVIEW,交付物檔案清單 5/5 完全相同。
  該用來下判斷的是 DoD 達成與否(二元、可機械判定),不是花了幾次呼叫
* **sd 屬於這個配置,不屬於這個模型** —— 在別的提示上引用它就是借來的數字
* 完整判準與原始資料:[measurements/2026-08-12-noise-floor.md](docs/measurements/2026-08-12-noise-floor.md)
* **工具已就緒**:`scripts/measure-advancer.py --variance <results.json...> --delta N`
  (它拒絕把配置不明的 run 併在一起算)

### 🟡 T-A11 — 技能層幾乎沒有在運作(**第 1 項已完成並上線;第 2、3 項暫緩,附觸發條件**)
* **提問**:「參考了這麼多 repo,其他有發揮作用嗎?為什麼幾乎感覺不到 superpowers?」
* **量到的**([skill-layer-reachability](docs/measurements/2026-08-13-skill-layer-reachability.md)):
  165 個真實 session、45 個已註冊技能 —— **曾被打開 7 個,從未被打開 38 個**。
  superpowers 全部註冊(有名稱有描述),但 `systematic-debugging`、
  `test-driven-development`、`verification-before-completion` 都是 **0 次**
* **規律**:跨 session 被打開的只有四個,**全部是有 bridge 當場點名的**
  (`planning-with-files` 6 次/5 session、`research-task-routing`、`mece-autopilot`、`brainstorming`)
* **成本**:`<available_skills>` 佔系統提示 **44%**(19,885 / 45,637 字元)
* **蒸餾的 16 個核心技能有 15 個連註冊層都不在**,只在 120 個名字的目錄層
* **服務哪一層**:整個「參考眾多 repo」的價值 —— 目前絕大部分沒有到達執行期
* **可做的三件事,未決定**:(1) 把三個 superpowers 技能接進形狀路由(唯一有實測效果的機制)
  (2) 把從未被打開的降級以回收提示預算 (3) 蒸餾技能升上註冊層或承認它是文件
* **先做 1 再量**,不要三件一起改 —— 否則量到的是三件事的和
* **2026-08-13 已完成第 1 項**([Round 15](docs/mece/rounds/2026-08-13_round15_註冊了但沒有人叫它.md)):
  形狀路由現在依工作種類點名 `systematic-debugging` / `test-driven-development`,
  多步路由尾端點名 `verification-before-completion`。
  **順帶抓到一個活的缺陷**:路由器注入的是未註冊的 `planning-with-files`,
  而不是 `pi-planning-with-files` —— 8/12 的改名漏掉了真正送到模型面前的那個檔案
* **送達已證明,效果未證明**:實跑一次(非 C.A.S.E. 專案、真實 bug),
  系統提示裡確實有 `[task-shape] This reads like debugging: load the systematic-debugging...`,
  但**模型沒打開該技能,直接把 bug 修好**。效果要靠累積的真實 session
* **第 2、3 項暫緩**,觸發條件寫在 Round 15:上線後累積 ≥5 個真實 session,
  若兩個技能的打開次數仍為 0,則問題不在觸發而在載具,那時再談降級提示預算

### ⚪ T-A9 — 路徑中途漂移(**已查前提:126 個真實 session 裡 1 次。不做,附觸發條件**)
* **證據**:session `019ff6c1` 第 32 步起,模型少寫了 `02_Task_Queue/` 這一層,
  後半段交付物(phase5/6/7 + final-synthesis)落在專案根目錄的另一個同名資料夾。
  它自己的 `progress.md` 產出清單裡兩種路徑並列,而且其中一列與磁碟不符
* **為什麼沒有守衛看得見**:兩邊都在專案內,圍堵只管有沒有離開專案
* **服務哪一層**:**L1**
* **查前提的結果(2026-08-13)**:掃過 126 個真實 session 的每一次 `write`/`edit` 路徑,
  找「同一個任務目錄名出現在兩個不同上層」的形狀 —— **命中 2 個,其中 1 個是誤判**
  (Viblux 那次是同一個位置的絕對路徑與相對路徑兩種寫法)。**真正的漂移:1 / 126。**
* **決定:不做。** 一次不足以定義問題,而守衛會製造自己的失效模式
* **觸發條件**:再出現一次(累積 2 次)就實作 —— 任務認領時記住任務資料夾,
  之後的寫入若落在同名但不同層的路徑就提醒

### ⚪ T-A10 — 產出裡的時間戳是捏造的(**已查前提:126 個裡 2 次,且不可機械判定。不做**)
* **證據**:`progress.md` 的 Session Log 寫「2026-08-07 14:00 / 14:15 / … 18:00」,
  實際檔案 mtime 是 2026-08-13 00:18–00:40。時間看起來合理、間隔平整,**全是編的**
* **為什麼重要**:這個 repo 的核心紀律是「數字來自當下的實跑」。
  一份自帶假時間的產出,會讓後續所有以它為據的判斷失真
* **服務哪一層**:誠信(與 L2 的驗收物守衛同一家族)
* **查前提的結果(2026-08-13)**:掃過 126 個真實 session 寫出的內容,找「日期+時鐘時間
  且日期不是該 session 當天」的行 —— **8 個 session 命中**。但逐一讀過內容後,
  **6 個是合法的**:引用新聞事件時間、引用 API 回應裡的 `TIME=` 欄位、引用裝置紀錄。
  **真正是自己編的只有 2 個**(`019ff6c1` 的 Session Log、`019f7b9f` 的「最後更新」)
* **決定:不做,而且理由比 T-A9 更強** —— 這個形狀**不可機械判定**:
  合法的日期與捏造的日期在工具參數裡長得一模一樣。
  依這個 repo 的教訓(閘會製造自己的失效模式),做一個會誤擋合法引用的守衛,代價高於收益
* **能做的替代**:把「產出裡的時間戳必須來自實際檔案時間或指令輸出」寫進驗收要求,
  而不是寫成守衛

### 已擱置(附觸發條件)
* **技能位置遷移** —— 解的是探針假象。設計保留於
  [decisions/2026-08-11-skill-location-migration.md](docs/decisions/2026-08-11-skill-location-migration.md);
  **真實專案出現 harness 路徑污染時重啟**
* **反轉極性** —— 需要誤擋先驗,而先驗要靠真實使用累積
* **變異掃描支援 `bun`** —— 13 個 `async-exec-bridge/*` 模組因此掃不到,
  理由已寫進 `scripts/check-guard-mutations.py` 的 `UNSWEPT_WITH_REASON`。
  **這台機器 PATH 上沒有 bun,做了驗不了**;裝了 bun 才重啟

---

## 前一段的 Task Queue(2026-08-10)—— **沒有被取代,只是沒被讀**

> **兩個佇列並存,是這份帳本目前最大的缺陷。** 這裡不合併搬移(那會是一份看不出誰動了什麼
> 的大 diff),改成一條規則:**認領下一個任務時,兩份清單都要看**。
> 這一段目前還活著的:**T3、T5、T6、T7**。已結案的:T1、T1b、T1b-rest、T4、T8。
> 撤銷的:T2。併入 T-A5 的:T9。
>
> 規則:**一次認領一個**。做完 → 驗收(附實際指令與輸出)→ 復盤 → 有發現就加 task → 再認領下一個。
> 每一條都要寫**為什麼**,而且要指得出它服務哪一層目標。

### ✅ T1 — 檢查形狀稽核(**已完成 2026-08-10**)
* **為什麼**:一天之內出現**三次**「檢查不會失敗」——
  46 條圍堵測試判 `!== null`、三條路由測試被 fallback 蓋過、
  「repo 沒被污染」查的是看不到 gitignored 的 `git status`。
  **是模式不是巧合。** MECE Round 12 面板判定**優先於新功能**
* **服務哪一層**:全部三層的**前提** —— 檢查會說謊的話,其餘結論都不可信
* **Local DoD**(逐條驗收):
  - [x] 掃出弱檢查清單 —— 143 個候選,收斂到 15 個「拒絕存在但不驗內容」
  - [x] 每一條給處置 —— **而處置的結論推翻了做法本身,見下**
  - [x] 蓄意破壞驗證 —— **做了反事實,結果是我的強化一條都沒多抓到**
* **驗收證據**:`Ran 1288 tests, OK`;`check-guard-mutations.py --cap 4` → 17 模組 0 存活者

**復盤:T1 的結論與它的假設相反。**

1. **強化斷言買不到東西。** 我把 6 條 `assertIsNotNone` 換成「斷言是哪個階段拒絕」,
   然後做反事實(破壞程式碼 × 有/無強化):**25 對 25,強化獨力抓到 0 條** ——
   因為姊妹測試早就斷言了內容。**強化斷言不等於改進,只有在別人抓不到時才算。**
2. **真正找到弱檢查的一直是變異掃描。** 當天三個真實弱檢查
   (`block: true`、路由 fallback、上限)全是掃描找到的,沒有一個是讀斷言風格找到的。
3. **所以槓桿是掃描的覆蓋率,不是斷言的措辭。** 量出來:**48 個純模組,33 個從未被掃過。**
   納入決策路徑上的兩個(`shape.ts`、`plan.ts`)後**立刻冒出 22 個存活者**,
   其中 10 個在我當天才改過的 `plan.ts`。
4. **順帶抓到一個真的分類器偏誤:** `text.length < 25` 是照英文校準的,
   而中文每字元的內容量約兩倍。「研究並比較三個競品的定價與功能差異,並整理成表格」
   24 字,**在看任何訊號之前就被丟掉**。已改成加權長度(CJK 算 2)。
   **但誠實說:真實歷史上 18/106 的多步比例修改前後完全一樣 ——**
   那 6 則卡在線下的中文提示本來就不是多步。**原理對,目前零效果。**

**新增的 task(依規則「有發現就增加」):見 T1b。**

### ✅ T1b — 未掃描模組的變異掃描(**DONE,2026-08-12 Path A 核可**)

**前提更新:未掃描是 22 個,不是 31**(舊數字用了不同的定義,含 `index.ts` 與測試檔)。
純模組 39 個:掃描 26 + 具名排除 13。

**batch 1(2026-08-12 當天寫的程式碼):`case-bridge/calibration.ts`、
`task-shape-bridge/calibration.ts`、`mece-autopilot-bridge/notice.ts`,連帶重掃
`task-shape-bridge/plan.ts` 與 `phase-notice.ts`。**

* 兩支 calibration 各有一個存活者,**同一個突變 `v > 0` → `v > 1`** ——
  設定值剛好是 `1` 時行為不同,而沒有測試分得出來。`1` 是合法值
  (`goalRestateMax: 1`、`queueListingCap: 1`),所以補測試,不是豁免
* `plan.ts` 的 `mtimeMs >= since` → `> since`:計畫寫在 session 起始的**那一毫秒**
  時兩者不同。補了邊界測試
* `plan.ts` 的 catch 分支要 TOCTOU 競態才到得了 → 具名豁免,並寫明方向是刻意的
* `phase-notice.ts` 的既有豁免條目**因行號漂移而失效**(allowlist 檔頭警告過的陷阱,
  第二次發生)。重新對上並實測確認,不是重寫論證
* `notice.ts` 沒有任何可變異的運算子(純字串組裝)——**掃描對它說不出話**,
  覆蓋它的是測試

**batch 2(先前從未掃描的 6 個)**:

| 模組 | 存活者 | 處置 |
|---|---|---|
| `ecc-hooks-bridge/plan.ts` | 2 | **兩個都用測試殺掉**:`.active_plan` 指向沒有計畫的目錄要回退到專案根;`isGitCommit("")` 不是 commit |
| `ecc-hooks-bridge/advisory.ts` | 5 | **4 個用測試殺掉**(空 advisory 被拒、剛好等於預算不截斷、預算小於截斷標記時只回標記、advisory 之間的換行有計數);`DEFAULT_DRAIN_BUDGET` ±1 具名豁免 |
| `ecc-hooks-bridge/ecc-payload.ts` | 3 | **2 個用測試殺掉**(空字串 path 不該變成 `file_path`、空白 `additionalContext` 不該變成 advisory);非物件 section 具名豁免(呼叫端只讀三個欄位,字串上全是 undefined,實測過) |
| `stealth-web-bridge/truncate.ts` | 9 | **待處理**(`humanSize` 的 1024 邊界、`truncateForTool` 的 `<=`/`&&`/換行計數) |
| `stealth-web-bridge/readability.ts` | 1 | **待處理**(`headsAResult` 的 `index + 2`) |
| `deep-research-bridge/research.ts` | 6 | **待處理** |

**掃描器自己的缺陷(這一批最重要的發現):被中斷會把突變留在磁碟上。**
我用 2 分鐘的 timeout 包住一次掃描,它被 SIGTERM 殺掉,
`readability.ts` 就留著 `index + 2`(原始碼是 `index + 1`)。
`mutated_file` 的 `finally` 擋得住所有例外,**而 SIGTERM 不是例外** ——
行程在 `finally` 之前就消失了。二十分鐘後是全套測試把它抓出來的。

* **為什麼比紅測試嚴重**:留在工作區的突變可以被 commit,
  而 `setup.py --mode restore` 會把它裝進 `~/.pi`,在真實 session 裡執行
* **修法兩層**:能攔的訊號(SIGTERM/SIGBREAK/SIGHUP)轉成例外,讓既有的
  `finally` 生效;攔不到的(SIGKILL、斷電)用**標記檔** —— 記下正在被變異的檔案,
  下一次啟動看到標記就拒絕執行並指名該檔。標記檔的行為有測試
* **教訓**:別用短 timeout 包住慢掃描;測試在你沒動過的檔案上變紅時,
  第一個假設應該是「有東西寫了我的工作區」,而不是去 debug 那個測試

**結構性成果(比單次掃描更重要):`tests/test_mutation_coverage.py`** ——
每一個純模組都必須出現在 `GUARD_MODULES` 或**附理由的** `UNSWEPT_WITH_REASON` 裡,
兩者都不在就紅。T1b 的起因正是「33/48 沒被掃描而沒有人說得出來」;
一次性掃描不會保住這件事,這條檢查會。移除任一模組登記 → 紅 1 條(已驗)。

* **13 個 `async-exec-bridge/*` 具名排除**:它們的測試是 bun 的 `.test.ts`,
  而這支掃描器跑的是 `python -m unittest`;`test_async_exec_bridge.py` 只驗結構
  (是不是 ESM、有沒有註冊),指過去只會**每個突變都報 killed 而什麼都沒測**。
  2026-08-12 查證:`bun` 也不在這台機器的 PATH 上。
  **觸發條件**:讓 runner 會呼叫 `bun test <file>`,13 個模組一次進入範圍

### ✅ T1b-rest — 其餘存活者(**完成;「16 個」是抽樣數字,實際更多**)

* **`truncate.ts`:9 個全部用測試殺掉,0 存活者。** `humanSize` 的三個 1024 邊界
  (1023B / 1.0KB / 1.0MB)、剛好等於預算不截斷、只超過其中一個預算仍要截斷、
  保留的第一行必須是原本的第一行、每行的換行只算一次
  (99 位元組 + 換行 = 100,預算剛好裝 500 行)
* **`readability.ts`:抽樣說 1 個,`--all` 窮舉說 8 個。**
  **抽樣的數字會低估,而我先前用抽樣的數字定義了這個任務的規模。**
  已殺掉:heading 緊接在下一行時位址不能被丟、頁尾沒有 heading 的位址仍要丟、
  heading 在第一行時反向掃描要看得到、同縮排的 sibling heading 不算祖先、
  剛好等於 `minChars` 不回退
* **我自己寫了一個不會失敗的檢查**:`assertFalse(out.get("fellBack", False))` ——
  `ReadableResult` 根本沒有 `fellBack` 這個欄位,所以那條斷言對任何輸入都成立,
  `200 -> 201` 因此存活。**寫在專門抓這種缺陷的檔案裡。**
  改成斷言可觀察的行為(回退時 `text === snapshot`),並補上 199 的反向案例
* **`readability.ts`:窮舉後 0 個未豁免**(1 個具名豁免:`indentOf` 的 `: 0`
  分支 —— `/^(\s*)/` 對空字串也匹配,那個分支到不了,已實測四種輸入)
* **`research.ts`:窮舉後 0 個未豁免。** 用測試殺掉 8 個(空 config 不得開啟 deep research、
  摘要剛好等於上限不加省略號、截斷從第一個字元開始、只有 assistant 的 message_end
  才算發現、壞的 content block 不能覆蓋真正的發現、只說一句話的子代理不算沒說話);
  6 個尺寸常數(8 MiB / 256 KiB / 300 的 ±1)以一族具名豁免;
  `appendBounded` 的 `<=` **實測等價**(四種組合都回同一字串);
  另外兩個在**型別註記**上(`: { ok: true } | { ok: false }`),TypeScript 型別
  執行前就被抹除 —— 與已在案的 `bash-containment.ts:47` 同類,而**執行期**的
  `ok` 旗標由新測試斷言
* **T1b-rest 三個模組全部收斂:truncate 9→0、readability 8→0、research 13→0**
  (未豁免計);豁免共 11 條,每條都附呼叫端或實測證據
* **我一直用 `tail -6` 看掃描輸出,前面的存活者被截掉了** ——
  「剩 4 個」有兩次是顯示問題而不是實際數字。完整清單要保留整份輸出

**這一批的另外兩個工具面教訓**

1. **掃描必須單獨跑。** 我讓全套測試與掃描並行,測試讀到被變異的原始碼,
   報出 `failures=9, errors=13`,**沒有一個是真的**;掃描自己的數字同樣不可信。
   已寫進腳本檔頭與 CLAUDE.md
2. **標記檔真的救了一次。** 一次 `--all` 掃描死掉,下一次執行**拒絕啟動並指名檔案**
   (`readability.ts` 停在 `minChars = 201`)。一小時前才加的機制,當天就攔到一次真實復發
* **為什麼**:T1 量到 48 個純模組只有 15 個在掃描裡。納入 2 個就找到 22 個存活者,
  其中 10 個在當天改過的檔案。**剩下 31 個是未知的**
* **服務哪一層**:全部三層的前提(同 T1)
* **Local DoD**:逐一評估納入或寫明為何不納入(例如 `async-exec-bridge/*` 用 bun 測試,
  與這個掃描器的 python 測試模組對不上)
* **成本**:中。掃描很慢,要分批

### 🚫 T2 — 導航修法量測(**已撤銷 2026-08-11,見 Round 14**)
> 它建立在探針假象上:探針 cwd 自己帶著 harness 名稱,而真實 session 是 228 次呼叫碰到 1 次。
> 下面的原文保留,因為**沒有寫下來的撤銷會被重建**。
* **為什麼**:Round 12 的「第二次拒絕時印出工作目錄」上線後,
  **模型第一次自己回頭**(n=1),但下一個 run 又跑回去。
  Round 13 同時要求量誤擋先驗,因為 T3 不能沒有它就上線
* **服務哪一層**:**L1** —— 這是主要失效模式的直接量測
* **可證偽預測(已寫進程式碼)**:三輪內 harness 佇列的認領應下降、工作區佇列應上升。
  **三輪都沒變 = 第四次失敗的加字,改走結構**
* **Local DoD**:
  - [ ] 三個真實 run,同情境同提示
  - [ ] 用 `mine-session.py` 逐一體檢,記錄認領位置
  - [ ] 記錄期間所有被擋的合法工作(誤擋先驗)
* **成本**:三輪 × 最多 25 分鐘

### ⚪ T3 — 反轉極性(唯讀白名單)
* **為什麼**:圍堵六輪被繞過,根因是**枚舉「會寫檔的形式」是無界的**。
  cua 的 deny-by-default 指出正確極性
* **服務哪一層**:**L1 的安全網**(不是根因,根因是 T2)
* **擋住它的東西**:**必須先有 T2 的誤擋先驗。**
  這個 repo 已經有一個因為誤擋被永久關掉的守衛(GateGuard)
* **先寫死的失敗條件**:真實 run 出現誤擋且嚴重到讓人想關掉守衛 → **設計輸了,不是再加例外**

### ✅ T4 — 驗收物守衛的真實驗證(**其實 2026-08-11 就達成了,沒人回來勾**)
* **Local DoD 原文**:一個真實 run 走到「想進 REVIEW 但沒有交付物」並被擋,session log 為憑
* **達成證據**:run 7(session `019ff0e2`)第 23 呼叫、run 8(`019ff0f5`)第 20 呼叫,
  兩次都被 `C.A.S.E. 驗收物守衛` 擋下,模型隨即 `read` 該檔、拿到 ENOENT、重寫交付物。
  `mine-session.py` 的 `dod artifacts` 標籤各記 1 次
* **這一條為什麼會擺著**:完成它的工作是在另一條任務線(T-A1/T-A6)底下做的,
  而**沒有人回頭看舊佇列**。這正是下面那條「兩個佇列」的成本

### ⚪ T5 — 探針殘留清理(**需要擁有者決定**)
* **為什麼**:`02_Task_Queue/Task_001_Inventory/` 是 2026-08-10 探針寫進 CK repo 的。
  我們花整天防未來的污染,**沒清掉自己造成的**
* **2026-08-12 實查**(先前寫「6 個檔案」是估的):`02_Task_Queue/` 本身 gitignored,
  底下 16 個任務包,**只有 `Task_001_Inventory` 是外來的**,7 個檔案
  (`action_log.md`、`inputs/`、`output.md`、`planning.md`、`recipe.md`、`role.md`、`status.txt`);
  其餘 15 個是擁有者自己的任務。**因此這不是「清掉一個目錄」,是「從你的工作目錄挑掉一個」**
* **服務哪一層**:誠信。而且它同時是模型的**誘餌**(L1)
* **擋住它的東西**:那是 CK 的工作目錄,**刪除要他決定**

### ⚪ T6 — Task_020 `[H]` Handoff Capsule
* **為什麼**:協定 §16 明文要求,**我們完全沒實作**。長 run 壓縮後接不上
* **服務哪一層**:**L3**
* **擋住它的東西**:L1 沒過的話,長 run 根本走不到需要 capsule 的地方

### ⚪ T7 — Task_021 learnings 注入(**T8 已完成,見 T-A3**)
* **T7 仍在**:`[T]` 反重複沒實作
* **T8 已完成**:目標重述的內容源已於 T-A3 換成當前任務的 Local DoD,
  live 送達由 run 9 證明(第 31、48 呼叫)
* **服務哪一層**:**L3**;**擋住 T7 的東西**:同 T6

### 🔗 T9 — 噪音底線量測 → **與 T-A5 是同一件事,已併**
* 兩條的內容相同(同提示同臂 42 vs 4)。**以 T-A5 為準**,這裡保留指標而不刪,
  免得下一個人以為漏了一項

**排序理由:T1 是全部的前提(檢查要先可信),T2 是 L1 的直接量測且擋著 T3,
T4 便宜且可順帶做,T6–T8 都被 L1 擋住,T9 只擋效果宣稱。**

---

## 方法:為什麼改成「批次改 + 深挖一份 log」

2026-08-10 統計本段工作的實際產出:

| 方法 | 花費 | 產出 |
|---|---|---|
| A/B 實驗(漂移 v1、v2) | 7 個真實 run + 3 次情境設計 | **0 個結論** |
| 深讀 session log | 4 份 | **6 個真實缺陷** |
| 變異掃描 | 4 個模組 | 4 個缺陷 + 1 段死碼 |
| 蓄意破壞 | ~20 次 | 驗證了每一個守衛 |

**關鍵區分:控制變因只有「量效果」需要,「找缺陷」不需要。**
`cp a b 2>/dev/null` 讓目的地消失,這是不是缺陷跟同時改了幾件事無關。
我們大部分工作是找缺陷,卻一直付量效果的價錢。

**已做成工具:`python scripts/mine-session.py --latest [--full]`。**
它跑的就是那四次手動深讀的固定清單:輪次與呼叫數、批次形狀、
哪些注入真的送到模型、哪個守衛拒絕了幾次、**連續拒絕是否逐字重複**、
**模型有沒有自己讀過被注入給它的檔案(歸因混淆)**、以及完整工具序列。

驗證方式是拿**已知答案的 session** 對照 —— 對那個跑錯 repo 的 run,
它自動報出 `phase gate 9 / containment 1 / harness-root hint 1 / tool-first 1`
與「4 次拒絕與前一則逐字相同」,與我手動查出的完全一致。
fixture 是從真實 session **切出來的連續片段**,不是編的。

---

## 方法論缺口(2026-08-10 查證 → **已修**)

擁有者問:subagent 領 local 任務時,有沒有 planning 與 superpowers 方法在執行?
**答案是沒有,而且是三個獨立缺口。**

| # | 缺口 | 證據 |
|---|---|---|
| 1 | **路由器分類的是使用者訊息,不是任務** | `task-shape-bridge/index.ts:110` 是 `classifyRequest(event.prompt)`。佇列 run 的使用者訊息是「繼續」,而多步的工作寫在 `recipe.md` 裡,路由器從來沒讀過它 |
| 2 | **兩套計畫系統互不認識** | `plan.ts:55` 的 `hasAnyPlan` 找的是 `task_plan.md`;C.A.S.E. 任務寫的是任務包裡的 `planning.md`。專案根目錄有一份 `task_plan.md`,佇列裡每個任務的路由提示就全被抑制 |
| 3 | **任務層完全沒有方法論路由** | 階段閘的 PLAN 拒絕說的是「寫 planning.md(步驟、檔案、驗證方式 + Self-Review)」—— 那是**範本**,不是**方法**。沒有任何注入說「除錯用 systematic-debugging、新工作先 brainstorming」,而那是 `CLAUDE.md` 與 `AGENTS.md §10` 的規定 |

### 修法:讓位,而不是搬分類器

兩個 bridge 是同層安裝、彼此沒有相依,**沒有跨 bridge import 的先例**;
而重造分類器是本 repo 已經犯過的錯。所以修法是:

* **路由器在 C.A.S.E. 專案裡讓位**(`plan.ts::isCaseProject`)——
  它的 routine 說「寫 `task_plan.md`」,而 C.A.S.E. 任務要的是任務包裡的 `planning.md`。
  **它在 C.A.S.E. 專案裡給的建議本來就是錯的**,所以缺口 1 與 2 一起消失,不需要分類器。
  這與階段閘讓位給目錄圍堵是同一個模式:**誰有更具體的抱怨誰講話,而且只有一個講得到。**
* **方法論寫進任務專屬憲法**(`task-context.ts::methodology`)——
  在認領那一刻、走已證明送得到的通道。依任務 Objective 的少數字面訊號
  挑 `systematic-debugging` / `brainstorming` / `test-driven-development`;
  **沒命中時給出完整路由規則,不是沉默**(沉默會被讀成「不需要方法」)。
  `planning.md` + `## Self-Review` 那一半**永不隨關鍵字而條件化** ——
  階段閘無論任務長什麼樣都會擋。

證據:`Ran 1210 tests, OK`;四個蓄意破壞全紅;變異掃描 `--only task-context --all` **0 存活者**;
`verify-bridges.py` 13 bridges 0 failures。

**過程中修掉一個我自己寫的假測試**:三條路由測試原本只斷言「技能名出現過」,
而沒命中時的 fallback 會列出全部三個 —— **刪掉路由規則測試照樣綠**。
改成斷言「有沒有真的路由」(前綴 + 該前綴之後的內容),三個分支現在都咬得住。

**關於 subagent:** 目前**沒有**每個任務開一個子行程的機制。
若要做,子行程有自己的 user prompt,`before_agent_start` 會重跑 ——
**缺口 1 會自動被修掉**,因為子行程的提示就是任務描述。
但 Pi 自己的 subagent 範例用 `--no-session`,那會廢掉本 repo 的驗證紀律,必須改用 `--session-dir`。

---

## 進度真實狀態(2026-08-10 逐條查證)

> **注意:`01_Roadmap/roadmap.md` 的勾選框是壞的** —— 18 個 `- [ ]` 裡約 8 個內文已寫
> `DONE` / `REVIEW`,只是從來沒打勾。要看真實狀態請看這一節。

### 已完成並驗證
| 項目 | 證據 |
|---|---|
| 目錄圍堵(write/edit/bash) | [Task_004](docs/case/task-004-case-guard-bash.md)、[Task_013](docs/case/task-013-write-forms.md) |
| cwd 混淆重導提示 | [Task_003](docs/case/task-003-cwd-confusion.md) |
| 研究深度守衛 | [Task_005](docs/case/task-005-research-depth-bash.md) |
| 被擋呼叫的矯正器 | [Task_010](docs/case/task-010-blocked-claim-vocabulary.md)、[Task_011](docs/case/task-011-blocked-claim-channel.md) |
| 階段閘 + 階段開放通知 | [Task_016](docs/case/task-016-phase-tool-gate.md) |
| Path A 人類驗收 | [Task_018](docs/case/task-018-path-a-human-review.md) |
| 推進器 settled 迴圈 | [Task_015](docs/case/task-015-advancer-settled-loop.md) |
| 佇列推進器 | [Task_001](docs/case/task-001-queue-advancer.md) |
| Checker pass | [2026-08-08](docs/case/2026-08-08-checker-pass.md) |
| 推進器預設值建議 | [2026-08-09](docs/case/2026-08-09-advancer-default-recommendation.md) |

### 做了但沒有結論
| 項目 | 狀態 |
|---|---|
| `Task_019` 目標重述 | **送達已證明,有效性三次量測都測不到** — [預先登記與三次結果](docs/measurements/2026-08-09-task019-preregistration.md) |
| `Task_023` 任務小憲法 | **送達已證明,行為影響未歸因**(模型在認領前自己讀了 role.md)— [文件](docs/case/2026-08-10-task-local-constitution.md) |
| `Task_022` 漂移 A/B | 7 個 run,**三次情境都造不出會漂移的對照組** |

### 尚未開始(9 項,2026-08-10 修好勾選框後的實數)
`Task_012` 守衛形狀稽核 / `Task_014` 上游回饋 / `Task_020` Handoff Capsule /
`Task_021` learnings 注入 / `Task_024` 重述換內容源 /
`Task_006` Layer 1 可達性 / `Task_007` catalog 分級 / `Task_009` 舊議題重評

> 勾選框已於 2026-08-10 逐條核對修正:6 項內文寫著 DONE/REVIEW 卻沒打勾,已補;
> `Task_001` / `Task_015` 補上完成註記;`Task_022`(結論為「測不到」)與
> `Task_023`(送達已證明、影響未歸因)改為已完成並註明真實狀態 ——
> **「已跑出否定結果」不是待辦。**

### 其他缺口
* **Global DoD:3 條 ❌、1 條 ⚠️** — [global_dod.md](01_Roadmap/global_dod.md)。
  第 6 條(噪音底線未量測)是所有 A/B 結論的前提,至今未做
* **Prior art:37 個來源,16 個未審視** — [REGISTER.md](docs/prior-art/REGISTER.md)
* **新的第 2 階拒絕(帶佇列資料)在真實 run 從未觸發過**

---

## 工作紀錄

### 2026-08-12(第七段) — 量到噪音底線,順手抓到一個會說謊的測試套件

**1. 噪音底線(T-A5)。** 同題同臂五次:44 / 47 / 49 / 62 / 116 次工具呼叫,
sd 26.91,變異係數 42%。**n=2 只能偵測 38 次呼叫以上的差** ——
這個 repo 過去每一個引用呼叫數的比較都是 n=1 或 n=2。
判準寫在看數字之前([noise-floor](docs/measurements/2026-08-12-noise-floor.md)),
outlier 沒有拿掉(拿掉 sd 剩 6.87,等於把「這個比較做不了」改成「做得了」)。
**過程指標吵、結果指標穩**:status 5/5 REVIEW、交付物清單 5/5 相同 ——
所以判斷要用二元 DoD,不要用呼叫數。

**2. 一個五次跑出一次紅的套件,真因不是玄學。**
36 個測試檔各自把 node 驅動寫到**寫死的檔名**(`tests/.tmp_*_driver.mjs`)。
一次跑一個沒事;兩個測試程序同時跑,彼此的 `finally` 互刪對方的檔案。
舊碼並發重現:`failures=25, errors=5` 與 `failures=42, errors=9`,**沒有一個是真的**。
改成帶行程編號的名字(`tests/_scratch.py`)後,同樣的並發六次全綠、無殘留。

**這一段自己的三個教訓:**
* **紅了就重跑會訓練出「紅是雜訊」的習慣** —— 那是這個 repo 能產生的最貴的訊號。
  防回歸的檢查 `tests/test_scratch_paths.py` 因此附了一條「證明比對式抓得到真壞寫法」的測試
* **機械式大量改寫會半路死掉。** 我的改寫腳本在第 31 個檔案拋例外,前 30 個已經寫回磁碟且
  少一行 import —— repo 當下既不是舊的也不是新的。用 `NameError` 才發現。
  改完立刻編譯 + 立刻跑,不要等最後
* **修完要重跑「重現步驟」,不是重跑單元測試。** 第一輪漏掉 pathlib 的
  `ROOT / "tests" / ".tmp_x.mjs"` 寫法,單元測試全綠,**是並發重現把它抓出來的**


### 2026-08-10(第六段) — CI 抓到我、cua 審視、Round 13
**做了什麼:** 修 CI(平台專屬 fixture);審視 cua 並登記;MECE Round 13 重定威脅模型;
修掉兩個守衛對「絕對路徑」的定義不一致。
[Round 13](docs/mece/rounds/2026-08-10_round13_把導航問題當成資安問題.md)・
[cua 審視](docs/prior-art/2026-08-10-cua-review.md)

**收穫:**
* **我們從來沒有沙箱** —— 唯一邊界是解析字串的守衛。而 Pi 自己
  (`dist/bun/restore-sandbox-env.d.ts`)預期**在外部沙箱裡跑**,擴充層沒有任何權限機制
* **cua 唯一可移植的是極性:deny-by-default。** 而關鍵不是 fail-closed,是
  **哪一半是無界的** —— 枚舉「會寫檔的形式」無限,枚舉「唯讀指令」有界
* **這是導航問題,不是資安問題。** 模型先迷路,**被擋之後才開始規避**
  (`ECC_GATEGUARD=off`)。強化邊界會製造它要防的行為
* **CI 是對的,我的 fixture 是錯的** —— `D:/...` 在 Linux 是相對路徑。
  而修完測試才發現**產品碼有同一個病**:containment 認得磁碟機代號,phase gate 不認得,
  **兩個守衛對同一條路徑給相反答案**
* **有些測試只在 CI 上有牙齒** —— 那條跨平台測試在 Windows 上蓄意破壞也不會紅,已寫進 docstring
* **同一處修到第三次,就不是缺陷是設計錯了** —— 我修了六輪才回頭查 prior art,
  而那條規則一直都在

### 2026-08-10(第五段) — MECE Round 12:守衛都對,結果仍然錯
**做了什麼:** 十三角色面板復盤五個真實 run;實作結論一(圍堵從描述改成展示)。
完整討論:[Round 12](docs/mece/rounds/2026-08-10_round12_守衛都對而結果仍錯.md)

**收穫:**
* **不作弊的情況下,五個 run 有四個沒產出交付物** —— 今天修的七項沒有改變這個數字
* **模型不是混淆,是推論** —— 系統提示裡 harness 路徑出現 28 次、cwd 出現 1 次,
  而那個路徑下真的有一個二十個任務的佇列。**它選了證據強的那一邊**
* **修法不是告訴它「你錯了」,是把它缺的那一半證據給它** ——
  第二次拒絕起改成印出工作目錄的實際內容與任務名稱
* **我自己的檢查也在用弱證據下強結論**:`git status` 乾淨就宣布沒污染、
  `!== null` 就宣布守衛有效、只斷言技能名出現就宣布路由正確。**三次,是模式不是巧合**
* **誘餌是開發環境特有的** —— 使用者 clone 後 `02_Task_Queue/` 是空的。
  但 28:1 的證據比例在任何機器上都在

**尚未做(Round 12 的其餘結論):**
* F:檢查形狀稽核(掃現有測試裡不會失敗的弱斷言)—— **優先於新功能**
* B:誘餌是 CK 的工作狀態,**只報告不動手**
* E:噪音底線量測,排 roadmap,不擋缺陷修正

### 2026-08-10(第四段) — 三個守衛各自成功,合起來放行一個空的 REVIEW
**做了什麼:** 體檢真實 run;補上「進 REVIEW 前檢查 DoD 點名的檔案是否存在」。

**收穫:**
* **圍堵修好之後,模型第一次自己回頭** —— 第 9 次呼叫想在 harness repo 建任務包被擋,
  之後回到自己的 cwd 正常工作。前三次都沒有回頭
* **任務憲法終於在真實 run 觸發**,方法論路由挑了 `brainstorming` ——
  **與跑之前寫下的預測一致**
* **但最終狀態是 `REVIEW`,而 `output.md` 與 `planning.md` 都不存在。**
  模型兩次想跳到 DONE,兩次被轉換守衛擋下,於是走了**合法的那條路**到 REVIEW ——
  而合法的那條路不需要任何交付物。**門檻定義規避的形狀,又一次**
* **它其實已經寫出報告了** —— 被擋掉的那次呼叫帶著完整的 retries 對照表。
  認領完成、階段開放通知響了兩次,**它從來沒有重寫 output.md**。工作做完然後丟掉
* **REVIEW 是召喚人類驗收的狀態** —— 照原樣,使用者會被請去驗收一個空資料夾

### 2026-08-10(第三段) — 圍堵被直譯器繞過,而我的驗證看不見
**做了什麼:** 用 `mine-session.py` 體檢真實 run,查出 containment 有六種繞過,全數封閉。

**收穫:**
* **模型被擋兩次之後改用 `python3` 寫檔,成功寫進另一個專案** ——
  一整個任務包(role/recipe/planning/5188 bytes output/status)進了 harness repo。
  `bashContainmentBlock` 只認得 shell 重導向、`tee`、`cp`/`mv`、`mkdir`、`dd`、`sed -i`,
  **不知道直譯器會寫檔**。這是同一類的第四次
* **它先試 `ECC_GATEGUARD=off bash -c ...` —— 主動找繞過**。被擋才改用 python3
* **我當時宣告「repo 乾淨」是錯的** —— 我查 `git status`,而 `02_Task_Queue/` 是 gitignored,
  **那個檢查在結構上看不到它**。驗證方法本身無法證明它宣稱排除的事
* **`block: true` 是物件字面值,不是型別宣告** —— 變異掃描把它翻成 `false`,
  我 46 條測試全綠,因為測試判的是 `!== null`,而 `{block:false}` 也不是 null
* **allowlist 用行號當鍵,一個 session 內位移三次**,第三次在我記錄第二次的十分鐘後。
  已改成**用欄位與運算子比對**,位移只提示不失敗 —— 治因不治症

### 2026-08-10(第二段) — 任務層方法論(Task_025)
**做了什麼:** 路由器在 C.A.S.E. 專案讓位;方法論路由寫進任務專屬憲法;總控文件 `PROGRESS.md` 上線。

**收穫:**
* **兩個機制給相反建議時,先問哪一個本來就不該說話** —— 路由器在 C.A.S.E. 專案裡
  指的是 `task_plan.md`,那個建議從一開始就是錯的。讓位比整合便宜
* **沉默會被讀成「不需要」** —— 方法論沒命中任何訊號時給完整規則,不是不講
* **一個分不出「命中」與「fallback」的測試,不是測試** —— 刪掉路由規則它照樣綠
* **總控文件必須被檢查守著** —— `test_progress_ledger.py` 第一次跑就抓到 11 份沒被連到的文件

### 2026-08-10(上半) — 守衛品質三修 + 儀器缺陷
**做了什麼:** 守衛互撞三項全修;`2>/dev/null` 解析缺陷兩處;`pi --print` stdin 卡死。

**收穫:**
* **`2>/dev/null` 讓兩個抽取器同時壞掉,方向相反** —— 階段閘誤擋無害的 `ls`,
  目錄圍堵放行逃出專案的 `cp`。同一個疏漏,只補過一個地方。
  [文件](docs/case/2026-08-10-guards-collide.md)
* **守衛互撞看起來像優先權問題,查下去是解析器的錯。**
  先問「這些拒絕本來就該發生嗎」,再問「誰該先講話」
* **一個 tool_call 只有一個守衛擋得成,先開口的就是唯一被聽見的。**
  階段閘說「先認領任務」(真的,而且是錯的那句),containment 知道「你在別的專案」卻被跳過
* **`pi --print` 會卡在讀 stdin** —— 兩次 25 分鐘空白被我說成「暫時性」,
  實際是可重現的:`< /dev/null` 就好。**卡住和真實的零長得一模一樣**
* **修法不是多寫幾段話** —— 階段閘手上有佇列絕對路徑,卻背誦路徑的形狀。缺的是資料
* **allowlist 條目會過期** —— 用行號當鍵,上面插程式碼就靜默失配,存活者看起來像新的
* **測試綁在實作拼法上會假性變紅** —— 比對常數名稱、切固定字元數,兩者都咬過我

### 2026-08-09 — 反漂移缺口分析
**做了什麼:** 對照 C.A.S.E. 找出反漂移缺口;`Task_019` 目標重述;`Task_023` 任務小憲法。

**收穫:**
* **`before_agent_start` 每則使用者訊息只跑一次,不是每輪** ——
  實測 1 則訊息 / 16 輪。`CLAUDE.md` 寫錯了好幾週
  [文件](docs/case/2026-08-09-anti-drift-gap-analysis.md)
* **換任務用的是 custom message,不開新 prompt cycle** ——
  所以憲法、Roadmap、小憲法都不會因為換任務而重新出現
  [文件](docs/case/2026-08-10-task-local-constitution.md)
* **每個機制都在回答「這一步准不准」,而漂移問的是「我還在做對的事嗎」**
* **乾淨的 run 無法驗證反漂移機制** —— 沒有病人就證明不了藥
* **不能用「給更多資料」把任務變長** —— 40 個檔案被一個 for-loop 吃掉,3 次呼叫做完
* **同一提示同一臂:42 vs 4 次工具呼叫** —— 一個數量級的變異,小樣本 A/B 無意義

---

## 相關索引

* [反漂移缺口分析](docs/case/2026-08-09-anti-drift-gap-analysis.md)
* [任務小憲法](docs/case/2026-08-10-task-local-constitution.md)
* [守衛互撞](docs/case/2026-08-10-guards-collide.md)
* [Task_019 預先登記與結果](docs/measurements/2026-08-09-task019-preregistration.md)
* [oh-my-pi-can1357 審視](docs/prior-art/2026-08-09-oh-my-pi-can1357-review.md)
* [Global DoD](01_Roadmap/global_dod.md) ・ [Roadmap](01_Roadmap/roadmap.md)

## 其餘紀錄(由 tests/test_progress_ledger.py 維持齊全)

* [佇列推進器:拿掉誘餌之後的重測](docs/measurements/2026-08-06-advancer-clean-rerun.md)
* [佇列推進器:三個 bash 洞補完後的重測與判定](docs/measurements/2026-08-06-advancer-verdict.md)
* [深度閘與產出閘:第一次實測開火](docs/measurements/2026-08-06-depth-and-artifact-gates-live.md)
* [佇列推進器:第一次真實量測](docs/measurements/2026-08-06-queue-advancer-first-run.md)
* [2026-08-08 4b 重測:閘擋住了開場那一擊,而模型從此不再搜尋](docs/measurements/2026-08-08-4b-turn-ramp.md)
* [2026-08-08 推進器重測:迴圈接起來了,而開場那一擊仍然穿過去](docs/measurements/2026-08-08-advancer-remeasure.md)
* [2026-08-09 CLAIM 額度實驗:先下注,再量](docs/measurements/2026-08-09-claim-budget-bet.md)
* [2026-08-09 乾淨重測:迴圈第一次在研究型 run 收斂,而先規劃只成立一半](docs/measurements/2026-08-09-clean-research-runs.md)
* [2026-08-09 階段轉換通知:響了,而且模型恢復搜尋](docs/measurements/2026-08-09-phase-notice-live.md)
* [Measurements](docs/measurements/README.md)
* [技能可達性全掃](docs/measurements/skill-reachability.md)
