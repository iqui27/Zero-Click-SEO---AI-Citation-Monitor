#!/usr/bin/env bash
# Simple wrapper to run smoke tests with CI-friendly logs and exit codes.
# Usage:
#   scripts/smoke.sh
# Optional env vars:
#   BASE_URL, HEALTH_PATH, START_PATH, START_METHOD, START_BODY,
#   STREAM_PATH_TEMPLATE, AUTH_BEARER, EXTRA_HEADERS, TIMEOUT_SECS, STREAM_TIMEOUT_SECS

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 "$SCRIPT_DIR/smoke_test.py"
EXIT_CODE=$?

case "$EXIT_CODE" in
  0) echo "[CI] Smoke tests passed";;
  2) echo "[CI] Failure: homepage check";;
  3) echo "[CI] Failure: health check";;
  4) echo "[CI] Failure: start job";;
  5) echo "[CI] Failure: stream/polling";;
  6) echo "[CI] Failure: unexpected error";;
  *) echo "[CI] Failure: unknown exit code $EXIT_CODE";;

esac

exit "$EXIT_CODE"

