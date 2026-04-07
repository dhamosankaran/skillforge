#!/usr/bin/env bash
# HirePort AI — Start Script
# Kills any stale processes on ports 8000 & 5199, activates venv, then starts backend + frontend.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/hirelens-backend"
FRONTEND_DIR="$ROOT_DIR/hirelens-frontend"
VENV_DIR="$BACKEND_DIR/venv"
BACKEND_PORT=8000
FRONTEND_PORT=5199

# ── Colours ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

info()    { echo -e "${CYAN}[hireport]${NC} $*"; }
success() { echo -e "${GREEN}[hireport]${NC} $*"; }
warn()    { echo -e "${YELLOW}[hireport]${NC} $*"; }
error()   { echo -e "${RED}[hireport]${NC} $*" >&2; }

# ── 1. Kill stale processes ─────────────────────────────────────────────────────
kill_port() {
  local port=$1
  local pids
  pids=$(lsof -ti tcp:"$port" 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    warn "Port $port is in use (PID $pids). Killing..."
    echo "$pids" | xargs kill -9 2>/dev/null || true
    sleep 0.5
    success "Port $port cleared."
  fi
}

info "Checking for stale processes..."
kill_port "$BACKEND_PORT"
kill_port "$FRONTEND_PORT"

# ── 2. Check / activate Python venv ────────────────────────────────────────────
info "Checking Python virtual environment..."

if [[ ! -d "$VENV_DIR" ]]; then
  warn "venv not found at $VENV_DIR — creating one..."
  python3 -m venv "$VENV_DIR"
  success "venv created."
fi

# Activate
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"
success "venv activated: $(python --version)"

# Install / sync dependencies if requirements.txt is newer than venv marker
MARKER="$VENV_DIR/.deps_installed"
if [[ ! -f "$MARKER" ]] || [[ "$BACKEND_DIR/requirements.txt" -nt "$MARKER" ]]; then
  info "Installing/updating Python dependencies..."
  pip install --quiet --upgrade pip
  pip install --quiet -r "$BACKEND_DIR/requirements.txt"
  # Download spaCy model if missing
  python -c "import spacy; spacy.load('en_core_web_sm')" 2>/dev/null \
    || { info "Downloading spaCy model en_core_web_sm..."; python -m spacy download en_core_web_sm --quiet; }
  touch "$MARKER"
  success "Python dependencies up to date."
fi

# ── 3. Check frontend node_modules ─────────────────────────────────────────────
info "Checking frontend dependencies..."
if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  warn "node_modules missing — running npm install..."
  (cd "$FRONTEND_DIR" && npm install --silent)
  success "npm packages installed."
fi

# ── 4. Check .env files ─────────────────────────────────────────────────────────
if [[ ! -f "$BACKEND_DIR/.env" ]]; then
  warn "Backend .env not found. Copying from .env.example..."
  cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
  warn "⚠️  Edit $BACKEND_DIR/.env and set GEMINI_API_KEY before using AI features."
fi

if [[ ! -f "$FRONTEND_DIR/.env" ]]; then
  warn "Frontend .env not found. Copying from .env.example..."
  cp "$FRONTEND_DIR/.env.example" "$FRONTEND_DIR/.env"
fi

# ── 5. Start backend ────────────────────────────────────────────────────────────
info "Starting backend (FastAPI on :$BACKEND_PORT)..."
(
  cd "$BACKEND_DIR"
  source "$VENV_DIR/bin/activate"
  uvicorn app.main:app --reload --port "$BACKEND_PORT" --log-level info \
    > "$ROOT_DIR/logs/backend.log" 2>&1 &
  echo $! > "$ROOT_DIR/logs/backend.pid"
)
success "Backend started (PID $(cat "$ROOT_DIR/logs/backend.pid")). Log → logs/backend.log"

# ── 6. Start frontend ───────────────────────────────────────────────────────────
info "Starting frontend (Vite on :$FRONTEND_PORT)..."
(
  cd "$FRONTEND_DIR"
  npm run dev -- --port "$FRONTEND_PORT" \
    > "$ROOT_DIR/logs/frontend.log" 2>&1 &
  echo $! > "$ROOT_DIR/logs/frontend.pid"
)
success "Frontend started (PID $(cat "$ROOT_DIR/logs/frontend.pid")). Log → logs/frontend.log"

# ── 7. Wait and verify ──────────────────────────────────────────────────────────
info "Waiting for services to come up..."
sleep 3

check_port() {
  local port=$1 name=$2
  if lsof -ti tcp:"$port" &>/dev/null; then
    success "$name is listening on :$port"
  else
    error "$name did NOT start on :$port — check logs/$name.log"
  fi
}

check_port "$BACKEND_PORT"  "backend"
check_port "$FRONTEND_PORT" "frontend"

echo ""
success "HirePort AI is running!"
echo -e "  ${CYAN}Frontend:${NC} http://localhost:$FRONTEND_PORT"
echo -e "  ${CYAN}Backend:${NC}  http://localhost:$BACKEND_PORT"
echo -e "  ${CYAN}API Docs:${NC} http://localhost:$BACKEND_PORT/docs"
echo ""
info "To stop all services: ./scripts/stop.sh"
