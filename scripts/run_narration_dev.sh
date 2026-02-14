#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$ROOT/.venv"
LOG_DIR="$ROOT/logs"

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

    # Preserve explicit shell exports (higher priority than .env).
    if [ -n "${!key+x}" ]; then
      continue
    fi
    if [[ "$value" == \"*\" && "$value" == *\" ]]; then
      value="${value:1:${#value}-2}"
    elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
      value="${value:1:${#value}-2}"
    fi
    export "$key=$value"
  done < "$env_file"
}

load_env_file_if_present "$ROOT/.env"
load_env_file_if_present "$ROOT/.env.run"

ENABLE_R2R="${ENABLE_R2R:-0}"
RESTART_R2R_ON_START="${RESTART_R2R_ON_START:-0}"
R2R_RUNTIME="${R2R_RUNTIME:-docker}" # docker|local
R2R_PORT="${R2R_PORT:-7272}"
R2R_PID_FILE="${R2R_PID_FILE:-$ROOT/status/r2r.pid}"
R2R_DOCKER_STOP_ON_EXIT="${R2R_DOCKER_STOP_ON_EXIT:-1}" # legacy alias
R2R_DOCKER_DOWN_ON_START="${R2R_DOCKER_DOWN_ON_START:-1}"
R2R_DOCKER_DOWN_ON_EXIT="${R2R_DOCKER_DOWN_ON_EXIT:-1}"
R2R_DOCKER_PRUNE_VOLUMES_ON_START="${R2R_DOCKER_PRUNE_VOLUMES_ON_START:-0}"
R2R_DOCKER_PRUNE_VOLUMES_ON_EXIT="${R2R_DOCKER_PRUNE_VOLUMES_ON_EXIT:-0}"
R2R_DOCKER_PROFILE="${R2R_DOCKER_PROFILE:-postgres}"
R2R_DOCKER_SERVICES="${R2R_DOCKER_SERVICES:-postgres r2r}"
R2R_DOCKER_COMPOSE_FILE="${R2R_DOCKER_COMPOSE_FILE:-$ROOT/app/narration_agent/tools/r2r/docker/compose.yaml}"
R2R_MULTI_DOMAIN="${R2R_MULTI_DOMAIN:-1}"
R2R_NARRATIVE_PORT="${R2R_NARRATIVE_PORT:-7272}"
R2R_NARRATIVE_POSTGRES_PORT="${R2R_NARRATIVE_POSTGRES_PORT:-5432}"
R2R_ART_PORT="${R2R_ART_PORT:-7274}"
R2R_ART_POSTGRES_PORT="${R2R_ART_POSTGRES_PORT:-5434}"
R2R_SOUND_PORT="${R2R_SOUND_PORT:-7275}"
R2R_SOUND_POSTGRES_PORT="${R2R_SOUND_POSTGRES_PORT:-5435}"
R2R_NARRATIVE_PROJECT="${R2R_NARRATIVE_PROJECT:-r2r_narrative}"
R2R_ART_PROJECT="${R2R_ART_PROJECT:-r2r_art}"
R2R_SOUND_PROJECT="${R2R_SOUND_PROJECT:-r2r_sound}"
R2R_STARTUP_TIMEOUT_S="${R2R_STARTUP_TIMEOUT_S:-120}"
R2R_STRICT_STARTUP="${R2R_STRICT_STARTUP:-0}"
API_PORT="${API_PORT:-3333}"
UI_PORT="${UI_PORT:-5173}"
API_PID_FILE="${API_PID_FILE:-$ROOT/status/api.pid}"
UI_PID_FILE="${UI_PID_FILE:-$ROOT/status/ui.pid}"

R2R_API_BASE_NARRATIVE="${R2R_API_BASE_NARRATIVE:-http://127.0.0.1:$R2R_NARRATIVE_PORT}"
R2R_API_BASE_ART="${R2R_API_BASE_ART:-http://127.0.0.1:$R2R_ART_PORT}"
R2R_API_BASE_SOUND="${R2R_API_BASE_SOUND:-http://127.0.0.1:$R2R_SOUND_PORT}"
R2R_API_BASE="${R2R_API_BASE:-$R2R_API_BASE_NARRATIVE}"
export R2R_API_BASE
export R2R_API_BASE_NARRATIVE
export R2R_API_BASE_ART
export R2R_API_BASE_SOUND

mkdir -p "$LOG_DIR"
mkdir -p "$ROOT/status"

API_PID=""
UI_PID=""
R2R_PID=""
R2R_DOCKER_STARTED=0
R2R_COMPOSE_CMD=""

if [ ! -d "$VENV" ]; then
  echo "[setup] Creation du venv..."
  python -m venv "$VENV"
fi

echo "[setup] Activation du venv..."
# shellcheck disable=SC1091
source "$VENV/bin/activate"

echo "[setup] Installation des dependances Python..."
pip install -r "$ROOT/requirements.txt"

kill_pid_if_running() {
  local pid="$1"
  if [ -z "$pid" ]; then
    return 0
  fi
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    sleep 0.5
    if kill -0 "$pid" 2>/dev/null; then
      kill -9 "$pid" 2>/dev/null || true
    fi
  fi
}

kill_from_pid_file() {
  local pid_file="$1"
  local label="$2"
  if [ ! -f "$pid_file" ]; then
    return 0
  fi
  local pid
  pid="$(tr -d '[:space:]' < "$pid_file" || true)"
  if [ -n "$pid" ]; then
    echo "[cleanup] Arret $label via pid file ($pid)"
    kill_pid_if_running "$pid"
  fi
  rm -f "$pid_file" 2>/dev/null || true
}

kill_on_port() {
  local port="$1"
  local label="$2"
  if ! command -v lsof >/dev/null 2>&1; then
    return 0
  fi
  local pids
  pids="$(lsof -ti tcp:"$port" || true)"
  if [ -z "$pids" ]; then
    return 0
  fi
  echo "[cleanup] Arret $label sur :$port (PID(s): $pids)"
  # shellcheck disable=SC2086
  kill $pids 2>/dev/null || true
  sleep 0.5
  pids="$(lsof -ti tcp:"$port" || true)"
  if [ -n "$pids" ]; then
    # shellcheck disable=SC2086
    kill -9 $pids 2>/dev/null || true
  fi
}

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

r2r_domain_lines() {
  cat <<EOF
narrative|$R2R_NARRATIVE_PROJECT|$R2R_NARRATIVE_PORT|$R2R_NARRATIVE_POSTGRES_PORT
art|$R2R_ART_PROJECT|$R2R_ART_PORT|$R2R_ART_POSTGRES_PORT
sound|$R2R_SOUND_PROJECT|$R2R_SOUND_PORT|$R2R_SOUND_POSTGRES_PORT
EOF
}

wait_r2r_health_on_port() {
  local port="$1"
  local attempts=$((R2R_STARTUP_TIMEOUT_S * 2))
  local i=1
  while [ "$i" -le "$attempts" ]; do
    if command -v curl >/dev/null 2>&1; then
      if curl -fsS "http://127.0.0.1:$port/v3/health" >/dev/null 2>&1; then
        return 0
      fi
    elif command -v lsof >/dev/null 2>&1; then
      if lsof -ti tcp:"$port" >/dev/null 2>&1; then
        return 0
      fi
    fi
    sleep 0.5
    i=$((i + 1))
  done
  return 1
}

compose_stack_cmd() {
  local project="$1"
  local r2r_port="$2"
  local pg_port="$3"
  shift 3
  COMPOSE_PROJECT_NAME="$project" \
  R2R_PORT="$r2r_port" \
  R2R_POSTGRES_PORT="$pg_port" \
  R2R_POSTGRES_VOLUME_NAME="${project}_postgres_data" \
  R2R_MINIO_VOLUME_NAME="${project}_minio_data" \
  OPENAI_API_KEY="${OPENAI_API_KEY:-}" OPENAI_API_BASE="${OPENAI_API_BASE:-}" \
  "$@"
}

wait_r2r_health() {
  wait_r2r_health_on_port "$R2R_PORT"
}

wait_compose_service_healthy() {
  local service="$1"
  if [ -z "$R2R_COMPOSE_CMD" ]; then
    return 1
  fi

  local attempts=$((R2R_STARTUP_TIMEOUT_S * 2))
  local i=1
  while [ "$i" -le "$attempts" ]; do
    local cid
    # shellcheck disable=SC2086
    cid="$($R2R_COMPOSE_CMD -f "$R2R_DOCKER_COMPOSE_FILE" --profile "$R2R_DOCKER_PROFILE" ps -q "$service" 2>/dev/null || true)"
    if [ -n "$cid" ]; then
      local state
      state="$(docker inspect -f '{{.State.Status}}' "$cid" 2>/dev/null || true)"
      local health
      health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$cid" 2>/dev/null || true)"
      if [ "$state" = "running" ] && { [ "$health" = "healthy" ] || [ "$health" = "none" ]; }; then
        return 0
      fi
    fi
    sleep 0.5
    i=$((i + 1))
  done
  return 1
}

wait_compose_service_healthy_stack() {
  local service="$1"
  local project="$2"
  local r2r_port="$3"
  local pg_port="$4"
  if [ -z "$R2R_COMPOSE_CMD" ]; then
    return 1
  fi
  local attempts=$((R2R_STARTUP_TIMEOUT_S * 2))
  local i=1
  while [ "$i" -le "$attempts" ]; do
    local cid
    cid="$(compose_stack_cmd "$project" "$r2r_port" "$pg_port" \
      $R2R_COMPOSE_CMD -f "$R2R_DOCKER_COMPOSE_FILE" --profile "$R2R_DOCKER_PROFILE" ps -q "$service" 2>/dev/null || true)"
    if [ -n "$cid" ]; then
      local state
      state="$(docker inspect -f '{{.State.Status}}' "$cid" 2>/dev/null || true)"
      local health
      health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$cid" 2>/dev/null || true)"
      if [ "$state" = "running" ] && { [ "$health" = "healthy" ] || [ "$health" = "none" ]; }; then
        return 0
      fi
    fi
    sleep 0.5
    i=$((i + 1))
  done
  return 1
}

stop_r2r_docker() {
  if [ -z "$R2R_COMPOSE_CMD" ]; then
    return 0
  fi
  if [ ! -f "$R2R_DOCKER_COMPOSE_FILE" ]; then
    return 0
  fi
  if [ "$R2R_MULTI_DOMAIN" = "1" ]; then
    while IFS='|' read -r _domain project r2r_port pg_port; do
      [ -z "$project" ] && continue
      compose_stack_cmd "$project" "$r2r_port" "$pg_port" \
        $R2R_COMPOSE_CMD -f "$R2R_DOCKER_COMPOSE_FILE" --profile "$R2R_DOCKER_PROFILE" stop $R2R_DOCKER_SERVICES >/dev/null 2>&1 || true
    done < <(r2r_domain_lines)
    return 0
  fi
  # shellcheck disable=SC2086
  OPENAI_API_KEY="${OPENAI_API_KEY:-}" OPENAI_API_BASE="${OPENAI_API_BASE:-}" \
    $R2R_COMPOSE_CMD -f "$R2R_DOCKER_COMPOSE_FILE" --profile "$R2R_DOCKER_PROFILE" stop $R2R_DOCKER_SERVICES >/dev/null 2>&1 || true
}

down_r2r_docker() {
  local with_volumes="${1:-0}"
  if [ -z "$R2R_COMPOSE_CMD" ]; then
    return 0
  fi
  if [ ! -f "$R2R_DOCKER_COMPOSE_FILE" ]; then
    return 0
  fi
  if [ "$R2R_MULTI_DOMAIN" = "1" ]; then
    while IFS='|' read -r _domain project r2r_port pg_port; do
      [ -z "$project" ] && continue
      if [ "$with_volumes" = "1" ]; then
        compose_stack_cmd "$project" "$r2r_port" "$pg_port" \
          $R2R_COMPOSE_CMD -f "$R2R_DOCKER_COMPOSE_FILE" --profile "$R2R_DOCKER_PROFILE" down --remove-orphans --volumes >/dev/null 2>&1 || true
      else
        compose_stack_cmd "$project" "$r2r_port" "$pg_port" \
          $R2R_COMPOSE_CMD -f "$R2R_DOCKER_COMPOSE_FILE" --profile "$R2R_DOCKER_PROFILE" down --remove-orphans >/dev/null 2>&1 || true
      fi
    done < <(r2r_domain_lines)
    return 0
  fi
  if [ "$with_volumes" = "1" ]; then
    # shellcheck disable=SC2086
    OPENAI_API_KEY="${OPENAI_API_KEY:-}" OPENAI_API_BASE="${OPENAI_API_BASE:-}" \
      $R2R_COMPOSE_CMD -f "$R2R_DOCKER_COMPOSE_FILE" --profile "$R2R_DOCKER_PROFILE" down --remove-orphans --volumes >/dev/null 2>&1 || true
  else
    # shellcheck disable=SC2086
    OPENAI_API_KEY="${OPENAI_API_KEY:-}" OPENAI_API_BASE="${OPENAI_API_BASE:-}" \
      $R2R_COMPOSE_CMD -f "$R2R_DOCKER_COMPOSE_FILE" --profile "$R2R_DOCKER_PROFILE" down --remove-orphans >/dev/null 2>&1 || true
  fi
}

start_r2r_docker() {
  local compose_cmd
  compose_cmd="$(resolve_docker_compose_cmd || true)"
  if [ -z "$compose_cmd" ]; then
    echo "[error] docker compose indisponible pour R2R"
    return 1
  fi
  if [ ! -f "$R2R_DOCKER_COMPOSE_FILE" ]; then
    echo "[error] compose file introuvable: $R2R_DOCKER_COMPOSE_FILE"
    return 1
  fi
  R2R_COMPOSE_CMD="$compose_cmd"
  if [ "$R2R_MULTI_DOMAIN" = "1" ]; then
    if [ "$RESTART_R2R_ON_START" = "1" ]; then
      echo "[run] Redemarrage explicite des stacks R2R (narrative/art/sound)..."
      if [ "$R2R_DOCKER_DOWN_ON_START" = "1" ]; then
        down_r2r_docker "$R2R_DOCKER_PRUNE_VOLUMES_ON_START"
      else
        stop_r2r_docker
      fi
    fi
    while IFS='|' read -r domain project r2r_port pg_port; do
      [ -z "$project" ] && continue
      if command -v lsof >/dev/null 2>&1; then
        existing_r2r_pids="$(lsof -ti tcp:"$r2r_port" || true)"
        if [ -n "$existing_r2r_pids" ] && [ "$RESTART_R2R_ON_START" = "1" ]; then
          echo "[run] Stack $domain: nettoyage du port R2R :$r2r_port"
          kill_on_port "$r2r_port" "R2R-$domain"
        fi
      fi
      echo "[run] Stack $domain: demarrage postgres(:$pg_port) + r2r(:$r2r_port)"
      compose_stack_cmd "$project" "$r2r_port" "$pg_port" \
        $R2R_COMPOSE_CMD -f "$R2R_DOCKER_COMPOSE_FILE" --profile "$R2R_DOCKER_PROFILE" up -d postgres >/dev/null
      R2R_DOCKER_STARTED=1
      if ! wait_compose_service_healthy_stack "postgres" "$project" "$r2r_port" "$pg_port"; then
        echo "[error] Stack $domain: service postgres indisponible."
        return 1
      fi
      compose_stack_cmd "$project" "$r2r_port" "$pg_port" \
        $R2R_COMPOSE_CMD -f "$R2R_DOCKER_COMPOSE_FILE" --profile "$R2R_DOCKER_PROFILE" up -d r2r >/dev/null
      R2R_DOCKER_STARTED=1
      if ! wait_compose_service_healthy_stack "r2r" "$project" "$r2r_port" "$pg_port"; then
        echo "[error] Stack $domain: service r2r non stable."
        return 1
      fi
      if ! wait_r2r_health_on_port "$r2r_port"; then
        echo "[error] Stack $domain: endpoint /v3/health indisponible sur :$r2r_port."
        return 1
      fi
    done < <(r2r_domain_lines)
    return 0
  fi
  if command -v lsof >/dev/null 2>&1; then
    local existing_r2r_pids
    existing_r2r_pids="$(lsof -ti tcp:"$R2R_PORT" || true)"
    if [ -n "$existing_r2r_pids" ]; then
      if [ "$RESTART_R2R_ON_START" = "1" ]; then
        echo "[run] Port R2R :$R2R_PORT occupe, nettoyage avant demarrage Docker."
        kill_on_port "$R2R_PORT" "R2R"
      elif wait_r2r_health; then
        echo "[run] R2R deja disponible sur :$R2R_PORT, skip demarrage Docker."
        return 0
      else
        echo "[error] Port :$R2R_PORT occupe mais endpoint /v3/health indisponible. Utilise RESTART_R2R_ON_START=1."
        return 1
      fi
    fi
  fi
  if [ "$RESTART_R2R_ON_START" = "1" ]; then
    echo "[run] Redemarrage explicite R2R docker services..."
    if [ "$R2R_DOCKER_DOWN_ON_START" = "1" ]; then
      down_r2r_docker "$R2R_DOCKER_PRUNE_VOLUMES_ON_START"
    else
      stop_r2r_docker
    fi
  fi
  if [[ " $R2R_DOCKER_SERVICES " == *" postgres "* ]]; then
    echo "[run] Demarrage R2R docker (postgres)"
    # shellcheck disable=SC2086
    OPENAI_API_KEY="${OPENAI_API_KEY:-}" OPENAI_API_BASE="${OPENAI_API_BASE:-}" \
      $R2R_COMPOSE_CMD -f "$R2R_DOCKER_COMPOSE_FILE" --profile "$R2R_DOCKER_PROFILE" up -d postgres >/dev/null
    R2R_DOCKER_STARTED=1
    if ! wait_compose_service_healthy "postgres"; then
      echo "[error] Service postgres indisponible (docker)."
      return 1
    fi
  fi

  echo "[run] Demarrage R2R docker (r2r)"
  # shellcheck disable=SC2086
  OPENAI_API_KEY="${OPENAI_API_KEY:-}" OPENAI_API_BASE="${OPENAI_API_BASE:-}" \
    $R2R_COMPOSE_CMD -f "$R2R_DOCKER_COMPOSE_FILE" --profile "$R2R_DOCKER_PROFILE" up -d r2r >/dev/null
  R2R_DOCKER_STARTED=1
  if ! wait_compose_service_healthy "r2r"; then
    echo "[error] Service r2r non stable (docker)."
    return 1
  fi
  if ! wait_r2r_health; then
    echo "[error] R2R docker indisponible sur :$R2R_PORT apres ${R2R_STARTUP_TIMEOUT_S}s."
    return 1
  fi

  # Start optional extra services if requested.
  for svc in $R2R_DOCKER_SERVICES; do
    if [ "$svc" = "postgres" ] || [ "$svc" = "r2r" ]; then
      continue
    fi
    # shellcheck disable=SC2086
    OPENAI_API_KEY="${OPENAI_API_KEY:-}" OPENAI_API_BASE="${OPENAI_API_BASE:-}" \
      $R2R_COMPOSE_CMD -f "$R2R_DOCKER_COMPOSE_FILE" --profile "$R2R_DOCKER_PROFILE" up -d "$svc" >/dev/null || true
  done
  return 0
}

pre_start_cleanup() {
  echo "[cleanup] Nettoyage des processus residuels..."
  kill_from_pid_file "$API_PID_FILE" "API"
  kill_from_pid_file "$UI_PID_FILE" "UI"
  kill_on_port "$API_PORT" "API"
  kill_on_port "$UI_PORT" "UI"
  if [ "$ENABLE_R2R" = "1" ] && [ "$R2R_RUNTIME" = "local" ] && [ "$RESTART_R2R_ON_START" = "1" ]; then
    kill_from_pid_file "$R2R_PID_FILE" "R2R"
    if [ "$R2R_MULTI_DOMAIN" = "1" ]; then
      kill_on_port "$R2R_NARRATIVE_PORT" "R2R-narrative"
      kill_on_port "$R2R_ART_PORT" "R2R-art"
      kill_on_port "$R2R_SOUND_PORT" "R2R-sound"
    else
      kill_on_port "$R2R_PORT" "R2R"
    fi
  fi
}

cleanup() {
  echo "[stop] Arret des processus..."
  kill_pid_if_running "$API_PID"
  if [ -n "$UI_PID" ]; then
    kill_pid_if_running "$UI_PID"
  fi
  if [ -n "$R2R_PID" ]; then
    kill_pid_if_running "$R2R_PID"
  fi
  kill_on_port "$API_PORT" "API"
  kill_on_port "$UI_PORT" "UI"
  if [ -n "$R2R_PID" ]; then
    if [ "$R2R_MULTI_DOMAIN" = "1" ]; then
      kill_on_port "$R2R_NARRATIVE_PORT" "R2R-narrative"
      kill_on_port "$R2R_ART_PORT" "R2R-art"
      kill_on_port "$R2R_SOUND_PORT" "R2R-sound"
    else
      kill_on_port "$R2R_PORT" "R2R"
    fi
  fi
  if [ "$ENABLE_R2R" = "1" ] && [ "$R2R_RUNTIME" = "docker" ] && [ "$R2R_DOCKER_STOP_ON_EXIT" = "1" ]; then
    echo "[stop] Arret des services Docker R2R..."
    if [ "$R2R_DOCKER_DOWN_ON_EXIT" = "1" ]; then
      down_r2r_docker "$R2R_DOCKER_PRUNE_VOLUMES_ON_EXIT"
    else
      stop_r2r_docker
    fi
  fi
  rm -f "$API_PID_FILE" 2>/dev/null || true
  rm -f "$UI_PID_FILE" 2>/dev/null || true
  if [ -f "$R2R_PID_FILE" ]; then
    rm -f "$R2R_PID_FILE" 2>/dev/null || true
  fi
}

trap cleanup EXIT

pre_start_cleanup
if [ "$ENABLE_R2R" = "1" ]; then
  if [ "$R2R_RUNTIME" = "docker" ]; then
    if ! start_r2r_docker; then
      if [ "$R2R_STRICT_STARTUP" = "1" ]; then
        exit 1
      fi
      echo "[warn] R2R indisponible au demarrage. On continue quand meme (R2R_STRICT_STARTUP=0)."
    fi
  else
    if [ "$RESTART_R2R_ON_START" = "1" ]; then
      echo "[run] Redemarrage explicite R2R sur :$R2R_PORT"
      if command -v lsof >/dev/null 2>&1; then
        EXISTING_R2R_PIDS="$(lsof -ti tcp:"$R2R_PORT" || true)"
        if [ -n "$EXISTING_R2R_PIDS" ]; then
          # Intentional explicit restart for local development.
          kill $EXISTING_R2R_PIDS 2>/dev/null || true
          sleep 1
        fi
      fi
    else
      if command -v lsof >/dev/null 2>&1; then
        EXISTING_R2R_PIDS="$(lsof -ti tcp:"$R2R_PORT" || true)"
        if [ -n "$EXISTING_R2R_PIDS" ]; then
          echo "[run] R2R detecte sur :$R2R_PORT (PID(s): $EXISTING_R2R_PIDS), skip demarrage."
        fi
      fi
    fi

    if command -v lsof >/dev/null 2>&1 && [ -z "$(lsof -ti tcp:"$R2R_PORT" || true)" ]; then
      echo "[run] Demarrage R2R sur :$R2R_PORT (logs: $LOG_DIR/r2r.log)"
      python -m r2r.serve > "$LOG_DIR/r2r.log" 2>&1 &
      R2R_PID=$!
      echo "$R2R_PID" > "$R2R_PID_FILE"
    elif ! command -v lsof >/dev/null 2>&1; then
      echo "[run] lsof indisponible, demarrage R2R sans verification de port."
      python -m r2r.serve > "$LOG_DIR/r2r.log" 2>&1 &
      R2R_PID=$!
      echo "$R2R_PID" > "$R2R_PID_FILE"
    fi
  fi
fi

echo "[run] Demarrage API (FastAPI) sur :$API_PORT"
cd "$ROOT"
# Avoid "Too many open files" from watchfiles on large repos.
ulimit -n 8192 2>/dev/null || true
export WATCHFILES_FORCE_POLLING=true

start_api() {
  local mode="$1"
  if [ "$mode" = "reload" ]; then
    python -m uvicorn app.main:app --host 0.0.0.0 --port "$API_PORT" --reload \
      > "$LOG_DIR/api.log" 2>&1 &
  else
    python -m uvicorn app.main:app --host 0.0.0.0 --port "$API_PORT" \
      > "$LOG_DIR/api.log" 2>&1 &
  fi
  API_PID=$!
  echo "$API_PID" > "$API_PID_FILE"
}

api_is_healthy() {
  if command -v curl >/dev/null 2>&1; then
    curl -fsS "http://127.0.0.1:$API_PORT/projects" >/dev/null 2>&1
    return $?
  fi
  if command -v lsof >/dev/null 2>&1; then
    lsof -ti tcp:"$API_PORT" >/dev/null 2>&1
    return $?
  fi
  return 0
}

wait_for_api_health() {
  local attempts=20
  local i=1
  while [ "$i" -le "$attempts" ]; do
    if ! kill -0 "$API_PID" 2>/dev/null; then
      return 1
    fi
    if api_is_healthy; then
      return 0
    fi
    sleep 0.5
    i=$((i + 1))
  done
  return 1
}

start_api "reload"
if ! wait_for_api_health; then
  echo "[warn] API en mode --reload non disponible. Fallback sans --reload..."
  kill "$API_PID" 2>/dev/null || true
  sleep 1
  start_api "plain"
  if ! wait_for_api_health; then
    echo "[error] API indisponible sur :$API_PORT. Voir $LOG_DIR/api.log"
    exit 1
  fi
fi

if [ -d "$ROOT/interface" ]; then
  echo "[run] Installation dependances UI..."
  npm --prefix "$ROOT/interface" install >/dev/null
  echo "[run] Demarrage UI (Vite) sur :$UI_PORT"
  npm --prefix "$ROOT/interface" run dev -- --host 0.0.0.0 --port "$UI_PORT" \
    > "$LOG_DIR/ui.log" 2>&1 &
  UI_PID=$!
  echo "$UI_PID" > "$UI_PID_FILE"
else
  UI_PID=""
fi

echo "[ok] API PID: $API_PID"
if [ -n "$UI_PID" ]; then
  echo "[ok] UI PID: $UI_PID"
fi
if [ -n "$R2R_PID" ]; then
  echo "[ok] R2R PID: $R2R_PID"
fi
echo "[logs] $LOG_DIR/api.log"
echo "[logs] $LOG_DIR/ui.log"
if [ "$ENABLE_R2R" = "1" ]; then
  if [ "$R2R_RUNTIME" = "docker" ]; then
    if [ "$R2R_MULTI_DOMAIN" = "1" ]; then
      echo "[r2r] narrative: $R2R_API_BASE_NARRATIVE"
      echo "[r2r] art:       $R2R_API_BASE_ART"
      echo "[r2r] sound:     $R2R_API_BASE_SOUND"
      echo "[logs] docker compose logs -f r2r (project: $R2R_NARRATIVE_PROJECT)"
      echo "[logs] docker compose logs -f r2r (project: $R2R_ART_PROJECT)"
      echo "[logs] docker compose logs -f r2r (project: $R2R_SOUND_PROJECT)"
    else
      echo "[logs] docker compose logs -f r2r (compose: $R2R_DOCKER_COMPOSE_FILE)"
    fi
  else
    echo "[logs] $LOG_DIR/r2r.log"
  fi
fi

wait
