# 研究決策紀錄 (Research Rationale)

記錄每次參考研究的來源、評估結果、與導入決策。

> **格式取自 [OmniHeal](https://github.com/Chiakai-Chang/OmniHeal) 的 `reference/RATIONALE.md`。**
> 那份文件用 14 個來源證明了一件事:**「放棄項目」欄比「採用項目」欄更值錢** ——
> 沒有寫下來的否決,會被下一個人原封不動重做一次。本專案 2026-08-06 就付了這個代價
> (見下方 pi-until-done 條目)。
>
> 索引與強制檢查在 [REGISTER.md](REGISTER.md);**這份是逐次研究的正文**。
> 一個來源在 REGISTER 標為「已審視」的前提,是這裡有它的條目。

---

## 2026-08-06 — srinitude/pi-until-done(**重讀,非首次**)

**來源**:https://github.com/srinitude/pi-until-done(`reference/pi-until-done`)
**研究目的**:本專案的佇列推進器連續三次量測都以 ESCALATED 收場,重讀其續跑迴圈的實作,
確認是參數問題還是地基問題。
**完整對照**:[2026-08-06-pi-until-done-loop-reference.md](2026-08-06-pi-until-done-loop-reference.md)

### 核心發現

**四項都是地基,不是參數。** 逐行讀 `extensions/lib/`(非讀我們自己的摘要):

1. 續跑掛 **`agent_settled`**(`hooks/agent.ts:62`),`turn_end` 只用來記最後一段文字。
2. 停滯的判準是**這一輪做了什麼**:`tool_call` 加權計分(edit/write 3、bash 2、
   read/grep/find/ls 1、其他工具 2),`=== 0` 才算空轉(`hooks/tools.ts:65`)。
3. 自動化放棄時**只把自己設成 `paused` / `blocked`**(`hooks/agent-end-helpers.ts:13`),
   **從不去動被執行任務的狀態**。
4. 續跑用 `sendUserMessage(..., { deliverAs: "followUp" })`,**沒有** `triggerTurn`。

### 採用項目(待移植,列為 `Task_015_advancer_settled_loop`)

| # | 移植什麼 | 取代本專案的什麼 |
|---|---|---|
| 1 | 續跑改掛 `agent_settled` | `turn_end` 每輪注入 —— 實測「正常進行中的步驟被判停滯」的直接成因 |
| 2 | 加權 progress signal,`=== 0` 才算停滯 | 數注入次數(數的是「我說了幾次」而非「你做了什麼」) |
| 3 | **自動化放棄 = 暫停自己,不寫 `status.txt`** | 要求模型寫 `ESCALATED` —— 五次 run 三次 ESCALATED,至少兩次是我們自己造的假失敗 |
| 4 | 終端步驟不計時 | 「交還使用者核可」這個設計上不會再變的狀態被判成卡住 |

### 放棄項目

| 項目 | 放棄原因 |
|------|---------|
| 直接安裝 `pi-until-done` | 它鎖 Pi `0.81.1`,本機是 `0.83.0`;lockstep 設計,不可跨版 |
| turn budget 的對話框確認 | 本專案量測以 `--print` 為主,無 UI 可確認 |
| YAML 狀態檔與 widget UI | TUI 專屬,模型收不到(本專案已知:只有兩個通道到得了模型) |
| `mise` 綁定的驗證指令路由 | 本專案不使用 mise |

### 被推翻的舊決定

`docs/superpowers/pi-until-done-learnings/07-optimization-plan.md` 曾把
**「Judge 系統、Ralph loop」列為不實作 —— 擴充層職責**。

2026-08-06 的 Task_001/008 做了 Ralph loop,Task_010/011 做了一個以詞表與結構規則
判斷「回覆是否謊報完成」的 `blocked-claim` —— **那就是一個很弱的 judge**。
**那條排除事實上已被推翻,只是沒有人寫下來。** 現重新列為待決事項。

---

## 2026-08-06 — Chiakai-Chang/OmniHeal

**來源**:https://github.com/Chiakai-Chang/OmniHeal(`research/OmniHeal`)
**研究目的**:它是擁有者自己的專案,且以 14 個 repo 的蒸餾為設計基礎 ——
評估其研究紀錄方法與可轉用的機制。

### 核心發現

**`reference/RATIONALE.md` 886 行,14 個來源,每個都有「採用項目」與「放棄項目 + 原因」。**
本專案缺的正是這個:13 個 research clone 蒸餾成 13 個技能,而 9 個來源在
`docs/` 與 `pi-skills/` 裡出現 0 次,技能檔也不寫來源。

**它解決的是同一個問題,而且早就解決了。**

### 採用項目

**1. RATIONALE 格式本身** → 就是本檔。日期 / 來源 / 研究目的 / 核心發現 / 採用 / 放棄。
**2. 「放棄項目」為必填欄** → 已寫進 `REGISTER.md` 的使用說明與 `CLAUDE.md` 的 Prior Art First。
**3. Task Queue 的恢復點定義**(恢復點 = queue 第一個未完成任務,**不依賴 Agent 記憶力**)
→ 與 C.A.S.E. 的佇列一致,可作為 `Task_015` 的設計佐證:狀態在檔案裡,不在迴圈裡。
**4. 3-Strike Protocol 的分層**(第 1 次換方式、第 2 次再換、第 3 次記錄永久跳過並繼續)
→ 本專案的守衛退場是「擋滿 3 次就讓路」,**沒有「換一種方式」這一層**,值得補。

### 放棄項目

| 項目 | 放棄原因 |
|------|---------|
| 零安裝 / 純 stdlib 的硬約束 | 本專案是 Pi extension harness,本來就依賴 Pi 與 Node |
| `skill_code_lint` / `log_parse` / `text_align` 三個技能 | 領域不同(專案健檢 vs agent 行為約束) |
| SWOT+TOWS 產出 `action_plan.md` | 本專案已有 `docs/mece/rounds/` 等效流程 |
| Phase 0/1/1.5 的掃描階段模型 | 本專案的工作單位是任務包,不是掃描 |

### 附帶價值

OmniHeal 的 14 個來源中,**有 5 個與本專案重疊**(planning-with-files、llm-wiki-plugin、
ECC、evolver、yes.md、karpathy-skills)。它們的「放棄理由」多半來自 OmniHeal 的零安裝約束,
不直接適用於本專案 —— 但**它已經替我們讀過一遍**,再讀時可以從它的核心發現開始,而不是從零。

---

## 待辦:尚未寫入本檔的來源

`REGISTER.md` 目前有 **26 個標為「未審視」**。優先序依「壓在當前卡點上」排:

| 優先 | 來源 | 壓在哪個卡點 |
|---|---|---|
| 1 | auto-pi(`workflow-os-guide` 的來源) | Pins / Gates / Steers 階段門控 —— 直接對應「先規劃再開始」 |
| 2 | loopy | 循環工程閉環控制 —— 與 Task_015 的續跑迴圈同題 |
| 3 | agentic-harness.pi | `detect → parse → review` 生命週期合約 —— 對應守衛的通道選擇 |
| 4 | harness-engineering | grilling 一問一答門控 —— 對應「不先釐清就動手」 |
| 5 | pi-browser-harness | 研究型 session 的實作(本專案最痛的場景) |
