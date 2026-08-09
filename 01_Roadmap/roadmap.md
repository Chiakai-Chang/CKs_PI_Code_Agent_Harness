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

## 當前工作順序(2026-08-09 再次重寫)

**這份表在 8/8 才重寫過一次,一天內又長出三列已完成卻標成待辦的項目。**
成因是我在同一個 session 裡「發現→新增一列→當場做完」,而只記得新增。
**規則:一列做完就當場移到下一節,不留到下次重寫。**

| # | 做什麼 | 為什麼排在這 |
|---|---|---|
| **1** | **決定 `enableCaseAdvancer` 的預設值** | 五項需求都已實測為綠,**而整條迴圈只在旗標開啟時運作,旗標預設是關的**。這是唯一擋在「使用者實際受益」前面的一步 |
| 2 | 基準線提示以出貨設定重跑 ≥3 次 | 目前的 2/2 只涵蓋研究型;預設值要對所有情境負責 |
| 3 | refinement 事件 append-only + 回滾(取自 prime-agent) | **在有回滾之前不要讓 harness 自我改進** |
| 4 | supplemental-only 提示層(取自 prime-agent) | 會改變注入形狀,排在回滾之後 |
| 5 | 讀 Continual Harness 論文(arXiv 2605.09998) | 確認上面兩項有無前提沒抄到 |
| 6 | 清掉 REGISTER 其餘 23 個未審視來源 | 每清一個寫一則 RATIONALE |
| 7 | 變異掃描 `--all` 的既有存活者 | 品質債,非活的繞道 |

**待核可(Path A)**:`Task_020_phase_opened_notice`

## 已完成(2026-08-06 ~ 08)

| 項目 | 結論 |
|---|---|
| `Task_019_harness_scope` | local/global 分域,預設 local;實驗設定從此活在 fixture,repo 不再被改 |
| 階段轉換通知 | **實測送達**:認領前成功搜尋 0、認領後 22。4b 的代價沒有重演 |
| 擋阻額度改以**階段**為鍵 | 換工具不再換到新預算;`web_open` 不再收到「第一次」 |
| 狀態合法性檢查(反轉舊決定) | `COMPLETE` 寫入曾被放行並弄停狀態機;現在擋下並列出五個合法值 |
| CLAIM 額度 8 輪 | 事先下注、事先定規則,2/2 走到 REVIEW;**結論寫成「未被否證」** |
| 迴圈收斂 | 研究型 run **4/4** 走到 `REVIEW`,任務包完整(對照 2026-08-06 的 0/5) |
| prior-art 登記表 + CI 檢查 + RATIONALE | 三份清單交叉比對;prime-agent 那次連抓兩個缺失,機制有效 |
| `Task_016_phase_tool_gate` | 閘會響、繞道被堵;但擋阻只能移除錯的路,不能供給對的路 |
| `Task_015_advancer_settled_loop` | 閘 + 推一起才跑通;換事件那一項**以證據反轉** |
| repo↔installed 漂移檢查 | Task_003 的修正推了卻沒安裝,Pi 整天跑舊版而四個檢查全綠。以前只有紀律 |
| Checker 核可批次 | 十個任務九個 DONE、`Task_003` 擋下 —— [2026-08-08-checker-pass.md](../docs/case/2026-08-08-checker-pass.md) |
| `Task_017_guard_mutation_check` | 機制成立且抓到真洞;`block: true` 物件字面值**同型出現四次** |
| `Task_003_cwd_confusion` | 兩個破壞原樣重現都會紅;窮舉 10/10。**驗收要重現破壞,不是驗工具碰得到那一行** |
| 變異檢查進 CI | `--cap 4` 實測 79 秒;進 CI 的前提是先清掉取樣點上的存活者 |
| `Task_013_write_forms_blind_spot` | `sed -i` / `dd of=` 的後門補上;**變異掃描當場否決了作者自己的判斷** |
| 推進器重測 | **4/4 走到 REVIEW、零升級**(對照 0/5 與三次 ESCALATED)。但兩個門檻定在錯單位 |
| 4a 門檻修正 | 退場改以**輪**為單位;`nextStep()` 在 REVIEW 回頭檢查交付物 |
| `Task_018_path_a_human_review` | **協定的 Path A 一直都在,是我們把它關掉了** —— [task-018](../docs/case/task-018-path-a-human-review.md) |

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
- [x] `Task_013_write_forms_blind_spot`(REVIEW):**已補。** 事實修正:`tee -a` 本來就抽得到,
      實際缺口是 `sed -i`(四種寫法)與 `dd of=`,一併納入 `perl -i`。兩份抽取器同步改,
      分段改為引號感知(`sed -i -e 's|a|b|'` 原本被 `|` 切成四段)。
      **變異掃描當場在新分支抓到 3 個存活者**,補測試 + 刪掉一個冗餘條件後 7/7 全殺。
      結論見 [docs/case/task-013-write-forms.md](../docs/case/task-013-write-forms.md)。
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
