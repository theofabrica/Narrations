#!/usr/bin/env bash

# Helper to run a persistent Cloudflare Tunnel bound to your MCP server.
# Prerequisites (one-off):
#   cloudflared login
#   cloudflared tunnel create mcp-narrations
#   cloudflared tunnel route dns mcp-narrations mcp.numeniagen76.com
#
# Usage:
#   TUNNEL_HOSTNAME=mcp.numeniagen76.com \
#   TUNNEL_NAME=mcp-narrations \
#   TARGET_URL=http://localhost:3333 \
#   ./scripts/expose_cloudflare.sh
#
# Optional env:
#   CLOUDFLARED_BIN   (default: cloudflared)
#   CONFIG_DIR        (default: ~/.cloudflared)
#   TUNNEL_ID         (force a specific credentials JSON: ~/.cloudflared/<id>.json)
#   TUNNEL_CREDENTIALS_FILE (explicit path to credentials JSON)

set -euo pipefail

TUNNEL_NAME="${TUNNEL_NAME:-mcp-narrations}"
TUNNEL_HOSTNAME="${TUNNEL_HOSTNAME:-mcp.numeniagen76.com}"
TARGET_URL="${TARGET_URL:-http://localhost:3333}"
CLOUDFLARED_BIN="${CLOUDFLARED_BIN:-cloudflared}"
CONFIG_DIR="${CONFIG_DIR:-$HOME/.cloudflared}"
CONFIG_FILE="${CONFIG_FILE:-$CONFIG_DIR/config.yml}"

mkdir -p "$CONFIG_DIR"

# Resolve credentials file
if [[ -z "${TUNNEL_CREDENTIALS_FILE:-}" ]]; then
  if [[ -n "${TUNNEL_ID:-}" && -f "$CONFIG_DIR/${TUNNEL_ID}.json" ]]; then
    TUNNEL_CREDENTIALS_FILE="$CONFIG_DIR/${TUNNEL_ID}.json"
  else
    first_json=$(ls "$CONFIG_DIR"/*.json 2>/dev/null | head -n1 || true)
    if [[ -n "$first_json" ]]; then
      TUNNEL_CREDENTIALS_FILE="$first_json"
    fi
  fi
fi

if [[ -z "${TUNNEL_CREDENTIALS_FILE:-}" || ! -f "$TUNNEL_CREDENTIALS_FILE" ]]; then
  echo "❌ Credentials file not found."
  echo "   Run 'cloudflared login' then 'cloudflared tunnel create ${TUNNEL_NAME}' first."
  exit 1
fi

cat > "$CONFIG_FILE" <<EOF
tunnel: ${TUNNEL_NAME}
credentials-file: ${TUNNEL_CREDENTIALS_FILE}
ingress:
  - hostname: ${TUNNEL_HOSTNAME}
    service: ${TARGET_URL}
  - service: http_status:404
EOF

echo "▶️ Starting tunnel '${TUNNEL_NAME}' -> ${TARGET_URL} (hostname ${TUNNEL_HOSTNAME})"
echo "   Using credentials: ${TUNNEL_CREDENTIALS_FILE}"
echo "   Config: ${CONFIG_FILE}"
exec "${CLOUDFLARED_BIN}" --config "${CONFIG_FILE}" run "${TUNNEL_NAME}"
