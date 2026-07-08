---
name: camofox-stealth
description: 網路偵察／動工前調研用的專業級隱身瀏覽器。當任務涉及外部庫、未知或易過時的技術，或目標網站有強大機器人偵測（Cloudflare/登入牆）、或需極低 Token 消耗讀長頁時使用。以 curl 驅動本地釘版 camofox-browser 伺服器（@askjo/camofox-browser@1.11.2），Camoufox C++ 級指紋偽造，看到的內容接近真人。
---

# /camofox-stealth — 隱身網路偵察

> 後端需自架（不含在 repo）。首次會下載 Camoufox ~300MB 到 `~/.camofox`。授權使用：僅用於你有權存取的內容之研究與驗證，遵守目標站服務條款與 robots。

## 何時用（選型）
- **簡單、公開、不擋的頁** → 用 `dev-browser`（更輕）。
- **受保護 / 登入牆 / CF / 要省 token 讀長頁 / 動工前調研別人做法** → 用本技能。
- 目標：找既有做法、**提前避坑**、**參考不照抄**，把結論寫進 `findings.md`。

## 工作流

### 0. 確保伺服器就緒
```bash
sh $PI_HARNESS_ROOT/pi-skills/optional/camofox-stealth/recon.sh ensure
```
就緒後 API 在 `http://127.0.0.1:9377`（可用 `STEALTH_RECON_URL` 覆寫；預設埠避開常見的 8080）。

### 1. 搜尋 / 讀頁（內建 macro，免另裝搜尋工具）
```bash
# 建立 tab 並取得快照
TID=$(curl -s -X POST http://127.0.0.1:9377/tabs \
  -H 'Content-Type: application/json' \
  -d '{"userId":"recon","sessionKey":"r1","url":"https://duckduckgo.com"}' | \
  sed -n 's/.*"tabId":"\([^"]*\)".*/\1/p')
curl -s "http://127.0.0.1:9377/tabs/$TID/snapshot?userId=recon" -o /tmp/recon-snap.txt
```
（macro 也支援 `@google_search`；快照是無障礙樹，比 raw HTML 小約 90%，省 token。內建搜尋 macro 可直接對 tab 執行查詢操作。）

### 2. 讀頁 + 擋頁偵測
```bash
curl -s -X POST http://127.0.0.1:9377/tabs \
  -H 'Content-Type: application/json' \
  -d '{"userId":"recon","sessionKey":"r1","url":"<目標URL>"}'
curl -s "http://127.0.0.1:9377/tabs/$TID/snapshot?userId=recon" -o /tmp/recon-page.txt
if sh $PI_HARNESS_ROOT/pi-skills/optional/camofox-stealth/recon.sh is_blocked /tmp/recon-page.txt; then
  echo "BLOCKED"   # 見步驟 4
fi
```

### 3. 需要登入態時（VNC 交接）
偵測到登入牆時 **暫停並請使用者手動登入**（agent 無法自動過 2FA/captcha）：
1. 告訴使用者：開瀏覽器到 `http://localhost:6080`（noVNC），在裡面登入目標站。
2. camofox 會把 session 存到 `~/.camofox/profiles/`。
3. 使用者完成後回覆，續跑；後續 `goto` 自動帶登入態。
（快速路徑：若已有 Netscape `cookies.txt`，放到 `~/.camofox/cookies/` 由 `POST /sessions/recon/cookies` 匯入。）

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
sh $PI_HARNESS_ROOT/pi-skills/optional/camofox-stealth/recon.sh stop
```
