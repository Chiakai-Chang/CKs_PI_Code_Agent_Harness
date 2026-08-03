#!/usr/bin/env bash
# End-to-end proof that a background job wakes the agent.
#
# Requires a model server reachable at the configured apiBase.
#
# Two things this script has already got wrong once, both preserved as comments
# rather than as scar tissue in someone else's afternoon:
#
#  1. rpc mode does NOT take a positional prompt. The prompt is a JSON command
#     on stdin ({"type":"prompt","message":"..."}). Passing it as an argument
#     starts a session that never runs a turn, and every counter reads zero.
#  2. `grep -c` prints 0 AND exits 1 when there is no match, so `$(grep -c ... ||
#     echo 0)` yields the two-line string "0\n0", `[ "$x" -lt 2 ]` dies with
#     "integer expected", and the failed test falls through to PASS. Use
#     `|| true`. A check that cannot fail is worse than no check.
#
# rpc mode exits the moment stdin hits EOF, so stdin is held open deliberately —
# an earlier spike read a dead process as "the timer never fired".
set -u

HOLD="${E2E_HOLD_SECONDS:-180}"
LOGDIR="$(mktemp -d)"
LOG="$LOGDIR/e2e.rpc"
BRIDGE="pi-extensions/async-exec-bridge/index.ts"

PROMPT='Call the bg_start tool with cmd "sleep 20; echo DONE" and label "e2e". After it returns, stop: issue no further tool calls and end your turn.'

> "$LOG"
started=$(date +%s)

# Hold stdin for HOLD seconds, but stop as soon as the resumed turn has landed:
# the run length would otherwise be pinned by the hold, which makes the wall
# clock a measure of this script rather than of the wake path.
{
  printf '{"id":"e2e-1","type":"prompt","message":%s}\n' "$(printf '%s' "$PROMPT" | python -c 'import json,sys; print(json.dumps(sys.stdin.read()))')"
  for _ in $(seq 1 $((HOLD * 2))); do
    if [ -f "$LOGDIR/woke_at" ] && [ "$(grep -c '"type":"turn_end"' "$LOG" || true)" -ge 3 ]; then
      break
    fi
    sleep 0.5
  done
} | timeout $((HOLD + 60)) pi --mode rpc --no-session -e "$BRIDGE" >> "$LOG" 2>&1 &
pipeline=$!

# Record when the envelope actually reached the agent. That instant, minus the
# start, is the dispatch-to-resume figure the plan wants as a regression guard.
(
  while kill -0 $pipeline 2>/dev/null; do
    if grep -q '"customType":"async-exec"' "$LOG" 2>/dev/null; then
      date +%s > "$LOGDIR/woke_at"
      break
    fi
    sleep 0.5
  done
) &
watcher=$!

wait $pipeline
ended=$(date +%s)
kill $watcher 2>/dev/null || true

echo "log: $LOG"

lines=$(wc -l < "$LOG" | tr -d ' ')
turns=$(grep -c '"type":"turn_end"' "$LOG" || true)
dispatched=$(grep -c 'bg_start' "$LOG" || true)
woke=$(grep -c 'async-exec' "$LOG" || true)
total=$((ended - started))
echo "log_lines=$lines  turn_end=$turns  bg_start_mentions=$dispatched  async-exec_mentions=$woke  total=${total}s"

fail() { echo "FAIL: $1"; echo "      inspect $LOG"; exit 1; }

# Prove the instrument saw anything at all before trusting any count of zero.
[ "$lines" -gt 0 ] || fail "the rpc log is empty — pi produced no output, so nothing was measured"
[ "$dispatched" -gt 0 ] || fail "the model never called bg_start, so the wake path was never exercised"
[ "$turns" -ge 2 ] || fail "expected at least 2 turn_end (dispatch turn + resumed turn), got $turns"
[ "$woke" -ge 1 ] || fail "no async-exec envelope reached the agent"

if [ -f "$LOGDIR/woke_at" ]; then
  resume=$(( $(cat "$LOGDIR/woke_at") - started ))
  echo "PASS  (dispatch-to-resume: ${resume}s, of which the job itself is 20s; total run ${total}s)"
else
  fail "the envelope was counted but its arrival was never timestamped — the baseline would be a guess"
fi
