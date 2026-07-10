#!/usr/bin/env sh
# CK's Pi Code Agent Harness - stealth-recon backend helper
# Drives a pinned Camoufox browser server (@askjo/camofox-browser@1.11.2)
# via curl. POSIX sh; runs under Git Bash on Windows.

STEALTH_RECON_URL="${STEALTH_RECON_URL:-http://127.0.0.1:9377}"
CAMOFOX_HOME="${CAMOFOX_HOME:-$HOME/.camofox}"
PIDFILE="$CAMOFOX_HOME/recon.pid"
LOGFILE="$CAMOFOX_HOME/recon.log"
# Wrapper is pinned to @askjo/camofox-browser@1.11.2, but its playwright-core
# range (^1.58.0) floats up to 1.61+, whose Browser.setDefaultViewport sends a
# viewport.isMobile field the bundled Camoufox juggler rejects — that breaks
# every tab create. We install into a local prefix with an npm override forcing
# playwright-core to the camoufox-js-tested 1.53.x, so the engine stays
# compatible regardless of what floats to latest upstream. (Replaces bare
# `npx -y`, which always grabbed the broken latest.)
CAMOFOX_PKG="@askjo/camofox-browser@1.11.2"
PINNED_PLAYWRIGHT="1.53.1"
SERVER_DIR="$CAMOFOX_HOME/pinned-server"
SERVER_JS="$SERVER_DIR/node_modules/@askjo/camofox-browser/server.js"
START_TIMEOUT="${STEALTH_RECON_TIMEOUT:-40}"

log() { printf '[recon] %s\n' "$*" >&2; }

health() {
  curl -sf "$STEALTH_RECON_URL/health" >/dev/null 2>&1
}

# install_server: create the pinned local install if the server entry is absent.
# Idempotent — skips entirely once node_modules is in place.
install_server() {
  [ -f "$SERVER_JS" ] && return 0
  log "安裝釘版隱身伺服器 ($CAMOFOX_PKG, playwright-core $PINNED_PLAYWRIGHT)…"
  mkdir -p "$SERVER_DIR" || return 1
  cat > "$SERVER_DIR/package.json" <<EOF
{
  "name": "camofox-pinned",
  "private": true,
  "dependencies": { "$(printf '%s' "$CAMOFOX_PKG" | sed 's/@[^@]*$//')": "$(printf '%s' "$CAMOFOX_PKG" | sed 's/.*@//')" },
  "overrides": { "playwright-core": "$PINNED_PLAYWRIGHT" }
}
EOF
  ( cd "$SERVER_DIR" && npm install --no-audit --no-fund --foreground-scripts >>"$LOGFILE" 2>&1 ) || {
    log "npm install 失敗，見 $LOGFILE"; return 1;
  }
  # better-sqlite3 ships a native addon; ensure it built even if npm gated scripts.
  ( cd "$SERVER_DIR" && npm rebuild better-sqlite3 >>"$LOGFILE" 2>&1 ) || true
  [ -f "$SERVER_JS" ]
}

ensure() {
  if health; then
    log "server already up at $STEALTH_RECON_URL"
    return 0
  fi
  mkdir -p "$CAMOFOX_HOME"
  # First run auto-installs the engine (npm fetches the pinned package; camofox
  # then downloads Camoufox ~300MB). That can exceed the normal wait, so we
  # announce it and use a longer timeout the first time only.
  INIT_MARKER="$CAMOFOX_HOME/.recon-initialized"
  wait_timeout="$START_TIMEOUT"
  if [ ! -f "$INIT_MARKER" ]; then
    log "首次啟動：正在自動下載並安裝隱身瀏覽器引擎 Camoufox (~300MB, 一次性)，約需數分鐘，請稍候…"
    wait_timeout="${STEALTH_RECON_FIRST_RUN_TIMEOUT:-600}"
  fi
  install_server || { log "server install failed; see $LOGFILE"; return 1; }
  log "starting stealth server (detached): node server.js (pinned)"
  # Detach so the server survives this tool-call shell. ENABLE_VNC lets the
  # user log in visually at http://localhost:6080 when a site needs auth.
  # Derive the bind port from STEALTH_RECON_URL so a user override actually
  # binds the server where health() will poll it. NOVNC_PORT is pinned per spec.
  RECON_PORT=$(printf '%s' "$STEALTH_RECON_URL" | sed -n 's|.*:\([0-9][0-9]*\).*|\1|p')
  [ -n "$RECON_PORT" ] || RECON_PORT=9377
  ENABLE_VNC=1 CAMOFOX_PORT="$RECON_PORT" NOVNC_PORT=6080 nohup node "$SERVER_JS" >"$LOGFILE" 2>&1 &
  echo "$!" > "$PIDFILE"
  i=0
  while [ "$i" -lt "$wait_timeout" ]; do
    if health; then
      : > "$INIT_MARKER"
      log "server ready after ${i}s"
      return 0
    fi
    i=$((i + 1))
    sleep 1
  done
  log "server did NOT become ready in ${wait_timeout}s; see $LOGFILE"
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
