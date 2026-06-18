#!/usr/bin/env bash
#
# setup-graphify.sh — portable, idempotent graphify install + MCP registration.
#
# Wires the graphify knowledge-graph MCP server into Claude Code on ANY machine
# using $HOME-relative paths. Kills the hardcoded /Users/<name> problem that made
# graphify silently skip on cloned/synced setups.
#
# Package note: the PyPI package is "graphifyy" (double-y); its CLI entrypoint is
# "graphify" (single-y). `uv tool install graphify` FAILS — must be graphifyy.
#
# Usage:
#   bash ~/.claude/scripts/setup-graphify.sh
#   bash ~/.claude/scripts/setup-graphify.sh --upgrade   # also bump graphifyy to latest
#
set -euo pipefail

UPGRADE=0
[ "${1:-}" = "--upgrade" ] && UPGRADE=1

GRAPH_DIR="$HOME/.claude/graphify-out/unified"
GRAPH_JSON="$GRAPH_DIR/graph.json"

say() { printf '\033[1;36m==>\033[0m %s\n' "$1"; }
warn() { printf '\033[1;33mWARN\033[0m %s\n' "$1"; }
die() { printf '\033[1;31mERROR\033[0m %s\n' "$1" >&2; exit 1; }

# 1. Preconditions -----------------------------------------------------------
command -v uv >/dev/null 2>&1 || die "uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
command -v claude >/dev/null 2>&1 || warn "claude CLI not found on PATH — MCP registration step will be skipped."

# 2. Install the tool (correct package name: graphifyy) ----------------------
if uv tool list 2>/dev/null | grep -q '^graphifyy '; then
  say "graphifyy already installed."
  [ "$UPGRADE" = "1" ] && { say "Upgrading graphifyy..."; uv tool upgrade graphifyy; }
else
  say "Installing graphifyy (CLI entrypoint: graphify)..."
  uv tool install graphifyy
fi

# 3. Resolve the tool's python dynamically ($HOME-safe, no hardcoded user) ----
UV_TOOL_BASE="$(uv tool dir)"
UV_PY="$UV_TOOL_BASE/graphifyy/bin/python"
[ -x "$UV_PY" ] || die "graphifyy python not found at $UV_PY after install."
say "Tool python: $UV_PY"

# 4. Ensure the unified graph exists (seed a valid empty graph if absent) -----
mkdir -p "$GRAPH_DIR"
if [ ! -s "$GRAPH_JSON" ]; then
  say "No graph.json — seeding empty networkx node-link graph at $GRAPH_JSON"
  # Schema matches live: keys directed/multigraph/graph/nodes/links.
  # Edges live under "links" (NOT "edges") — wrong key silently drops all edges.
  printf '%s\n' '{"directed": true, "multigraph": false, "graph": {}, "nodes": [], "links": []}' > "$GRAPH_JSON"
else
  say "graph.json present ($(wc -c < "$GRAPH_JSON" | tr -d ' ') bytes) — leaving as is."
fi

# 5. Register the MCP server with $HOME-relative paths -----------------------
if command -v claude >/dev/null 2>&1; then
  if claude mcp list 2>/dev/null | grep -q '^graphify[: ]'; then
    say "graphify MCP already registered — re-registering with current paths."
    claude mcp remove graphify >/dev/null 2>&1 || true
  fi
  say "Registering graphify MCP server..."
  claude mcp add graphify -- "$UV_PY" -m graphify.serve "$GRAPH_JSON"

  say "Verifying connection..."
  if claude mcp list 2>/dev/null | grep -i graphify; then
    say "graphify MCP registered. Restart your Claude session to load it."
  else
    warn "Registration ran but graphify not visible in 'claude mcp list'. Check 'claude mcp list' manually."
  fi
else
  warn "Skipped MCP registration (no claude CLI). Run this when claude is on PATH:"
  printf '    claude mcp add graphify -- "%s" -m graphify.serve "%s"\n' "$UV_PY" "$GRAPH_JSON"
fi

# 6. Next steps --------------------------------------------------------------
cat <<EOF

Done.
  Tool:   graphifyy $(uv tool list 2>/dev/null | awk '/^graphifyy /{print $2}')
  Graph:  $GRAPH_JSON
  MCP:    graphify -> $UV_PY -m graphify.serve <graph>

Next:
  1. Restart the Claude Code session so the MCP server loads.
  2. The seeded graph is empty — real project graphs populate it via
     /save-state Step 11b (per-project graph build + merge into unified).
  3. Verify in-session: graph enrichment should no longer say "graphify MCP not active".
EOF
