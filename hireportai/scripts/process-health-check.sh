#!/usr/bin/env bash
#
# process-health-check.sh — measure SESSION-STATE / BACKLOG / CLAUDE.md
# size against locked caps (B-092 pilot).
#
# Usage: ./scripts/process-health-check.sh [--quiet]
#
# Caps:
#   - SESSION-STATE total lines:           warn 400 / fail 600
#   - SESSION-STATE worst RC entry words:  warn 200 / fail 250
#   - BACKLOG total lines:                 warn 200 / fail 300
#   - BACKLOG active row count:            warn 50  / fail 75
#   - CLAUDE.md total lines:               warn 600 / fail 700
#
# Exit 0 if no fails, 1 if any cap fails. --quiet hides ✓ pass lines.
# Portable bash 3.2+ (no mapfile). Pilot per B-092; CI integration TBD.

set -euo pipefail

QUIET=0
[ "${1:-}" = "--quiet" ] && QUIET=1

cd "$(git rev-parse --show-toplevel)"
[ -d hireportai ] && cd hireportai

FAILED=0

emit() {
  # emit <verdict> <label> <measured> <warn> <fail> <unit>
  local verdict="$1" label="$2" measured="$3" warn="$4" fail="$5" unit="$6"
  if [ "$verdict" = "✓" ] && [ "$QUIET" -eq 1 ]; then
    return
  fi
  printf '%s %-44s %s %s (warn %s / fail %s)\n' \
    "$verdict" "$label" "$measured" "$unit" "$warn" "$fail"
}

verdict_for() {
  # verdict_for <measured> <warn> <fail>
  local m="$1" w="$2" f="$3"
  if [ "$m" -ge "$f" ]; then
    echo "✗"
  elif [ "$m" -ge "$w" ]; then
    echo "⚠️"
  else
    echo "✓"
  fi
}

check_lines() {
  # check_lines <file> <label> <warn> <fail>
  local file="$1" label="$2" warn="$3" fail="$4"
  if [ ! -f "$file" ]; then
    echo "✗ $label  (missing $file)"
    FAILED=1
    return
  fi
  local lines
  lines=$(wc -l < "$file" | tr -d ' ')
  local v
  v=$(verdict_for "$lines" "$warn" "$fail")
  [ "$v" = "✗" ] && FAILED=1
  emit "$v" "$label" "$lines" "$warn" "$fail" "lines"
}

check_session_state_worst_rc_words() {
  # Extract every Recently Completed entry (numbered "N. 2026-..." lines
  # with their continuation paragraphs up to the next numbered entry, the
  # forward-note blockquote, or the next H2). Count `wc -w` per entry,
  # report the maximum.
  local file="SESSION-STATE.md"
  if [ ! -f "$file" ]; then
    echo "✗ SESSION-STATE worst RC entry        (missing $file)"
    FAILED=1
    return
  fi
  local worst
  worst=$(awk '
    /^## Recently Completed/    { rc=1; next }
    rc && /^## /                { rc=0 }
    rc && /^[0-9]+\. 2026/ {
      if (cur != "") { wc=split(cur, a, /[ \t\r\n]+/); if (wc > max) max = wc }
      cur = $0; next
    }
    rc && /^> Recently Completed entries/ {
      if (cur != "") { wc=split(cur, a, /[ \t\r\n]+/); if (wc > max) max = wc }
      cur = ""; next
    }
    rc { cur = cur " " $0 }
    END {
      if (cur != "") { wc=split(cur, a, /[ \t\r\n]+/); if (wc > max) max = wc }
      print max+0
    }
  ' "$file")
  local v
  v=$(verdict_for "$worst" 200 250)
  [ "$v" = "✗" ] && FAILED=1
  emit "$v" "SESSION-STATE worst RC entry" "$worst" 200 250 "words"
}

check_backlog_active_rows() {
  local file="BACKLOG.md"
  if [ ! -f "$file" ]; then
    echo "✗ BACKLOG active rows                 (missing $file)"
    FAILED=1
    return
  fi
  # Active rows live above `## Closed`. Match `| B-NNN |` or `| E-NNN |`
  # rows whose status column (5th pipe-separated field) carries
  # 🔴 / 🟡 / 🟦. Notes-column matches must NOT count, so split on `|`
  # and inspect column 5 specifically.
  local count
  count=$(awk -F'|' '
    /^## Closed/ { exit }
    $2 ~ /^ ?(B|E)-[0-9]+/ && $6 ~ /(🔴|🟡|🟦)/ { n++ }
    END { print n+0 }
  ' "$file")
  local v
  v=$(verdict_for "$count" 50 75)
  [ "$v" = "✗" ] && FAILED=1
  emit "$v" "BACKLOG active rows" "$count" 50 75 "rows"
}

check_lines               "SESSION-STATE.md" "SESSION-STATE total lines"     400 600
check_session_state_worst_rc_words
check_lines               "BACKLOG.md"       "BACKLOG total lines"           200 300
check_backlog_active_rows
check_lines               "CLAUDE.md"        "CLAUDE.md total lines"         600 700

exit "$FAILED"
