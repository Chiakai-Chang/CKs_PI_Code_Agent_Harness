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

## Phase 1:把流程的持有權拿回來

- [ ] `Task_001_queue_advancer`:佇列推進器 —— turn_end 讀佇列狀態,查 CASE 轉換表得出下一步,
      注入並觸發下一輪。預設關閉。
- [x] `Task_002_advancer_measurement`:在真實專案量遵循率 = 狀態前進次數 / 推進次數。
      **魔鬼代言人已下注:第一次不會是 1.0。先說,再量。**
      → **注贏了:0/3。** 但機制成立(3 次推進 + 1 次升級,分毫不差),0 的原因是模型在
      錯的目錄作業,與推進器無關。見
      [docs/measurements/2026-08-06-queue-advancer-first-run.md](../docs/measurements/2026-08-06-queue-advancer-first-run.md)。

**出口條件**:✅ 有一份真實 session 的遵循率數字。

## Phase 2:依量測結果決定下一步

- [ ] `Task_003_cwd_confusion`:**降級為效率問題。** 乾淨重測顯示模型前 16 步在錯的目錄,
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
- [ ] `Task_008_advancer_verdict`:bash 洞補上後重測遵循率,再決定預設值與門檻。
      **三個 bash 洞都補上了,這是下一步。**

**出口條件**:預設值有實測依據,不是設計時的直覺。

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
