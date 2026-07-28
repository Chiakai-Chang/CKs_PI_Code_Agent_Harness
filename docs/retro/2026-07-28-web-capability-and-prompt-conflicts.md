# 復盤：2026-07-28 網頁能力回到出發點，與跨 bridge 指令衝突

**觸發**：使用者指出「能上網查資料非常重要，但一般搜尋常被阻擋，才引入 camoufox；後來找到 pi-browser-harness 卻只 clone 回來參考，沒有融會貫通，有點可惜」，要求回到出發點重新思考。
**方法**：先量測既有能力的真實成效，再決定要搬什麼。

---

## 一、數據推翻了出發點的前提

掃 56 個 session、127 次 `web_search` + 85 次 `web_open`：

| 工具 | n | 成功率 | 失敗原因 |
| :--- | ---: | ---: | :--- |
| `web_open` | 84 | 94% | backend_down 2、開不了頁 2、**被擋 1** |
| `web_search` | 126 | 82% | backend_down 21、**被擋 1** |
| `web_snapshot` | 7 | 14% | thin_result 6 |

**126 次搜尋只有 1 次被擋。** camoufox 已經解決了「被阻擋」這個原始問題。真正的問題在別處。

## 二、我兩次判讀錯誤，都是同一種

### `spawn sh ENOENT`「沒根治」——錯的

我先報「近期每次 session 仍固定發生 2 次」。正確限定為 `web_*` 工具的結果後：

```
2026-07-16 : 14
2026-07-19 :  9
（之後零）
```

`705edd0`（07-19）就修好了。我把**模型讀到談論這個 bug 的文件**也算成失敗——今天那筆的 `toolName` 是 `read`。

### `web_snapshot`「86% 壞掉」——也錯

7 次全在同一個 session：第一次成功回傳 4,648 字元，接著同一分頁連續 6 次空結果。不是工具壞掉，是**模型對著死分頁重試**。

**同一個錯誤今天犯了三次**（技能用量 37.9%→實際 0%、ENOENT、web_snapshot）：拿子字串在整份 session 比對，沒限定紀錄型別。

## 三、真正搬過來的東西

pi-browser-harness 沒有隱身能力，兩者互補：camofox 匿名讀取被 bot 牆擋住的公開頁；pi-browser-harness 驅動使用者本人的 Chrome。可搬的是 camofox 缺的**紀律**：

### 1. 輸出預算 + 溢位落檔

Pi 對自己的 `read` 是 2000 行 / 50KB，而這些 web 工具上限 80,000 字元——**比 Pi 對自己還寬**。實測分布：`web_open` 中位數 9,319、p90 36,593、max 80,029 字元（約 20K tokens 在單一 tool result）。

當天稍早已實測 42,999 字元的 tool result 會讓這個模型當場失控。全部 5 個回傳點改為截到 Pi 的預算、不切斷行、完整內容寫入暫存檔並在結果裡告知路徑。

### 2. `web_snapshot` 空結果改為錯誤

原本以**成功結果**回傳字串 `(empty snapshot)`：沒有原因、沒有下一步。現在區分「分頁還在」（去互動或重開，並明說不要再 snapshot）與「分頁已死」（重新 `web_open`），因為兩者需要相反的處置。

### 3. `deep-research-guide` 從散文變成實作

原技能寫著「fan out one `web-search-researcher` subagent per sub-question **in parallel**」、「2 輪、8 次派遣」——**harness 裡沒有任何 subagent**。模型被要求假裝自己有。

新 `deep-research-bridge` 註冊真的 `deep_research` 工具，每個子問題 spawn 獨立 `pi --print` 行程。設計由兩個實測決定：

* **序列而非並行**：本機 `-np 1`，實測兩個並行請求分別於 7.3s / 14.3s 完成——完全序列化。並行零收益、牆鐘時間乘以 N。上限從「8 次派遣」壓到 5。
* **價值是 context 隔離，不是速度**。

端對端實測：

```
child 研究耗時       : 408s（自己的 context 讀網頁）
回傳父層的 digest    : 1,408 chars (~352 tokens)
父層 prompt          : 7,692 -> 8,476 tokens
```

對照：父層直接 `web_search` 單次回傳 14,613 字元。**同一個問題，進入主線的內容差約 10 倍。**

遞迴防護：每個子行程帶 `PI_HARNESS_DEEP_RESEARCH_CHILD`，工具偵測到就拒絕。沒有這道防線，一次錯誤拆解就會 fork 到機器掛掉。

## 四、核心結構問題：跨 bridge 指令衝突

第一次端對端測試，即使提示明寫「Call the deep_research tool once」，模型仍直接 `web_search`。**根因不是註冊失敗**（用 `--tools deep_research` 不給退路，證明工具能正常運作），而是：

`stealth-web-bridge` 無條件注入：

> "call web_search for **any task needing current or external information**"

這句涵蓋一切，包括不該歸它管的。今天觀測到兩次：

1. 模型拿著剛從 `skill-catalog.json` 讀到的**本地路徑**跑去 web_search
2. 明確指名 deep_research，仍然 web_search

**11 個 bridge 各自注入很有信心的指令，沒有任何機制在看合起來的效果。**

### 新增 `scripts/check-prompt-conflicts.py`

* **FAIL**：無條件範圍宣稱（`for any task`、`always call`、無例外的 `whenever you need`）——已證實的缺陷形狀
* **WARN**：被多個工具同時宣稱的觸發詞
* **INFO**：每輪注入總量（目前 4,882 字元 / ~1,220 tokens，這個數字先前沒有人有）
* **明確列出它沒涵蓋的部分**：6 個直接改寫 `systemPrompt` 的 bridge

**用真實歷史文字驗證**，不是合成範例：把原句放回去 → 失敗、exit 1 並指名；換成收斂後的版本 → 通過。

它立刻抓到我第一輪漏掉的一處：我只改了 `promptGuidelines`，**沒改 `description`**，而 description 一樣進提示。

已接進 CI。

## 五、收穫

1. **先量測既有能力，再決定要搬什麼。** 使用者的假設（被阻擋）和我的假設（ENOENT 沒修好）都被數據推翻。真正的問題是輸出太大與指令衝突，兩者都不在原本的懷疑名單上。
2. **同一種量測錯誤犯三次，代表那不是失誤而是習慣。** 「子字串比對 session」必須永遠先限定 `role` / `toolName`。
3. **散文技能的傷害不是零，是負的。** `deep-research-guide` 教模型去派遣不存在的子代理；模型只能假裝執行，然後回報做完了。**一個描述不存在機制的技能，比沒有這個技能更糟。**
4. **注入的指令會互相抵消，而沒有人在看整體。** 每個 bridge 的措辭單獨看都合理；合起來，最絕對的那句吃掉其他所有工具。這是多 bridge 架構的結構性風險，不是措辭品味問題。
5. **檢查工具要對著真實的歷史缺陷驗證。** 合成測資只能證明程式會跑；把當初那句話原樣放回去，才證明它抓得到。

## 六、尚未處理

* **readability 正文抽取**未搬（pi-browser-harness 有一套零依賴、依文字/連結密度評分的實作）。目前只砍位元組，沒有語意層的縮減。
* **`deep_research` 的自主觸發率沒有證據**：兩次測試都是我明確指名。收斂 `web_search` 措辭後會不會自然被選中，未驗證。
* **`check-prompt-conflicts.py` 讀不到 `systemPrompt` 直接注入**的那 6 個 bridge——已在輸出中標明，但仍是真實盲區。

---

## 七、readability 正文抽取（補做）

「尚未處理」清單裡的第一項已完成，但**做法跟原本打算搬的不一樣**，而且是量測改的主意。

### 量測先推翻了搬運方式

先抓兩個真實頁面的 AX-tree 快照分析組成：

| 成分 | Wikipedia 文章 | 新聞首頁 |
| :--- | ---: | ---: |
| `/url:` 純管線 | 43.1% | 16.8% |
| link 行 | 20.3% | 34.2% |
| nav/chrome/widget | 8.6% | 11.2% |
| **正文** | **22.9%** | **31.7%** |

外加一個決定架構的事實：Wikipedia 頁面 **57 個 `[eN]` 參照，落在正文行的是 0 個**。

pi-browser-harness 用 CDP 注入頁內腳本、以**文字密度／連結密度評分猜測**哪裡是正文——因為他們面對原始 DOM。我們手上是 AX-tree，**語意角色已經標好**，直接依角色過濾比密度啟發式可靠，而且不需額外往返、不需 `web_evaluate`、不會在敵意頁面炸掉。

**所以搬的是概念，不是實作。**

### 唯一整段照搬的東西：`inBoilerplate`

第一版逐行過濾，結果導覽連結全部存活——回傳的「正文」裡有 `Donate`、`Create account`、`Log in`、`Article`、`Talk`。**丟掉 `navigation` 容器行、卻留下它的子連結**，正是這個檢視要移除的垃圾。

pi-browser-harness 的 readability 有 `inBoilerplate`（祖先是 nav/header/footer/aside 就整片作廢）。這一條值得整段搬，只是改用**縮排**追蹤祖先：容器行命中就跳過其後所有縮排更深的行。

結果：8,253 → 1,936 字元（23%），導覽全清、正文與標題保留。

### 連結標題要留

純正文過濾在**首頁／搜尋結果頁**會把標題全砍掉——那些標題本身就是連結。實測：新聞首頁純正文剩 31.5%，保留連結標題則是 63.5%，**差的那 32% 就是標題**。所以政策是「留連結標題、丟 `/url:` 行」。

最終：文章頁 23%、連結密集首頁 56%（48 個標題連結全保留）。

### 預設值由用量決定，但能力不刪

歷史 223 次 `web_*` 呼叫中，`web_click` / `web_type` / `web_press` / `web_scroll` 合計 **0 次**。所以閱讀檢視設為 `web_search` / `web_open` 的**預設**，`raw: true` 退回完整樹，`web_snapshot` 完全不動——那才是要點擊前該叫的工具。

**沒有刪掉互動能力**：「至今沒用過」不等於「將來不需要」，這跟技能分層時的推論一致。檢視結尾會告訴模型去哪裡拿參照，讓能力是「延後一次呼叫」而不是「消失」。

### fail open

過濾後幾乎沒東西（純 app shell）就原樣回傳。回傳空的「正文」會被讀成「成功讀到一個空白頁」——正是 `web_snapshot` 連續六輪把 `(empty snapshot)` 當成功回傳的同一種失敗。

### 實測（Pi 內，非單元測試）

```
RESULT web_search 4,064 chars | refs: 無 | /url 行: 無 | footer: 有
```

對照今天稍早同類搜尋的 13,589 / 14,613 字元——**降約 70%**。

### 第四次判讀失誤（一分鐘內抓到）

`ls` 安裝目錄看到 `readability.ts` 不見了，一度以為 restore.py 沒複製。實際是我的觀察撞進 restore 的「先刪後複製」空窗。檔案在。

原本那條 `test_restore_ships_the_module` 只 grep `copy_dir_contents` 字串——**真的壞掉時它照樣會過**。已換成走訪每個 bridge 的相對 import，檢查同目錄有無對應 `.ts`。

## 八、剩下的

* **`deep_research` 自主觸發率仍無證據**：三次測試我都明確指名工具。
* **6 個 `systemPrompt` 直寫的 bridge** 仍在 `check-prompt-conflicts.py` 涵蓋外（已在輸出標明）。
* **閱讀檢視只有兩個 fixture**：Wikipedia 與 BBC。其他版型（論壇、文件站、SPA）未驗證。
