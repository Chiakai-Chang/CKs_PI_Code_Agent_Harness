#!/usr/bin/env bash
# Shared preflight for the two checks that need a live agent (e2e-check.sh,
# lifecycle-check.sh). Sourced, not executed.
#
# These cannot run without pi, an installed bridge and a reachable model server,
# and none of those exist on a hosted CI runner. They therefore SKIP rather than
# fail, so CI can carry them and still run them wherever a model is present.
#
# A check that always skips is worth nothing, so the skip is made honest in two
# ways: it always says which precondition was missing, and
# ASYNC_EXEC_REQUIRE_LIVE=1 turns every skip into a failure — which is what a
# developer who meant to test locally should set, and what a self-hosted runner
# with a model should set.

live_api_base() {
  if [ -n "${ASYNC_EXEC_API_BASE:-}" ]; then
    printf '%s' "$ASYNC_EXEC_API_BASE"
    return
  fi
  python - <<'PY' 2>/dev/null || printf 'http://127.0.0.1:8080'
import json
import os

path = os.path.join(os.path.expanduser("~"), ".pi", "agent", "settings.json")
try:
    with open(path, encoding="utf-8") as handle:
        print(json.load(handle).get("apiBase") or "http://127.0.0.1:8080")
except Exception:
    print("http://127.0.0.1:8080")
PY
}

live_skip() {
  if [ "${ASYNC_EXEC_REQUIRE_LIVE:-0}" = "1" ]; then
    echo "FAIL: $1"
    echo "      (ASYNC_EXEC_REQUIRE_LIVE=1 is set, so skipping is not allowed)"
    exit 1
  fi
  echo "SKIP: $1"
  exit 0
}

# Exits 0 with a SKIP line unless everything this check needs is present.
live_preflight() {
  command -v pi >/dev/null 2>&1 || live_skip "pi is not on PATH"

  installed="$HOME/.pi/agent/extensions/async-exec-bridge/index.ts"
  [ -f "$installed" ] || live_skip "the bridge is not installed at $installed (run: python scripts/setup.py --mode restore)"

  base="$(live_api_base)"
  curl -s -m 5 -o /dev/null "$base/v1/models" 2>/dev/null ||
    live_skip "no model server reachable at $base"
}
