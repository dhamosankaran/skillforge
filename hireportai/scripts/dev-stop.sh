#!/usr/bin/env bash
# HirePort AI — Dev Stop Script
# Clean shutdown of all dev background processes. Use --full to also stop PostgreSQL and Redis.

set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$ROOT_DIR/.dev-pids"
BACKEND_PORT=8000
FRONTEND_PORT=5199
FULL_STOP=false

# Parse flags
for arg in "$@"; do
  case $arg in
    --full) FULL_STOP=true ;;
  esac
done

# ── Colours ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

info()    { echo -e "${CYAN}[dev-stop]${NC} $*"; }
success() { echo -e "${GREEN}[dev-stop]${NC} $*"; }
warn()    { echo -e "${YELLOW}[dev-stop]${NC} $*"; }

# ── Stop processes from .dev-pids ──────────────────────────────────────────────
stopped=()

if [[ -f "$PID_FILE" ]]; then
  while IFS=: read -r name pid; do
    [[ -z "$name" || -z "$pid" ]] && continue
    if kill -0 "$pid" 2>/dev/null; then
      info "Stopping $name (PID $pid)..."
      kill "$pid" 2>/dev/null || true
      sleep 1
      # Force kill if still alive
      if kill -0 "$pid" 2>/dev/null; then
        warn "$name still running — force killing..."
        kill -9 "$pid" 2>/dev/null || true
      fi
      stopped+=("$name")
      success "$name stopped."
    else
      warn "$name (PID $pid) was not running."
      stopped+=("$name (already stopped)")
    fi
  done < "$PID_FILE"
  rm -f "$PID_FILE"
else
  warn "No .dev-pids file found."
fi

# ── Force clear dev ports (catch stragglers) ───────────────────────────────────
kill_port() {
  local port=$1
  local pids
  pids=$(lsof -ti tcp:"$port" 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    warn "Port $port still has processes ($pids). Force killing..."
    echo "$pids" | xargs kill -9 2>/dev/null || true
    success "Port $port cleared."
  fi
}

kill_port "$BACKEND_PORT"
kill_port "$FRONTEND_PORT"

# ── Optionally stop PostgreSQL and Redis ───────────────────────────────────────
if [[ "$FULL_STOP" == true ]]; then
  info "Stopping PostgreSQL 16..."
  brew services stop postgresql@16 2>/dev/null || true
  stopped+=("postgresql")
  success "PostgreSQL stopped."

  info "Stopping Redis..."
  brew services stop redis 2>/dev/null || true
  stopped+=("redis")
  success "Redis stopped."
fi

# ── Summary ────────────────────────────────────────────────────────────────────
echo ""
success "Dev environment stopped."
if [[ ${#stopped[@]} -gt 0 ]]; then
  echo -e "  Stopped: ${stopped[*]}"
fi
if [[ "$FULL_STOP" == false ]]; then
  info "PostgreSQL and Redis left running. Use --full to stop them too."
fi
