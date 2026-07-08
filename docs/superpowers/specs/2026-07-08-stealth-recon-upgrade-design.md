# Stealth-Recon 能力升級設計 (2026-07-08)

> 升級既有 `pi-skills/optional/camofox-stealth`，使其成為可用的「網路偵察／動工前調研」能力：搜尋 → 讀頁 → 避坑 → 落地 `findings.md`，全程走 Camoufox 真人級隱身瀏覽器。**不新增重複 skill。**

## 目標 (Goal)
讓 pi agent 在動工前能把網路當 RAG，透過免費、自架、C++ 級指紋偽造的 Camoufox 瀏覽器搜尋並讀取真實頁面（含登入態），避免因反爬蟲擋頁或裸抓垃圾而給出過時／錯誤建議。

## 非目標 (Non-Goals)
- 不把 Camoufox ~300MB 二進位放進 repo（維持「倉庫零二進位」）。
- 不解決最硬的 Akamai/Datadome 頂層——那需 residential proxy，任何免費工具都做不到，明確排除。
- 不做通用大規模爬蟲框架（anansi 類）。
- 不動 minimal profile（保持極簡）。

## Global Constraints（每個 Task 隱含遵守）
- **釘版可重現**：camofox-browser 版本釘在 `pi-config/harness-config.json`，skill 對準該版 API；升級是刻意動作，不吃 `latest`。
- **零依賴 repo / bash 相容**：harness 僅以 `bash`+`curl` 驅動；helper 為 POSIX sh，Git Bash 可跑。
- **平台無關**：不硬編機器路徑；OS-specific 值執行期產生。
- **Port 不撞**：預設 `9377`，**嚴禁 8080**（使用者本地 LLM 常駐該埠）。可由 `STEALTH_RECON_URL` 覆寫。
- **誠實回報**：偵測到擋頁不得當成內容、不得編造；升級或跳過並告知。
- **授權使用**：文檔含 authorized-use 聲明（雙用途，比照上游 DISCLAIMER）。
- **測試零依賴**：`python -m unittest`（不引入 pytest）。

## 設計決策（來自 brainstorming）
| # | 決策 | 選擇 |
|---|------|------|
| 後端 | 引擎/執行 | node `@askjo/camofox-browser` 預設；`docker-stealthy-auto-browse` 文檔化為進階可選 |
| 接入 | pi 無內建 MCP | Skill + `bash`/`curl`（無 TS 擴充、無 MCP） |
| 生命週期 | 伺服器啟動 | `setup.py` 可選預抓 + skill 懶啟動（detached + pidfile + health-check） |
| 登入 | session | VNC 視覺登入 + 持久 profile 為主；cookie import 為次選 |
| 觸發 | 何時偵察 | Skill + 有界 pi-rule + 結論寫入 `findings.md`；瑣碎任務不強制 |
| 出貨 | profile | skill 留 `optional/`（standard 載入）、rule 進 `pi-rules/`（standard+）；後端 opt-in 預抓 |

## 復盤修正（相對初版）
1. **不新增 `stealth-recon`，升級既有 `camofox-stealth`**（避免 repo 內重複）。
2. **修 API 漂移**：既有 skill 寫 `port 3001` + `/navigate`，與現行 camofox-browser `/tabs`+snapshot 不符——對準釘版 API 重寫。
3. **釘版 + 併入更新流**：解決 `npx latest` 移動標的與「兩條更新軌漂移」。
4. **Port 改 9377、可設定**：避開使用者 LLM 的 8080。
5. **生命週期改 detached + pidfile**：解決 Windows/Git Bash 短命 tool-call 背景進程被收/孤兒問題。
6. **VNC 登入交接明文化**：agent 偵測到登入牆時暫停、請使用者手動登入、再續。

## 架構與元件

### A. 升級的 Skill：`pi-skills/optional/camofox-stealth/`
- `SKILL.md`（重寫）：偵察方法論 + 對準釘版的 curl 工作流 + 擋頁偵測 + 登入交接 + `findings.md` 落地 + 瀏覽器選型指引（簡單頁 → `dev-browser`；受保護/登入/省 token → camofox-stealth）。
- `recon.sh`（新增，POSIX sh）：
  - `ensure_server`：`curl -sf $URL/health` → 否則 detached 啟動（`nohup ... >log 2>&1 &` + 寫 `~/.camofox/recon.pid`），輪詢 health 直到就緒或逾時。
  - `is_blocked <snapshot_or_html>`：比對擋頁標記（見下）回傳 0/1。
  - `search <query>` / `read <url>`：包裝 curl 呼叫，統一輸出。
  - 全部讀 `STEALTH_RECON_URL`（預設 `http://127.0.0.1:9377`）。
- `RATIONALE.md`（更新）：補「升級/釘版/更新流」決策，維持 Thin Bridge 路徑判定。

### B. 觸發規則：`pi-rules/stealth-recon.md`（新增）
非瑣碎且涉及外部庫/未知技術/易過時做法的任務，動工前跑一次限時偵察（預設上限：3 個來源或一次搜尋+2 次讀頁），結論寫進 planning-with-files 的 `findings.md`（避坑清單／可參考做法「參考不照抄」／來源 URL）。瑣碎或純內部邏輯任務不強制。

### C. 安裝與更新：`scripts/setup.py`
- 完整安裝新增**可選、非互動安全**步驟：問是否預抓 Camoufox（釘版 `npx @askjo/camofox-browser@<pinned> --version` 觸發下載）；`--auto`/非 tty 預設「否」，best-effort，**絕不擋安裝**。
- 版本來源：讀 `harness-config.json` 的 `camofoxBrowserVersion`。
- 文檔給**單一更新路徑**：`git pull` → `setup.py --mode restore` → `pi update`；stealth 後端升級＝改 `harness-config.json` 版本後重跑 setup 預抓。

### D. 設定釘版：`pi-config/harness-config.json`
新增鍵：`"camofoxBrowserVersion": "<pinned>"`（實作時填當時最新穩定版並記於 spec 註）。

### E. 清理：`scripts/uninstall.py`
`camofox-stealth` 已在 `MANAGED_SKILLS`，無需改；新增註解：`~/.camofox/`（profiles/cookies 含登入密鑰）預設保留、不刪使用者資料。

### F. 文檔：`README.md` 整合表新增一列（stealth-recon / camofox-browser / Thin Bridge / ⚠️ 進階可選）；`docs/KNOWN_ISSUES.md` 視需要補「後端需自架、最硬 Akamai 需 proxy」。

## 資料流
```
任務(非瑣碎, 外部庫/未知技術)
  → rule 觸發 recon.sh ensure_server (health || detached start, ENABLE_VNC=1)
  → search: POST /tabs {url:@google_search|@duckduckgo, query} → GET /tabs/:id/snapshot  # 取連結+摘要
  → read:   POST /tabs {url} → GET /tabs/:id/snapshot(accessibility, ~90% 小)
  → is_blocked? ── yes ──→ headed/OS-input retry ── 仍擋 ──→ 誠實回報/跳過(不編造)
        │ no
  → 綜合: 避坑清單 / 可參考做法(不照抄) / 來源 → findings.md
需要登入態時:
  → 偵測登入牆 → 暫停, 指示使用者開 noVNC(localhost:6080) 手動登入
  → camofox 存 ~/.camofox/profiles/<user>/ → 續跑, 後續 goto 自動帶登入態
```

## 擋頁偵測標記（`is_blocked`）
標題含 `Just a moment`／`Attention Required`；出現 Cloudflare Turnstile／`cf-mitigated`／`__cf_chl`；文字/節點密度過低（疑 JS 空殼）；含 `Enable JavaScript and cookies to continue`；HTTP 403/429 + challenge body。命中任一 → 視為被擋。

## 釘版 API 契約（camofox-browser，`<pinned>`）
- 建 tab：`POST /tabs {userId, sessionKey, url}` → `{tabId}`
- 快照：`GET /tabs/:tabId/snapshot?userId=X`（accessibility + element refs；`offset` 分頁）
- 導航/搜尋：`POST /tabs/:tabId/navigate {macro:"@google_search", query}`
- 互動：`POST /tabs/:tabId/{click,type,press,scroll}`
- 登入：`POST /sessions/:userId/cookies`（cookie import）；`GET /sessions/:userId/storage_state`（VNC 後匯出）
- 健康：`GET /health`；VNC：`ENABLE_VNC=1`、`NOVNC_PORT=6080`
- 埠：`CAMOFOX_PORT`（預設 9377）

## 安全預設
只綁 `127.0.0.1`；預設不掛 proxy；可選 `CAMOFOX_ACCESS_KEY`；`~/.camofox` 在 repo 外且不入版控。

## 測試（`tests/test_stealth_recon.py`，unittest 零依賴）
- skill 存在且**不再**含舊 `3001`／`/navigate`；含新 `/tabs`＋`snapshot`＋擋頁偵測字樣。
- `pi-rules/stealth-recon.md` 存在且含「findings.md」「參考不照抄」。
- `recon.sh` 存在、`sh -n` 語法通過、含 `is_blocked`／`ensure_server`／pidfile。
- `harness-config.json` 有 `camofoxBrowserVersion`。
- setup 預抓為 opt-in：`--auto`/非 tty 不觸發下載、無裸 `input()` 阻塞。
- 出貨檔案**無** `:8080` 硬編、無機器路徑（比照既有平台無關測試）。

## 檔案清單
- 改：`pi-skills/optional/camofox-stealth/{SKILL.md,RATIONALE.md}`
- 新增：`pi-skills/optional/camofox-stealth/recon.sh`、`pi-rules/stealth-recon.md`、`tests/test_stealth_recon.py`
- 改：`scripts/setup.py`、`pi-config/harness-config.json`、`scripts/uninstall.py`（註解）、`README.md`、`docs/KNOWN_ISSUES.md`

## 驗證
- `python -m unittest discover -s tests` 全綠（含新測試）。
- `sh -n pi-skills/optional/camofox-stealth/recon.sh`。
- `python scripts/setup.py --mode restore --auto` 非互動完成、不觸發 300MB 下載。
- 端到端（有裝後端者）：`recon.sh` 起服務→搜尋→讀頁→對受保護站驗證擋頁偵測與誠實回報。
- `grep -rn ":8080\|D:/MyProject\|Myproject" pi-skills/optional/camofox-stealth pi-rules/stealth-recon.md` 無命中。
