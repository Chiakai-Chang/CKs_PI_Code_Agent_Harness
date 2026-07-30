# 設計：harness 可用性實地驗證（2026-07-30）

## 為什麼是現在

這個 harness 的目的是「穩定、有方法、可靠的萬用 agent」。過去兩天為了追一個
「agent 一直卡死」的症狀，做了大量模型與引擎量測。那些量測回答了一個真問題，
而且結論**推翻了原本的假設方向**：在 harness 真實每輪負載 15,287 tokens 上，
逐位元組相同的 fixture 下，Fable-Fusion-711 是 0/16、Qwythos-27B-v1 是 32/32
（Fisher p = 4.4e-13，見 [2026-07-30 復盤](../../retro/2026-07-30-laguna-abandoned-and-strix-halo-survey.md) §8）。

**瓶頸是模型，不是注入的內容量。** 但同時暴露了一個更大的空白：

* harness 的**內容**（每輪 15,287 tokens）——測過
* harness 的**機制**（11 個 bridge、Guard 1–6、compaction、技能觸發、唯讀工具代執行）
  ——**兩天下來一次都沒在真實 Pi session 裡跑過**

使用者自述的三個症狀正好全落在第二項：agent 中途卡死、守衛干擾正常工作、
沒信心開始用。這份設計就是去驗第二項。

## 目的與非目的

**目的**：回答「拿這個 harness 做真實工作，會不會壞、壞在哪」。

**非目的**（寫下來是因為過去兩天正是敗在這裡）：

* 不刻畫模型的失敗曲線
* 不調 prompt 大小、不砍技能、不跑模型階梯
* **不新增任何量測腳本或鷹架**

## 儀器：不新增任何東西

用既有的 `~/.pi/agent/sessions/<專案>/`。Guard 的糾正是透過 `sendMessage` 以注入訊息
送出的，本來就會出現在 session log 裡；技能觸發、工具呼叫、compaction 亦然。

這一條是刻意的約束。**用蓋儀器代替使用，是過去兩天最大的實際損失。**

## 前置（每次重跑都要確認）

1. llama-server 起來且行為正常。判準用**行為**不用 log：`/metrics` 的
   `predicted_tokens_seconds` 應在 18 t/s 量級。若掉到個位數以下代表層被靜默丟回 CPU。
2. `python scripts/setup.py --mode restore` —— Pi 跑的是 `~/.pi/agent/` 的安裝副本，
   改了 `pi-extensions/` 不 restore 等於沒改。
3. `~/.pi/agent/settings.json` 的 `defaultModel` 與 server 的 `--alias` 一致。

## 執行方式與其限制

每個任務以 `pi --print "<指派文字>"` 在目標目錄執行。`--print` 會跑完整的 agentic
loop，多回合工具使用都在同一次呼叫內完成，session 也照常寫入。

**已知限制，本輪不假裝驗過**：互動式 TUI 無法從腳本驅動，所以只有互動式才會走到的
路徑（最典型的是 `/compact` 之後由 `compact-continuation-bridge` 接手續作）
這輪可能碰不到。若某個 session 自然長到觸發壓縮，那是額外收穫，不是設計。

**不得中途介入。** 一旦下場幫 agent，這就不是驗證。session 跑完之前只觀察，
唯一的例外是觸發停止規則時中止。

**session 檔的辨識**：每個任務記錄開始時間，事後取 `~/.pi/agent/sessions/<專案>/`
下最新的那份，並以時間戳核對。（曾經比對錯 session 而得出錯誤結論。）

**T1 的隔離**：T1 會改動本 repo 的工作區。必須先開專用分支，事後審 diff，
不合格就丟棄；不得因為「agent 寫了」就留下。

## 任務集

四個**真實待辦**，對應使用者選定的四類用途。不是合成任務，做完有實際價值。

### T1 — 維護 harness（本 repo）

> `scripts/make-probe-fixture.py` 今天新增了 `--sources rules|neutral` 旗標，
> 但 `tests/test_make_probe_fixture.py` 沒有覆蓋它。請用 TDD 補上測試：
> 先寫會失敗的測試、確認紅燈、再讓它綠。跑 `python -m unittest tests.test_make_probe_fixture` 驗證。

壓力點：多回合、read/edit/write/bash、方法論技能（test-driven-development）該不該自動觸發。

### T2 — 寫程式（本 repo 以外）

目標是一個拋棄式 scratch repo（見「T2 fixture」）。指派：

> `<scratch>/` 是一個小型 Python 專案，`python -m unittest discover -s tests` 目前有測試失敗。
> 找出原因並修好，不要改測試。

壓力點：跨專案目錄圍堵、多檔案導航、systematic-debugging 是否觸發。

### T3 — 資料搜集與研究

> llama.cpp 上游對 Qwen3.5（`qwen35`）的 MTP / draft 支援現況如何？
> 本機實測 draft acceptance 只有 0.45，想知道是引擎實作的缺口還是模型本身的特性。
> 給我結論與具名出處。

壓力點：`web_search` / `web_open` / deep-research，以及冷啟動路徑（stealth 後端沒開時）。

### T4 — 雜事

> 本機模型目錄下有數個 `.bat` 啟動腳本指向已不存在的模型檔。
> 盤點哪些失效、附上證據（哪個路徑、檔案是否存在），不要刪除任何東西。

壓力點：ls/read/grep 為主，唯讀，最安全；驗證基本工具鏈與「不要多做」的約束遵守度。

**預期摩擦，事先寫明**：模型目錄在專案之外，`yes-hooks-bridge` 的目錄圍堵很可能擋下。
那本身就是觀察項目——agent 面對「使用者要求專案外的資源」是優雅說明並請求確認，
還是靜默卡死。**被擋不等於 T4 設計失敗**，卡死才是缺陷。

## T2 fixture

在暫存區建立一個最小 Python 專案：`src/` 兩到三個模組、`tests/` 有一個**真實的**
失敗測試（bug 在原始碼不在測試）、一份 README。不初始化 git remote，不進版控。
難度刻意設定為「需要讀兩個以上檔案才能定位」。

## 觀察表（每個 session 一份，由人讀 log 填寫）

| 欄位 | 判準 |
|---|---|
| 完成度 | 完成／部分／卡死 |
| 工具呼叫數 | 總數；並記錄**有無零呼叫卻宣稱完成**的回合 |
| Guard 觸發 | 哪幾個、各幾次，且逐次判定**正確攔截**或**誤傷** |
| 技能觸發 | 哪些被載入；方法論優先（process → domain）有沒有真的發生 |
| context | 每輪 token、有無 compaction、壓縮後有無自動續作 |
| 成本 | 回合數、牆鐘時間 |
| stall | 是否出現 3 strikes 交還使用者 |
| **副作用** | **`git status` 與工作區異動：這個 session 有沒有改到它不該改的東西** |

最後一欄是 2026-07-30 補的，因為漏掉它差點讓最嚴重的缺陷整個溜走。原本的觀察表
只記錄 agent **說了什麼、呼叫了什麼**，沒有記錄它**改變了什麼**——而 `deep_research`
的子代理是獨立行程、帶 `--no-session`，它們的動作在主 session log 裡完全不存在。
每個 session 結束後必須跑 `git status`，並比對非預期的新增／修改檔案。

**「誤傷」的判定準則**（不先寫死，事後會自圓其說）：

* Guard 5（repeat-call）：模型重複讀同一檔案，但**兩次之間該檔案被改過**，或
  第二次帶了不同 offset —— 那是合理重讀，攔下來算誤傷。
* Guard 6（fabricated-work）：模型宣稱完成，而 session 裡**確實有對應的真實工具呼叫**
  —— 那是真話，糾正它算誤傷。
* 唯讀代執行：模型本來就會正確發出原生呼叫，卻被 bridge 搶先代執行 —— 算誤傷。
* 任何 Guard 導致 agent 放棄一條**原本正確**的路徑 —— 算誤傷。

## 停止規則

單一 session 超過 **25 回合**，或連續 **10 分鐘無進展**（無新工具呼叫、無檔案變更），
判定 stall、停止、記錄。目的是避免再燒掉一小時去看同一個現象。

## 產出與判讀

一張四列的表 + 一份依嚴重度排序的缺陷清單。

**只有實際觀察到的缺陷才驅動修改。** 沒被觸發的 bridge／skill 不當成缺陷，
但會累積成「有證據的降級候選」——能力盤點因此免費長出來，不需要另外做一輪。

判讀方向先寫死：

```
四個都完成、無誤傷           -> harness 可用。缺陷清單即後續 backlog
完成但有誤傷                 -> 修守衛，不是修模型。誤傷是最高優先，它讓使用者不敢用
卡死且形狀與 API 層量到的相同 -> 模型層問題，但已知 Qwythos 在此負載 32/32，需要解釋差異
卡死但形狀是新的             -> harness 機制問題，這正是這輪要找的東西
```

## 風險

* **T3 會碰網路與 camofox 後端**，冷啟動路徑歷史上壞過（`KNOWN_ISSUES` §4、§5）。
  若後端未安裝，第一次會下載約 300MB。這本身就是驗證項目之一，不是干擾。
* **T2 會寫檔**，但只在暫存區的拋棄式 repo 內，且不進版控。
* 四個 session 累計可能一到兩小時。停止規則就是為了防止失控。
