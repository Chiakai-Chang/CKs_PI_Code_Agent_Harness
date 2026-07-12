---
description: "隱身瀏覽器上網查資料／讀擋 bot 的長頁。用釘版本地 Camoufox 伺服器（camofox-stealth）搜尋與讀頁，繞過 Cloudflare／登入牆／JS 牆，快照省 token。把使用者打在 /browse 後面的文字當查詢或目標 URL。"
---

使用者要用隱身瀏覽器上網查資料或讀取會擋自動存取的頁面。把使用者打在 `/browse` 後面的文字當作**查詢字串**（若像網址則當**目標 URL**）。

不要用 `ctx_fetch_and_index` 或直接 curl 抓 Google——那些會被擋。不要用 `find` 去找技能檔（檔案就在 `$PI_HARNESS_ROOT/pi-skills/optional/camofox-stealth/`）。照下面步驟走 camofox-stealth 後端。

## 步驟

### 1. 確保後端就緒（首次會下載 ~300MB Camoufox，約數分鐘，只此一次）
```bash
sh "$PI_HARNESS_ROOT/pi-skills/optional/camofox-stealth/recon.sh" ensure
```
就緒後 API 在 `http://127.0.0.1:9377`。若這步失敗，如實回報「隱身後端起不來」並貼 `~/.camofox/recon.log` 最後幾行，不要編造搜尋結果。

### 2. 搜尋（使用者給的是查詢字串時）
直接開 DuckDuckGo HTML 端點——**不要用 `@duckduckgo_search` macro（本伺服器版本沒有），也不要用 `@google_search`（Google 會回 `/sorry` 擋 bot）**。DDG HTML 對自動存取友善且結果好抽。中文查詢**務必用檔案傳 payload**（避免 Windows shell 把 UTF-8 轉錯碼）：

```bash
# 把查詢字串寫進 JSON 檔（保 UTF-8），DDG html 端點直接帶 ?q=
cat > /tmp/browse-tab.json <<EOF
{"userId":"recon","sessionKey":"r1","url":"https://html.duckduckgo.com/html/?q=使用者的查詢字串放這"}
EOF
RESP=$(curl -s -X POST http://127.0.0.1:9377/tabs \
  -H 'Content-Type: application/json; charset=utf-8' --data-binary @/tmp/browse-tab.json)
TID=$(printf '%s' "$RESP" | sed -n 's/.*"tabId":"\([^"]*\)".*/\1/p')
sleep 4   # 等結果載入；建 tab 的 url 不可用 about:blank（會被拒）
curl -s "http://127.0.0.1:9377/tabs/$TID/snapshot?userId=recon" -o /tmp/browse-results.txt
```
快照是無障礙樹（JSON 內含 `snapshot` 欄），比 raw HTML 小約 90%。結果在搜尋表單下方，抽 `"標題" [eN]` 與其後的 `/url:` 或連結。

### 3. 讀特定頁（使用者給的是 URL，或要深入某個搜尋結果）
含非 ASCII 的 URL 一樣用檔案傳 payload。**務必接住回應的 `tabId`**，snapshot 才讀得到對的 tab：
```bash
cat > /tmp/browse-tab.json <<EOF
{"userId":"recon","sessionKey":"r1","url":"目標URL放這"}
EOF
RESP=$(curl -s -X POST http://127.0.0.1:9377/tabs \
  -H 'Content-Type: application/json; charset=utf-8' --data-binary @/tmp/browse-tab.json)
TID=$(printf '%s' "$RESP" | sed -n 's/.*"tabId":"\([^"]*\)".*/\1/p')
sleep 3
curl -s "http://127.0.0.1:9377/tabs/$TID/snapshot?userId=recon" -o /tmp/browse-page.txt
```

### 4. 擋頁偵測（重要，勿把擋頁當真）
```bash
if sh "$PI_HARNESS_ROOT/pi-skills/optional/camofox-stealth/recon.sh" is_blocked /tmp/browse-page.txt; then
  echo "BLOCKED"
fi
```
若 `BLOCKED`：**不要編造內容**。如實告訴使用者「此來源擋自動存取」，改用搜尋摘要或換來源。若整站需登入，暫停並請使用者到 `http://localhost:6080`（noVNC）手動登入，完成後續跑。

### 5. 讀快照、整理回答
讀 `/tmp/browse-results.txt` 或 `/tmp/browse-page.txt`，用內容回答使用者。附上來源 URL。查不到就說查不到，別瞎掰。
