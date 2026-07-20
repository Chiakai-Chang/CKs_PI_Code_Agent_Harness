#!/usr/bin/env sh
# CK's Pi Code Agent Harness - camofox-browser server.js fixes for Linux
#
# Patches the pinned-server install (~/.camofox/pinned-server) with fixes for
# bugs in @askjo/camofox-browser's Firefox Juggler compatibility and Linux
# startup path. Idempotent: each fix checks its own fixed state before applying.
#
# Run after `recon.sh install` (which populates the pinned-server install).
# Callers: setup.py maybe_heal_linux_stealth(), manual `sh camofox-server-fixes.sh`.
#
# Root cause details: docs/retro/2026-07-20-camofox-linux-root-cause-fix.md

set -e

CAMOFOX_HOME="${CAMOFOX_HOME:-$HOME/.camofox}"
SERVER_JS="$CAMOFOX_HOME/pinned-server/node_modules/@askjo/camofox-browser/server.js"
PATCH_MARKER="# patched by harness camofox-server-fixes.sh (see docs/retro/2026-07-20-camofox-linux-root-cause-fix.md)"
PATCHED=0

need_server_js() {
  if [ ! -f "$SERVER_JS" ]; then
    echo "[-] server.js 未找到 ($SERVER_JS)，先執行 recon.sh install。" >&2
    return 1
  fi
  return 0
}

apply_fix() {
  local desc="$1"
  # $2 = sed substitution expression
  # $3 = fixed-state grep pattern (fixed-string, matched with grep -qF)
  local substitution="$2"
  local fixed_marker="$3"

  need_server_js || return 1

  if grep -qF "$fixed_marker" "$SERVER_JS" 2>/dev/null; then
    echo "[✓] $desc 已修復，跳過" >&2
    return 0
  fi

  sed -i "$substitution" "$SERVER_JS"
  PATCHED=$((PATCHED + 1))
  echo "[*] 修復: $desc" >&2
  echo "$PATCH_MARKER" >> "$SERVER_JS"
  return 0
}

main() {
  echo "[*] 檢查 camofox-browser server.js 修復狀態 ($SERVER_JS)..." >&2

  if ! need_server_js; then
    return 1
  fi

  # Fix 1: async bug — VirtualDisplay.get() is async, missing await.
  # The un-awited Promise object becomes DISPLAY, so Firefox dies with
  # "cannot open display: [object Promise]" while Xvfb is actually running.
  apply_fix \
    "虛擬顯示 await 缺失（[object Promise] 當 DISPLAY，Firefox cannot open display）" \
    "s|vdDisplay = localVirtualDisplay.get();|vdDisplay = await localVirtualDisplay.get();|" \
    "vdDisplay = await localVirtualDisplay.get();"

  # Fix 2: browser launch retry = 1 → 3 (more resilience on Linux where
  # xvfb/sandbox failures cascade).
  apply_fix \
    "瀏覽器啟動 retry 從 1 次改為 3 次" \
    "s|const maxAttempts = proxyPool?.launchRetries ?? 1;|const maxAttempts = proxyPool?.launchRetries ?? 3;|" \
    "const maxAttempts = proxyPool?.launchRetries ?? 3;"

  # Fix 3: Firefox sandbox vs AppArmor — pass firefox_user_prefs to disable
  # user-namespace sandbox (EPERM under AppArmor unprivileged_userns profile).
  apply_fix \
    "launchOptions 加入 firefox_user_prefs 關閉 Firefox sandbox（AppArmor EPERM）" \
    "s|virtual_display: vdDisplay,$|virtual_display: vdDisplay,\n        firefox_user_prefs: { \"browser.sandbox.level\": 0 },|" \
    "firefox_user_prefs:"

  # Fix 4a/b: Playwright viewport schema vs Firefox Juggler protocol — Firefox
  # rejects newContext({ viewport: { isMobile, deviceScaleFactor } }). Pass null.
  # Fix 4b MUST run before 4a: 4a's fix introduces "viewport: null" into the
  # file, and 4b's fixed-marker check would then incorrectly skip.
  apply_fix \
    "probeGoogleSearch 的 newContext 加入 viewport: null（Firefox Juggler 不接受 Playwright viewport schema）" \
    "s|context = await candidateBrowser.newContext({$|context = await candidateBrowser.newContext({ viewport: null,|" \
    "context = await candidateBrowser.newContext({ viewport: null,"

  apply_fix \
    "getSession 的 newContext 加入 viewport: null（同上 Juggler 協議差異）" \
    "s|const context = await b.newContext(contextOptions);|const context = await b.newContext({ ...contextOptions, viewport: null });|" \
    "contextOptions, viewport: null"

  # Fix 5a/b: page.setViewportSize() sends screenSize the Juggler protocol
  # rejects. These call sites exist in some camofox-browser versions (the
  # tab-create/retry paths) and not in others; the sed is a no-op on versions
  # without them, and the fixed-marker check catches the comment left when
  # this script previously patched the endpoint variant.
  apply_fix \
    "移除 tab 創建的 page.setViewportSize()（Firefox Juggler 不接受 screenSize 參數）" \
    "s|await page.setViewportSize({ width: 1280, height: 720 });||" \
    "Firefox Juggler does not support Page.setViewportSize"

  apply_fix \
    "移除 retryPage.setViewportSize()" \
    "s|await retryPage.setViewportSize({ width: 1280, height: 720 });||" \
    "Firefox Juggler does not support Page.setViewportSize"

  # Fix 6: the viewport API endpoint's setViewportSize call — leave the
  # endpoint alive but neutralize the unsupported call with a comment.
  apply_fix \
    "註解 viewport API 端點的 setViewportSize 調用" \
    "s|await tabState.page.setViewportSize({ width: Math.round(width), height: Math.round(height) });|// Firefox Juggler does not support Page.setViewportSize with screenSize; viewport resizing unavailable on Firefox|" \
    "Firefox Juggler does not support Page.setViewportSize"

  if grep -qF "$PATCH_MARKER" "$SERVER_JS" 2>/dev/null; then
    echo "[✓] server.js 修復完成（已標記 patched marker）" >&2
  else
    echo "[*] 所有修復檢查完成（無 patch 標記，可能上游已修復或版本不同）" >&2
  fi
  return 0
}

main "$@"
