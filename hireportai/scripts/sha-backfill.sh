#!/usr/bin/env bash
#
# sha-backfill.sh — replace `<this-slice>` placeholders with a real SHA.
#
# Usage: ./scripts/sha-backfill.sh <slice-sha> [--dry-run]
#
# Scope (per docs/audits/process-bloat-2026-05-01.md §5):
#   BACKLOG.md, SESSION-STATE.md, docs/specs/**
#
# Validates <slice-sha> via `git rev-parse --verify`. With --dry-run prints
# a unified-diff preview and exits without writing. Idempotent: running on
# a tree with no placeholders reports "0 replacements" and exits 0.
#
# Pilot per B-091 (Thread B optimization sprint). Single marker only;
# no slice-type classification, no auto-commit. User stages + commits.

set -euo pipefail

MARKER='<this-slice>'

usage() {
  echo "Usage: $0 <slice-sha> [--dry-run]" >&2
  exit 1
}

[ $# -ge 1 ] || usage
SHA="$1"
DRY_RUN=0
[ "${2:-}" = "--dry-run" ] && DRY_RUN=1

# Resolve to short SHA via git; rejects invalid refs.
RESOLVED=$(git rev-parse --verify --short "$SHA" 2>/dev/null) || {
  echo "error: '$SHA' is not a valid SHA in this repo" >&2
  exit 1
}

# Run from repo root (script lives at scripts/sha-backfill.sh).
cd "$(git rev-parse --show-toplevel)"
[ -d hireportai ] && cd hireportai

# Enumerate target files containing the marker. Portable read-loop —
# `mapfile` is bash 4+ only; macOS still ships bash 3.2.
FILES=()
while IFS= read -r f; do
  [ -n "$f" ] && FILES+=("$f")
done < <(
  grep -rl --include='*.md' "$MARKER" \
    BACKLOG.md SESSION-STATE.md docs/specs/ 2>/dev/null || true
)

if [ "${#FILES[@]}" -eq 0 ]; then
  echo "0 replacements — no '$MARKER' placeholders in scope. Exiting."
  exit 0
fi

TOTAL=0
for f in "${FILES[@]}"; do
  COUNT=$(grep -c "$MARKER" "$f" || true)
  TOTAL=$((TOTAL + COUNT))
  if [ "$DRY_RUN" -eq 1 ]; then
    echo "--- $f ($COUNT replacements proposed) ---"
    grep -n "$MARKER" "$f" | while IFS=: read -r line _; do
      echo "  L$line: $MARKER → $RESOLVED"
    done
  else
    tmp=$(mktemp)
    sed "s|$MARKER|$RESOLVED|g" "$f" > "$tmp" && mv "$tmp" "$f"
    echo "$f: $COUNT replacement(s)"
  fi
done

if [ "$DRY_RUN" -eq 1 ]; then
  echo "[dry-run] Total: $TOTAL replacement(s) across ${#FILES[@]} file(s). No writes."
else
  echo "Total: $TOTAL replacement(s) across ${#FILES[@]} file(s). Stage + commit when ready."
fi
