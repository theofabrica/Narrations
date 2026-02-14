#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEFAULT_COMPOSE_FILE="$ROOT/app/narration_agent/tools/r2r/docker/compose.yaml"

load_env_file_if_present() {
  local env_file="$1"
  if [ ! -f "$env_file" ]; then
    return 0
  fi
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%$'\r'}"
    [[ -z "$line" || "${line#\#}" != "$line" ]] && continue
    [[ "$line" != *"="* ]] && continue
    local key="${line%%=*}"
    local value="${line#*=}"
    key="${key#"${key%%[![:space:]]*}"}"
    key="${key%"${key##*[![:space:]]}"}"
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"
    if [ -n "${!key+x}" ]; then
      continue
    fi
    export "$key=$value"
  done < "$env_file"
}

load_env_file_if_present "$ROOT/.env.run"

R2R_DOCKER_COMPOSE_FILE="${R2R_DOCKER_COMPOSE_FILE:-$DEFAULT_COMPOSE_FILE}"
R2R_DOCKER_PROFILE="${R2R_DOCKER_PROFILE:-postgres}"
R2R_DOCKER_SERVICE="${R2R_DOCKER_SERVICE:-r2r}"
R2R_PORT="${R2R_PORT:-7272}"
R2R_MULTI_DOMAIN="${R2R_MULTI_DOMAIN:-1}"
R2R_NARRATIVE_PROJECT="${R2R_NARRATIVE_PROJECT:-r2r_narrative}"
R2R_ART_PROJECT="${R2R_ART_PROJECT:-r2r_art}"
R2R_SOUND_PROJECT="${R2R_SOUND_PROJECT:-r2r_sound}"
R2R_NARRATIVE_PORT="${R2R_NARRATIVE_PORT:-7272}"
R2R_ART_PORT="${R2R_ART_PORT:-7274}"
R2R_SOUND_PORT="${R2R_SOUND_PORT:-7275}"

resolve_docker_compose_cmd() {
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    echo "docker compose"
    return 0
  fi
  if command -v docker-compose >/dev/null 2>&1; then
    echo "docker-compose"
    return 0
  fi
  return 1
}

COMPOSE_CMD="$(resolve_docker_compose_cmd || true)"
if [ -z "$COMPOSE_CMD" ]; then
  echo "[error] docker compose indisponible."
  exit 1
fi

if [ ! -f "$R2R_DOCKER_COMPOSE_FILE" ]; then
  echo "[error] compose file introuvable: $R2R_DOCKER_COMPOSE_FILE"
  exit 1
fi

usage() {
  cat <<EOF
Usage: $(basename "$0") <live|errors|health|report> [domain] [args]

Commands:
  live [domain] [tail] [since]   Stream logs (default: domain=all, tail=150, since=10m)
  errors [domain] [since]        Filtre erreurs/warnings (default: domain=all, since=30m)
  health [domain]                Etat conteneurs + endpoint /v3/health
  report [domain] [since]        Snapshot complet (default: domain=all, since=30m)

Domains:
  narrative | art | sound | all

Examples:
  $(basename "$0") live
  $(basename "$0") live narrative 300 2m
  $(basename "$0") errors art 60m
  $(basename "$0") health sound
  $(basename "$0") report all 15m
EOF
}

domain_lines() {
  cat <<EOF
narrative|$R2R_NARRATIVE_PROJECT|$R2R_NARRATIVE_PORT
art|$R2R_ART_PROJECT|$R2R_ART_PORT
sound|$R2R_SOUND_PROJECT|$R2R_SOUND_PORT
EOF
}

is_valid_domain() {
  case "$1" in
    narrative|art|sound|all) return 0 ;;
    *) return 1 ;;
  esac
}

selected_domains() {
  local domain="${1:-all}"
  if [ "$R2R_MULTI_DOMAIN" != "1" ]; then
    echo "narrative"
    return 0
  fi
  if [ "$domain" = "all" ] || [ -z "$domain" ]; then
    echo "narrative art sound"
    return 0
  fi
  echo "$domain"
}

project_for_domain() {
  local domain="$1"
  while IFS='|' read -r d project _port; do
    if [ "$d" = "$domain" ]; then
      echo "$project"
      return 0
    fi
  done < <(domain_lines)
  echo ""
}

port_for_domain() {
  local domain="$1"
  while IFS='|' read -r d _project port; do
    if [ "$d" = "$domain" ]; then
      echo "$port"
      return 0
    fi
  done < <(domain_lines)
  echo "$R2R_PORT"
}

compose_logs_domain() {
  local domain="$1"
  shift
  if [ "$R2R_MULTI_DOMAIN" != "1" ]; then
    # shellcheck disable=SC2086
    $COMPOSE_CMD -f "$R2R_DOCKER_COMPOSE_FILE" --profile "$R2R_DOCKER_PROFILE" logs --no-color "$@"
    return 0
  fi
  local project
  project="$(project_for_domain "$domain")"
  if [ -z "$project" ]; then
    echo "[error] domaine inconnu: $domain"
    return 1
  fi
  COMPOSE_PROJECT_NAME="$project" \
    $COMPOSE_CMD -f "$R2R_DOCKER_COMPOSE_FILE" --profile "$R2R_DOCKER_PROFILE" logs --no-color "$@"
}

cmd_live() {
  local domain="${1:-all}"
  local tail_lines="${2:-150}"
  local since="${3:-10m}"
  if ! is_valid_domain "$domain"; then
    echo "[error] domaine invalide: $domain"
    usage
    exit 1
  fi
  if [ "$R2R_MULTI_DOMAIN" = "1" ] && [ "$domain" = "all" ]; then
    local pids=""
    for d in $(selected_domains "$domain"); do
      (
        compose_logs_domain "$d" --tail "$tail_lines" --since "$since" -f "$R2R_DOCKER_SERVICE" \
          | sed "s/^/[$d] /"
      ) &
      pids="$pids $!"
    done
    trap 'for p in '"$pids"'; do kill "$p" 2>/dev/null || true; done' INT TERM EXIT
    wait
    return 0
  fi
  compose_logs_domain "$(selected_domains "$domain")" --tail "$tail_lines" --since "$since" -f "$R2R_DOCKER_SERVICE"
}

cmd_errors() {
  local domain="${1:-all}"
  local since="${2:-30m}"
  if ! is_valid_domain "$domain"; then
    echo "[error] domaine invalide: $domain"
    usage
    exit 1
  fi
  for d in $(selected_domains "$domain"); do
    if [ "$R2R_MULTI_DOMAIN" = "1" ]; then
      echo "=== errors: $d ==="
    fi
    compose_logs_domain "$d" --since "$since" "$R2R_DOCKER_SERVICE" | python -c '
import re
import sys

ansi = re.compile(r"\x1b\[[0-9;]*m")
needles = [
    " error ",
    " error -",
    "warning",
    "exception",
    "traceback",
    "timed out",
    "temporary failure",
    "connection refused",
    "failed to",
    "not found",
    "unhealthy",
    "restarting",
]

for raw in sys.stdin:
    line = ansi.sub("", raw.rstrip("\n"))
    low = line.lower()
    if any(n in low for n in needles):
        print(line)
'
    echo
  done
}

cmd_health() {
  local domain="${1:-all}"
  if ! is_valid_domain "$domain"; then
    echo "[error] domaine invalide: $domain"
    usage
    exit 1
  fi
  for d in $(selected_domains "$domain"); do
    local project
    local port
    project="$(project_for_domain "$d")"
    port="$(port_for_domain "$d")"
    [ "$R2R_MULTI_DOMAIN" = "1" ] && echo "=== domain: $d (project=$project, port=$port) ==="
    echo "=== compose ps ==="
    if [ "$R2R_MULTI_DOMAIN" = "1" ]; then
      COMPOSE_PROJECT_NAME="$project" \
        $COMPOSE_CMD -f "$R2R_DOCKER_COMPOSE_FILE" --profile "$R2R_DOCKER_PROFILE" ps
    else
      # shellcheck disable=SC2086
      $COMPOSE_CMD -f "$R2R_DOCKER_COMPOSE_FILE" --profile "$R2R_DOCKER_PROFILE" ps
    fi
    echo
    echo "=== inspect restart_count / health ==="
    local cid
    if [ "$R2R_MULTI_DOMAIN" = "1" ]; then
      cid="$(COMPOSE_PROJECT_NAME="$project" \
        $COMPOSE_CMD -f "$R2R_DOCKER_COMPOSE_FILE" --profile "$R2R_DOCKER_PROFILE" ps -q "$R2R_DOCKER_SERVICE" 2>/dev/null || true)"
    else
      cid="$($COMPOSE_CMD -f "$R2R_DOCKER_COMPOSE_FILE" --profile "$R2R_DOCKER_PROFILE" ps -q "$R2R_DOCKER_SERVICE" 2>/dev/null || true)"
    fi
    if [ -n "$cid" ]; then
      docker inspect -f 'name={{.Name}} restart_count={{.RestartCount}} state={{.State.Status}} health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$cid"
    else
      echo "service $R2R_DOCKER_SERVICE non trouve."
    fi
    echo
    echo "=== endpoint /v3/health ==="
    if command -v curl >/dev/null 2>&1; then
      curl -fsS "http://127.0.0.1:$port/v3/health" && echo
    else
      echo "curl indisponible"
    fi
    echo
  done
}

cmd_report() {
  local domain="${1:-all}"
  local since="${2:-30m}"
  if ! is_valid_domain "$domain"; then
    echo "[error] domaine invalide: $domain"
    usage
    exit 1
  fi
  echo "=== R2R REPORT ($(date -Iseconds)) ==="
  echo "compose_file=$R2R_DOCKER_COMPOSE_FILE service=$R2R_DOCKER_SERVICE profile=$R2R_DOCKER_PROFILE multi_domain=$R2R_MULTI_DOMAIN domain=$domain"
  echo
  cmd_health "$domain" || true
  for d in $(selected_domains "$domain"); do
    echo "=== last logs [$d] ($since) ==="
    compose_logs_domain "$d" --since "$since" --tail 400 "$R2R_DOCKER_SERVICE" || true
    echo
  done
  echo "=== filtered errors ($since) ==="
  cmd_errors "$domain" "$since" || true
}

cmd="${1:-}"
case "$cmd" in
  live)
    shift
    cmd_live "${1:-}" "${2:-}" "${3:-}"
    ;;
  errors)
    shift
    cmd_errors "${1:-}" "${2:-}"
    ;;
  health)
    shift
    cmd_health "${1:-}"
    ;;
  report)
    shift
    cmd_report "${1:-}" "${2:-}"
    ;;
  -h|--help|"")
    usage
    ;;
  *)
    echo "[error] commande inconnue: $cmd"
    usage
    exit 1
    ;;
esac
