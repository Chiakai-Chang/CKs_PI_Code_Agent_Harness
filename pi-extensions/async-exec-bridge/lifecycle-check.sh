#!/usr/bin/env bash
# Proves a background job survives session replacement.
#
# /new, /resume, /fork and /clone all fire session_shutdown -> session_start.
# Session replacement is the normal case, not an edge case: the ctx and pi
# objects captured when the job was dispatched belong to the OLD session and
# throw once it is gone. The bridge handles this by setting a dead flag,
# clearing its timers, and letting the NEW session's session_start pick the job
# back up off disk.
#
# That is the claim. This checks it against a live pi, because the failure mode
# it guards against - a detached timer firing into a dead session - produces an
# unhandled rejection that no unit test would ever see.
#
# Runs against the INSTALLED copy with no -e flag, for the same reason
# e2e-check.sh does: passing -e while the installed copy is auto-discovered
# registers the tools twice and pi refuses to start.
set -u

HOLD="${LIFECYCLE_HOLD_SECONDS:-180}"
LOGDIR="$(mktemp -d)"
LOG="$LOGDIR/lifecycle.rpc"

# Skips (exit 0) when pi, the installed bridge or a model server is missing, so
# CI can carry this check and still run it wherever a model exists. Set
# ASYNC_EXEC_REQUIRE_LIVE=1 to turn every skip into a failure.
# shellcheck source=pi-extensions/async-exec-bridge/live-preflight.sh
. "$(dirname "$0")/live-preflight.sh"
live_preflight

RUNDIR=".pi/async-exec"
DISPATCH='Call the bg_start tool with cmd "sleep 25; echo SURVIVED" and label "lifecycle". After it returns, stop: issue no further tool calls and end your turn.'
AFTER='In one short sentence, state whether any background job result was reported to you.'

json() { printf '%s' "$1" | python -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

> "$LOG"
started=$(date +%s)
{
  printf '{"id":"l-1","type":"prompt","message":%s}\n' "$(json "$DISPATCH")"

  # Wait for the job to actually be running before replacing the session -
  # replacing it before dispatch would test nothing.
  for _ in $(seq 1 120); do
    if ls "$RUNDIR"/job-*.json >/dev/null 2>&1; then break; fi
    sleep 0.5
  done
  sleep 3

  # The event under test.
  printf '{"id":"l-2","type":"new_session"}\n'

  # Let the job finish inside the REPLACEMENT session, then take a turn so the
  # before_agent_start injection has somewhere to land.
  sleep 35
  printf '{"id":"l-3","type":"prompt","message":%s}\n' "$(json "$AFTER")"

  for _ in $(seq 1 $((HOLD * 2))); do
    if [ "$(grep -c '"id":"l-3"' "$LOG" || true)" -ge 1 ] &&
       [ "$(grep -c '"type":"turn_end"' "$LOG" || true)" -ge 3 ]; then
      break
    fi
    sleep 0.5
  done
} | timeout $((HOLD + 60)) pi --mode rpc --no-session >> "$LOG" 2>&1
ended=$(date +%s)

echo "log: $LOG"

fail() { echo "FAIL: $1"; echo "      inspect $LOG"; exit 1; }

lines=$(wc -l < "$LOG" | tr -d ' ')
switched=$(grep -c '"command":"new_session","success":true' "$LOG" || true)
crashes=$(grep -ciE 'unhandled|UnhandledPromiseRejection|Cannot read properties of (null|undefined)' "$LOG" || true)
echo "log_lines=$lines  session_replaced=$switched  crash_markers=$crashes  wall=$((ended - started))s"

[ "$lines" -gt 0 ] || fail "the rpc log is empty — nothing was measured"
[ "$switched" -ge 1 ] || fail "the session was never replaced, so the thing under test never happened"

# The job must have completed and been recorded, by the replacement session.
record=$(ls "$RUNDIR"/job-*.json 2>/dev/null | head -1)
[ -n "$record" ] || fail "no job record on disk"
state=$(python -c "import json,sys;print(json.load(open(sys.argv[1]))['state'])" "$record")
code=$(python -c "import json,sys;print(json.load(open(sys.argv[1]))['exitCode'])" "$record")
echo "job state=$state exit=$code"
[ "$state" = "done" ] || fail "job ended as '$state', expected 'done' — it did not survive the switch"
[ "$code" = "0" ] || fail "job exit code was $code, expected 0"

# A timer firing into a replaced session is the specific failure this guards.
[ "$crashes" -eq 0 ] || fail "$crashes crash marker(s) in the log — a handler fired into the dead session"

echo "PASS  (job survived session replacement; ${ended}s-${started}s = $((ended - started))s)"
