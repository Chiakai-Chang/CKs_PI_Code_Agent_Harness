# 復盤：2026-07-27 Pi 卡死根因（JSON 假工具呼叫）與 system prompt 減重

**日期**：2026-07-27
**觸發**：使用者回報「pi 一直出問題、無法正常執行」，並貼出完整 `update.bat` + `pi` 啟動紀錄。畫面上模型輸出了一段 ` ```json ` 工具呼叫清單後就停住，什麼也沒發生。
**方法**：systematic-debugging——先用真實樣本重現失效（不是讀 code 推測），確認防護網為何沒攔到，再逐層往外查其他同源問題。所有數字都來自寫稿當下的實際執行。

---

## 一、根因：假工具呼叫的 JSON 形態完全不在偵測範圍內

模型當時輸出的是：

````
```json
  [
    {"tool": "Read", "arguments": {"path": "..."}},
    {"tool": "Bash", "arguments": {"command": "ls -la"}}
  ]
```
````

`pi-extensions/yes-hooks-bridge/index.ts` 有兩道防線，兩道都沒接住：

| 防線 | 涵蓋範圍 | 對這段文字 |
| :--- | :--- | :--- |
| `FAKE_TOOL_CALL_PATTERN` | XML 標籤（`<invoke>`、`<read>`、`<tool_code>`…）與 ` ```bash ` 圍欄 | **不匹配**——沒有 ` ```json ` |
| `parseUniversalToolTag` | XML 包裝，或首鍵剛好是 `"name"` 的**單一物件** | **不匹配**——是**陣列**，且鍵是 `"tool"` 不是 `"name"` |

實測重現（修復前）：

```
$ node -e "...FAKE_TOOL_CALL_PATTERN / tagPatterns against the real sample..."
FAKE_TOOL_CALL_PATTERN matches: false
parseUniversalToolTag matches: false
```

兩者皆 false，`loopGuard` 直接 `return`。結果是**最糟的一種失敗**：不算 strike、不通知、不自癒、不交還控制權——回合結束、畫面靜止、使用者只能看著 agent 發呆。

### 連帶發現的第二個根因：工具名稱是錯的

橋接把 `<read>` 對應到 `read_file`、把 `<ls>` 對應到 `bash` 跑 `dir "..."`。但實際查證安裝中的引擎（`dist/core/tools/*.js`），Pi 的內建工具只有七個：

```
bash  edit  find  grep  ls  read  write
```

`read_file` 根本不存在。也就是說**即使**轉譯器成功攔截，它送出的自動糾正訊息也是在叫模型呼叫一個不存在的工具——一次失誤因此升級成穩定的失敗迴圈。

---

## 二、修了什麼

1. **JSON 工具呼叫偵測**（`extractJsonToolCalls`）：支援圍欄／裸露、物件／陣列、`tool`/`name`/`function`/`tool_name` 鍵、`arguments`/`args`/`input`/`parameters` 鍵。裸露 JSON 用**括號平衡掃描**而非非貪婪正則——後者會停在巢狀 `arguments` 的第一個 `}`，切出無效 JSON。
2. **誤判閘門**：必須**同時**有工具名鍵與參數鍵才算工具呼叫。順手修掉一個既有誤判——舊的 ` ```json ` 樣式只看首鍵是不是 `"name"`，會把模型正常展示給使用者看的 skill frontmatter 片段劫持成工具呼叫。
3. **工具名正規化**（`canonicalizeToolName` / `canonicalizeArgs`）：`Read`/`read_file`/`view`/`cat` → `read`，`dir`/`list_dir` → `ls`，`file_path`/`target_file` → `path` 等。非內建工具標記 `unknownTool`，自動糾正訊息會附上合法工具清單。
4. **轉譯器自己的 strike 上限**：舊版每次轉譯都把 `consecutiveFakeToolStrikes` 歸零，而轉譯又帶 `triggerTurn: true`——模型只要持續吐出「解析得動但仍然是假的」呼叫就會無限自動重試。新增獨立的 `consecutiveTransformStrikes`，滿 3 次改用 `deliverAs: "followUp"` 交還人類。
5. **回音截斷**：`MAX_RAW_ECHO = 400`。JSON 路徑的 `raw` 是整段文字，原樣塞回提示會再灌一次 context。
6. **兩個殭屍旗標接上線**：README 教使用者設 `enableUniversalTagTransformer` / `enableSelfHealingLoopGuard` 來解決標籤死鎖，但**全 repo 沒有任何程式讀這兩個鍵**——照文件做完全不會有任何改變。現已實際讀取（預設開啟，缺設定即維持原行為）。

---

## 三、第二層問題：啟動 system prompt 的一半是技能索引

查證引擎的 `formatSkillsForPrompt`：**每一個**已註冊技能，每一輪都會把 name + description + **絕對路徑**包成 XML 寫進 system prompt。

修復前實測（腳本複刻引擎的同一個格式化函式）：

```
skills discovered: 358
<available_skills> block: 141,750 chars  ~= 35,437 tokens
  of which <location> absolute paths: 39,932 chars (~9,983 tokens)
external/* submodule skills: 335 -> 132,916 chars (94% of block)

cost by source:
  ecc                      276 skills   109,064 chars (~27,266 tok)
  (global) ~/.pi            20 skills     7,594 chars
  taste-skill               13 skills     7,188 chars
  superpowers               14 skills     4,966 chars
  ...
```

ECC 一個子模組就佔了技能區塊的 77%。內容包括 `visa-doc-translate`、`uspto-database`、`carrier-relationship-management`、`prediction-market-risk-review` 等與本 harness 用途無關的領域包。

**關鍵發現**：ECC 上游本來就有 `manifests/install-modules.json` 把技能分成 19 個 module，`restore.py` 卻直接 `os.listdir` 全量註冊，等於把上游的分類設計整個丟掉。

**做法**：`ecc_skill_paths()` 改為依 module 過濾，由 `harness-config.json` 的 `eccSkillModules` 控制；預設 `workflow-quality` + `agentic-patterns` + `security` + `optimization-workflows`，另加 `ecc-guide` / `ecc-recipes` / `configure-ecc` / `ecc-tools-cost-audit` 永遠註冊（否則 ECC 橋接會變成無法被發現的功能）。設 `"all"` 可回到全量。

修復後實測：

```
$ python scripts/restore.py --auto
[RESTORE]   - ECC skills: 65 registered (modules: workflow-quality, agentic-patterns, security, optimization-workflows)

skills discovered: 147
<available_skills> block: 56,810 chars  ~= 14,202 tokens
```

技能區塊 **35,437 → 14,202 tokens**（減少 21,235，約 60%）。

**失敗模式選擇**：manifest 讀不到時**故意 fail open**（註冊全部並印警告），不 fail closed。上游改版導致所有 ECC 技能靜默消失，比提示變胖嚴重得多。這條有測試釘住。

---

## 四、第三層：`update.bat` 每次都噴的 commit-graph 錯誤

```
error: failed to rename temporary commit-graph file
error: failed to write commit-graph
error: task 'commit-graph' failed
```

查證 `.git/modules/external/ecc/objects/info/commit-graphs/`：

- `commit-graph-chain` 只列了一個 graph，但目錄裡躺著**兩個** `.graph`（前一次寫入中斷的孤兒）。
- 所有檔案權限是 `-r--r--r--`（唯讀）。

Windows 上要 rename 覆蓋唯讀檔就會失敗，加上鏈結與磁碟內容不一致，於是每次 fetch 都重演一次。

`fetch.writeCommitGraph false` 其實**已經**設在主 repo——但沒用，因為**每個 submodule 有自己的 `.git/modules/<name>/config`，不繼承主專案設定**。18 個 submodule 一個都沒設到。

**做法**：`scripts/setup.py` 新增 `disable_commit_graph()`，走訪主 repo + 全部 submodule 的 git dir（實測 19 個），清掉毀損快取（先清唯讀位元，否則刪除會跟 rename 一樣失敗）並同時停用 `fetch.writeCommitGraph` 與 `maintenance.commit-graph.enabled`。commit-graph 是純查詢快取，刪掉不會遺失任何歷史。

實測：

```
$ git fetch --recurse-submodules 2>&1 | grep -ci "commit-graph"
0
```

---

## 五、順手修掉的紅色測試

`4ea1c26` 把 `DEPRECATED_PACKAGES` 改名為 `DEPRECATED_PACKAGE_SUBSTRINGS`，但沒改測試，留下 2 個 `AttributeError`。已改為驗證新的子字串語意，並補一條 `superpowers` 套件被剪除的回歸測試。

---

## 六、驗證證據（寫稿當下實際執行）

```
$ python -m unittest discover -s tests
Ran 203 tests in 3.996s
OK

$ python scripts/verify-bridges.py
Bridge verification complete: 9 bridges checked, 0 failure(s) found.

$ python scripts/validate-config.py
Config validation complete: 0 failure(s) found.

$ pi --print "Say exactly: OK"
[ecc-bridge] ECC Submodule Version: 2.0.0
OK
```

新增 `tests/test_universal_tool_parser.py`：不是字串契約測試，而是用 Node 24 原生 type-stripping **真的 import 並執行** `parseUniversalToolTag`，餵入這次卡死的原始文字樣本。測試數 176（含 2 紅）→ 203 全綠。

---

## 六之二、自我複審抓到的四個自造缺陷

修完之後回頭審自己的 diff，抓到四個問題，都已修正並補測試：

1. **括號平衡掃描是 O(n²)。** 遇到沒有配對的 `{`，內層掃描會從下一個字元重新開始。一段 40,000 個 `{` 的訊息就是 16 億次運算——而這段程式跑在**每一次** `turn_end`。一個防死鎖的機制自己變成死鎖來源，是最諷刺的失敗。加了 `JSON_SCAN_BUDGET = 200_000` 上限，實測 40k 病態輸入 **0.09s**。
2. **`disable_commit_graph()` 只在 `run_update()` 呼叫。** 全新安裝走的是 `git submodule update --init`，第一次 `git pull` 照樣會噴。已在 init 之後補上（必須在 init **之後**，submodule 的 git dir 那時才存在）。
3. **新程式沒有測試。** 這個 repo 的規矩是所有東西都有測試，我卻加了 `git_dirs()` / `disable_commit_graph()` 兩個新函式就想直接送出。補了 `TestCommitGraphCleanup`：用唯讀 0444 檔案的假 git 樹，驗證巢狀 submodule 也會走到、兩個 config 鍵都寫到每一個 git dir、以及冪等性。
4. **`ECC_ALWAYS_SKILLS` 沒有存在性檢查。** 上游改名會讓這份清單靜默失效、ECC 橋接變成無法被發現的功能，而且不會有任何錯誤訊息。補了對照 `external/ecc/skills/` 的測試。

順帶一提：測試本身也踩到 `[WinError 206] 檔名或副檔名太長`——40k 字元的樣本透過 argv 傳給 node 超過 Windows 命令列上限，改走檔案傳遞。

---

## 七、收穫

1. **防護網的盲區比防護網本身危險。** 這個 loop guard 三道防線寫得很完整，但因為漏了一種形態，觸發時的行為是「完全靜默」——比沒有防護網更難察覺，因為沒有人會去懷疑一個「已經做了」的功能。往後寫 guard，未匹配路徑至少要留一條可觀測訊號。
2. **自動糾正訊息裡的名字必須查證，不能憑印象。** `read_file` 看起來合理、寫起來順手，但引擎裡叫 `read`。一個錯字讓自癒機制變成迴圈製造機。
3. **文件寫了、程式沒讀，比沒寫更糟。** 兩個 config 旗標白紙黑字寫在 README 的「修復指南」裡，使用者照做、什麼都沒發生，只會得出「這個 harness 修不好」的結論。這正是 repo 自己禁止的 zombie config，只是這次是以旗標而非檔案的形式出現。
4. **整合外部倉庫時，先看它自己有沒有分類。** ECC 的 module manifest 一直都在，`restore.py` 卻用 `os.listdir` 全吃——多付了 21k tokens／輪。接子模組時該問的第一個問題是「上游打算怎麼被局部安裝」。
5. **submodule 不繼承主 repo 的 git config。** 一條「已經設好了」的設定，在 17 個子模組上其實一次都沒生效。跨 submodule 的設定要逐一寫入 `.git/modules/*/config`。
6. **量測要複刻真實格式，不要抓概數。** 一開始只算 name+description 得到 19k tokens；照引擎的 `formatSkillsForPrompt` 加上 XML 包裝與絕對路徑後是 35k——光是 `<location>` 絕對路徑就 ~10k tokens。差了將近一倍。
7. **修 bug 的程式碼跟原本的程式碼一樣會有 bug。** 這次自我複審抓到的四個缺陷（§六之二）全部是這一輪新寫出來的，其中 O(n²) 那個嚴重度不亞於原始 bug。「修完就送」和「修完再審一次」之間差了四個缺陷。

---

## 八、尚未處理（建議後續）

- **`(global) ~/.pi` 20 個技能、7,594 chars** 未納入管理範圍，屬使用者自行安裝，本次未動。
- **`.git/modules/external/agi-super-team/`** 是已不在 `.gitmodules` 中的殘留 submodule 目錄，值得確認是否該清除。
- **技能區塊仍有 14,202 tokens**，若本地模型仍吃緊，下一個可談的目標是 `taste-skill`（13 個）與 unclassified 的取捨。
