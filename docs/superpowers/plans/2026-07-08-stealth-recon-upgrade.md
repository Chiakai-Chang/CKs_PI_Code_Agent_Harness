# Stealth-Recon 能力升級 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 升級既有 `pi-skills/optional/camofox-stealth`，成為可用的網路偵察能力（搜尋→讀頁→避坑→`findings.md`），以 `bash`+`curl` 驅動釘版 Camoufox 瀏覽器伺服器。

**Architecture:** 不新增重複 skill。重寫既有 skill 的 SKILL.md、新增 POSIX `recon.sh`（生命週期+擋頁偵測）、新增觸發 rule、在 `harness-config.json` 釘 camofox 版本、`setup.py` 加可選預抓、補零依賴 unittest 與文檔。所有整合經 bash/curl，維持倉庫零二進位。

**Tech Stack:** POSIX sh (Git Bash 相容)、Python 3 標準庫（setup/測試）、`@askjo/camofox-browser@1.11.2`（外部、跑在使用者機器、不進 repo）。

## Global Constraints

- 釘版：`@askjo/camofox-browser@1.11.2`，記於 `pi-config/harness-config.json` 的 `camofoxBrowserVersion`；skill 對準此版 API。
- Port 預設 `9377`，**嚴禁硬編 `8080`**（使用者本地 LLM 常駐）；可由 `STEALTH_RECON_URL` 覆寫。
- bash/POSIX sh 相容；不硬編機器路徑（無 `D:/MyProject`、`C:\`、`file:///`）。
- 偵測到擋頁不得當內容、不得編造；升級或跳過並告知。
- 測試零依賴：`python -m unittest`（不引入 pytest）。
- 本機 Python 直譯器路徑：`C:/Users/User/AppData/Local/Python/bin/python.exe`（`python` 在此環境指向失效的 WindowsApps stub）。
- Git 身分已設 `Chiakai Chang <lotifv@gmail.com>`。

## File Structure

- `pi-config/harness-config.json` — 新增 `camofoxBrowserVersion` 釘版鍵。
- `pi-skills/optional/camofox-stealth/recon.sh` — 新增；伺服器生命週期 + 擋頁偵測 helper（唯一含邏輯的檔）。
- `pi-skills/optional/camofox-stealth/SKILL.md` — 重寫；方法論 + curl 工作流 + 登入交接 + findings 落地。
- `pi-skills/optional/camofox-stealth/RATIONALE.md` — 更新；補釘版/更新流決策。
- `pi-rules/stealth-recon.md` — 新增；有界觸發規則（restore 自動整包複製 pi-rules，無需改 restore.py）。
- `scripts/setup.py` — 新增可選、非互動安全的 Camoufox 預抓步驟。
- `scripts/uninstall.py` — 補註解（`~/.camofox` 使用者資料保留）。
- `README.md` — 整合表新增一列。
- `docs/KNOWN_ISSUES.md` — 補「後端需自架、最硬 Akamai 需 proxy」。
- `tests/test_stealth_recon.py` — 新增；零依賴 unittest。

---

### Task 1: 釘版設定鍵

**Files:**
- Modify: `pi-config/harness-config.json`
- Test: `tests/test_stealth_recon.py`

**Interfaces:**
- Produces: `harness-config.json` 內 `camofoxBrowserVersion: "1.11.2"`，供 setup.py 與文檔引用。

- [ ] **Step 1: 寫失敗測試**

新建 `tests/test_stealth_recon.py`：

```python
import json
import os
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_file(rel):
    with open(os.path.join(ROOT, rel), "r", encoding="utf-8") as f:
        return f.read()


class TestHarnessConfigPin(unittest.TestCase):
    def test_camofox_version_pinned(self):
        cfg = json.loads(read_file("pi-config/harness-config.json"))
        self.assertEqual(cfg.get("camofoxBrowserVersion"), "1.11.2",
                         "harness-config.json must pin camofoxBrowserVersion")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `C:/Users/User/AppData/Local/Python/bin/python.exe -m unittest tests.test_stealth_recon -v`
Expected: FAIL（`camofoxBrowserVersion` 為 None ≠ "1.11.2"）

- [ ] **Step 3: 加釘版鍵**

`pi-config/harness-config.json` 現況：
```json
{
  "harnessVersion": "1.0.0",
  "minRecommendedPiVersion": "0.73.0",
  "description": "CK's Pi Code Agent Harness configuration version"
}
```
改為：
```json
{
  "harnessVersion": "1.0.0",
  "minRecommendedPiVersion": "0.73.0",
  "camofoxBrowserVersion": "1.11.2",
  "description": "CK's Pi Code Agent Harness configuration version"
}
```

- [ ] **Step 4: 跑測試確認通過**

Run: `C:/Users/User/AppData/Local/Python/bin/python.exe -m unittest tests.test_stealth_recon -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pi-config/harness-config.json tests/test_stealth_recon.py
git commit -m "feat(config): pin camofoxBrowserVersion for stealth-recon"
```

---

### Task 2: `recon.sh` 生命週期與擋頁偵測 helper

**Files:**
- Create: `pi-skills/optional/camofox-stealth/recon.sh`
- Test: `tests/test_stealth_recon.py`

**Interfaces:**
- Produces:
  - env `STEALTH_RECON_URL`（預設 `http://127.0.0.1:9377`）
  - `recon.sh health` → exit 0 若伺服器就緒
  - `recon.sh ensure` → health 或 detached 啟動（`nohup ... &` + pidfile `~/.camofox/recon.pid`），輪詢至就緒/逾時
  - `recon.sh is_blocked <file>` → exit 0 若內容判定被擋
  - 內部 `START_CMD="npx -y @askjo/camofox-browser@1.11.2"`（釘版），`ENABLE_VNC=1`

- [ ] **Step 1: 寫失敗測試**

在 `tests/test_stealth_recon.py` 追加：

```python
class TestReconScript(unittest.TestCase):
    REL = "pi-skills/optional/camofox-stealth/recon.sh"

    def test_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(ROOT, self.REL)),
                        "recon.sh must exist")

    def test_posix_syntax_valid(self):
        r = subprocess.run(["sh", "-n", os.path.join(ROOT, self.REL)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, f"sh -n failed: {r.stderr}")

    def test_pins_version_and_port_and_pidfile(self):
        c = read_file(self.REL)
        self.assertIn("@askjo/camofox-browser@1.11.2", c)
        self.assertIn("9377", c)
        self.assertIn("recon.pid", c)
        self.assertNotIn(":8080", c)

    def test_has_functions(self):
        c = read_file(self.REL)
        for token in ["ensure", "is_blocked", "STEALTH_RECON_URL", "ENABLE_VNC"]:
            self.assertIn(token, c, f"recon.sh must reference {token}")

    def test_block_markers_present(self):
        c = read_file(self.REL)
        for marker in ["Just a moment", "cf-mitigated", "Enable JavaScript"]:
            self.assertIn(marker, c, f"recon.sh must detect '{marker}'")
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `C:/Users/User/AppData/Local/Python/bin/python.exe -m unittest tests.test_stealth_recon.TestReconScript -v`
Expected: FAIL（檔案不存在）

- [ ] **Step 3: 建立 `recon.sh`**

```sh
#!/usr/bin/env sh
# CK's Pi Code Agent Harness - stealth-recon backend helper
# Drives a pinned Camoufox browser server (@askjo/camofox-browser@1.11.2)
# via curl. POSIX sh; runs under Git Bash on Windows.

STEALTH_RECON_URL="${STEALTH_RECON_URL:-http://127.0.0.1:9377}"
CAMOFOX_HOME="${CAMOFOX_HOME:-$HOME/.camofox}"
PIDFILE="$CAMOFOX_HOME/recon.pid"
LOGFILE="$CAMOFOX_HOME/recon.log"
START_CMD="npx -y @askjo/camofox-browser@1.11.2"
START_TIMEOUT="${STEALTH_RECON_TIMEOUT:-40}"

log() { printf '[recon] %s\n' "$*" >&2; }

health() {
  curl -sf "$STEALTH_RECON_URL/health" >/dev/null 2>&1
}

ensure() {
  if health; then
    log "server already up at $STEALTH_RECON_URL"
    return 0
  fi
  mkdir -p "$CAMOFOX_HOME"
  log "starting stealth server (detached): $START_CMD"
  # Detach so the server survives this tool-call shell. ENABLE_VNC lets the
  # user log in visually at http://localhost:6080 when a site needs auth.
  ENABLE_VNC=1 CAMOFOX_PORT=9377 nohup $START_CMD >"$LOGFILE" 2>&1 &
  echo "$!" > "$PIDFILE"
  i=0
  while [ "$i" -lt "$START_TIMEOUT" ]; do
    if health; then
      log "server ready after ${i}s"
      return 0
    fi
    i=$((i + 1))
    sleep 1
  done
  log "server did NOT become ready in ${START_TIMEOUT}s; see $LOGFILE"
  return 1
}

# is_blocked <file>: exit 0 (blocked) if the fetched snapshot/HTML looks like
# an anti-bot challenge or JS shell rather than real content. Callers MUST NOT
# treat blocked output as content — fall back or report honestly, never invent.
is_blocked() {
  f="$1"
  [ -f "$f" ] || return 1
  if grep -qiE 'Just a moment|Attention Required|cf-mitigated|__cf_chl|Enable JavaScript and cookies to continue|Checking your browser' "$f"; then
    return 0
  fi
  # JS shell heuristic: almost no visible text
  bytes=$(wc -c < "$f" 2>/dev/null || echo 0)
  words=$(wc -w < "$f" 2>/dev/null || echo 0)
  if [ "$bytes" -gt 2000 ] && [ "$words" -lt 30 ]; then
    return 0
  fi
  return 1
}

stop() {
  [ -f "$PIDFILE" ] || { log "no pidfile"; return 0; }
  pid=$(cat "$PIDFILE")
  kill "$pid" 2>/dev/null && log "stopped pid $pid"
  rm -f "$PIDFILE"
}

case "${1:-}" in
  health) health ;;
  ensure) ensure ;;
  is_blocked) is_blocked "$2" ;;
  stop) stop ;;
  *) echo "usage: recon.sh {health|ensure|is_blocked <file>|stop}" >&2; exit 2 ;;
esac
```

- [ ] **Step 4: 跑測試確認通過**

Run: `C:/Users/User/AppData/Local/Python/bin/python.exe -m unittest tests.test_stealth_recon.TestReconScript -v`
Expected: PASS（5 個測試全過）

- [ ] **Step 5: Commit**

```bash
git add pi-skills/optional/camofox-stealth/recon.sh tests/test_stealth_recon.py
git commit -m "feat(stealth-recon): add recon.sh lifecycle + block-detection helper"
```

---

### Task 3: 重寫 `SKILL.md`

**Files:**
- Modify: `pi-skills/optional/camofox-stealth/SKILL.md`
- Test: `tests/test_stealth_recon.py`

**Interfaces:**
- Consumes: `recon.sh`（Task 2）的 `ensure`/`is_blocked`；釘版 API（`/tabs`、`/tabs/:id/snapshot`、`navigate` macro）。
- Produces: agent 可讀的偵察工作流（供 rule 於 Task 4 引用）。

- [ ] **Step 1: 寫失敗測試**

在 `tests/test_stealth_recon.py` 追加：

```python
class TestSkillMd(unittest.TestCase):
    REL = "pi-skills/optional/camofox-stealth/SKILL.md"

    def test_no_stale_api(self):
        c = read_file(self.REL)
        self.assertNotIn("3001", c, "must not reference the stale port 3001")
        self.assertNotIn("/navigate", c, "must not reference the stale /navigate endpoint")

    def test_current_api_and_workflow(self):
        c = read_file(self.REL)
        self.assertIn("/tabs", c)
        self.assertIn("snapshot", c)
        self.assertIn("recon.sh ensure", c)
        self.assertIn("is_blocked", c)
        self.assertIn("findings.md", c)
        self.assertIn("9377", c)

    def test_selection_guidance_and_honesty(self):
        c = read_file(self.REL)
        self.assertIn("dev-browser", c, "must guide when to use dev-browser vs stealth")
        # honest fallback wording
        self.assertTrue("誠實" in c or "不編造" in c)

    def test_no_machine_paths(self):
        import re
        c = read_file(self.REL)
        self.assertIsNone(re.search(r"file:///[A-Za-z]:/|[A-Za-z]:/MyProject|:8080", c))
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `C:/Users/User/AppData/Local/Python/bin/python.exe -m unittest tests.test_stealth_recon.TestSkillMd -v`
Expected: FAIL（現況含 3001 與 /navigate）

- [ ] **Step 3: 重寫 SKILL.md**

以下列完整內容覆寫 `pi-skills/optional/camofox-stealth/SKILL.md`：

````markdown
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
sh "$PI_HARNESS_ROOT/pi-skills/optional/camofox-stealth/recon.sh" ensure
```
就緒後 API 在 `http://127.0.0.1:9377`（可用 `STEALTH_RECON_URL` 覆寫；預設埠避開常見的 8080）。

### 1. 搜尋（內建 macro，免另裝搜尋工具）
```bash
# 建立 tab 並用搜尋 macro
TID=$(curl -s -X POST http://127.0.0.1:9377/tabs \
  -H 'Content-Type: application/json' \
  -d '{"userId":"recon","sessionKey":"r1","url":"https://duckduckgo.com"}' | \
  sed -n 's/.*"tabId":"\([^"]*\)".*/\1/p')
curl -s -X POST "http://127.0.0.1:9377/tabs/$TID/navigate" \
  -H 'Content-Type: application/json' \
  -d '{"userId":"recon","macro":"@duckduckgo_search","query":"<你的查詢>"}'
curl -s "http://127.0.0.1:9377/tabs/$TID/snapshot?userId=recon" -o /tmp/recon-snap.txt
```
（macro 也支援 `@google_search`；快照是無障礙樹，比 raw HTML 小約 90%，省 token。）

### 2. 讀頁 + 擋頁偵測
```bash
curl -s -X POST http://127.0.0.1:9377/tabs \
  -H 'Content-Type: application/json' \
  -d '{"userId":"recon","sessionKey":"r1","url":"<目標URL>"}'
curl -s "http://127.0.0.1:9377/tabs/$TID/snapshot?userId=recon" -o /tmp/recon-page.txt
if sh "$PI_HARNESS_ROOT/pi-skills/optional/camofox-stealth/recon.sh" is_blocked /tmp/recon-page.txt; then
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
sh "$PI_HARNESS_ROOT/pi-skills/optional/camofox-stealth/recon.sh" stop
```
````

- [ ] **Step 4: 跑測試確認通過**

Run: `C:/Users/User/AppData/Local/Python/bin/python.exe -m unittest tests.test_stealth_recon.TestSkillMd -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pi-skills/optional/camofox-stealth/SKILL.md tests/test_stealth_recon.py
git commit -m "feat(stealth-recon): rewrite SKILL.md to current API + recon workflow"
```

---

### Task 4: 觸發規則 `pi-rules/stealth-recon.md`

**Files:**
- Create: `pi-rules/stealth-recon.md`
- Test: `tests/test_stealth_recon.py`

**Interfaces:**
- Consumes: Task 3 的 skill（以名稱 `camofox-stealth` 引用）。
- Produces: standard profile 下的有界觸發規則（restore.py 整包複製 `pi-rules/`，自動生效，無需改 restore.py）。

- [ ] **Step 1: 寫失敗測試**

在 `tests/test_stealth_recon.py` 追加：

```python
class TestRule(unittest.TestCase):
    REL = "pi-rules/stealth-recon.md"

    def test_exists_and_bounded(self):
        c = read_file(self.REL)
        self.assertIn("findings.md", c)
        self.assertIn("參考不照抄", c)
        self.assertIn("camofox-stealth", c)
        # bounded: mentions a cap so trivial tasks aren't dragged
        self.assertTrue("上限" in c or "瑣碎" in c)
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `C:/Users/User/AppData/Local/Python/bin/python.exe -m unittest tests.test_stealth_recon.TestRule -v`
Expected: FAIL（檔案不存在）

- [ ] **Step 3: 建立規則**

`pi-rules/stealth-recon.md`：

```markdown
# 動工前網路偵察 (Stealth Recon)

## 何時觸發
當任務**非瑣碎**且符合任一：涉及外部庫/框架/API、用到不熟悉或易過時的技術、要做設計決策而缺乏依據。純內部邏輯、格式修正、單行改動等瑣碎任務**不強制**。

## 怎麼做
1. 用 `camofox-stealth` 技能做一次**有界**偵察：**上限**約一次搜尋 + 讀 2–3 個來源，別無限展開。
2. 目的：找既有做法、**提前避坑**、**參考不照抄**（理解原理後自己實作，不複製貼上）。
3. 偵測到擋頁時**誠實回報、不編造**（見技能第 4 節）。
4. 把結論寫進當前任務的 `findings.md`（planning-with-files）：可參考做法、要避的坑、來源 URL。

## 邊界
偵察是為了品質，不是拖延。達到上限或已足夠回答設計問題就停，進入實作。
```

- [ ] **Step 4: 跑測試確認通過**

Run: `C:/Users/User/AppData/Local/Python/bin/python.exe -m unittest tests.test_stealth_recon.TestRule -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pi-rules/stealth-recon.md tests/test_stealth_recon.py
git commit -m "feat(stealth-recon): add bounded pre-work recon trigger rule"
```

---

### Task 5: `setup.py` 可選、非互動安全的 Camoufox 預抓

**Files:**
- Modify: `scripts/setup.py`
- Test: `tests/test_stealth_recon.py`

**Interfaces:**
- Consumes: `harness-config.json` 的 `camofoxBrowserVersion`（Task 1）；既有 `ask()` 輔助（非 tty/`--auto` 回傳預設）、`run_stream()`。
- Produces: 完整安裝流程中一個「是否預抓 stealth 引擎」的可選步驟，預設「否」，best-effort。

- [ ] **Step 1: 寫失敗測試**

在 `tests/test_stealth_recon.py` 追加：

```python
class TestSetupPrefetch(unittest.TestCase):
    REL = "scripts/setup.py"

    def test_prefetch_present_and_optional(self):
        c = read_file(self.REL)
        self.assertIn("camofoxBrowserVersion", c, "setup must read pinned version")
        self.assertIn("@askjo/camofox-browser", c)
        # opt-in via ask() default "n" — must not force download
        self.assertIn("prefetch", c.lower())

    def test_prefetch_uses_ask_not_raw_input(self):
        # the prefetch prompt must degrade in --auto/non-tty (uses ask(), not input())
        c = read_file(self.REL)
        idx = c.lower().find("prefetch")
        window = c[max(0, idx - 400): idx + 400]
        self.assertIn("ask(", window, "prefetch prompt must use ask() for --auto safety")
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `C:/Users/User/AppData/Local/Python/bin/python.exe -m unittest tests.test_stealth_recon.TestSetupPrefetch -v`
Expected: FAIL

- [ ] **Step 3: 加預抓步驟**

在 `scripts/setup.py` 中，找到 `mode == "full"` 區塊裡安裝 pi 的段落（`if has_command("pi"): run_stream("pi update")` 之後、模型設定之前），插入：

```python
        # Optional: prefetch the stealth-recon browser engine (Camoufox ~300MB).
        # Opt-in and best-effort — never block install; --auto / non-tty skips it.
        cfg = load_json(HARNESS_CONFIG_PATH)
        camofox_ver = cfg.get("camofoxBrowserVersion", "1.11.2")
        pf = ask(f"是否預抓 stealth-recon 隱身瀏覽器引擎 Camoufox (~300MB, 可選)? [y/N]: ", "n")
        if pf.strip().lower() == "y":
            print("[*] 正在預抓 stealth 引擎 (best-effort)...")
            # prefetch: triggers Camoufox binary download to ~/.camofox
            run_stream(f"npx -y @askjo/camofox-browser@{camofox_ver} --version")
        else:
            print("[*] 略過 stealth 引擎預抓 (可日後執行 pi 時由 camofox-stealth 技能懶啟動)。")
```

（`HARNESS_CONFIG_PATH`、`load_json`、`ask`、`run_stream` 皆已存在於 setup.py。）

- [ ] **Step 4: 跑測試確認通過 + 冒煙**

Run: `C:/Users/User/AppData/Local/Python/bin/python.exe -m unittest tests.test_stealth_recon.TestSetupPrefetch -v`
Expected: PASS

Run: `C:/Users/User/AppData/Local/Python/bin/python.exe -m py_compile scripts/setup.py`
Expected: 無輸出（編譯成功）

- [ ] **Step 5: Commit**

```bash
git add scripts/setup.py tests/test_stealth_recon.py
git commit -m "feat(setup): optional best-effort prefetch of pinned stealth engine"
```

---

### Task 6: RATIONALE、uninstall 註解、README、KNOWN_ISSUES

**Files:**
- Modify: `pi-skills/optional/camofox-stealth/RATIONALE.md`
- Modify: `scripts/uninstall.py`
- Modify: `README.md`
- Modify: `docs/KNOWN_ISSUES.md`
- Test: `tests/test_stealth_recon.py`

**Interfaces:**
- Consumes: 全部前置 Task 的成品。
- Produces: 文檔一致性 + uninstall 對使用者資料的說明。

- [ ] **Step 1: 寫失敗測試**

在 `tests/test_stealth_recon.py` 追加：

```python
class TestDocs(unittest.TestCase):
    def test_readme_lists_stealth_recon(self):
        c = read_file("README.md")
        self.assertIn("camofox", c.lower())
        self.assertIn("stealth", c.lower())

    def test_rationale_mentions_pin_and_update(self):
        c = read_file("pi-skills/optional/camofox-stealth/RATIONALE.md")
        self.assertIn("1.11.2", c)
        self.assertTrue("釘版" in c or "更新" in c)

    def test_uninstall_notes_user_data(self):
        c = read_file("scripts/uninstall.py")
        self.assertIn(".camofox", c)
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `C:/Users/User/AppData/Local/Python/bin/python.exe -m unittest tests.test_stealth_recon.TestDocs -v`
Expected: FAIL

- [ ] **Step 3a: 更新 RATIONALE.md**

在 `pi-skills/optional/camofox-stealth/RATIONALE.md` 末尾（`---` 分隔線之前）加入：

```markdown
## 5. 升級與釘版 (2026-07-08)
*   **釘版**：後端釘 `@askjo/camofox-browser@1.11.2`（記於 `pi-config/harness-config.json`），skill 對準此版 `/tabs`+snapshot API，杜絕 `npx latest` 移動標的與既有 `3001`/`/navigate` 漂移。
*   **更新流**：後端升級＝改 `harness-config.json` 版本後重跑 `setup.py`；harness 其餘更新照 `git pull` → `setup.py --mode restore` → `pi update` 單一路徑。
*   **生命週期**：`recon.sh` detached 啟動 + pidfile + health-check，解決 Windows/Git Bash 短命 tool-call 背景進程問題。
```

- [ ] **Step 3b: uninstall.py 加註解**

在 `scripts/uninstall.py` 的 `clean_settings()` 定義前（或 `MANAGED_SKILLS` 定義後）加入註解說明：

```python
# Note: the stealth-recon backend stores logged-in browser profiles and cookies
# under ~/.camofox/ (session secrets). This is user data outside the harness —
# it is intentionally NOT removed here; delete it manually if desired.
```

- [ ] **Step 3c: README 整合表加一列**

在 `README.md` 的「整合外部倉庫」表格（`| **記憶進化** | [claude-reflect]...` 那列之後）加入：

```markdown
| **隱身偵察** | [camofox-browser](https://github.com/jo-inc/camofox-browser) | Thin Bridge (橋接) | 動工前網路偵察（隱身讀頁/搜尋/登入） | ❌ | ⚠️ |
```

- [ ] **Step 3d: KNOWN_ISSUES 補一節**

在 `docs/KNOWN_ISSUES.md` 末尾加入：

```markdown
## 4. stealth-recon 後端需自架

`camofox-stealth` 技能需要本地跑 `@askjo/camofox-browser@1.11.2`（首次下載 Camoufox ~300MB 到 `~/.camofox`，不含在 repo）。安裝時可選預抓，或執行 pi 時由技能懶啟動。最硬的 Akamai/Datadome 頂層可能仍需 residential proxy（本技能預設不掛 proxy，不在支援範圍）。
```

- [ ] **Step 4: 跑測試確認通過**

Run: `C:/Users/User/AppData/Local/Python/bin/python.exe -m unittest tests.test_stealth_recon.TestDocs -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pi-skills/optional/camofox-stealth/RATIONALE.md scripts/uninstall.py README.md docs/KNOWN_ISSUES.md tests/test_stealth_recon.py
git commit -m "docs(stealth-recon): rationale pin/update, uninstall note, README row, known-issue"
```

---

### Task 7: 全套驗證與收尾

**Files:**
- Test: `tests/` 全部

- [ ] **Step 1: 全套測試**

Run: `C:/Users/User/AppData/Local/Python/bin/python.exe -m unittest discover -s tests -v`
Expected: 全綠（含既有 test_setup / test_restore / test_onboarding 與新 test_stealth_recon）

- [ ] **Step 2: 語法與 lint**

Run:
```bash
C:/Users/User/AppData/Local/Python/bin/python.exe -m py_compile scripts/setup.py scripts/restore.py scripts/uninstall.py
sh -n pi-skills/optional/camofox-stealth/recon.sh
```
Expected: 皆無輸出/exit 0

- [ ] **Step 3: 非互動 restore 冒煙（不觸發下載）**

Run: `C:/Users/User/AppData/Local/Python/bin/python.exe scripts/restore.py --auto --profile standard`（可對沙盒 HOME）
Expected: 完成；`camofox-stealth` 與 `recon.sh` 出現在 `~/.pi/agent/skills/camofox-stealth/`；不觸發 300MB 下載。

- [ ] **Step 4: 平台無關與 port 檢查**

Run: `grep -rn ":8080\|D:/MyProject\|Myproject\|file:///" pi-skills/optional/camofox-stealth pi-rules/stealth-recon.md`
Expected: 無命中。

- [ ] **Step 5: 收尾**

Announce: 使用 superpowers:finishing-a-development-branch 完成分支（驗證測試、呈現合併/PR 選項）。

---

## Self-Review

**1. Spec coverage：**
- 升級既有 skill（非新增）→ Task 3。
- 修 API 漂移（3001/navigate → /tabs+snapshot）→ Task 3（含反向斷言）。
- 釘版 + harness-config → Task 1；skill/recon 對準 → Task 2、3。
- 併入更新流 → Task 5（setup 讀釘版）+ Task 6（RATIONALE 更新流文檔）。
- Port 9377、禁 8080 → Task 2、3（斷言 `not :8080`）、Task 7 grep。
- detached + pidfile 生命週期 → Task 2。
- VNC 登入交接 → Task 3 第 3 節。
- 擋頁偵測 + 誠實回報 → Task 2（`is_blocked`）、Task 3 第 4 節。
- findings.md 整合 + 有界觸發 → Task 4。
- setup 可選、非互動安全預抓 → Task 5。
- uninstall 使用者資料註記 → Task 6。
- README 列 + KNOWN_ISSUES → Task 6。
- authorized-use 聲明 → Task 3（SKILL.md 開頭 blockquote）。
- 零依賴測試 → 每個 Task 的 unittest。
- 覆寫：所有 spec 檔案清單項目均有對應 Task。無缺口。

**2. Placeholder scan：** 無 TBD/TODO；版本 `1.11.2` 為具體值；所有程式步驟均附完整內容。

**3. Type consistency：** `recon.sh` 子命令 `ensure`/`is_blocked`/`health`/`stop` 在 Task 2 定義、Task 3 SKILL.md 一致引用；`STEALTH_RECON_URL`/`9377`/`camofoxBrowserVersion`/`@askjo/camofox-browser@1.11.2` 全計畫一致；`ask()`/`run_stream()`/`load_json`/`HARNESS_CONFIG_PATH` 均為 setup.py 既有符號。
