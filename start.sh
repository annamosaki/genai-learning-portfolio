#!/usr/bin/env bash
# Kinetic Atelier — start web + API together with multi-zone support.
# Usage:
#   ./start.sh              # install if needed, then run all services
#   ./start.sh --portfolio  # run portfolio only (web + api)
#   ./start.sh --lab        # run LLM Lab only (web + api)
#   ./start.sh --desk       # run Agent Desk only (web + api)
#   ./start.sh --digest     # run Research Digest only (web + api)
#   ./start.sh --no-install # skip dependency checks
#   ./start.sh --help

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

WEB_PORT="${WEB_PORT:-3000}"
API_PORT="${API_PORT:-8000}"
SKIP_INSTALL=0
PROFILE="all" # all | portfolio | lab | desk | digest

RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
BRASS=$'\033[0;33m'
BONE=$'\033[0;37m'
DIM=$'\033[2m'
RESET=$'\033[0m'

log() { printf '%s→%s %s\n' "$BRASS" "$RESET" "$*"; }
ok() { printf '%s✓%s %s\n' "$GREEN" "$RESET" "$*"; }
err() { printf '%s✗%s %s\n' "$RED" "$RESET" "$*" >&2; }

usage() {
  cat <<EOF
${BONE}Anna Mosaki — Kinetic Atelier${RESET}

Starts the monorepo with Next.js multi-zones and Python APIs.

Usage: ./start.sh [options]

Profiles:
  --portfolio    Start portfolio web + API only (:${WEB_PORT}, :${API_PORT})
  --lab          Start LLM Lab zone only (:3100, :8100)
  --desk         Start Agent Desk zone only (:3200, :8200)
  --digest       Start Research Digest zone only (:3300, :8300)
  (default)      Start all services with multi-zones

Options:
  --no-install   Do not run npm/pip install even if deps look missing
  -h, --help     Show this help

URLs when running all services:
  Portfolio      http://localhost:${WEB_PORT}
  LLM Lab zone   http://localhost:${WEB_PORT}/demos/llm-lab
  Agent Desk     http://localhost:${WEB_PORT}/demos/agent-desk
  Research Digest http://localhost:${WEB_PORT}/demos/research-digest
  API docs       http://localhost:${API_PORT}/docs
  Lab API        http://localhost:8100/docs
  Desk API       http://localhost:8200/docs
  Digest API     http://localhost:8300/docs
  Edgar MCP      http://localhost:8210/mcp
  Status page    http://localhost:${WEB_PORT}/status
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-install) SKIP_INSTALL=1; shift ;;
    --portfolio) PROFILE="portfolio"; shift ;;
    --lab) PROFILE="lab"; shift ;;
    --desk) PROFILE="desk"; shift ;;
    --digest) PROFILE="digest"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) err "Unknown option: $1"; usage; exit 1 ;;
  esac
done

cleanup() {
  printf '\n'
  log "Shutting down…"
  # Kill all background processes from this session
  if command -v honcho >/dev/null 2>&1; then
    pkill -P $$ 2>/dev/null || true
  fi
  jobs -p | while read -r pid; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
  ok "Stopped."
}
trap cleanup EXIT INT TERM

port_in_use() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"$port" -sTCP:LISTEN -t >/dev/null 2>&1
  else
    return 1
  fi
}

ensure_env() {
  if [[ ! -f "$ROOT/.env" ]]; then
    cp "$ROOT/.env.example" "$ROOT/.env"
    ok "Created .env from .env.example (add API keys when ready — demos fall back to replay)."
  fi
  # Keep Next.js public API URL in sync with API_PORT unless already set in .env
  if ! grep -q '^NEXT_PUBLIC_API_BASE_URL=' "$ROOT/.env" 2>/dev/null; then
    echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:${API_PORT}" >>"$ROOT/.env"
  fi
  if ! grep -q '^API_BASE_URL=' "$ROOT/.env" 2>/dev/null; then
    echo "API_BASE_URL=http://localhost:${API_PORT}" >>"$ROOT/.env"
  fi
  # Add multi-zone URLs if missing
  if ! grep -q '^LLM_LAB_URL=' "$ROOT/.env" 2>/dev/null; then
    echo "LLM_LAB_URL=http://localhost:3100" >>"$ROOT/.env"
  fi
  if ! grep -q '^AGENT_DESK_URL=' "$ROOT/.env" 2>/dev/null; then
    echo "AGENT_DESK_URL=http://localhost:3200" >>"$ROOT/.env"
  fi
  if ! grep -q '^RESEARCH_DIGEST_URL=' "$ROOT/.env" 2>/dev/null; then
    echo "RESEARCH_DIGEST_URL=http://localhost:3300" >>"$ROOT/.env"
  fi
}

ensure_node() {
  if [[ ! -d "$ROOT/node_modules" ]] || [[ ! -d "$ROOT/apps/web/node_modules" && ! -e "$ROOT/node_modules/next" ]]; then
    if [[ "$SKIP_INSTALL" -eq 1 ]]; then
      err "node_modules missing. Run without --no-install, or: npm install"
      exit 1
    fi
    log "Installing npm workspaces…"
    npm install
  fi
}

ensure_python() {
  local venv="$ROOT/.venv"
  if [[ ! -x "$venv/bin/uvicorn" ]]; then
    if [[ "$SKIP_INSTALL" -eq 1 ]]; then
      err "Python venv missing. Run without --no-install, or install deps manually"
      exit 1
    fi
    log "Creating shared Python venv and installing all API deps…"
    python3 -m venv "$venv"
    # shellcheck disable=SC1091
    source "$venv/bin/activate"
    
    # Install all Python requirements into shared venv
    [[ -f "$ROOT/services/api/requirements.txt" ]] && pip install -q -r "$ROOT/services/api/requirements.txt"
    [[ -f "$ROOT/projects/01-llm-lab/api/requirements.txt" ]] && pip install -q -r "$ROOT/projects/01-llm-lab/api/requirements.txt"
    [[ -f "$ROOT/projects/02-agent-desk/api/requirements.txt" ]] && pip install -q -r "$ROOT/projects/02-agent-desk/api/requirements.txt"
    [[ -f "$ROOT/projects/03-research-digest/requirements.txt" ]] && pip install -q -r "$ROOT/projects/03-research-digest/requirements.txt"
    
    # Install honcho for process management
    pip install -q honcho
    
    # Install edgartools for MCP if available
    pip install -q "edgartools[ai]" 2>/dev/null || log "Could not install edgartools - MCP server will sleep"
  fi
  
  # Add .venv/bin to PATH for this session
  export PATH="$ROOT/.venv/bin:$PATH"
}

sync_artifacts() {
  if [[ -d "$ROOT/content/artifacts" ]]; then
    mkdir -p "$ROOT/apps/web/public/artifacts"
    cp -R "$ROOT/content/artifacts/." "$ROOT/apps/web/public/artifacts/"
  fi
}

# Load .env into this shell (export for child processes)
load_env() {
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
  export NEXT_PUBLIC_API_BASE_URL="${NEXT_PUBLIC_API_BASE_URL:-http://localhost:${API_PORT}}"
  export LLM_LAB_URL="${LLM_LAB_URL:-http://localhost:3100}"
  export AGENT_DESK_URL="${AGENT_DESK_URL:-http://localhost:3200}"
  export RESEARCH_DIGEST_URL="${RESEARCH_DIGEST_URL:-http://localhost:3300}"
}

check_ports() {
  local ports=("$@")
  for port in "${ports[@]}"; do
    if port_in_use "$port"; then
      err "Port $port already in use. Stop the other process or change ports."
      exit 1
    fi
  done
}

start_with_honcho() {
  # Remaining args are process names (space-separated). Empty = all.
  if ! command -v honcho >/dev/null 2>&1; then
    err "honcho not found in PATH. Install with: pip install honcho"
    exit 1
  fi

  print_urls "$PROFILE"
  if [[ $# -gt 0 ]]; then
    log "Starting services: $*"
    exec honcho start -f Procfile "$@"
  else
    log "Starting all services with honcho…"
    exec honcho start -f Procfile
  fi
}

wait_http() {
  local url="$1" name="$2" tries=40
  for ((i = 1; i <= tries; i++)); do
    if curl -sf "$url" >/dev/null 2>&1; then
      ok "$name ready — $url"
      return 0
    fi
    sleep 0.25
  done
  err "$name did not become ready at $url"
  return 1
}

print_urls() {
  local profile="$1"
  printf '\n'
  case "$profile" in
    all)
      ok "Portfolio     →  http://localhost:${WEB_PORT}"
      ok "LLM Lab zone →  http://localhost:${WEB_PORT}/demos/llm-lab"
      ok "Agent Desk   →  http://localhost:${WEB_PORT}/demos/agent-desk"
      ok "Research Digest →  http://localhost:${WEB_PORT}/demos/research-digest"
      ok "API docs     →  http://localhost:${API_PORT}/docs"
      ok "Lab API      →  http://localhost:8100/docs"
      ok "Desk API     →  http://localhost:8200/docs"
      ok "Digest API   →  http://localhost:8300/docs"
      ok "Yahoo MCP    →  http://localhost:8211/health"
      ok "Edgar MCP    →  http://localhost:8210/mcp"
      ok "Status       →  http://localhost:${WEB_PORT}/status"
      ;;
    portfolio)
      ok "Portfolio →  http://localhost:${WEB_PORT}"
      ok "API docs  →  http://localhost:${API_PORT}/docs"
      ;;
    lab)
      ok "LLM Lab   →  http://localhost:3100"
      ok "Lab API   →  http://localhost:8100/docs"
      ;;
    desk)
      ok "Agent Desk →  http://localhost:3200"
      ok "Desk API   →  http://localhost:8200/docs"
      ;;
    digest)
      ok "Research Digest →  http://localhost:3300"
      ok "Digest API      →  http://localhost:8300/docs"
      ;;
  esac
  printf '%sCtrl+C to stop all services.%s\n\n' "$DIM" "$RESET"
}

printf '\n%sAnna Mosaki — Kinetic Atelier%s\n' "$BONE" "$RESET"
printf '%sMulti-zone monorepo · portfolio + demos%s\n\n' "$DIM" "$RESET"

ensure_env
load_env
ensure_node
ensure_python
sync_artifacts

case "$PROFILE" in
  all)
    check_ports 3000 8000 3100 8100 3200 8200 3300 8300 8210 8211
    start_with_honcho
    ;;
  portfolio)
    check_ports 3000 8000
    start_with_honcho portfolio-web portfolio-api
    ;;
  lab)
    check_ports 3100 8100
    start_with_honcho lab-web lab-api
    ;;
  desk)
    check_ports 3200 8200
    start_with_honcho desk-web desk-api
    ;;
  digest)
    check_ports 3300 8300
    start_with_honcho digest-web digest-api
    ;;
esac

# Unreachable when honcho execs successfully
print_urls "$PROFILE"
wait