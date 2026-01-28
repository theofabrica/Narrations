#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$ROOT/.venv"
LOG_DIR="$ROOT/logs"

mkdir -p "$LOG_DIR"

if [ ! -d "$VENV" ]; then
  echo "[setup] Creation du venv..."
  python -m venv "$VENV"
fi

echo "[setup] Activation du venv..."
# shellcheck disable=SC1091
source "$VENV/bin/activate"

echo "[setup] Installation des dependances Python..."
pip install -r "$ROOT/requirements.txt"

echo "[run] Demarrage API (FastAPI) sur :3333"
cd "$ROOT"
python -m uvicorn app.main:app --host 0.0.0.0 --port 3333 --reload \
  > "$LOG_DIR/api.log" 2>&1 &
API_PID=$!

if [ -d "$ROOT/interface" ]; then
  echo "[run] Installation dependances UI..."
  npm --prefix "$ROOT/interface" install >/dev/null
  echo "[run] Demarrage UI (Vite) sur :5173"
  npm --prefix "$ROOT/interface" run dev -- --host 0.0.0.0 --port 5173 \
    > "$LOG_DIR/ui.log" 2>&1 &
  UI_PID=$!
else
  UI_PID=""
fi

echo "[ok] API PID: $API_PID"
if [ -n "$UI_PID" ]; then
  echo "[ok] UI PID: $UI_PID"
fi
echo "[logs] $LOG_DIR/api.log"
echo "[logs] $LOG_DIR/ui.log"

cleanup() {
  echo "[stop] Arret des processus..."
  kill "$API_PID" 2>/dev/null || true
  if [ -n "$UI_PID" ]; then
    kill "$UI_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT
wait
