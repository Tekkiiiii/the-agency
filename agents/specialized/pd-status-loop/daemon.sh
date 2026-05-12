#!/usr/bin/env bash
# PD Status Loop — persistent daemon
# Runs the Python heartbeat logic every 60 minutes.
# The Python script handles adaptive timing (2h normal / 1h after skip).
#
# To install as a launchd service (macOS):
#   cp pd-status-loop.plist ~/Library/LaunchAgents/
#   launchctl load ~/Library/LaunchAgents/pd-status-loop.plist

set -euo pipefail

AGENT_DIR="$HOME/.claude/agents/specialized/pd-status-loop"
LOG_FILE="$AGENT_DIR/loop.log"

log() {
  echo "[$(date '+%Y-%m-%dT%H:%M:%S')] $*" >> "$LOG_FILE"
}

log "=== PD Status Loop starting ==="
python3 "$AGENT_DIR/heartbeat.py" >> "$LOG_FILE" 2>&1
log "=== PD Status Loop done ==="
