#!/usr/bin/env bash
# End-to-end proof that a background job wakes the agent.
#
# Requires a model server reachable at the configured apiBase. rpc mode exits
# the moment stdin hits EOF, so stdin is held open deliberately — an earlier
# spike read a dead process as "the timer never fired".
set -u
LOG="$(mktemp -d)/e2e.log"
export SPIKE_LOG="$LOG"

timeout 300 bash -c 'sleep 260 | pi --mode rpc --no-session \
  -e "pi-extensions/async-exec-bridge/index.ts" \
  "Use bg_start to run: sleep 20; echo DONE. Then PARK."' > "$LOG.rpc" 2>&1

turns=$(grep -oc '"type":"turn_end"' "$LOG.rpc" || echo 0)
woke=$(grep -c "async-exec" "$LOG.rpc" || echo 0)
echo "turn_end=$turns  async-exec messages=$woke"

# A check that only prints is a check that never fails.
if [ "$turns" -lt 2 ]; then
  echo "FAIL: expected at least 2 turn_end (dispatch turn + resumed turn), got $turns"
  exit 1
fi
if [ "$woke" -lt 1 ]; then
  echo "FAIL: no async-exec envelope reached the agent"
  exit 1
fi
echo "PASS"
