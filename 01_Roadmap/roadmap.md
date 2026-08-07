# Roadmap — 讓方法論真的跑起來

> **Authority:** Layer 2 (Macro Planner / 宏觀層)
> **Read-Only for:** Layer 3 (Micro Executors / 微觀層)
> **建立於** 2026-08-06,承接 `docs/mece/rounds/` 第 1–10 輪與
> `docs/superpowers/specs/2026-08-06-requirement-realignment.md`

## 為什麼有這份 roadmap

擁有者的原始需求拆成十條(R1–R10,見需求對齊文件)。**實測狀態:2 條解決、2 條部分、6 條開放。**

已解決的都屬於同一類:**擋住最糟的路**(不讀就搜、不留檔、無憑據)。開放的也屬於同一類:
**讓最好的路自己發生**(先規劃、切分、逐項、復盤、進 queue)。

第 9–10 輪把差別命名了:

> **agent-proposed activation**(把技能攤在模型面前,等它提議)—— 實測 0/3
> **policy-mediated activation**(系統依設定與觸發條件決定)—— 2026 文獻與 Anthropic 指引的共識

所有開放項目卡在同一句話:**程式管得了「怎麼做」,管不了「要不要開始做」。**

## 當前工作順序(2026-08-06 重排,理由見下)

前一版的順序是「照疤痕修」。今天量到的三件事把順序整個推翻:

* 推進器的三個缺陷是**地基**(事件位置、停滯判準、誰的狀態被改),不是參數;
* 這三件我們自己的筆記早就寫過,而**沒有東西把筆記接到工作上**;
* cwd 混淆吃掉 5 次 run 裡的 2 次 —— 它比推進器更上游。

新順序:

| # | 做什麼 | 為什麼排在這 |
|---|---|---|
| 0 ✅ | prior-art 登記表 + CI 檢查 + RATIONALE 格式(取自 OmniHeal) | 不先修這個,下面每一項都會再重做一次 |
| 1 ✅ | **先讀**:`auto-pi`、`loopy`,寫進 [RATIONALE](../docs/prior-art/RATIONALE.md) | 做對了:auto-pi 的階段門控直接改變了下面的順序,新增 Task_016 排在 Task_015 前面 |
| 2 ✅ | **`Task_016_phase_tool_gate`**(REVIEW):階段工具白名單,在 `tool_call` 擋 | **閘會響、繞道被堵、但模型仍未認領** —— 擋阻移除錯的路,不供給對的路。見 [docs/case/task-016-phase-tool-gate.md](../docs/case/task-016-phase-tool-gate.md) |
| 2b ✅ | `Task_015_advancer_settled_loop`(REVIEW) | **跑通了**:閘 + 推一起,任務自己走到 `REVIEW`,推進器只開口 4 次、零升級。換事件那一項以證據反轉(`agent_settled` 依合約接不到續跑) |
| 2d ✅ | **repo↔installed 漂移檢查**(`scripts/verify-bridges.py`) | 2026-08-08:Task_003 的修正推上去了卻**沒安裝**,Pi 整天載入修正前版本,而 910 測試 + 四個檢查全綠。「Pi 跑的是安裝副本」以前**只有紀律**;現在有 missing / changed / extra 三種形狀,對真實安裝目錄證明過會紅 |
| 2e ✅ | **Checker 核可批次**(使用者授權單軌) | 十個任務九個 `DONE`、`Task_003` 擋下。判定與三項副產發現見 [docs/case/2026-08-08-checker-pass.md](../docs/case/2026-08-08-checker-pass.md) |
| **2c** | **`Task_017_guard_mutation_check`**(新增) | 全日復盤:B 類失敗(檢查無法失敗 / fixture 無法區分)今天兩次、更早兩次,而目前**只有紀律沒有機制**。**且 Task_003 已明確把兩個活下來的變異留給它抓,那是解除 Task_003 REVIEW 的條件。** 見 [docs/retro/2026-08-06-session-retrospective.md](../docs/retro/2026-08-06-session-retrospective.md) |
| 3 ⏸ | `Task_003_cwd_confusion`:交付已生效,**核可被擋在 REVIEW** | 5 種破壞只抓到 3 種;結論見 [docs/case/task-003-cwd-confusion.md](../docs/case/task-003-cwd-confusion.md) |
| 4 | 重測(基準線 3 次 + 研究型 1 次),**才**談 `enableCaseAdvancer` 預設值 | 判定要建立在修好的地基上 |
| 5 | 依 `docs/prior-art/REGISTER.md` 的優先序清掉其餘 25 個未審視來源 | 每清一個寫一則 RATIONALE 條目 |

**一條從 OmniHeal 借來、待評估的改進**:它的 3-Strike 是分層的
(第 1 次換方式 → 第 2 次再換 → 第 3 次記錄並跳過)。
本專案的守衛退場是「擋滿 3 次就讓路」,**中間沒有「換一種方式」那一層** ——
模型撞三次同一道牆之後直接放行,而不是被引導改用別的做法。

## Phase 1:把流程的持有權拿回來

- [ ] `Task_001_queue_advancer`:佇列推進器 —— turn_end 讀佇列狀態,查 CASE 轉換表得出下一步,
      注入並觸發下一輪。預設關閉。
- [ ] `Task_002_advancer_measurement`(佇列狀態 `REVIEW`;§1 不許做這件工作的 session 核可它自己):在真實專案量遵循率 = 狀態前進次數 / 推進次數。
      **魔鬼代言人已下注:第一次不會是 1.0。先說,再量。**
      → **注贏了:0/3。** 但機制成立(3 次推進 + 1 次升級,分毫不差),0 的原因是模型在
      錯的目錄作業,與推進器無關。見
      [docs/measurements/2026-08-06-queue-advancer-first-run.md](../docs/measurements/2026-08-06-queue-advancer-first-run.md)。

**出口條件**:✅ 有一份真實 session 的遵循率數字。

## Phase 2:依量測結果決定下一步

- [ ] `Task_003_cwd_confusion`:**降級已撤銷 —— 2026-08-06 的 advancer 判定量測顯示
      它吃掉 5 次 run 裡的 2 次(擋阻 11 次與 72 次,狀態一次都沒離開 PENDING)。
      這是目前最大的單一失敗來源,最高優先。** 原本的降級理由如下,保留以示對照:
      ~~降級為效率問題。~~ 乾淨重測顯示模型前 16 步在錯的目錄,
      但**自己修正了**,任務仍走到 DONE。所以它拖慢流程、不阻斷流程。原本的計畫是: Task_002 顯示遵循率 0 的原因
      不是推進器,是模型把相對路徑解析到 harness 根目錄去。同一問題今天出現三次。
      **修法已依實測修正**:dump 出的 prompt 顯示 Pi **本來就宣告了** cwd(1 次,89% 深度),
      而 harness 的絕對路徑出現 28 次(多數是 `<available_skills>` 的 `<location>`)。
      問題是訊噪比,不是沒講 —— 所以不再往建議通道加話,改在**擋阻理由**裡糾正世界觀。
- [ ] `Task_004_case_guard_bash`:**最高優先。** 2026-08-06 的乾淨重測顯示五條 C.A.S.E.
      守衛全部被 `bash printf > status.txt` 繞過 —— 包括「Worker 不得自我核可」這條
      §1 不可協商的公理。守衛只看 `write`/`edit`。協定 SKILL.md:122 與 for_agents.md:424
      **本來就禁止** shell 重導向改檔,所以這是強制既有規則,不是新增。
      → REVIEW,結論見 [docs/case/task-004-case-guard-bash.md](../docs/case/task-004-case-guard-bash.md)。
- [ ] `Task_005_research_depth_bash`:**第三個同型洞。** `research-depth.ts:84` 同樣只認
      `write`/`edit`。後果:產出閘看不到 bash 寫的檔會誤擋;**引用閘完全繞得過** ——
      而它正是唯一被實測證明改變行為的守衛(檔案內網址 0/0/0 → 10/15/0)。
      不是推測:乾淨重測的紀錄裡模型用 `cat > output.md << EOF` 寫檔。
      → REVIEW,結論見 [docs/case/task-005-research-depth-bash.md](../docs/case/task-005-research-depth-bash.md)。
- [ ] `Task_010_blocked_claim_vocabulary`:矯正器的動詞表漏掉真實說法(第三句)。
      → REVIEW,結論見 [docs/case/task-010-blocked-claim-vocabulary.md](../docs/case/task-010-blocked-claim-vocabulary.md)。
- [ ] `Task_011_blocked_claim_channel`:**被擋的呼叫不發 `tool_result`**,所以這個守衛
      從來沒響過;改用 `tool_execution_start`/`end` 配對,並修好輪次邊界。
      → REVIEW,**已在真實 session 拿到交付證明**(模型收到注入後自己查檔並更正)。
      結論見 [docs/case/task-011-blocked-claim-channel.md](../docs/case/task-011-blocked-claim-channel.md)。
- [x] `Task_008_advancer_verdict`(佇列狀態 `REVIEW`):**判定 = 維持 `false`。**
      21 次 status 寫入全走 `write`/`edit`、`bash` 0 次(基準線是 3 次全走 bash)——
      Task_004/005 的修正在真實流程裡成立。但 5 次 run 沒有一次到 DONE,因為退場計數器
      數的是注入次數而非停滯,終點步驟必然被判卡住;而研究型 run 顯示推進器在 `turn_end`
      根本追不上「一上來就搜」。見
      [docs/measurements/2026-08-06-advancer-verdict.md](../docs/measurements/2026-08-06-advancer-verdict.md)。
- [ ] `Task_015_advancer_settled_loop`:**不是調計數器,是換地基。** 依
      [docs/prior-art/2026-08-06-pi-until-done-loop-reference.md](../docs/prior-art/2026-08-06-pi-until-done-loop-reference.md)
      的四項對照移植:(1) 續跑改掛 `agent_settled`;(2) 停滯判準改為加權 progress
      signal `=== 0`;(3) **自動化放棄時暫停自己,不去寫 `status.txt`** ——
      目前三次 ESCALATED 有至少兩次是我們自己造的假失敗;(4) 終端步驟不計時。
      移植前先用探針量 `agent_settled` 的真實觸發時機(型別不說觸發時機)。

**出口條件**:預設值有實測依據,不是設計時的直覺。

## Phase 2b:三個 retro 提出、目前只活在任務包裡的後續

**這一節存在的理由:** retro 寫在 `02_Task_Queue/`,而那是 gitignore 的。
`docs/case/` 有結論摘錄,但沒有人會把摘錄當待辦追。不列進來就是靜靜漂走。

- [ ] `Task_012_guard_shape_audit`:掃 `pi-extensions/**/*.ts`,凡是以工具名稱集合為
      條件的分支,同檔沒有 `bash` 分支就報告。**同型缺陷今天出現三次**
      (Task_004 / Task_005 以及更早的目錄圍堵),第四次不該再靠人想起來。
      同一支腳本可一併檢查「每個 bridge 有沒有訂閱它需要的事件」(Task_011 的教訓)。
- [ ] `Task_013_write_forms_blind_spot`:`sed -i`、`tee -a`、`dd of=` 對 `writeTargets`
      完全不可見。補它要同步改 `bash-containment.ts`、case-bridge 的複製與平權測試。
- [ ] `Task_014_case_upstream_round2`:兩條上游回饋還沒送出 ——
      (a) 任務包之間沒有「同型缺陷」的連結欄位;
      (b) `Local Definition of Done` 沒有區分單元證據與**交付證據**,
      而 Task_011 證明了兩者可以差一整天。

## Phase 3:剩下的可達性缺口

- [ ] `Task_006_layer1_reachability`:README 的 Layer 1(`grilling-protocol` /
      `contrarian-review` / `adversary-review`)全在 catalog 層無描述。先量升 core 的
      prompt 成本,再決定。
- [ ] `Task_007_catalog_triage`:120 個 catalog 技能逐一評估哪些值得升 core。
      已全數落檔於 `docs/measurements/skill-reachability.md`。

## Phase 4:已知但刻意未解

- [ ] `Task_009_open_issues_review`:結論隨施壓翻轉、編造搜尋端點網址、19 個外來技能佔
      描述層。每一項重新評估「刻意不做」是否仍成立。

## 不在這份 roadmap 裡的

* **重寫 C.A.S.E. 或 MECE-Autopilot 為原生** —— 第 5–6 輪否決:分岔風險,而且
  「bridge 有問題」的診斷本身不成立(有效的引用閘就是 bridge,差別在通道)。
* **自動 bootstrap** —— 汙染不知情使用者的目錄;啟動是決策,政策 opt-in 才是解。

---
*Edit this file to define project phases and milestones. Layer 3 agents must NOT modify this file.*
