#!/usr/bin/env bash
# HirePort AI — Stop Script
# Gracefully stops backend and frontend processes, then force-kills anything still on the ports.

set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PORT=8000
FRONTEND_PORT=5199

# ── Colours ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

info()    { echo -e "${CYAN}[hireport]${NC} $*"; }
success() { echo -e "${GREEN}[hireport]${NC} $*"; }
warn()    { echo -e "${YELLOW}[hireport]${NC} $*"; }

# ── Stop via PID file ───────────────────────────────────────────────────────────
stop_pid_file() {
  local pidfile=$1 name=$2
  if [[ -f "$pidfile" ]]; then
    local pid
    pid=$(cat "$pidfile")
    if kill -0 "$pid" 2>/dev/null; then
      info "Stopping $name (PID $pid)..."
      kill "$pid" 2>/dev/null || true
      sleep 1
      # Force kill if still alive
      if kill -0 "$pid" 2>/dev/null; then
        warn "$name still running — force killing..."
        kill -9 "$pid" 2>/dev/null || true
      fi
      success "$name stopped."
    else
      warn "$name PID $pid is not running (already stopped)."
    fi
    rm -f "$pidfile"
  fi
}

# ── Force clear a port ──────────────────────────────────────────────────────────
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

# ── Main ────────────────────────────────────────────────────────────────────────
info "Stopping HirePort AI services..."

stop_pid_file "$ROOT_DIR/logs/backend.pid"  "backend"
stop_pid_file "$ROOT_DIR/logs/frontend.pid" "frontend"

# Catch anything that might still be holding the ports
kill_port "$BACKEND_PORT"
kill_port "$FRONTEND_PORT"

success "All HirePort AI services stopped."
