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
  # Derive the bind port from STEALTH_RECON_URL so a user override actually
  # binds the server where health() will poll it. NOVNC_PORT is pinned per spec.
  RECON_PORT=$(printf '%s' "$STEALTH_RECON_URL" | sed -n 's|.*:\([0-9][0-9]*\).*|\1|p')
  [ -n "$RECON_PORT" ] || RECON_PORT=9377
  ENABLE_VNC=1 CAMOFOX_PORT="$RECON_PORT" NOVNC_PORT=6080 nohup $START_CMD >"$LOGFILE" 2>&1 &
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
