#!/usr/bin/env bash
# HirePort AI — Dev Status Script
# Health check of all local services.

set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/hirelens-backend"
VENV_DIR="$BACKEND_DIR/venv"
PID_FILE="$ROOT_DIR/.dev-pids"
BACKEND_PORT=8000
FRONTEND_PORT=5199

# ── Colours ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

pass() { echo -e "  ${GREEN}[OK]${NC}   $*"; }
fail() { echo -e "  ${RED}[FAIL]${NC} $*"; }
skip() { echo -e "  ${YELLOW}[SKIP]${NC} $*"; }

echo ""
echo -e "${BOLD}${CYAN}HirePort AI — Service Status${NC}"
echo -e "${CYAN}────────────────────────────${NC}"
echo ""

# ── PostgreSQL ─────────────────────────────────────────────────────────────────
if pg_isready -q 2>/dev/null; then
  pass "PostgreSQL — accepting connections"
else
  fail "PostgreSQL — not responding"
fi

# ── Redis ──────────────────────────────────────────────────────────────────────
if redis-cli ping 2>/dev/null | grep -q PONG; then
  pass "Redis — PONG"
else
  fail "Redis — not responding"
fi

# ── pgvector extension ─────────────────────────────────────────────────────────
if pg_isready -q 2>/dev/null; then
  PGVECTOR=$(psql -d hireport -t -c "SELECT extname FROM pg_extension WHERE extname='vector';" 2>/dev/null | tr -d '[:space:]')
  if [[ "$PGVECTOR" == "vector" ]]; then
    pass "pgvector — extension installed"
  else
    fail "pgvector — extension NOT found in hireport database"
  fi
else
  skip "pgvector — cannot check (PostgreSQL is down)"
fi

# ── Backend ────────────────────────────────────────────────────────────────────
BACKEND_HTTP=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$BACKEND_PORT/health" 2>/dev/null || echo "000")
if [[ "$BACKEND_HTTP" == "200" ]]; then
  pass "Backend — http://localhost:$BACKEND_PORT/health (200 OK)"
else
  fail "Backend — http://localhost:$BACKEND_PORT/health (HTTP $BACKEND_HTTP)"
fi

# ── Frontend ───────────────────────────────────────────────────────────────────
FRONTEND_HTTP=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$FRONTEND_PORT" 2>/dev/null || echo "000")
if [[ "$FRONTEND_HTTP" == "200" ]]; then
  pass "Frontend — http://localhost:$FRONTEND_PORT (200 OK)"
else
  fail "Frontend — http://localhost:$FRONTEND_PORT (HTTP $FRONTEND_HTTP)"
fi

# ── Stripe CLI ─────────────────────────────────────────────────────────────────
if [[ -f "$PID_FILE" ]] && grep -q '^stripe:' "$PID_FILE"; then
  STRIPE_PID=$(grep '^stripe:' "$PID_FILE" | cut -d: -f2)
  if kill -0 "$STRIPE_PID" 2>/dev/null; then
    pass "Stripe CLI — running (PID $STRIPE_PID)"
  else
    fail "Stripe CLI — process $STRIPE_PID not running"
  fi
else
  skip "Stripe CLI — not started"
fi

# ── Database: pending migrations ───────────────────────────────────────────────
if pg_isready -q 2>/dev/null && [[ -d "$VENV_DIR" ]]; then
  MIGRATION_STATUS=$(cd "$BACKEND_DIR" && source "$VENV_DIR/bin/activate" && alembic current 2>/dev/null | tail -1)
  if [[ -n "$MIGRATION_STATUS" ]]; then
    pass "Alembic — $MIGRATION_STATUS"
  else
    fail "Alembic — could not determine migration status"
  fi
else
  skip "Alembic — cannot check (PostgreSQL or venv unavailable)"
fi

# ── .dev-pids file ─────────────────────────────────────────────────────────────
echo ""
if [[ -f "$PID_FILE" ]]; then
  echo -e "${BOLD}Active PIDs (from .dev-pids):${NC}"
  while IFS=: read -r name pid; do
    [[ -z "$name" || -z "$pid" ]] && continue
    if kill -0 "$pid" 2>/dev/null; then
      echo -e "  ${GREEN}$name${NC} — PID $pid (running)"
    else
      echo -e "  ${RED}$name${NC} — PID $pid (dead)"
    fi
  done < "$PID_FILE"
else
  echo -e "${YELLOW}No .dev-pids file found — dev session not started via dev-start.sh${NC}"
fi

echo ""
