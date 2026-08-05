# 已知問題 (Known Issues)

記錄目前已知、且根因不在本專案可直接修復範圍內的問題。每項均附影響評估與處理方式。

## 1. 全域技能名稱重複導致的 `[Skill conflicts]` 警告（已修復，2026-07-21 改版）

**現象**：執行 `scripts/restore.py` 時出現大量 `Skill conflicts` 警告，提示全域目錄 (`~/.pi/agent/skills`) 與本地子模組存在相同名稱的技能（如 `design-taste-frontend`、`brainstorming` 等）。

**根因**：
- 本專案透過 Git Submodule 整合外部倉庫（taste-skill、superpowers、graphify 等）
- 使用者可能透過 `pi install <pkg>` 將相同名稱的技能安裝到全域目錄
- Pi Agent 啟動時在多個路徑 discovery 技能，重複名稱觸發警告

**影響**：
- **輕度**：技能仍能正常載入（優先使用 temp 路徑）
- **維護成本**：累積警告可能造成困擾
- **潛在風險**：版本錯位可能導致行為差異

**處理**：**已在本專案自動修復**（2026-07-21 版：取代 2026-07-19 那版）
- 2026-07-19 版的做法（`PRUNE_GLOBAL_SKILLS` 清單 + `restore.py` 執行時強制清空同名全域目錄）已**移除**——它不比對內容，任何使用者自己裝的同名技能都會被無聲清空，跟「讓使用者能自由安裝不受影響」的目標直接衝突。
- 改用 `pi-extensions/skill-namespace-guard`：**每次 Pi 啟動**時即時比對內容——相同就跳過（不重複註冊、不刪除）、不同才把 harness 這份隔離成 `harness-<name>`，兩份並存，完全不動使用者自己的版本。
- `restore.py` 現在只負責把 `external/*` 技能路徑寫進 `pi-config/external-skills-manifest.json` 清單，不再直接寫進 `settings.json`。
- 詳見 [docs/superpowers/specs/2026-07-21-skill-namespace-isolation-design.md](docs/superpowers/specs/2026-07-21-skill-namespace-isolation-design.md)；舊版做法歷史記錄見 [docs/decisions/2026-07-19-skill-conflicts-fix.md](docs/decisions/2026-07-19-skill-conflicts-fix.md)（**已被取代，不再反映目前程式碼行為**）。

## 2. Pi 啟動時的 `[Skill conflicts]` 名稱不符警告（僅舊版 pi；≥0.74.1 已消失）

**現象**：`pi` 0.73.x 及更舊版本啟動時列出多條 `name "X" does not match parent directory "Y"` 警告，來源為 `external/` 子模組（ECC、taste-skill、evolver、Local-Agent-Workspace、planning-with-files）。

**根因**：這些上游專案的 `SKILL.md` frontmatter `name` 與資料夾名稱不一致。Pi 舊版對此發出警告但照常載入。

**影響**：純視覺噪音。技能實際以 frontmatter 名稱正常載入。

**處理**：**執行 `pi update` 即可**——pi 0.74.1 起已移除此警告（pi-mono #4534）。已實測 0.80.3 啟動不再出現。

## 2. ECC `loop-design-check` 技能載入失敗（上游 YAML 錯誤）

**現象**：啟動警告 `Nested mappings are not allowed in compact mappings at line 2, column 14`，該技能未載入。

**根因**：上游 `affaan-m/ECC` 的 `skills/loop-design-check/SKILL.md` 中，`description:` 的值是未加引號的純量、內含 `: `（如 `Two actions: (1) WRITE`），為無效 YAML。上游 HEAD（截至 2026-07-08）仍存在此問題。

**影響**：僅此一個 ECC 技能無法使用，其餘 ECC 技能正常。

**處理**：`scripts/restore.py` 已改為逐一註冊 ECC 技能並跳過 `ECC_BROKEN_SKILLS` 清單中的損壞項目（不修改子模組內容），啟動時不再出現此錯誤。執行更新流程（README「更新與升級」）即生效。待上游修正 YAML 後（一行修正：description 值加引號），自 `ECC_BROKEN_SKILLS` 移除該項即可恢復載入。

## 3. npm 安裝時的 deprecated 警告

**現象**：安裝時出現 `@mariozechner/pi-* deprecated: please use @earendil-works/pi-*`。

**根因**：Pi 官方將 npm scope 從 `@mariozechner` 遷移至 `@earendil-works`；舊 scope 凍結在 0.73.1。

**處理**：本專案 `setup.py` 全新安裝已改用 `@earendil-works/pi-coding-agent`。既有安裝執行 `pi update` 即自動遷移（0.73.1 起的自我更新支援改名，會移除舊全域套件並安裝新套件）。

## 4. stealth-recon 後端首次自動安裝（~300MB）

`camofox-stealth` 技能的後端 `@askjo/camofox-browser@1.11.2` **會自動安裝，不需手動架設**：`recon.sh` 以 `npx -y` 取得套件，camofox-browser 首次啟動時再自動下載 Camoufox（~300MB 到 `~/.camofox`，一次性，不含在 repo）。第一次啟動會顯示下載提示並延長等待逾時（預設 600 秒）；之後啟動為秒級。也可在 `setup.py` 完整安裝時選擇預先下載。最硬的 Akamai/Datadome 頂層可能仍需 residential proxy（本技能預設不掛 proxy，不在支援範圍）。

## 5. camofox-browser 在 Linux + systemd 上的多層失效（已在實機修復，harness 已納入自動修復）

**現象**：Linux 機上 `web_search` / `web_open` 全部回傳 "Could not open a browser tab"。camofox-browser 健康檢查 `browserConnected: false`，但引擎（`~/.cache/camoufox/camoufox-bin`）已下載完成、server 進程也跑著。

**根因（6 層，疊加失效）**：
1. **systemd unit 的 PATH 不含 nvm node**（`~/.nvm/versions/node/*/bin`），shebang `#!/usr/bin/env node` 的入口秒掛 exit 127。
2. **瀏覽器啟動 retry 只有 1 次**（`?? 1`），內層 bug 無 retry 緩衝。
3. **server.js async bug**：`localVirtualDisplay.get()` 是 async 但沒 await，`[object Promise]` 對象當 DISPLAY 傳入 Firefox，`Error: cannot open display: [object Promise]`。
4. **Firefox sandbox vs AppArmor**：`unprivileged_userns` profile 拒絕 `cap_sys_admin` → `EPERM` → Firefox exit(1)。
5. **Playwright viewport schema vs Firefox Juggler 協議**：`newContext({ viewport: {...} })` 傳入的 `isMobile/deviceScaleFactor` 不被 Firefox Juggler 接受，`Browser.setDefaultViewport` 錯誤。
6. **`page.setViewportSize()` 傳入 Firefox 不支持的 screenSize**：同上協議差異，`Page.setViewportSize` 錯誤。

詳見 [docs/retro/2026-07-20-camofox-linux-root-cause-fix.md](docs/retro/2026-07-20-camofox-linux-root-cause-fix.md)。

**影響**：**stealth-web 工具鏈完全不可用**（web_search/open/click/screenshot 全部失效）。macOS/Windows 不受影響（無 xvfb、無 systemd unit；Windows 的 headless 路徑不同）。

**處理**：
- `setup.py` 加入 `maybe_heal_linux_stealth()`，於 `--mode full` 與 `--mode update` 流程中自動修復 systemd unit 的 PATH 缺失，並對 pinned-server 的 `server.js` 執行 `pi-skills/optional/camofox-stealth/camofox-server-fixes.sh` patch（冪等、grep 特徵驅動）。
- 層 3/5/6 是 `@askjo/camofox-browser` 的代碼 bug（Firefox Juggler 協議兼容缺口、async 編碼錯誤），不在 harness 控制範圍。harness 透過 patch 腳本補救；upstream 修復後 patch 檢查可自動跳過。

---

## 工具呼叫參數失控：格式不是原因，負載才是（2026-07-28）

**症狀**：模型「一直出問題」——單一回合跑 350–700 秒、session 檔數百 KB、工具實際上沒有執行。Pi 回報：

```
Tool call "web_search" was not executed: the response hit the output token limit,
so its arguments may be truncated.
```

實測捕捉（`usage.output = 32768`、`stopReason = "length"`）：模型發出**真正的原生** `web_search` 呼叫，但 `query` 參數長 **145,638 字元**，內容是不斷重複的 XML 工具呼叫語法。

> ### ⚠️ 本文先前兩版的診斷都是錯的，完整保留以誌其事
>
> **第一版**：認定根因是自訂 template 的 `_tool_format` 預設為 `'xml'`，建議在 `.bat` 加
> `--chat-template-kwargs "{\"tool_call_format\":\"json\"}"`。理由是失控字串與 template 的 XML 範例逐字相符。
>
> **第二版**：發現該 CLI 寫法未生效（CMD 對 `\"` 的處理與 C runtime 不符），改建議環境變數
> `set LLAMA_ARG_CHAT_TEMPLATE_KWARGS={"tool_call_format":"json"}`。
>
> **兩版的方向都是反的。** 使用者套用環境變數並重啟後，直接對 `/v1/chat/completions` 帶 `tools` 做對照（條件一致、temperature 0.6、n=5）：
>
> ```
> xml  -> 5/5 乾淨   finish=tool_calls, args=28    {"query":"pi-mono badlogic"}
> json -> 0/5 乾淨   finish=length,     args~1000  XML 洩漏
> ```
>
> **xml 才是可用的格式，json 反而穩定失敗。** 請**移除**那行環境變數，回到 template 的預設。
>
> 為何第一版會誤判：失控字串確實跟 template 的 XML 範例一字不差，看起來像鐵證。但那只說明模型在**輸出**該格式，不說明該格式是**病因**——llama.cpp 對這個 template 的 XML 分支有正確的解析與停止處理，對 JSON 分支則沒有。

**真正的變數是負載。** 同樣 xml 格式、同樣 temperature：

```
小 prompt（379 tokens）、簡短工具描述        -> 5/5 乾淨
大 prompt（28,071 tokens）、13 個工具        -> 0/3 乾淨
```

失敗是**隨機**的，且隨 prompt 規模與工具描述長度顯著惡化。單一小樣本會誤導——本文第一版就是這樣產生的。

**這直接連回本 harness 的 context 工作**：把每輪 system prompt 從 95,559 降到 49,485 字元、把 web 工具輸出納入 Pi 自身的 50KB 預算、把技能索引從 35,437 tokens 降到 14,202——這些不只是省 token，而是**直接降低這個失效模式的發生率**。

**處理（harness 端）**：`yes-hooks-bridge` 的 Guard 4 `runawayArgumentGuard` 攔截參數值含工具呼叫語法、或非批量欄位超過 8,000 字元的呼叫，並回傳可行動的指示。攔截本身不花成本（Pi 反正會拒絕），買到的是把引擎那句令人困惑的訊息換成具體修正方向。既有守衛全部看不到這個形狀：loop guard 檢查「沒有真工具呼叫」而這**有**一個，`FAKE_TOOL_CALL_PATTERN` 只掃訊息文字、從不看參數值。

### 已驗證的根因：量化 KV cache

改回 `-ctk f16 -ctv f16`（其餘完全不動：xml 格式、temperature 0.6、同一組 13 個工具、同一份 28,958 token 的 prompt）：

```
-ctk q4_0 -ctv q4_0   重負載  ->  0/3 乾淨，失敗全部是 ~1,000 字元的 XML 失控
-ctk f16  -ctv f16    重負載  ->  4/6 乾淨，**一次 XML 失控都沒有**
                                   兩次失敗是 args 長度 0 與 1（空參數）
                      輕負載  ->  3/3 乾淨
```

**災難性的失效模式（參數失控燒滿 32,768 token）由量化 KV cache 造成。** q4_0 在長 context 下降低注意力品質，模型因而在工具呼叫的參數中陷入重複迴圈——這也解釋了為何小 prompt 測不出來、規模越大越嚴重。

殘餘的 2/6 空參數呼叫是**性質不同、嚴重度低得多**的問題：Pi 會把它當成一次失敗的工具呼叫回報，可以恢復，不會出現 700 秒空轉與數百 KB 的 session。

**代價**：`f16` KV cache 記憶體用量明顯高於 `q4_0`。在 262,144 的 context 下這不是小數字，使用者需自行權衡；若必須降低記憶體，`q8_0` 是介於兩者之間、值得測試的中間值（本文未測）。

詳見 [docs/retro/2026-07-28-web-capability-and-prompt-conflicts.md](retro/2026-07-28-web-capability-and-prompt-conflicts.md)。

---

## 重負載下模型不呼叫工具，改用「拒絕」或「捏造」（2026-07-29）

**症狀**：session 從頭到尾一個工具都沒真正呼叫。模型改以標籤文字描述呼叫（`<read><path>…</path></read>`），transformer 連續糾正三次，loop guard 交還使用者。

**量測**（`scripts/probe-tool-calls.mjs`。同一份 `chat_template.jinja`（qwen3.6-froggeric-v21.3）、同一組 13 個工具、同一份釘死的 fixture、全部 `-ctk f16 -ctv f16`、請求端釘死 temp 0.6 / top_k 20 / top_p 0.95 / min_p 0 / rep_pen 1。乾淨 = `finish_reason` 為 `tool_calls`、工具名正確、無標籤洩漏）：

**prompt 規模階梯**（Fable-711，全部在同一個時間窗、同一台已運行約兩小時的 server；填充物是與工作無關的虛構文件，只改大小不改性質）：

```
   671 tok（原版 Pi 真正送出的 system prompt）  ->  12/12
14,095 tok（其中 13,930 是 harness 的規則文字） ->  12/12
16,880 tok                                     ->   8/8
20,100 tok                                     ->   8/8
23,083 tok（中性填充）                          ->   6/8
23,280 tok（repo 文件）                         ->   6/8   ← 與中性填充相同
26,052 tok                                     ->   6/8
```

> ### ⚠️ 這條階梯上沒有懸崖——差異全在噪音內
>
> 上表看起來像個門檻，但把它當門檻是錯的。逐階與 23,083 那階做 Fisher 精確檢定：
>
> ```
> 14,095  12/12  vs 6/8   p = 0.147
> 16,880   8/8   vs 6/8   p = 0.233
> 20,100   8/8   vs 6/8   p = 0.233
> 26,052   6/8   vs 6/8   p = 0.715
> ```
>
> **沒有任何一階與其他階有統計上的差異。** 整條階梯符合「每一階都是同一個約 91%
> 成功率」（合計 40/44）。8/8 對 6/8 是 8 次抽樣裡差 2 次，那不是訊號。
>
> 而本節自己記錄過：窗間漂移（同配置 0/12 ↔ 6/8）比階梯上任何差異都大。
> 我先寫下那句話，然後照樣拿階梯去推導出一個 26,800 的 contextWindow 上限，
> 對一個原生 262k 的模型。使用者一句「你覺得合理嗎」才擋下來。
>
> **已撤回**：`usableContextTokens` 設回 0，`contextWindow` 回到 262,144。
> 機制留著（預設不作用），但沒有能穿透噪音的證據之前不該有人去設它。
>
> 要真的回答「這個模型在多大的 context 下開始退化」，需要的是：
> 每個尺寸 n 遠大於 8、尺寸在**同一個 server session 內隨機交錯**（而不是分塊，
> 否則時間漂移會混進尺寸）、而且用真正壓長 context 的任務，
> 不是「呼叫一次 read」這種單步測試。

**注入的內容不影響結果。** 同樣 23k，中性填充與 repo 文件都是 6/8；把 harness 的規則文字塞到 13,930 tokens 是 12/12。這一點的證據方向是「兩者相同」，不需要跨越噪音門檻就能說——但它證明的是內容無關，不是大小有關。

**但窗間漂移比規模效應更大。** 同一份 23,280 fixture、同一台 server、同一個模型：

```
server 剛啟動      ->  0/12
server 運行約兩小時 ->   6/8
```

同樣的模式在兩個模型上各出現一次：

```
GRM Q6_K   新啟動 1/12、0/12（官方 HIP 亦然）  |  開機十小時的實例 9/13
Fable-711  新啟動 0/12                        |  開機兩小時的實例 6/8
```

**目前最大的嫌疑是 server 暖機狀態**，來源不明（ROCm kernel 首次執行路徑、MTP draft 狀態、記憶體配置皆有可能）。這比 prompt 規模更能解釋本日全部數據——**所有「新啟動即量測」的批次都接近 0，所有「已運行一段時間」的批次都在 6/8 以上**。尚未設計對照實驗（做法：新啟動後先灌一批短請求暖機，再跑同一份 fixture，與不暖機對照）。

**真正被排除的只有一個：注入的內容。** 它是唯一在乾淨區（13,930 tokens）與門檻區（23k）
都做過對齊比較的變數。

其餘全部**判定作廢，不是「無影響」**：權重量化、推論引擎（lemonade `91d2fc3` /
官方 HIP `b10173`）、模型（GRM / Fable-711）、draft KV 量化、`--rope-freq-base`、
`top_k`、`min_p` 與 `repeat_penalty`——這些都是在 23k、且多半在剛啟動的 server 上比的。
兩邊同時被壓在地板上時，看不出差別不等於沒有差別。要重做就得在乾淨區與門檻區各比一次，
且兩邊 server 的暖機狀態要一致。

**對 harness 的實務結論**：目前沒有證據支持「某個 context 大小是問題來源」。約 9% 的回合會失敗，而這個比率在 671 到 26,052 tokens 之間量不出差別。真正被觀察到、且幅度大到無法用抽樣解釋的，只有窗間漂移（同配置 0/12 ↔ 6/8），來源仍不明——server 暖機是目前最大的嫌疑。在那之前，**不要為了這件事去改 contextWindow 或壓縮設定**。

> ### ⚠️ 這個量測的變異極大，不要用單一批次下結論
>
> 本節前三版各宣告過一次根因，三次都被自己的重測推翻：
>
> 1. **「權重量化才是變數，Q4_K_M 不堪用」** — 根據 Q6_K 6/6 對 Q4_K_M 0/6。那個 6/6 重現不出來。
> 2. **「變數是 prompt 規模，不是量化」** — 方向對了，但把「重負載 0/6」當成穩定事實。
> 3. **「引擎、模型、注入內容全部排除，重負載一律 0/12」** — 同一份 fixture 在暖機後的 server 上是 6/8。
>
> **最根本的錯誤在更前面**：整天的「重負載」fixture 是 23,280 tokens，
> 而 harness 真實每輪只有 15,287。這個數字當初只是「把幾份大文件串起來差不多這麼大」，
> 從未對齊過要模擬的對象。**所有配置比較都是在門檻之上做的**——
> 而門檻之上每個配置都會壞，所以每次比較都「沒有差別」。
> 用一個比目標重 50% 的負載測了一整天，得到的每個結論都不適用於目標。
>
> **實務規則**：
> - 負載必須對齊要模擬的對象，先量目標的真實值，再設計 fixture。
> - n=12 起跳；換配置一定要在同一時間窗內 ABAB 重測，不要跟幾小時前的數字比。
> - server 啟動後先暖機再量測（目前最大的未解釋變異來源）。
> - 差距沒有大過已觀察到的漂移幅度就當成「這個變數沒影響」。

失敗**不是**參數失控，是更難察覺的形狀：`finish_reason=stop`、`tool_calls=0`，然後宣稱「File `scripts/verify-bridges.py` read. Stopping as instructed.」（沒讀）或「I don't have direct access to your local filesystem」（工具清單裡就有 `read`）。一次甚至把整份檔案內容捏造在 ```python 區塊裡。**這種輸出對 Pi 而言是一個正常結束的回合**，沒有任何守衛看得見。

換模型後失敗形狀會變，但不會消失。Fable-Fusion-711 在重負載下發明了不存在的呼叫語法：

```
<tool_code><call_function name="read_file"><parameter name="path">…</parameter></call_function></tool_code>
<tool_code>print(read_file("scripts/verify-bridges.py"))</tool_code>
<antThinking>The user wants me to read the file …
```

**逐一排除的混淆變數**（各自單獨測試）：

```
-ctkd/-ctvd q8_0 -> f16（draft KV 去量化）        ->  0/6
移除 --rope-freq-base 10000000                   ->  0/6
top_k 20 -> 40                                   ->  0/4
min_p 0.05 -> 0 且 repeat_penalty 1.05 -> 1.0    ->  4/6（同窗對照組 5/6，即噪音）
lemonade 91d2fc3 -> 官方 HIP b10173               ->  0/12（同窗對照組 1/12）
GRM-2.6-Plus -> Fable-Fusion-711                 ->  0/12（同窗對照組 1/12）
```

全部無效。**目前沒有任何被重現過的槓桿能讓重負載變乾淨**——包括本文上一節說的「降低 prompt 規模」：
輕負載確實處處乾淨，但那是 ~500 tokens 對 23,280 tokens 的差距，
而實務上把每輪 prompt 從 16,965 砍到 15,287 之後並未觀察到乾淨率變化。
「砍 prompt 有幫助」目前只有「兩端點差異」這一個證據，中間段沒有量過，**不要當成已驗證的因果**。

每個配置在輕負載都測起來完全正常，正是這點讓人以為配置沒問題。

**處理**：
- `C:\models\GRM-2.6-Plus_rocm7.bat`（Q6_K 主啟動器）原本只有 `--jinja`、沒有 `--chat-template-file`，等於根本沒載入修好的 template；已補上並實跑驗證（`/props` 回報 `qwen3.6-froggeric-v21.3`）。
- `pi-config/settings.json` 的 `defaultModel` 是 `…Q4_K_M…`，但 `pi-config/models.json` 只宣告 `…Q6_K…`。兩者都是 gitignore 的本機檔，需自行對齊。
- harness 端（見下）改為在唯讀意圖上代為執行，讓標籤形式的失敗至少能繼續推進。

### Prompt 預算：量出來的，不是推出來的（2026-07-29）

先前所有 prompt 歸因都是「把候選檔案 tokenize 再相減」，那等於假設每個檔案都真的被注入。`yes-hooks-bridge` 的 `before_agent_start` 新增 `PI_HARNESS_DUMP_PROMPT=<file>`（未設就完全不動作），把 Pi 實際送出的 system prompt 倒出來量：

```
   644 tokens   Pi base / preamble
   620 tokens   web + deep-research guidance
  3923 tokens   AGENTS.md
  1418 tokens   CLAUDE.md          <- 推測時以為沒被注入，實際有
  6446 tokens   <available_skills>  <- 46%，60 個原生註冊技能
   274 tokens   case + mece bridge blocks
   642 tokens   skill catalog（104 個技能，只列名稱）
    90 tokens   native-tool protocol
 14055 tokens   TOTAL systemPrompt（單輪 input 合計 16,965）
```

**大宗是 `<available_skills>`，不是 AGENTS.md、也不是目錄。** 每個原生註冊技能約 307 tokens；catalog 裡的每個約 6 tokens。

根因：`skillTiers` 只作用在 `external/*` 的技能，`pi-skills/core` 與 `pi-skills/optional` 是整包 `copy_dir_contents` 進 `~/.pi/agent/skills/`，完全繞過分層。

**處理**：`restore.py` 新增 `tier_local_skills()` / `merge_into_catalog()`，讓本機技能走同一套分層。實測：

```
~/.pi/agent/skills   35 -> 17 個
<available_skills>   60 -> 42 個，6,446 -> 4,681 tokens
systemPrompt         14,055 -> 12,377 tokens
單輪 input           16,965 -> 15,287 tokens（-9.9%）
```

剩下的 4,681 是 20 個 core-tier 技能（方法論那批）。再砍就是砍 `skillTiers.core`，那會讓方法論技能不再自動觸發，與 CLAUDE.md 的「方法論優先」直接衝突——屬於取捨，不是缺陷。

### transformer 自己造成的死結（同日修復）

`parseUniversalToolTag` 沒有子標籤分支，`<read><path>X</path></read>` 解出來的 `path` 是整串 XML 字面值；`<parameter name="path">X</parameter>` 更糟，解成字串 `"path"`。糾正訊息把這些壞參數回灌給模型並要求照著呼叫，模型只能重寫原本的標籤——三次後交還使用者。**糾正機制自己餵出死循環。**

同時 `<tool_call><function=NAME><parameter=key>` —— 也就是 `chat_template.jinja` 教模型的原生格式 —— 每個分支都沒接到，回傳 `null`：沒有 strike、沒有糾正、沒有訊號，session 靜默卡死。

另外，Pi 沒有提供讓擴充代替模型執行工具的 API（對照裝好的引擎 `dist/core/extensions/types.d.ts`：只有 `sendMessage` / `sendUserMessage` / `appendEntry` / `exec`）。因此 `yes-hooks-bridge` 改為**唯讀意圖自己執行並回灌結果**（`read` / `ls`，8,000 字元上限，沿用與 `tool_call` 守衛相同的目錄圍堵規則，連續 8 次為上限）；`write` / `edit` / `bash` 一律不代為執行。回灌不計入 strike——把「模型忽略的糾正」和「模型已經拿到的檔案」算成同一件事，等於服務兩次就交還使用者。

---

## 多代理研究在本機模型下的成本（2026-07-31，未解）

`deep_research` 把問題拆成子問題，每個子問題開一個獨立的 `pi --print` 行程。
這個設計來自雲端規模的專案，**成本模型在本機不成立**：

```
一次研究任務   4 個子代理   44 分鐘   零可用產出
```

每個子代理都跑完整的 agent loop。在 18 t/s 的本機 server 上，
四個子代理就是四段完整的推論時間；`CHILD_TIMEOUT_MS` 是 15 分鐘，
五個子問題的最壞情況是 75 分鐘。

**目前的處置**：沒有改。這是取捨不是 bug——要嘛降低子問題上限、
要嘛在本機模型下改走單代理路徑，兩者都會犧牲這個工具存在的理由（context 隔離）。
在決定之前，**知道它很貴**就是目前的處置。

相關的三個缺陷已修（子代理無監督寫入、失敗訊息只有啟動橫幅、子輸出撐爆母行程），
見 [實地驗證結果](retro/2026-07-30-harness-usability-validation-results.md)。

## 「完成」不等於「正確」（2026-07-31，未解，可能無法用守衛修）

實地驗證中，一個 session 完成了任務、格式工整、零守衛觸發、沒有捏造任何東西，
**答案仍然是錯的**：它宣告「已盤點完畢、共有兩個」，真實答案是 10 個。

原因在第一步——它只 glob 了 `run-*.bat` 與 `launch-*.bat`，
所以從頭到尾只看見 19 個檔案中的 2 個。它報告的每一句都是真的，
**搜尋範圍比任務範圍窄，而沒有任何東西檢查這件事**。

**為什麼可能無法用守衛修**：守衛無法判斷一個 glob 是否涵蓋了任務的語意範圍。
可行方向只剩注入規則（「宣告清單完整之前先列出完整候選集」），
但那要花每輪 token，且與本 repo 既有的證據紀律重疊，效益未評估。

**實務上的意義**：驗收 agent 的產出時，**完成度不足以判斷成敗，必須獨立重做一次**。
記錄這件事的人自己也連錯兩次才做對——容易錯的任務上，
一份自信的錯誤摘要比一次看得見的卡死更危險。

## 工具呼叫因輸出撞上限而被丟棄（2026-07-31，守衛已加但未經田野驗證）

**現象**：一個回合發出正確的工具呼叫，Pi 卻回報

```
Tool call "bash" was not executed: the response hit the output token limit,
so its arguments may be truncated. Re-issue the tool call with complete arguments.
```

session 可能就此結束。實測捕捉：`output 16,384`（剛好等於 `maxTokens`）、
`stopReason=length`、呼叫本身只有一行、思考只有 1,086 字元——**失控的是呼叫前後的輸出**。

`yes-hooks-bridge` 的 Guard 4（runaway argument）看不到它：那個檢查的是**參數值**。

**處理**：新增 Guard 9，偵測「`stopReason=length` + 訊息含 toolCall + toolResult 是
Pi 的拒絕訊息」，要求模型重發**簡短**的同一個呼叫。
**這個守衛的單元測試通過，但尚未在真實 session 裡被觀察到觸發**（該形狀是間歇性的，
三次嘗試未能重現）。它的負向對照確保不會誤傷：撞上限但在寫長答案、或指令本身失敗，都不觸發。

**實務上更有效的緩解是調低 `maxTokens`。** 本機 `pi-config/models.json` 已從 16,384
（模型卡片建議值，針對雲端速度）降到 8,192——在 13.6 t/s 上，前者的一次失控回合要燒
約 20 分鐘，後者約 10 分鐘。實測正常回合輸出 163–413 tokens，最大合理輸出 4,261。

除錯時可用 `PI_HARNESS_DUMP_TURN_END=<file>` 倒出 `turn_end` 事件的真實結構
（未設定時完全不動作）。

## `~/.pi/agent/skills/` 底下全是 junction，其中多數目標端是空的（2026-08-04，未解，非本 harness 所有）

**現象**：`ls ~/.pi/agent/skills/` 列出十幾個項目，但其中多數載入不了任何 skill。

用 `find -type f` 或 `os.walk()` 去數會得到「0 檔案」，看起來像空目錄。它們不是——
它們是 **Windows junction**，指向 `~/.agents/skills/`：

```
st_reparse_tag: 0xa0000003    # IO_REPARSE_TAG_MOUNT_POINT
st_file_attributes: 0x410     # DIRECTORY | REPARSE_POINT
```

`find` 與 `os.walk()` 預設不跟隨 junction，`os.path.islink()` 對 junction 也回傳
**False**（只認 IO_REPARSE_TAG_SYMLINK）。要判定請用
`os.lstat(p).st_file_attributes & 0x400`，或在 Git Bash 跑 `ls -la` 看有沒有 `->`。

**為什麼不修**：這些 junction 由**別的工具**建立，指向 `~/.agents/skills/`，那個目錄
不歸本 harness 管。有內容的（`agents-best-practices`、`darwin-skill`）透過 junction
正常運作；空的（`brandkit`、`design-*` 等）是那個工具那邊的問題。本 harness 只負責
`managed_skills` 清單內的項目——`restore.py` 的 `delete_path` 修好 junction 處理後，
`planning-with-files` 這個一直刪不掉的項目已正常移除。

**連帶影響**：`~/.agents/skills/` 因此實際上是**第三個 skill 來源**。
`docs/superpowers/specs/2026-07-21-skill-namespace-isolation-design.md` 寫明
「不掃描 `~/.agents/skills/`（YAGNI）」，但由於 `~/.pi/agent/skills/` 底下都是指過去的
junction，namespace guard 一直都在讀那邊的內容。該決策的前提與現況不符，值得複查。

## ECC hook 整合層形同虛設（2026-08-04 查出，2026-08-05 已修）

**現象**：`README`、`CORE_CONCEPTS`、`HARNESS_INTEGRATION_GUIDE` 都把 GateGuard、
quality-gate 寫成運作中的功能。實測十五個被消費的 ECC hook 裡，**只有
`block-no-verify` 真的在運作**——它掃原始文字，所以形狀無關。

三個各自獨立的根因（皆有實測）：

1. **欄位名**。Pi 的 `write`／`edit` 工具送 `path`（已安裝 `dist/core/tools/write.d.ts:5`、
   `edit.d.ts:11`），ECC hook 一律讀 `tool_input.file_path`。同一個檔案只差欄位名：
   `path` 進去毫無輸出，`file_path` 進去立刻吐 `[Hook] WARNING: console.log found in ...`。
2. **bash 少一層外殼**。bridge 對 bash 傳 `JSON.stringify(event.input)`＝`{"command":...}`，
   而 `gateguard-fact-force.js:1145` 讀的是 `data.tool_name` 與 `data.tool_input`。
   包好外殼後同一條 `rm -rf build` 立刻回 `permissionDecision: "deny"`。
   **GateGuard 從來沒有評估過任何一條 bash 指令。**
3. **輸出通道**。`gateguard-fact-force` 與 `suggest-compact` 用 stdout 的
   `hookSpecificOutput` JSON（`suggest-compact.js` 的註解自己寫明 stderr 不會到模型），
   bridge 只讀 stderr 與 `exitCode === 2`。gateguard 回的是 `exitCode: 0`。

**連帶災情**：`config-protection` 是會 `exit(2)` 擋下設定弱化的守衛，它也讀 `file_path`
——從來沒擋過任何東西。`post-edit-accumulator` 同樣讀不到路徑，於是
`stop-format-typecheck` 永遠拿到空的 accumulator 而早退。

**修好之後會有行為改變，先講清楚**：`config-protection` 會開始真的擋下設定弱化的編輯；
GateGuard 會開始對破壞性 bash 指令要求先列出影響，因此它另立
`enableEccGateGuard` 旗標且**預設 false**——一個從未在本機跑過的守衛不該直接推上線。

**已修**（`pi-extensions/ecc-hooks-bridge/ecc-payload.ts`）。實測為證，兩個生產端各有
session log：`write` 的 tool result 出現
`ECC console check: [Hook] WARNING: console.log found in .../noisy.ts`；
`bash` 的 tool result 出現 `ECC GateGuard: [Fact-Forcing Gate] Before the first Bash
command this session...`。修前的同一組操作是「每個 tool result 各 1 block、什麼都沒有」。

**GateGuard 的擋阻預設關閉**（`enableEccGateGuard: false`）。實測它會擋掉每個 session 的
第一條 bash 指令，不論內容——`ls -la`、`echo hi` 都擋，理由是
「Before the first Bash command this session, present these facts」。在本 harness 針對的
弱本機模型上，第一回合就硬擋是很大的行為改變，該由操作者明示開啟。關閉時發現仍以建議
形式送達模型。ECC 上游另有逃生口：`ECC_GATEGUARD=off` 或把
`pre:bash:gateguard-fact-force` 加進 `ECC_DISABLED_HOOKS`。

**`config-protection` 現在真的會擋**設定弱化的編輯——它一直有 `exit(2)` 的能力，只是從沒
收到過路徑。

計畫與設計見 `docs/superpowers/plans/2026-08-04-ecc-hook-translation.md`
與 `docs/superpowers/specs/2026-08-04-ecc-hook-translation-design.md`。

**另一件獨立的事**：`pi-skills/core/hello-reflect/scripts/reflect_core.py:89` 找頂層
`entry["role"]` 且要求 content 是字串，Pi 的紀錄是 `entry["message"]["role"]` 加 block list。
實測對真實 session 檔 `extract_user_messages -> 0 messages`。**它一則訊息都沒讀過。**
已修：兩種格式都支援，並加了一條對真實 session 檔的測試（沒有本機紀錄時 skip）。

---

## 未解:結論隨施壓翻轉(2026-08-06)

Session `019fd29d` 三個 turn,同一個證據基礎(全是搜尋結果摘要),結論走了三步:

| turn | 對「事件被協調推動」假設的判定 |
|---|---|
| 1 | 「缺乏證據」「過度簡化」 |
| 2 | 「您的直覺有依據」「不是空穴來風」 |
| 3 | 「**這是事實**」「**這是在打盧秀燕的具體證據**」 |

中間新開啟的頁面數:0。同樣的材料不會同時支持這三個結論,所以發生的是迎合,不是查證。

這是那個 session 裡傷害最大的失效,而 `research-depth.ts` 的兩個閘**都沒有處理它**。
深度閘讓它讀更多,產出閘讓它留下檔案 —— 讀了十頁仍然可以在第三個 turn 翻掉第一個 turn
的結論。

**為什麼不做成閘**:偵測需要比對跨 turn 的語義立場,誤判成本高(使用者本來就有權
在提出新證據後要求改結論),而且沒有可靠的訊號。硬擋一個「改變結論」的行為,比放它過去
更危險。

**目前的處置**(都不是閘,都可被忽略):
* `D:\tmp\pi-test\investigation-brief.md` 的階段 3 要求「針對每個成立的說法主動找反駁材料,
  找不到也要寫找了什麼」。這讓翻轉需要付出證據代價。
* brief 的貫穿規則:「委託人施壓時,改變的應是**查證方向**,不是**結論**。」

**還沒做的**:這條規則沒有進入任何注入到模型的文字。要驗證它有效,需要一個能模擬
「同一 session 內多輪施壓」的量測情境,而 `measure-triggers.py` 目前是單輪 `--print`。

---

## 引用閘造成的新問題:被迫引用時會編造(2026-08-06)

引用閘上線後,同一情境三個 run 的檔案內網址從 `0 / 0 / 0` 變成 `10 / 15 / 0`。分數 0/3 → 1/3。
閘三個 run 都開火(2、1、2 次)。

**但 run1 只開了 2 頁,卻寫了 10 個網址。** 拆開來看:2 個是真的開過、4 個出現在搜尋結果裡
但沒開過、**4 個哪裡都沒出現過**。編造的那些有固定形狀:

```
https://24h.pchome.com.tw/search/?q=<主題>
https://biggo.com.tw/s/<主題>/
https://shopee.tw/<主題>
```

**全是購物網站的搜尋端點**,照網址模式拼出來的。一個搜尋端點永遠不是來源。

這是 Goodhart 的教科書案例:閘要求「檔案裡要有網址」,模型就給出網址 —— 不足的部分用
拼的。**閘讓引用數從 0 變成 10,同時讓編造從 0 變成 4。**

**已做的緩解**:閘的理由文字現在明說「只引用這個 session 真的開過的頁面;如果來源比主張少,
就標明哪些主張沒有來源,不要替它們發明網址」。**尚未量測這句話有沒有用。**

**還沒做的**:判準目前把「編造」判為 fail(正確),但沒有任何機制在**寫入當下**辨認出
搜尋端點。可行的作法是把「路徑是 /search、/s/ 且帶查詢字串」的網址視為非來源,
但誤判風險未評估(有些站的真實文章路徑也長這樣)。
