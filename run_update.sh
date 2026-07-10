#!/bin/bash
# Hourly (or manual) update run for the Atenas Rentals Tracker.
# Invokes Claude Code headlessly with UPDATE_PROMPT.md, which fetches
# current listings, diffs against the last snapshot, rebuilds docs/,
# and commits/pushes if anything changed. See README.md for setup.
set -uo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

# launchd/cron run with a minimal PATH that won't include user-local install
# dirs, so add the known Claude Code CLI location explicitly as a fallback.
export PATH="$HOME/.local/bin:$PATH"

mkdir -p logs
LOG_FILE="logs/update-$(date -u +%Y%m%d).log"

echo "=== Run started: $(date -u +'%Y-%m-%dT%H:%M:%SZ') ===" >> "$LOG_FILE"

if ! command -v claude >/dev/null 2>&1; then
  echo "ERROR: 'claude' CLI not found on PATH (checked \$HOME/.local/bin too). Install Claude Code (https://claude.com/claude-code) or update the PATH line in this script to match its actual location (run 'which claude' in Terminal)." | tee -a "$LOG_FILE"
  exit 1
fi

claude -p "$(cat UPDATE_PROMPT.md)" >> "$LOG_FILE" 2>&1
CLAUDE_EXIT=$?
echo "claude exited with code $CLAUDE_EXIT" >> "$LOG_FILE"

# Safety net: if Claude fetched/updated files but didn't get to the git
# commit/push step (e.g. it ran out of turns), make sure the update still
# gets published rather than silently sitting uncommitted.
if [ -n "$(git status --porcelain)" ]; then
  git add -A
  if ! git diff --cached --quiet; then
    git commit -m "Safety-net commit: $(date -u +'%Y-%m-%d %H:%M UTC')" >> "$LOG_FILE" 2>&1
    git push >> "$LOG_FILE" 2>&1
    echo "Safety-net commit pushed." >> "$LOG_FILE"
  fi
fi

echo "=== Run finished: $(date -u +'%Y-%m-%dT%H:%M:%SZ') ===" >> "$LOG_FILE"
exit $CLAUDE_EXIT
