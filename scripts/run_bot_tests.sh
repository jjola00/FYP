#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${ROOT}/venv"
PY="${VENV}/bin/python"
UVICORN="${VENV}/bin/uvicorn"
BASE_URL="${BASE_URL:-http://localhost:8000}"
ATTEMPTS="${ATTEMPTS:-20}"
MAX_MS="${MAX_MS:-5500}"

LOG_DIR="${LOG_DIR:-${ROOT}/logs/bot-tests/$(date +%Y%m%d_%H%M%S)}"
mkdir -p "${LOG_DIR}"

STARTED_BACKEND=0

health_check() {
  "${PY}" - <<PY
import json
import urllib.request

try:
    with urllib.request.urlopen("${BASE_URL}/health", timeout=2) as resp:
        json.load(resp)
    raise SystemExit(0)
except Exception:
    raise SystemExit(1)
PY
}

start_backend() {
  echo "[run_bot_tests] Starting backend..."
  "${UVICORN}" backend.main:app --port 8000 --log-level warning >"${LOG_DIR}/backend.log" 2>&1 &
  STARTED_BACKEND=1
  BACKEND_PID=$!
  for _ in $(seq 1 20); do
    if health_check; then
      return 0
    fi
    sleep 0.5
  done
  echo "[run_bot_tests] Backend failed to start; see ${LOG_DIR}/backend.log"
  kill "${BACKEND_PID}" >/dev/null 2>&1 || true
  return 1
}

cleanup() {
  if [[ "${STARTED_BACKEND}" == "1" ]]; then
    kill "${BACKEND_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

if [[ ! -x "${PY}" ]]; then
  echo "[run_bot_tests] Missing venv at ${VENV}. Run setup first."
  exit 1
fi
if [[ ! -x "${UVICORN}" ]]; then
  echo "[run_bot_tests] uvicorn not found in venv. Install backend requirements."
  exit 1
fi
if [[ ! -f "${ROOT}/scripts/bot_sim.py" ]]; then
  echo "[run_bot_tests] Missing scripts/bot_sim.py."
  exit 1
fi

if [[ "${SKIP_BACKEND_START:-0}" != "1" ]]; then
  if ! health_check; then
    start_backend
  fi
fi

RESULTS="${LOG_DIR}/results.txt"
{
  echo "Bot test run: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo "Base URL: ${BASE_URL}"
  echo "Attempts per variant: ${ATTEMPTS}"
  echo "Max duration per attempt: ${MAX_MS}ms"
  echo ""
} > "${RESULTS}"

run_variant() {
  local name="$1"
  shift
  {
    echo "## ${name}"
    "${PY}" "${ROOT}/scripts/bot_sim.py" --base-url "${BASE_URL}" --attempts "${ATTEMPTS}" --max-ms "${MAX_MS}" --peek-interval-ms 120 "$@"
    echo ""
  } | tee -a "${RESULTS}"
}

run_variant "baseline" --step-px 5 --step-ms 16 --advance-px 40 --jitter-px 0
run_variant "jitter_1_5" --step-px 5 --step-ms 16 --advance-px 40 --jitter-px 1.5
run_variant "slow_step_24" --step-px 5 --step-ms 24 --advance-px 40 --jitter-px 0
run_variant "curvature_aware_slow" \
  --step-px 5 \
  --step-ms 24 \
  --advance-px 40 \
  --jitter-px 0 \
  --step-ms-jitter 0.04 \
  --curvature-aware \
  --curvature-slow-factor 1.0 \
  --curvature-ms-jitter 0.35
run_variant "touch_jitter_1_5" --pointer-type touch --step-px 5 --step-ms 16 --advance-px 40 --jitter-px 1.5

"${PY}" "${ROOT}/scripts/summary_attempts.py" --limit 200 > "${LOG_DIR}/attempt_summary.txt"

echo "[run_bot_tests] Results saved to ${LOG_DIR}"
