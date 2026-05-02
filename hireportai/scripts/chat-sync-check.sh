#!/usr/bin/env bash
#
# chat-sync-check.sh — report which chat-Project-relevant files have
# changed since the last upload to the chat Project.
#
# Usage: ./scripts/chat-sync-check.sh [--quiet|--mark]
#
#   (default)  Diff stored SHA against HEAD; warn per stale watched file.
#   --quiet    Suppress the ✅ "current" line; warnings still print.
#   --mark     Stamp `.chat-sync-sha` with current HEAD short SHA.
#              Run this right after re-uploading files to the chat Project.
#
# State: short SHA in `.chat-sync-sha` at repo root (gitignored).
#
# Watched files: SESSION-STATE.md, CODE-REALITY.md, BACKLOG.md,
# CLAUDE.md, AGENTS.md.
#
# Portable bash 3.2+ (macOS + Linux). No external deps beyond git.

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
[ -d hireportai ] && cd hireportai

STATE_FILE=".chat-sync-sha"
WATCHED=(SESSION-STATE.md CODE-REALITY.md BACKLOG.md CLAUDE.md AGENTS.md)

QUIET=0
MARK=0
case "${1:-}" in
  --quiet) QUIET=1 ;;
  --mark)  MARK=1 ;;
  "")      ;;
  *)       echo "usage: $0 [--quiet|--mark]" >&2; exit 1 ;;
esac

if [ "$MARK" -eq 1 ]; then
  sha=$(git rev-parse --short HEAD)
  echo "$sha" > "$STATE_FILE"
  echo "Marked chat-sync at $sha."
  exit 0
fi

if [ ! -f "$STATE_FILE" ]; then
  echo "No $STATE_FILE found — run with --mark after your next chat Project upload."
  exit 0
fi

stored=$(tr -d '[:space:]' < "$STATE_FILE")
if [ -z "$stored" ]; then
  echo "No $STATE_FILE found — run with --mark after your next chat Project upload."
  exit 0
fi

changed=$(git diff --relative --name-only "$stored" HEAD -- "${WATCHED[@]}")
commits=$(git rev-list --count "$stored"..HEAD)

if [ -z "$changed" ]; then
  if [ "$QUIET" -eq 0 ]; then
    echo "✅ Chat Project copies are current."
  fi
  exit 0
fi

while IFS= read -r f; do
  [ -z "$f" ] && continue
  echo "⚠  $f changed ($commits commits since sync)"
done <<< "$changed"
