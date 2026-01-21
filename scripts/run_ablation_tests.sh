#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${ROOT}"
cd "${ROOT}"
VENV="${ROOT}/venv"
PY="${VENV}/bin/python"

ATTEMPTS="${ATTEMPTS:-200}"
MAX_MS="${MAX_MS:-5500}"
BASE_PORT="${BASE_PORT:-8100}"

TOP_LOG_DIR="${ROOT}/logs/ablations/$(date +%Y%m%d_%H%M%S)"
mkdir -p "${TOP_LOG_DIR}"

if [[ ! -x "${PY}" ]]; then
  echo "[run_ablation_tests] Missing venv tools. Activate venv and install requirements."
  exit 1
fi

health_check() {
  local url="$1"
  "${PY}" - <<PY
import json
import urllib.request

try:
    with urllib.request.urlopen("${url}/health", timeout=2) as resp:
        json.load(resp)
    raise SystemExit(0)
except Exception:
    raise SystemExit(1)
PY
}

start_backend() {
  local port="$1"
  shift
  local log_file="$1"
  shift
  ("$@" "${PY}" -m uvicorn backend.main:app --port "${port}" --log-level warning >"${log_file}" 2>&1) &
  echo $!
}

wait_for_backend() {
  local url="$1"
  for _ in $(seq 1 20); do
    if health_check "${url}"; then
      return 0
    fi
    sleep 0.5
  done
  return 1
}

run_variant() {
  local name="$1"
  local port="$2"
  shift 2
  local variant_dir="${TOP_LOG_DIR}/${name}"
  mkdir -p "${variant_dir}"
  local backend_log="${variant_dir}/backend.log"
  local url="http://localhost:${port}"

  echo "[run_ablation_tests] ${name} -> ${url}"
  local pid
  pid=$(start_backend "${port}" "${backend_log}" "$@")
  if ! wait_for_backend "${url}"; then
    echo "[run_ablation_tests] Backend failed for ${name}. See ${backend_log}"
    kill "${pid}" >/dev/null 2>&1 || true
    return 1
  fi

  BASE_URL="${url}" \
  SKIP_BACKEND_START=1 \
  ATTEMPTS="${ATTEMPTS}" \
  MAX_MS="${MAX_MS}" \
  LOG_DIR="${variant_dir}" \
  bash "${ROOT}/scripts/run_bot_tests.sh"

  kill "${pid}" >/dev/null 2>&1 || true
}

idx=0
run_variant "hardened" $((BASE_PORT + idx)) env
idx=$((idx + 1))
run_variant "no_peek_state" $((BASE_PORT + idx)) env ENFORCE_PEEK_STATE=0
idx=$((idx + 1))
run_variant "no_peek_rate" $((BASE_PORT + idx)) env ENFORCE_PEEK_RATE=0
idx=$((idx + 1))
run_variant "no_peek_distance" $((BASE_PORT + idx)) env ENFORCE_PEEK_DISTANCE=0
idx=$((idx + 1))
run_variant "no_peek_budget" $((BASE_PORT + idx)) env ENFORCE_PEEK_BUDGET=0
idx=$((idx + 1))
run_variant "no_monotonic" $((BASE_PORT + idx)) env ENFORCE_MONOTONIC_PATH=0
idx=$((idx + 1))
run_variant "no_speed_limits" $((BASE_PORT + idx)) env ENFORCE_SPEED_LIMITS=0
idx=$((idx + 1))
run_variant "no_min_duration" $((BASE_PORT + idx)) env ENFORCE_MIN_DURATION=0
idx=$((idx + 1))
run_variant "no_regularity" $((BASE_PORT + idx)) env ENFORCE_REGULARITY=0
idx=$((idx + 1))
run_variant "no_curvature_adaptation" $((BASE_PORT + idx)) env ENFORCE_CURVATURE_ADAPTATION=0
idx=$((idx + 1))
run_variant "no_behavioural" $((BASE_PORT + idx)) env ENFORCE_BEHAVIOURAL=0

echo "[run_ablation_tests] Results saved to ${TOP_LOG_DIR}"
