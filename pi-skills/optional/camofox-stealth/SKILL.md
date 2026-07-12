---
name: camofox-stealth
description: 網路偵察／動工前調研用的專業級隱身瀏覽器（camofox / camofox-browser / Camoufox 隱身瀏覽即用本技能，勿自行 npm install 或當 Node library import）。當任務涉及外部庫、未知或易過時的技術，或目標網站有強大機器人偵測（Cloudflare/登入牆）、或需極低 Token 消耗讀長頁時使用。以 curl 驅動本地釘版 camofox-browser 伺服器（@askjo/camofox-browser@1.11.2，playwright-core 釘 1.53.1 以相容 Camoufox 引擎），Camoufox C++ 級指紋偽造，看到的內容接近真人。
---

# /camofox-stealth — 隱身網路偵察

> 後端自動安裝（不需手動架設）：`recon.sh ensure` 以 `npx -y` 取得並啟動伺服器，首次自動下載 Camoufox ~300MB 到 `~/.camofox`（一次性，會顯示下載提示並延長逾時）。授權使用：僅用於你有權存取的內容之研究與驗證，遵守目標站服務條款與 robots。

## 何時用（選型）
- **簡單、公開、不擋的頁** → 用 `dev-browser`（更輕）。
- **受保護 / 登入牆 / CF / 要省 token 讀長頁 / 動工前調研別人做法** → 用本技能。
- 目標：找既有做法、**提前避坑**、**參考不照抄**，把結論寫進 `findings.md`。

## 工作流

### 0. 確保伺服器就緒
```bash
sh "$PI_HARNESS_ROOT/pi-skills/optional/camofox-stealth/recon.sh" ensure
```
就緒後 API 在 `http://127.0.0.1:9377`（可用 `STEALTH_RECON_URL` 覆寫；預設埠避開常見的 8080）。

> **不要**自己 `npm install camofox-browser` 或 `require('camofox')`——那是**不同廠商的同名套件**，且本引擎是 REST 伺服器，非 Node library。一律走 `recon.sh ensure` + 下面的 curl。伺服器由 `recon.sh` 以釘版本地安裝啟動（playwright-core 鎖 1.53.1，避開新版 `viewport.isMobile` 與 Camoufox juggler 不相容導致建 tab 失敗）。

### 1. 搜尋 / 讀頁（直接開 DuckDuckGo HTML 端點）
> **搜尋走 DDG，不要走 macro。** 後端 `@askjo/camofox-browser@1.11.2` 的 macro 清單**沒有** `@duckduckgo_search`（`expandMacro` 回 null，navigate 報 `url or macro required`）；`@google_search` 存在但 Google 會回 `/sorry/index` 擋 bot。實測能穩定拿結果的是直接把查詢帶進 DDG HTML 端點的 `?q=`。中文查詢用檔案傳 payload，避免 Windows shell UTF-8 轉錯碼。

```bash
cat > /tmp/recon-tab.json <<EOF
{"userId":"recon","sessionKey":"r1","url":"https://html.duckduckgo.com/html/?q=<你的查詢>"}
EOF
RESP=$(curl -s -X POST http://127.0.0.1:9377/tabs \
  -H 'Content-Type: application/json; charset=utf-8' --data-binary @/tmp/recon-tab.json)
TID=$(printf '%s' "$RESP" | sed -n 's/.*"tabId":"\([^"]*\)".*/\1/p')
sleep 4   # 等結果載入（建 tab 的 url 不可用 about:blank，會被拒）
curl -s "http://127.0.0.1:9377/tabs/$TID/snapshot?userId=recon" -o /tmp/recon-snap.txt
```
（快照是無障礙樹，比 raw HTML 小約 90%，省 token。結果在搜尋表單下方，抽 `"標題" [eN]` 與其後連結。）

### 2. 讀頁 + 擋頁偵測
**務必接住回應的 `tabId`**（snapshot 才讀得到對的 tab）；含非 ASCII 的 URL 用檔案傳 payload：
```bash
cat > /tmp/recon-tab.json <<EOF
{"userId":"recon","sessionKey":"r1","url":"<目標URL>"}
EOF
RESP=$(curl -s -X POST http://127.0.0.1:9377/tabs \
  -H 'Content-Type: application/json; charset=utf-8' --data-binary @/tmp/recon-tab.json)
TID=$(printf '%s' "$RESP" | sed -n 's/.*"tabId":"\([^"]*\)".*/\1/p')
sleep 3
curl -s "http://127.0.0.1:9377/tabs/$TID/snapshot?userId=recon" -o /tmp/recon-page.txt
if sh "$PI_HARNESS_ROOT/pi-skills/optional/camofox-stealth/recon.sh" is_blocked /tmp/recon-page.txt; then
  echo "BLOCKED"   # 見步驟 4
fi
```

### 3. 需要登入態時（依平台）
agent 無法自動過帳密/2FA/captcha，登入態要靠人先建立一次。**方式因平台而異**：

- **Linux / Docker**：伺服器以 xvfb 起虛擬顯示器，noVNC 在 `http://localhost:6080` 可用——請使用者在裡面手動登入，session 存進 profile，之後 `web_open` 自動帶登入態。
- **Windows / macOS（重要）**：本後端在非 Linux 一律 `headless: true`（見 `server.js`：xvfb 僅 Linux 建立），**noVNC 不會起、也不會開可見視窗**。所以 **VNC 交接在 Windows 不適用**。改用 **`/login <domain>` 命令**（stealth-web-bridge 提供）：
  1. 先試 **cookie 重用**——讀使用者日常瀏覽器（**Firefox 最穩**；Chrome/Edge v127+ 的 app-bound 加密可能讀不到）已登入該站的 cookie，`POST /sessions/recon/cookies` 灌進 camofox。不碰密碼。
  2. 讀不到才 fallback：以**對話框**問帳密（不進聊天）、存 OS keychain、自動填登入表單。有 captcha/2FA 的站仍會失敗（headless 無 UI，這是硬限制）。
  底層是 `scripts/stealth_login.py`（`cookies`/`store`/`fill` 子命令；密碼只走 stdin/getpass，永不進 argv 或模型）。選用依賴：`pip install browser_cookie3 keyring`（缺會提示）。

### 4. 被擋時的誠實原則
若 `is_blocked` 為真：**不要把擋頁內容當真、不要編造**。先試 headed/OS-input retry；仍擋則向使用者誠實回報「此來源擋自動存取，改用搜尋摘要／跳過」。

### 5. 落地
把「可參考做法（不照抄）／要避的坑／來源 URL」寫進當前任務的 `findings.md`（planning-with-files）。

## 限制
- Camoufox 啟動吃 CPU/磁碟；首次下載 ~300MB。
- 最硬的 Akamai/Datadome 頂層可能仍需 residential proxy（本技能預設不掛 proxy，不在範圍內）。
- REST 驅動，非完整 Playwright JS API。

## 停止
```bash
sh "$PI_HARNESS_ROOT/pi-skills/optional/camofox-stealth/recon.sh" stop
```
