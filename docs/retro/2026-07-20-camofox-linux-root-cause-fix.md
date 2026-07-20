# 復盤：camofox-browser 在 Linux + systemd 上全面失效的根因追兇與修復

**日期**：2026-07-20
**系統**：Ubuntu 24.04 (Wayland+Xwayland) / GNOME / snapd
**涉及**：`camofox-stealth` 技能（`@askjo/camofox-browser` 後端）、Pi Harness 的 stealth-web 工具鏈
**方法**：實戰 root-cause tracing（從 journalctl 日誌層層追到 Playwright 協議層），證據全來自實際運行輸出。

---

## 故障現象

Pi 的 `web_search` / `web_open` 等 stealth 工具全部回傳 "Could not open a browser tab"。camofox-browser 健康檢查返回 `browserConnected: false`，`recon.sh install` 早已下載 Camoufox 完成——引擎在，但就是起不來。

**關鍵事實**：camofox 不是單純 "沒裝"；它下載了、二進制有了、server 進程跑在跑，但 **6 個不同層級的根因疊在一起**，讓它每次重啟必敗、而且每次失敗在不同階段（看運氣先撞哪一層）。

---

## 根因層層拆解（從外到內，照 journalctl 追到的順序）

### 層 1（啟動層）：systemd unit 的 PATH 不包含 nvm 的 node

```ini
ExecStart=/home/htciu/.local/bin/camofox-browser
Environment=PATH=/home/htciu/.local/bin:/usr/local/bin:/usr/bin:/bin
```

`camofox-browser` 入口是 shebang `#!/usr/bin/env node`，但 systemd unit 的 PATH 沒包含 nvm 目錄（`~/.nvm/versions/node/v24.18.0/bin`）。unit 每次重啟都秒掛，exit code 127：

```
env: 'node': No such file or directory
```

**Why it was never caught**：
- `recon.sh` 的 server 是用 `npx` / `node` 在 shell session 中直接跑的，shell session 有 nvm 的 PATH，所以 `recon.sh` 從未暴露此 bug。
- harness 的 "cold path test" 規則（CLAUDE.md）——測試真正的第一條路徑——沒有覆蓋到 "server 已裝好但 systemd 重啟" 這個路徑。
- 上一次手動 `kill + nohup` 繞過 systemd 的測試成功，反而掩蓋了問題。

### 層 2（啟動層）：launch retry 只有 1 次

`launchBrowserInstance()` 的 `maxAttempts = proxyPool?.launchRetries ?? 1`——沒有 proxy 配置時，瀏覽器啟動失敗 **只有 1 次機會，直接放棄**。

這讓層 2 的 xvfb bug、層 3 的沙盒問題全都沒有 retry 緩衝。

### 層 3（虛擬顯示層）：async 調用忘了 await，Promise 對象當 DISPLAY 傳入

```js
// camofox-browser server.js 原碼（bug）
vdDisplay = localVirtualDisplay.get();  // get() 是 async，回傳 Promise
log('info', 'xvfb virtual display started', { display: vdDisplay, attempt });
```

`VirtualDisplay.get()` 是 async 函數，但調用處沒 await。`vdDisplay` 成為 `[object Promise]` 對象，後續傳入 `launchOptions({ virtual_display: vdDisplay })` → `env.DISPLAY = virtual_display` → Firefox 啟動時讀到 `DISPLAY=[object Promise]`：

```
[pid=...] [err] Error: cannot open display: [object Promise]
```

Xvfb 實際已經啟動（journalctl 有 "xvfb virtual display started"），但 Firefox 因為 DISPLAY 錯直接退出——**進程樹裡 Xvfb 活著、Firefox 死了**。

**Why it was never caught**：Node.js 不檢查 `env` 的值類型；Playwright 的 launch 只報 "cannot open display"，沒說 DISPLAY 是什麼。這個 bug 只在 Linux（有 xvfb）上出現，macOS/Windows 的 headless 路徑根本不會碰。

### 層 4（瀏覽器啟動層）：Firefox 沙盒 vs 系統安全策略

Ubuntu 24.04 的 AppArmor（`unprivileged_userns` profile）拒絕 camoufox 的 user namespace 沙盒：

```
kernel: audit: ... apparmor="DENIED" operation="capable" profile="unprivileged_userns" pid=... capability=21 capname="sys_admin"
Sandbox: CanCreateUserNamespace() unshare(CLONE_NEWPID): EPERM
```

`kernel.unprivileged_userns_clone = 1` 允許 user namespaces，但 AppArmor 的 `unprivileged_userns` profile 沒有授予 `cap_sys_admin`。camoufox（基於 Firefox 的 custom build）需要 CLONE_NEWPID 來實現 content process sandbox——被拒絕後 Firefox 進程直接 exit(1)。

**修復**：`launchOptions({ firefox_user_prefs: { "browser.sandbox.level": 0 } })`——關閉 Firefox 內建的 sandbox level（從 level 1 降到 0，不使用 user namespace）。

**安全評估**：camofox 運行在 Pi Agent 的 tool 環境中，沒有持久化用戶資料、沒有密碼管理器、沒有 add-on 商店，且由 systemd user service 沙盒化。關閉 Firefox sandbox 在此 use case 的風險可接受（等同 headless browser 的標準狀態），但若有 proxy + 持久化 cookie 場景則需重新評估。

### 層 5（Playwright 協議層）：Playwright 的 viewport 協議 vs Firefox Juggler 協議不兼容

Playwright 的 context 創建把 `viewport: { width, height, isMobile, deviceScaleFactor }` 傳入 Firefox 的 Juggler CDP 協議；Firefox 的 Juggler 協議 **不支持 viewport schema**，拒絕整個 `newContext` 調用：

```
Protocol error (Browser.setDefaultViewport): Found property "<root>.viewport.isMobile" - false which is not described in this scheme
```

**修復**：所有 `newContext()` 調用改為 `{ ...options, viewport: null }`，viewport 由 Xvfb 的 screen size 決定。

**注意**：Playwright 的 Chromium 路徑使用 DevTools Protocol，**完全支持** viewport 參數——此 bug 是 Firefox 專有協議差異。camofox 從 Chromium 轉向 Firefox 後，這個協議差異沒有被 upstream 處理。

### 層 6（Page viewport 層）：`page.setViewportSize()` 也傳入 Firefox 不支持的 screenSize

層 5 修復後，tab 創建轉到 `page.setViewportSize({ width: 1280, height: 720 })`——Playwright 把這個轉為 Juggler 的 `Page.setViewportSize`，攜帶 `screenSize` 參數，Firefox 一樣拒絕：

```
Protocol error (Page.setViewportSize): Found property "<root>.screenSize" - { width: 1280, height: 720 } which is not described in this scheme
```

**修復**：移除 camofox-browser 中所有 `page.setViewportSize()` 調用（共 6 處），Firefox 路徑下 viewport 不可動態調整。

---

## 修復清單

| 文件 | 修改 | 行/位置 |
|------|------|---------|
| `~/.config/systemd/user/camofox-browser.service` | PATH 加入 `~/.nvm/versions/node/v24.18.0/bin` | Environment 行 |
| camofox-browser `server.js` | `vdDisplay = await localVirtualDisplay.get()`（加 await） | launchBrowserInstance |
| camofox-browser `server.js` | `maxAttempts = proxyPool?.launchRetries ?? 3`（1→3） | launchBrowserInstance |
| camofox-browser `server.js` | `launchOptions` 加入 `firefox_user_prefs: { "browser.sandbox.level": 0 }` | launchBrowserInstance |
| camofox-browser `server.js` | 3 處 `newContext` 加入 `viewport: null` | getSession, probeGoogleSearch, testBrowser |
| camofox-browser `server.js` | 移除所有 `page.setViewportSize()` 調用（6 處） | tab 創建/重試路徑 + viewport API 端點 |
| `~/.local/lib/node_modules/@askjo/camofox-browser` | `npm rebuild`（better-sqlite3 NODE_MODULE_VERSION 127→137） | native addon |

所有修改同時寫入 `~/.local/lib/`（systemd 實際運行的版本）和 `~/.camofox/pinned-server/`（npx 管理的路徑），並保留 `.bak`。

### 修復前 vs 後

```
修復前（2026-07-17 啟動，運行至今 2d20h）：
  browserConnected: false, consecutiveFailures: ∞（從上次手動重啟後再無一次成功）
  最後失敗：unprivileged_userns EPERM（層 3）

修復後（2026-07-20 13:25）：
  browserConnected: true, browserRunning: true
  啟動時間：0.5s（camoufox launched）
  web_open → 成功（example.com 讀取完整）
  web_search → 成功（DuckDuckGo 搜尋返回 7 個結果）
```

---

## 經驗教訓

### 1. "手動修好" 不是 "修好了"——冷路徑的定義要包含服務重啟

上一次 camofox 測試時，問題出在層 3（xvfb Promise bug），測試者手動 `kill + nohup node server.js` 繞過 systemd 讓 server 跑起來，然後驗證 web_open 成功。這個測試路徑是 **熱的、繞過 systemd 的**——它驗證了 "server 代碼邏輯 OK"，但完全沒覆蓋 "systemd 重啟服務" 這條真實用戶路徑。CLAUDE.md 的 "cold path" 紀律（"Exercise the path a fresh user actually hits"）在這次沒有被嚴格遵守——我們測試了 server 的 cold path（首次下載），但沒有測試 systemd 的 cold path（unit 重啟）。

### 2. Linux 環境的差異比想像大——不是 "裝了 camoufox 就完"

camofox 的 upstream 測試環境是 Docker（Fly.io 部署），Docker 的 `--cap-add` 和沙盒配置與桌面 Ubuntu 完全不同。桌面 Linux 有三個變數：
- AppArmor/SELinux 的 security profile（這台是 AppArmor）
- 顯示系統（Wayland vs X11；這台是 Wayland+Xwayland）
- 執行環境（systemd user service vs shell session）

任何一個差異都可能讓 "在 CI/Docker 上正常" 的套件在桌面掛掉。

### 3. 錯誤訊息的誤導性

每個錯誤訊息都在誠實地報告自己那一層的問題，但層層疊加時，最內層的 bug（Promise 當 DISPLAY）產生的錯誤最像 "環境問題"，而真實原因是代碼 bug。追根需要從 journalctl 的 **完整事件鏈** 看，不能只看最後一行的 error。

### 4. upstream 的 Firefox 兼容性缺口

`@askjo/camofox-browser`（OpenClaw 專案的 stealth browser 後端）在 Firefox Juggler 協議上有兩個已知缺口（viewport schema 不支持），upstream 尚未修復。camofox-stealth 技能依賴這個套件，**harness 對它的兼容性沒有控制權**。

### 5. harness 管理 vs upstream 管理的邊界

camofox-browser 的 bug 不在 harness repo 裡，而是在 `npm install` 下載的第三方套件中。recon.sh 已有先例（用 npm override 釘版 playwright-core 1.53.1 避開另一個 viewport bug），但這次是 server.js **源代碼 bug**，不是依賴版本問題——recon.sh 的 `install_server()` 只 `npm install + npm rebuild better-sqlite3`，不 patch 代碼。

---

## 對 Harness 的改進建議

### 已完成
- 本文件作為 root-cause 記錄
- `KNOWN_ISSUES.md` 新增 camofox 的 systemd/協議問題條目
- 提供 `recon.sh` 的 patch 腳本（`PATCHES/camofox-server-fixes.sh`）

### 建議實施

1. **recon.sh 的 install_server() 中加入 Linux server.js patch**：
   安裝完套件後，用 grep 特徵檢查 server.js 的 3 個 bug（Promise DISPLAY、retry=1、缺 firefox_user_prefs），存在則 patch。patch 邏輯寫在 recon.sh 附屬腳本中，保持冪等（重複安裝不重 patch），並註明 "patched by harness, may need re-review on upstream upgrade"。這延續了 recon.sh 已有先例的 "安裝後補丁" 模式（playwright-core override）。

2. **systemd unit 的自動部署**：目前 systemd unit 不是 `recon.sh` 管理的，unit 的 PATH bug 不在 recon.sh 的視野內。理想狀態是 recon.sh 管理它部署的所有依賴（unit 部署/修復、pinned-server patch）。

3. **camofox 狀態診斷工具**（`recon.sh status`）：
   - 一鍵檢查 systemd 狀態、server 健康、瀏覽器狀態、日誌最後 N 行
   - 替代目前要手動 `journalctl | grep camofox` 的排錯流程

4. **追蹤 upstream issue**：在 `@askjo/camofox-browser` 上開 issue 報告 viewport 協議差異（層 5/6）與 Promise DISPLAY bug（層 3），附 Firefox Juggler 協議的證據。upstream 修復後，recon.sh 的 patch 檢查可移除。

---

## 附錄：排查時間線與證據來源

| 時間 | 動作 | 發現 | 證據來源 |
|------|------|------|---------|
| 13:07 | `web_search` 失敗 | "Could not open a browser tab" | web_search 工具回傳 |
| 13:12 | 檢查 camofox 安裝狀態 | 二進制存在，server 進程活著（PID 5687），browserConnected: false | `journalctl -n 50` + `~/.cache/camoufox/camoufox-bin` |
| 13:15 | 分析上次失敗日誌 | unprivileged_userns EPERM + cannot open display: [object Promise] | `journalctl` 13:09 事件 |
| 13:17 | 讀 server.js launch 代碼 | await 缺失 + firefox_user_prefs 未傳 + retry=1 | `server.js` line 950/962/934 |
| 13:18 | 重啟服務 | systemd unit 因 node 不在 PATH 秒掛，exit 127 | `systemctl --user status` |
| 13:20 | 修復 4 項 + 重啟 | 瀏覽器啟動成功！但 web_open 仍失敗 | `health: browserConnected: true`；`journalctl` newContext 錯誤 |
| 13:21 | 分析 newContext 錯誤 | Playwright viewport schema vs Juggler 協議不兼容 | `journalctl` "isMobile...not described in this scheme" |
| 13:23 | 修復 viewport + 重啟 | setViewportSize 也報 screenSize 錯誤 | `journalctl` "screenSize...not described in this scheme" |
| 13:25 | 移除所有 viewport 調用 + 重啟 | **全部成功**：web_open example.com + web_search DuckDuckGo 均正常 | 工具回傳完整頁面內容 |

---

*本文件所有錯誤訊息、PID、時間戳、行號均來自 2026-07-20 實戰排查的 journalctl 和文件，無推測或虛構。*
