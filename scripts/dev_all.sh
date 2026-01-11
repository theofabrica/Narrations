#!/bin/bash
# Launch API (+ optional Cloudflare tunnel) and the Vite interface together.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f "run.sh" ]; then
  echo "Erreur: run.sh introuvable. Lance ce script depuis la racine du projet."
  exit 1
fi

if [ ! -d "interface" ]; then
  echo "Erreur: dossier interface introuvable."
  exit 1
fi

LOG_DIR="${LOG_DIR:-./logs}"
mkdir -p "$LOG_DIR"

if [ ! -d "interface/node_modules" ]; then
  echo "Installation des dependances front..."
  (cd interface && npm install)
fi

echo "Demarrage API (logs: $LOG_DIR/api.log)"
./run.sh 2>&1 | tee "$LOG_DIR/api.log" &
API_PID=$!

echo "Demarrage interface (logs: $LOG_DIR/ui.log)"
(cd interface && npm run dev) 2>&1 | tee "$LOG_DIR/ui.log" &
UI_PID=$!

cleanup() {
  echo "Arret des services..."
  kill "$API_PID" "$UI_PID" 2>/dev/null || true
  wait "$API_PID" "$UI_PID" 2>/dev/null || true
}

trap cleanup INT TERM EXIT

echo "API: http://localhost:3333"
echo "UI : http://localhost:5173"
if [ "${ENABLE_CLOUDFLARE_TUNNEL:-0}" = "1" ]; then
  echo "Cloudflare: logs -> $LOG_DIR/tunnel.log"
fi

wait "$API_PID" "$UI_PID"
