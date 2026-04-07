#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${BASH_SOURCE:-}" ]]; then
  SCRIPT_PATH="${BASH_SOURCE[0]}"
else
  SCRIPT_PATH="$0"
fi

SCRIPT_DIR="$(cd "$(dirname "${SCRIPT_PATH}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

HOST="127.0.0.1"
PORT="8765"
DB_PATH="database/nimble.sqlite"
MIGRATION_PATH="database/migrations/0001_canonical_schema_freeze.sql"
PYTHON_BIN="${PYTHON_BIN:-python3}"
RESTART_MODE="true"

usage() {
  cat <<'EOF'
Start the character class management spike app.

Usage:
  scripts/start-class-management-app.sh [options]

Options:
  --host <host>            Host to bind (default: 127.0.0.1)
  --port <port>            Port to bind (default: 8765)
  --db <path>              SQLite DB path (default: database/nimble.sqlite)
  --migration <path>       Migration SQL path (default: database/migrations/0001_canonical_schema_freeze.sql)
  --python <binary>        Python binary to use (default: python3, or env PYTHON_BIN)
  --restart                Stop existing listener on target port before start (default)
  --no-restart             Do not stop existing listener before start
  -h, --help               Show this help text

Examples:
  scripts/start-class-management-app.sh
  scripts/start-class-management-app.sh --port 8787
  scripts/start-class-management-app.sh --db /tmp/nimble_admin.sqlite
  scripts/start-class-management-app.sh --no-restart
EOF
}

require_value() {
  local flag="$1"
  local value="${2:-}"
  if [[ -z "${value}" || "${value}" == -* ]]; then
    echo "Missing value for ${flag}" >&2
    usage
    exit 1
  fi
}

get_listening_pids() {
  if ! command -v lsof >/dev/null 2>&1; then
    echo ""
    return 0
  fi

  lsof -nP -t -iTCP:"${PORT}" -sTCP:LISTEN 2>/dev/null | sort -u || true
}

format_pids() {
  if [[ -z "${1:-}" ]]; then
    echo ""
    return 0
  fi
  echo "$1" | paste -sd ', ' -
}

stop_existing_instance_if_needed() {
  if [[ "${RESTART_MODE}" != "true" ]]; then
    return
  fi

  if ! command -v lsof >/dev/null 2>&1; then
    echo "Restart mode enabled, but 'lsof' is unavailable. Continuing without auto-stop."
    return
  fi

  local pids
  pids="$(get_listening_pids)"
  if [[ -z "${pids}" ]]; then
    return
  fi

  echo "Restart mode: stopping existing listener(s) on port ${PORT}: $(format_pids "${pids}")"
  while IFS= read -r pid; do
    [[ -n "${pid}" ]] || continue
    kill "${pid}" 2>/dev/null || true
  done <<< "${pids}"

  local attempts=0
  local remaining
  remaining="$(get_listening_pids)"
  while [[ -n "${remaining}" && ${attempts} -lt 30 ]]; do
    sleep 0.1
    attempts=$((attempts + 1))
    remaining="$(get_listening_pids)"
  done

  if [[ -n "${remaining}" ]]; then
    echo "Restart mode: forcing stop for listener(s): $(format_pids "${remaining}")"
    while IFS= read -r pid; do
      [[ -n "${pid}" ]] || continue
      kill -9 "${pid}" 2>/dev/null || true
    done <<< "${remaining}"
    sleep 0.1
    remaining="$(get_listening_pids)"
  fi

  if [[ -n "${remaining}" ]]; then
    echo "Could not free port ${PORT}. Remaining PID(s): $(format_pids "${remaining}")" >&2
    exit 1
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      require_value "$1" "${2:-}"
      HOST="$2"
      shift 2
      ;;
    --port)
      require_value "$1" "${2:-}"
      PORT="$2"
      shift 2
      ;;
    --db)
      require_value "$1" "${2:-}"
      DB_PATH="$2"
      shift 2
      ;;
    --migration)
      require_value "$1" "${2:-}"
      MIGRATION_PATH="$2"
      shift 2
      ;;
    --python)
      require_value "$1" "${2:-}"
      PYTHON_BIN="$2"
      shift 2
      ;;
    --restart)
      RESTART_MODE="true"
      shift
      ;;
    --no-restart)
      RESTART_MODE="false"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python binary not found: ${PYTHON_BIN}" >&2
  exit 1
fi

SERVER_SCRIPT="${REPO_ROOT}/spikes/character-class-crud/server.py"
if [[ ! -f "${SERVER_SCRIPT}" ]]; then
  echo "Server script not found: ${SERVER_SCRIPT}" >&2
  exit 1
fi

echo "Starting class management app..."
echo "  URL: http://${HOST}:${PORT}"
echo "  DB: ${DB_PATH}"
echo "  Migration: ${MIGRATION_PATH}"
if [[ "${RESTART_MODE}" == "true" ]]; then
  echo "  Restart mode: enabled"
else
  echo "  Restart mode: disabled"
fi
echo "Press Ctrl+C to stop."

cd "${REPO_ROOT}"
stop_existing_instance_if_needed
exec "${PYTHON_BIN}" "${SERVER_SCRIPT}" \
  --host "${HOST}" \
  --port "${PORT}" \
  --db "${DB_PATH}" \
  --migration "${MIGRATION_PATH}"
