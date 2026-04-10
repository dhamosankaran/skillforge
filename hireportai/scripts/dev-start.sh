#!/usr/bin/env bash
# HirePort AI — Dev Start Script
# Clean startup of all local services: PostgreSQL, Redis, backend, frontend, Stripe CLI.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/hirelens-backend"
FRONTEND_DIR="$ROOT_DIR/hirelens-frontend"
VENV_DIR="$BACKEND_DIR/venv"
LOG_DIR="$ROOT_DIR/logs"
PID_FILE="$ROOT_DIR/.dev-pids"
BACKEND_PORT=8000
FRONTEND_PORT=5199

# ── Colours ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${CYAN}[dev-start]${NC} $*"; }
success() { echo -e "${GREEN}[dev-start]${NC} $*"; }
warn()    { echo -e "${YELLOW}[dev-start]${NC} $*"; }
error()   { echo -e "${RED}[dev-start]${NC} $*" >&2; }

# ── Pre-flight: stop any existing dev session ──────────────────────────────────
if [[ -f "$PID_FILE" ]]; then
  warn "Found existing .dev-pids — stopping previous session first..."
  "$ROOT_DIR/scripts/dev-stop.sh" 2>/dev/null || true
fi

mkdir -p "$LOG_DIR"

# ── 1. Start PostgreSQL ───────────────────────────────────────────────────────
info "Starting PostgreSQL 16..."
brew services start postgresql@16 2>/dev/null || true

info "Waiting for PostgreSQL to be ready..."
for i in $(seq 1 30); do
  if pg_isready -q 2>/dev/null; then
    success "PostgreSQL is ready."
    break
  fi
  if [[ $i -eq 30 ]]; then
    error "PostgreSQL did not become ready in 30 seconds."
    exit 1
  fi
  sleep 1
done

# ── 2. Start Redis ────────────────────────────────────────────────────────────
info "Starting Redis..."
brew services start redis 2>/dev/null || true

info "Waiting for Redis to be ready..."
for i in $(seq 1 15); do
  if redis-cli ping 2>/dev/null | grep -q PONG; then
    success "Redis is ready."
    break
  fi
  if [[ $i -eq 15 ]]; then
    error "Redis did not become ready in 15 seconds."
    exit 1
  fi
  sleep 1
done

# ── 3. Activate venv ──────────────────────────────────────────────────────────
if [[ ! -d "$VENV_DIR" ]]; then
  error "Python venv not found at $VENV_DIR. Run scripts/start.sh first to bootstrap."
  exit 1
fi
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

# ── 4. Run Alembic migrations ─────────────────────────────────────────────────
info "Applying pending database migrations..."
(cd "$BACKEND_DIR" && alembic upgrade head)
success "Database migrations applied."

# ── 5. Kill stale processes on dev ports ───────────────────────────────────────
kill_port() {
  local port=$1
  local pids
  pids=$(lsof -ti tcp:"$port" 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    warn "Port $port is in use (PID $pids). Killing..."
    echo "$pids" | xargs kill -9 2>/dev/null || true
    sleep 0.5
  fi
}

kill_port "$BACKEND_PORT"
kill_port "$FRONTEND_PORT"

# Initialize PID tracking
> "$PID_FILE"

# ── 6. Start backend ──────────────────────────────────────────────────────────
info "Starting backend (FastAPI on :$BACKEND_PORT)..."
(
  cd "$BACKEND_DIR"
  source "$VENV_DIR/bin/activate"
  uvicorn app.main:app --reload --port "$BACKEND_PORT" --log-level info \
    > "$LOG_DIR/backend.log" 2>&1 &
  echo "backend:$!" >> "$PID_FILE"
  echo $!
) | read -r BACKEND_PID
BACKEND_PID=$(grep '^backend:' "$PID_FILE" | cut -d: -f2)
success "Backend started (PID $BACKEND_PID)"

# ── 7. Start frontend ─────────────────────────────────────────────────────────
info "Starting frontend (Vite on :$FRONTEND_PORT)..."
(
  cd "$FRONTEND_DIR"
  npm run dev -- --port "$FRONTEND_PORT" \
    > "$LOG_DIR/frontend.log" 2>&1 &
  echo "frontend:$!" >> "$PID_FILE"
)
FRONTEND_PID=$(grep '^frontend:' "$PID_FILE" | cut -d: -f2)
success "Frontend started (PID $FRONTEND_PID)"

# ── 8. Start Stripe CLI (if configured) ───────────────────────────────────────
STRIPE_PID=""
if [[ -f "$BACKEND_DIR/.env" ]] && grep -q '^STRIPE_SECRET_KEY=' "$BACKEND_DIR/.env"; then
  STRIPE_KEY=$(grep '^STRIPE_SECRET_KEY=' "$BACKEND_DIR/.env" | cut -d= -f2-)
  if [[ -n "$STRIPE_KEY" && "$STRIPE_KEY" != "sk_test_placeholder" ]]; then
    info "Starting Stripe CLI webhook listener..."
    stripe listen --forward-to "localhost:$BACKEND_PORT/api/v1/stripe/webhook" \
      > "$LOG_DIR/stripe.log" 2>&1 &
    STRIPE_PID=$!
    echo "stripe:$STRIPE_PID" >> "$PID_FILE"
    success "Stripe CLI started (PID $STRIPE_PID)"
  else
    info "STRIPE_SECRET_KEY is a placeholder — skipping Stripe CLI."
  fi
else
  info "No STRIPE_SECRET_KEY in .env — skipping Stripe CLI."
fi

# ── 9. Wait for services to come up ───────────────────────────────────────────
info "Waiting for services to come up..."
sleep 3

# ── 10. Print summary ─────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}========================================${NC}"
echo -e "${BOLD}${GREEN}  HirePort AI — Dev Environment Ready   ${NC}"
echo -e "${BOLD}${GREEN}========================================${NC}"
echo ""
echo -e "  ${BOLD}URLs:${NC}"
echo -e "    ${CYAN}Frontend:${NC}  http://localhost:$FRONTEND_PORT"
echo -e "    ${CYAN}Backend:${NC}   http://localhost:$BACKEND_PORT"
echo -e "    ${CYAN}API Docs:${NC}  http://localhost:$BACKEND_PORT/docs"
echo ""
echo -e "  ${BOLD}PIDs:${NC}"
echo -e "    ${CYAN}Backend:${NC}   $BACKEND_PID"
echo -e "    ${CYAN}Frontend:${NC}  $FRONTEND_PID"
if [[ -n "$STRIPE_PID" ]]; then
  echo -e "    ${CYAN}Stripe:${NC}    $STRIPE_PID"
fi
echo ""
echo -e "  ${BOLD}Logs:${NC}"
echo -e "    ${CYAN}Backend:${NC}   $LOG_DIR/backend.log"
echo -e "    ${CYAN}Frontend:${NC}  $LOG_DIR/frontend.log"
if [[ -n "$STRIPE_PID" ]]; then
  echo -e "    ${CYAN}Stripe:${NC}    $LOG_DIR/stripe.log"
fi
echo ""
echo -e "  ${BOLD}PID file:${NC}  $PID_FILE"
echo ""
info "To stop:   ./scripts/dev-stop.sh"
info "To status: ./scripts/dev-status.sh"
