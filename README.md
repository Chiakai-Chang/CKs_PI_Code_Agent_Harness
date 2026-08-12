# CK's Pi Code Agent Harness

給 [Pi Coding Agent](https://github.com/badlogic/pi-mono) 用的一層外框:擴充(bridge)、技能、
設定與驗證腳本。它不改 Pi 本身,只在 Pi 的事件上掛行為約束。MIT 授權,無二進位檔。

## 快速開始 (Quick Start)

```bash
git clone --recursive https://github.com/Chiakai-Chang/CKs_PI_Code_Agent_Harness.git
cd CKs_PI_Code_Agent_Harness
install.bat          # Windows
bash install.sh      # macOS / Linux
```

更新用 `update.bat` / `bash update.sh`。解除安裝、模式選擇與非互動用法見下方〈安裝與更新〉。

> **這份 README 的寫法:** 每一個數字都標明**什麼時候、在什麼配置上量的**,並且分成
> 「量過的」與「沒量過的」兩區。沒量過的事寫在〈尚未證明的部分〉,不寫在功能清單裡 ——
> 這是本專案的第一條紀律([Evidence-Based Completion](CLAUDE.md)),README 也不例外。

---

## 它想解決的問題

擁有者的原話,也是整個專案的驗收標準:

> 「每次專注做一件事,做完復盤,有發現就增加 task queue」
> 「他多搜幾次是好的阿?越多越好不是?**我抱怨的是他沒有先規劃就開始**」

拆成三個可判定的問題:

| | 問題 | 這個 harness 的做法 |
|---|---|---|
| **L1** | agent 在錯的地方工作(跑出專案、改到不相干的檔案) | bash 圍堵、子代理寫入邊界、目錄外移偵測 |
| **L2** | 沒規劃就開工、沒產出就宣稱完成 | C.A.S.E. 階段閘(認領→規劃→產出→驗收)、驗收物守衛 |
| **L3** | 跑到第 20 步已經忘記原本要什麼 | 任務目標中途重述(`before_agent_start` 只在每則使用者訊息觸發一次,不夠) |

---

## 量過的部分

**測量配置**(能力屬於 model–harness 配對,不屬於模型 —— Harness-Bench, arXiv 2605.27922):
本機 llama.cpp + `GRM-3.2-Sky-ONYX-balanced.gguf`,`n_ctx 262144`、`n_slots 1`,Windows 11。
**換模型或換 harness commit,以下數字都要重測。**

### C.A.S.E. 任務迴圈能不能把一件事做完

在一個路徑不含 harness 名稱的真實專案(`PiTaskLab`)上,用**事先算好的標準答案**評分,
提示不告訴模型 cwd、也不告訴它任務名稱:

| 批次 | 結果 |
|---|---|
| run 1–2 | DoD **11/11**、11/11 |
| run 3 | **1/11** —— 走到 REVIEW 但資料夾是空的。定位出兩個缺陷(見下),修好 |
| run 4–8 | **11/11 × 5**,23–33 次工具呼叫,2–4 分鐘 |
| run 9(較難的任務) | **9/9**,11 輪一輪不差 |

run 3 暴露的兩個缺陷,兩個都已修並附行為測試:
* **驗收物守衛從來沒有生效過** —— 呼叫用到一個不在該 scope 的變數,每次都拋 `ReferenceError`,
  被旁邊那個「recipe 讀不到就放行」的 `catch` 吞掉。**11 個單元測試全綠,守衛全程沒運作**
* **被拒絕的寫入會把內容丟掉,而沒有人講** —— 模型帶著完成的報告被閘擋下,認領後不再重寫。
  閘的措辭現在明講「剛才那次寫入的內容沒有被保存」

修好之後,**驗收物守衛在 run 7、run 8 各真的擋下一次空的 REVIEW**(session log 為憑),
模型隨即自己去 `read` 該檔、拿到 ENOENT、重寫交付物。

### 一次真實使用(不是實驗室)

2026-08-13,`019ff6c1`,一個十項要求的社會事件調查,38 次工具呼叫 / 28 輪 / 1 則使用者訊息:

* **先規劃再搜尋** —— 第 9 步寫 `task_plan.md`,第 10 步才第一次 `web_search`
* **任務目標中途重述送達 2 次**(第 12、第 24 次工具結果後)
* **引用閘擋下 2 次**,模型接著 `web_open` 開了 7 個實際頁面
* 產出 7 個階段檔 + 一份綜合報告,10 項要求全部有對應段落
* **碰到 harness 目錄 1 次**(載入技能),其餘全在使用者自己的專案裡

同一個 session 也暴露兩個**新的**缺陷,已記入 [PROGRESS.md](PROGRESS.md):
* **路徑中途漂移** —— 第 32 步起模型少寫了 `02_Task_Queue/` 這一層,
  後半段的交付物落在專案根目錄的另一個同名資料夾。**沒有任何守衛看得見**(兩邊都在專案內)
* **時間戳是捏造的** —— 產出的 `progress.md` 寫「2026-08-07 14:00–18:00」,
  實際檔案時間是 2026-08-13 00:18–00:40

### 這個模型的噪音底線(2026-08-12,n=5)

同一個提示、同一臂、同一配置跑五次:工具呼叫 47 / 62 / **116** / 44 / 49。

```
tool_calls         sd 26.91   →  想偵測 10 次呼叫的差,需要 n=29
assistant_turns    sd 13.96
blocked            sd  5.19
advance_injections sd  0.49   →  這一類指標 n=2 就夠
```

**結論不是「數字很吵」,是「用呼叫數比較就是在讀雜訊」。** 判斷要用二元的 DoD ——
同樣這五次,`status` 5/5 都是 REVIEW、交付物清單 5/5 完全相同。
過程指標吵,結果指標穩。完整判準與原始資料:[docs/measurements/2026-08-12-noise-floor.md](docs/measurements/2026-08-12-noise-floor.md)

### 其它有量測的數字(附量測日期)

| 項目 | 數字 | 日期 |
|---|---|---|
| 單元測試 | `Ran 1413 tests ... OK`(零依賴,stdlib unittest) | 2026-08-13 |
| Bridge 安裝一致性 | `13 bridges checked, 0 failure(s)` | 2026-08-13 |
| ECC 技能注入量 | 全量 277 技能 ≈ 27,560 tokens → 依 module 精選 65 個,技能區塊 35,437 → 14,202 tokens | 2026-07 |
| 隱身檢索閱讀檢視 | 文章頁 8,253 → 1,936 字元;搜尋結果頁 12,886 → 3,581 字元且保留 8 條可引用位址 | 2026-07 |
| `deep_research` 對照 | 同一問題:子代理 44 分鐘 / 零可用產出;`web_search`+`web_open` 8 分鐘 / 有具名出處 | 2026-07-31 |
| 真實 session 規劃順序 | 31 個 session:search-first **0**、no-plan 93.5%(此為**修正技能名稱之前**的基線) | 2026-08-12 |

---

## 尚未證明的部分

寫在這裡,是因為把它們寫進功能清單就是這個 repo 反覆踩到的坑。

* **L3(長 run 不漂移)沒有量測。** 目前的任務 23–38 次呼叫就結束,長度不足以觀察漂移。
  C.A.S.E. §16 的 Handoff Capsule **尚未實作**
* **只在一台機器、一個本機模型上測過。** 沒有跨模型比較,也沒有雲端模型的數字
* **`enableCaseAdvancer` 預設為 `false`** —— 自動推進佇列的效果沒有足夠樣本
* **`deep_research` 預設關閉**(`enableDeepResearch: false`),理由見上表。程式碼與測試都留著
* **任何「效果」宣稱都受上面那個噪音底線限制。** 呼叫數差 10 次以內的比較,在 n<29 時無意義
* **守衛只在真實跑過的情境下算驗證過。** 綠色測試只證明程式做了你叫它做的事;
  一個從沒在真實 run 裡響過的守衛,狀態是「未驗證」,不是「正常」

---

## 安裝與更新

* **安裝** —— Windows:`install.bat`;macOS / Linux:`bash install.sh`
* **更新**(保留你的設定與自訂技能) —— Windows:`update.bat`;macOS / Linux:`bash update.sh`
  * 等同 `python scripts/setup.py --mode update`:`git pull --recurse-submodules` →
    `restore --auto`(**自動同步全部 13 個 Extension** 至 `~/.pi/agent/extensions/`)→ `pi update --all`
  * **非互動情境**(腳本、背景工作)請直接用 `python scripts/restore.py --auto --profile standard < /dev/null`。
    `setup.py --mode restore` 會停下來問設定檔編號,在背景會**永遠等下去**
* **解除安裝** —— `python scripts/uninstall.py`(只移除 harness 管的項目);
  `--purge` 則逐項確認、可一併清掉備份與 Pi 本體

### 安裝模式

| 模式 | 內容 |
|---|---|
| `minimal` | Core 核心(含 `hello-reflect`)、Caveman、ECC |
| `standard`(預設) | 全部 18 個外部子模組與全部本地擴充 |

### 改完東西一定要做的事

**Pi 跑的是安裝好的副本,不是你的 repo 檔案。** 動過 `pi-extensions/` 或 `pi-skills/` 之後,
先 `python scripts/setup.py --mode restore`,否則你測的是上一版。
`python scripts/verify-bridges.py` 會直接比對 repo 與 `~/.pi` 的內容並指出差異。

---

## 健康檢查與驗證腳本

| 指令 | 檢查什麼 |
|---|---|
| `python -m unittest discover -s tests` | 全部單元測試(零依賴) |
| `python scripts/verify-bridges.py` | 入口路徑、manifest 與 package.json 一致性,**以及安裝副本是否還等於 repo** |
| `python scripts/validate-config.py` | 設定檔格式、反模式、機器特定路徑與明文金鑰 |
| `python scripts/check-prompt-conflicts.py` | 把 13 個 bridge 的注入**合起來**看:無條件宣稱、共用觸發詞、每輪注入總量 |
| `python scripts/check-prior-art.py` | README、manifest 與磁碟上的克隆有沒有互相漂移 |
| `python scripts/check-guard-mutations.py` | 機械式竄改守衛,要求測試抓得到(CI 跑抽樣;**必須單獨跑**,它會就地改原始碼) |
| `python scripts/mine-session.py --latest` | 讀一個真實 session:呼叫序列、注入送達、哪個守衛開口、批次形狀 |

慢速、需要真跑本機模型、**不進 CI** 的:`measure-advancer.py`、`measure-drift.py`、
`measure-triggers.py`、`probe-tool-calls.mjs`、`calibrate-context.py`。

---

## 機制:實際會在執行期作用的東西

### C.A.S.E. 任務迴圈(`case-bridge`)

任務以資料夾為單位(`recipe.md` / `role.md` / `planning.md` / `output.md` / `status.txt`),
狀態機由階段閘強制:

* **認領閘** —— 佇列裡還有 `PENDING` 沒人認領時,擋下產出寫入,並明講被擋的內容沒有保存
* **規劃閘** —— 沒有含 `## Self-Review` 的 `planning.md`,不准寫 `output.md`
* **驗收物守衛** —— `recipe.md` 的 Local DoD 點名的檔案不存在時,不准把狀態寫成 `REVIEW`
* **人類核可(Path A)** —— 到 `REVIEW` 時由對話中的人核可;
  bridge 讀**真實使用者輸入**為憑,模型的轉述不算

### 目標與方法論注入(`task-shape-bridge`)

* **請求形狀路由** —— 多步請求會提示先載入 `pi-planning-with-files` 或 `brainstorming`,
  而不是直接開搜
* **目標中途重述** —— `before_agent_start` **每則使用者訊息只觸發一次**(實測:1 則訊息 / 16 輪),
  所以目標會在跑到一定次數後重述一次,內容取自當前任務的 Local DoD

### 安全與圍堵(`yes-hooks-bridge`)

* 執行前硬擋毀滅性指令(`rm -rf /`、`git push --force` 等)
* **bash 圍堵**:寫入型指令的目標路徑必須留在專案內;
  也偵測 `cd 出去 && 用相對路徑寫入` 這種會跟著 cd 走的形狀
* 假工具呼叫(XML / ```json 陣列)轉義與迴圈斷路器

### 網頁檢索(`stealth-web-bridge`)

`web_search` / `web_open`,底層是 `camofox-stealth`(Camoufox 反偵測瀏覽器)。回傳採**閱讀檢視**:
依 AX-tree 語意角色剝除導覽子樹,但**保留搜尋結果的網址並解開轉址** ——
當初全部剝除的版本造成 632 次搜尋回傳 0 個網址,模型只能憑印象重建位址。
需要點擊/輸入時用 `raw: true` 或 `web_snapshot` 取回完整樹。

### 背景執行(`async-exec-bridge`)

`bg_start` / `bg_status` / `bg_cancel`:長工作以 detached 子行程送出後立刻回傳,
agent 可以結束這一輪,完成時被喚醒續跑。狀態落檔在 `.pi/async-exec/`,Pi 被砍掉也能對帳。

> **安全須知**:`bg_start` 執行的是**任意 shell 指令、detached、不另外確認**,
> 而且**中止 agent 不會中止它派出的背景工作**。要停用 `bg_cancel`(殺整棵進程樹)。
> 目前沒有白名單與確認提示,要接不受信任的提示來源請先自行加上。
> 逐工作逾時預設 30 分鐘,值被夾在 10 秒至 24 小時之間。

### 其它 bridge

`compact-continuation-bridge`(壓縮後接續未完成的工作)、`skill-namespace-guard`(同名技能即時隔離
成 `harness-<name>`,不動你自己裝的版本)、`skill-catalog-bridge`、`ecc-hooks-bridge`、
`mece-autopilot-bridge`、`taste-bridge`、`deep-research-bridge`(預設關閉)、
`planning-with-files-bridge`。

---

## 內容清單

| 類別 | 數量 | 位置 |
|---|---|---|
| Extension bridges | **13** | `pi-extensions/` |
| 蒸餾核心技能 | **16** | `pi-skills/core/` |
| 技能目錄(僅名稱,依需要載入) | **120** | `pi-config/skill-catalog.json` |
| 外部子模組 | **18** | `.gitmodules` / `external-manifest.json` |
| 單元測試 | **1413** | `tests/` |

### 蒸餾核心技能與其來源

「蒸餾」指提煉其模式與核心演算法後,以零外部依賴重寫;**不是**把整個專案搬進來。

| 技能 | 來源 | 解決什麼 |
| :--- | :--- | :--- |
| `deep-research-guide` | [pi-browser-harness](https://github.com/amankumarsingh77/pi-browser-harness) | 多子問題拆解與具名引用報告 |
| `browser-automation-guide` | 同上 | AX-Tree 語意定位與頁面變更驗證 |
| `ide-intelligence-guide` | [oh-my-pi](https://github.com/audreyt/oh-my-pi) | 模型專屬編輯格式、LSP 前檢 |
| `harness-factory-guide` | [metaharness](https://github.com/ruvnet/metaharness) | Repo Fit 打分、演化、MCP 靜態預檢 |
| `grilling-protocol` | [harness-engineering](https://github.com/vinicius91carvalho/harness-engineering) | 一問一答需求釐清門控 |
| `contrarian-review` | [the-last-harness](https://github.com/diegopetrucci/the-last-harness) | 反方論證 |
| `adversary-review` | [ultimate-pi](https://github.com/aryaniyaps/ultimate-pi) | 對立面壓力測試 |
| `autonomous-experiment-guide` | [pi-autoresearch-harness](https://github.com/monotykamary/pi-autoresearch-harness) | 統計顯著性與自動化實驗 |
| `tool-repair-guide` | [pi-tool-repair-layer](https://github.com/calionauta/pi-tool-repair-layer) | 工具參數欄位修復與降級 |
| `guardian-pipeline-guide` | [agentic-harness.pi](https://github.com/Jitsusama/agentic-harness.pi) | `detect`→`parse`→`review` 管線合約 |
| `subagent-orchestration-guide` | [pi-superagents](https://github.com/teelicht/pi-superagents) | 模型分層與上下文隔離 |
| `minimal-prompt-guide` | [Huiyu-Pi](https://github.com/huiyu9144/Huiyu-Pi) | 極簡 prompt 注意力配置 |
| `workflow-os-guide` | [auto-pi](https://github.com/romiluz13/auto-pi) | 階段門控與 `HANDOFF.md` |
| `hello-reflect` | [claude-reflect](https://github.com/BayramAnnakov/claude-reflect) | 規則自演進 |
| `planning-with-files` | [planning-with-files](https://github.com/OthmanAdi/planning-with-files) | 檔案化任務規劃 |
| `research-task-routing` | 本地 | 依請求形狀選方法論 |

外部子模組完整清單與整合方式(submodule / bridge / 僅參考)見
[`external-manifest.json`](external-manifest.json) 與 [`docs/prior-art/REGISTER.md`](docs/prior-art/REGISTER.md)。

---

## 與 Pi 本體共存的三個保證

1. **零覆蓋** —— `restore.py` / `uninstall.py` 只碰 `managed_skills` 清單裡的項目,
   不刪你自己裝在全域的技能與擴充
2. **同名隔離** —— 內容相同就跳過;內容不同才隔離成 `harness-<name>` 並存
3. **不重複註冊** —— 13 個 bridge 由 Pi **依目錄自動探索**,
   `settings.json` 的 `extensions` 陣列不會、也不該多出一筆(重複註冊會造成工具同名衝突而無法啟動)

---

## 給要動這個 repo 的人

* **先讀 [PROGRESS.md](PROGRESS.md)** —— 現在在做什麼、什麼做完了、什麼做了但沒證明
* **[CLAUDE.md](CLAUDE.md)** 是工程紀律的正本,包含所有踩過的坑與它們留下的規則
* **先查既有再動手** —— [docs/prior-art/REGISTER.md](docs/prior-art/REGISTER.md)。
  跳過這一步曾經花掉一整天:重造的東西,我們自己的筆記早就寫過
* **三層,一個改動只屬於一層** —— 協定(C.A.S.E.,不得依賴任何特定模型)/
  執行(bridge,依賴 Pi 的事件模型)/ 校準(門檻、預算,依賴特定模型)。
  校準值放在 `pi-config/harness-config.json` 的 `_calibration` 區

---

**由 [CK (Chiakai Chang)](https://github.com/Chiakai-Chang) 維護。實驗性專案。**
致謝所有被整合倉庫的作者與貢獻者。
