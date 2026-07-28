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
