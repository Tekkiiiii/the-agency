#!/usr/bin/env bash
#
# bootstrap-machine.sh — portable, idempotent machine bootstrap for the-agency.
#
# Gets a fresh machine from clone → working agency in one pass.
# Three layers: uv tools, CLI tools, MCP servers.
# Safe to re-run: every step checks before acting.
#
# Usage:
#   bash ~/.claude/scripts/bootstrap-machine.sh
#   bash ~/.claude/scripts/bootstrap-machine.sh --upgrade   # also upgrade existing tools
#   bash ~/.claude/scripts/bootstrap-machine.sh --dry-run   # print plan, do nothing
#
# Requirements: uv, node/npm (for gws + npx MCPs), python3 (for markitdown)
# Optional: claude CLI (for MCP registration)
#
# SAFETY: this script reads no credentials, no ~/.claude.json, no .env files.
# All paths are $HOME-relative. No hardcoded usernames or system paths.
#
set -euo pipefail

UPGRADE=0
DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --upgrade)  UPGRADE=1 ;;
    --dry-run)  DRY_RUN=1 ;;
  esac
done

# ── Helpers ──────────────────────────────────────────────────────────────────

say()  { printf '\033[1;36m==>\033[0m %s\n' "$1"; }
ok()   { printf '\033[1;32m  ✓\033[0m %s\n' "$1"; }
warn() { printf '\033[1;33m  !\033[0m %s\n' "$1"; }
skip() { printf '\033[0;90m  -\033[0m %s (skip)\n' "$1"; }
die()  { printf '\033[1;31mERROR\033[0m %s\n' "$1" >&2; exit 1; }

run() {
  # run <description> <command...>
  local desc="$1"; shift
  if [ "$DRY_RUN" = "1" ]; then
    printf '\033[0;90m  DRY-RUN\033[0m %s: %s\n' "$desc" "$*"
    return 0
  fi
  "$@" || warn "$desc: exited $?"
}

# ── Preconditions ─────────────────────────────────────────────────────────────

say "bootstrap-machine.sh — checking preconditions"

command -v uv >/dev/null 2>&1 || die "uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
ok "uv found: $(uv --version 2>/dev/null | head -1)"

if ! command -v node >/dev/null 2>&1; then
  warn "node/npm not found — gws and npx-based MCPs will be skipped."
  HAS_NODE=0
else
  ok "node found: $(node --version)"
  HAS_NODE=1
fi

if ! command -v python3 >/dev/null 2>&1; then
  warn "python3 not found — markitdown will be skipped."
  HAS_PYTHON=0
else
  ok "python3 found: $(python3 --version 2>/dev/null)"
  HAS_PYTHON=1
fi

if ! command -v claude >/dev/null 2>&1; then
  warn "claude CLI not found — MCP registration steps will be skipped."
  HAS_CLAUDE=0
else
  ok "claude CLI found"
  HAS_CLAUDE=1
fi

echo ""

# ── LAYER 1: uv tools ────────────────────────────────────────────────────────
# All tools in this layer are portable Python packages installed via uv tool.
# No secrets, no credentials, no machine-specific paths.

say "LAYER 1 — uv tools"

uv_install() {
  # uv_install <package-name> <entrypoint-check>
  local pkg="$1" entry="$2"
  if uv tool list 2>/dev/null | grep -q "^${pkg} "; then
    if [ "$UPGRADE" = "1" ]; then
      say "Upgrading ${pkg}..."
      run "uv upgrade ${pkg}" uv tool upgrade "$pkg"
    else
      skip "${pkg} already installed"
    fi
  else
    say "Installing ${pkg} (entrypoint: ${entry})..."
    run "uv install ${pkg}" uv tool install "$pkg"
    ok "${pkg} installed"
  fi
}

# graphifyy — knowledge graph builder
# NOTE: PyPI package is "graphifyy" (double-y); CLI entrypoint is "graphify" (single-y).
# `uv tool install graphify` (single-y) FAILS silently — always use the double-y name.
uv_install "graphifyy" "graphify"

# notebooklm-mcp-cli — NotebookLM MCP server (entrypoint: notebooklm-mcp + nlm)
uv_install "notebooklm-mcp-cli" "notebooklm-mcp"

# blue — Python formatter
uv_install "blue" "blue"

# browser-harness — browser automation harness
uv_install "browser-harness" "browser-harness"

# nano-pdf — lightweight PDF utility
uv_install "nano-pdf" "nano-pdf"

echo ""

# ── LAYER 2: other CLI tools ─────────────────────────────────────────────────
# Tools in this layer have varied install methods.
# Anything whose install method is unclear is SKIPPED and documented below
# in the manual checklist — we never fabricate install commands.

say "LAYER 2 — CLI tools"

# ── gws (Google Workspace CLI) ────────────────────────────────────────────────
# Source: npm global package @googleworkspace/cli
# Auth is NOT done here — requires OAuth login, see manual checklist below.
if [ "$HAS_NODE" = "1" ]; then
  if command -v gws >/dev/null 2>&1 && [ "$UPGRADE" = "0" ]; then
    skip "gws already installed ($(gws --version 2>/dev/null | head -1 || echo 'version unknown'))"
  else
    say "Installing gws (Google Workspace CLI)..."
    run "npm install gws" npm install -g @googleworkspace/cli
    ok "gws installed — run 'gws auth login' to authenticate (see checklist below)"
  fi
else
  warn "gws skipped — node/npm not available"
fi

# ── lightpanda (headless browser) ────────────────────────────────────────────
# Source: binary download, OS/arch-specific, from lightpanda-io/browser releases.
# The install script in the lightpanda skill handles this correctly.
if command -v lightpanda >/dev/null 2>&1 && [ "$UPGRADE" = "0" ]; then
  skip "lightpanda already installed"
else
  LIGHTPANDA_SKILL="$HOME/.claude/skills/lightpanda/scripts/install.sh"
  if [ -f "$LIGHTPANDA_SKILL" ]; then
    say "Installing lightpanda via skill install script..."
    run "lightpanda install" bash "$LIGHTPANDA_SKILL"
    ok "lightpanda installed"
  else
    warn "lightpanda install script not found at ${LIGHTPANDA_SKILL}"
    warn "Install manually: bash \$HOME/.claude/skills/lightpanda/scripts/install.sh"
  fi
fi

# ── markitdown (file-to-markdown converter) ───────────────────────────────────
# Source: pip3 (Microsoft's markitdown, python package)
if [ "$HAS_PYTHON" = "1" ]; then
  if command -v markitdown >/dev/null 2>&1 && [ "$UPGRADE" = "0" ]; then
    skip "markitdown already installed"
  else
    say "Installing markitdown..."
    run "pip3 install markitdown" pip3 install markitdown
    ok "markitdown installed"
  fi
else
  warn "markitdown skipped — python3 not available"
fi

# ── hermes (NousResearch AI agent platform) ──────────────────────────────────
# Source: NousResearch curl installer.
# Install creates ~/.hermes/ and adds 'hermes' to ~/.local/bin.
# Auth requires 'hermes login' or manual config — see checklist below.
if command -v hermes >/dev/null 2>&1 && [ "$UPGRADE" = "0" ]; then
  skip "hermes already installed"
else
  say "Installing hermes (NousResearch agent)..."
  warn "hermes install runs an external curl script — review before trusting on new machines:"
  warn "  https://github.com/NousResearch/hermes-agent/blob/main/scripts/install.sh"
  run "hermes install" bash -c 'curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash'
  ok "hermes installed — configure model + auth in ~/.hermes/config.yaml (see checklist)"
fi

# ── dia-tts ───────────────────────────────────────────────────────────────────
# Install method UNCLEAR. The binary at ~/.local/bin/dia-tts is a Python wrapper
# pointing to ~/.local/share/uv/tools/dia-tts/ but 'dia-tts' does not appear in
# 'uv tool list'. Could be a manual/custom install or a non-standard package name.
# DO NOT guess the install command. Listed in manual checklist below.
if command -v dia-tts >/dev/null 2>&1; then
  skip "dia-tts already installed"
else
  warn "dia-tts: install method unclear — see manual checklist below"
fi

echo ""

# ── LAYER 3: MCP servers ─────────────────────────────────────────────────────
# All registered with -s user scope so they load from ANY cwd.
# graphify is handled separately by scripts/setup-graphify.sh (handles
# the seed graph.json, uv tool dir resolution, and user-scope registration).

say "LAYER 3 — MCP server registration"

if [ "$HAS_CLAUDE" = "0" ]; then
  warn "claude CLI not found — skipping all MCP registration"
  cat <<EOF

  Register these manually once the claude CLI is on PATH:

    # graphify (run setup-graphify.sh instead of this raw command):
    bash ~/.claude/scripts/setup-graphify.sh

    # notebooklm-mcp
    NLM_PY=\$(uv tool dir)/notebooklm-mcp-cli/bin/python
    claude mcp add -s user notebooklm-mcp -- "\$NLM_PY" -m notebooklm_mcp.server

    # railway-mcp-server
    claude mcp add -s user railway-mcp-server -- npx -y @railway/mcp-server

    # stitch
    claude mcp add -s user stitch -- npx -y @_davideast/stitch-mcp proxy

EOF
else

  mcp_register() {
    # mcp_register <name> <cmd...>
    local name="$1"; shift
    if claude mcp list 2>/dev/null | grep -q "^${name}[: ]"; then
      if [ "$UPGRADE" = "1" ]; then
        say "Re-registering MCP: ${name}..."
        run "mcp remove ${name}" claude mcp remove -s user "$name" >/dev/null 2>&1 || true
        run "mcp remove ${name} local" claude mcp remove "$name" >/dev/null 2>&1 || true
        run "mcp add ${name}" claude mcp add -s user "$name" -- "$@"
        ok "${name} MCP re-registered (user scope)"
      else
        skip "${name} MCP already registered"
      fi
    else
      say "Registering MCP: ${name}..."
      run "mcp add ${name}" claude mcp add -s user "$name" -- "$@"
      ok "${name} MCP registered (user scope)"
    fi
  }

  # graphify — run the dedicated script which also handles graph.json seeding.
  # This avoids duplicating the uv tool dir resolution logic here.
  if claude mcp list 2>/dev/null | grep -q '^graphify[: ]'; then
    if [ "$UPGRADE" = "1" ]; then
      say "Re-running setup-graphify.sh --upgrade..."
      SETUP_GFY="$HOME/.claude/scripts/setup-graphify.sh"
      [ -f "$SETUP_GFY" ] && run "setup-graphify" bash "$SETUP_GFY" --upgrade || warn "setup-graphify.sh not found at $SETUP_GFY"
    else
      skip "graphify MCP already registered"
    fi
  else
    say "Running setup-graphify.sh for graphify MCP..."
    SETUP_GFY="$HOME/.claude/scripts/setup-graphify.sh"
    if [ -f "$SETUP_GFY" ]; then
      run "setup-graphify" bash "$SETUP_GFY"
    else
      warn "setup-graphify.sh not found at $SETUP_GFY — install graphify MCP manually:"
      warn "  bash ~/.claude/scripts/setup-graphify.sh"
    fi
  fi

  # notebooklm-mcp — uses the uv tool venv Python directly
  NLM_PY="$(uv tool dir 2>/dev/null)/notebooklm-mcp-cli/bin/python"
  if [ -x "$NLM_PY" ]; then
    mcp_register "notebooklm-mcp" "$NLM_PY" -m notebooklm_mcp.server
  else
    warn "notebooklm-mcp python not found at $NLM_PY — was Layer 1 install successful?"
    warn "  After Layer 1 succeeds, run: claude mcp add -s user notebooklm-mcp -- \$NLM_PY -m notebooklm_mcp.server"
  fi

  # railway-mcp-server — npx, no binary needed
  if [ "$HAS_NODE" = "1" ]; then
    mcp_register "railway-mcp-server" npx -y @railway/mcp-server
  else
    warn "railway-mcp-server skipped — npx not available (install node/npm first)"
  fi

  # stitch — npx, no binary needed
  if [ "$HAS_NODE" = "1" ]; then
    mcp_register "stitch" npx -y @_davideast/stitch-mcp proxy
  else
    warn "stitch MCP skipped — npx not available (install node/npm first)"
  fi

fi

echo ""

# ── EXCLUDED MCPs (never bootstrap, document why) ───────────────────────────
#
# These MCPs are deliberately excluded. Do NOT register or touch them here:
#
# telegram-mcp     — private local Node.js script + Telegram credentials.
#                    Project-local, set up per-project with their own .env.
#
# tekkisolutions    — carries live Supabase service-role key + BLOG_PUBLISH_TOKEN.
#                    Never script, never echo, never touch these credentials.
#
# obsidian         — broken: empty command string, Tekki investigating separately.
#                    Leave out until resolved.

# ── MANUAL AUTH CHECKLIST ────────────────────────────────────────────────────
cat <<'CHECKLIST'

────────────────────────────────────────────────────────────────────────────────
MANUAL AUTH CHECKLIST — cannot be scripted; do these by hand after bootstrap
────────────────────────────────────────────────────────────────────────────────

  □  nlm login
       Authenticates notebooklm-mcp-cli against Google.
       Run: nlm login

  □  gws auth login
       OAuth login for Google Workspace CLI.
       Run: gws auth login

  □  railway login
       Authenticates railway CLI / MCP server.
       Run: railway login

  □  hermes config + model
       Edit ~/.hermes/config.yaml — set provider, model, and API key.
       Then run: hermes login  (if applicable for your provider)

  □  dia-tts install
       Install method unclear (wrapper at ~/.local/bin/dia-tts points to
       ~/.local/share/uv/tools/dia-tts/ but package is not in 'uv tool list').
       Manual step: identify the correct package name and install method,
       or copy ~/.local/share/uv/tools/dia-tts/ from an existing machine.

────────────────────────────────────────────────────────────────────────────────
Restart your Claude Code session after bootstrap so all MCP servers load.
────────────────────────────────────────────────────────────────────────────────

  HEAVY RUNTIME SKILLS (opt-in, large downloads)
  ────────────────────────────────────────────────
  These skills are NOT installed by default — they require large downloads
  (300MB–2GB) and install to ~/.agents/skills/. Install only what you need.

  □  hyperframes (HTML-based video composition framework)
       Zero-install via npx — no clone needed. Just run:
         npx --yes hyperframes <command>
       Or install globally: npm install -g hyperframes
       Skill docs: ~/.claude/skills/hyperframes/SKILL.md

  □  video-use (conversation-driven video editor, ~316MB)
       git clone https://github.com/browser-use/video-use ~/.agents/skills/video-use
       cd ~/.agents/skills/video-use
       uv sync   # or: pip install -e .
       # Then symlink into Claude skills:
       ln -sfn ~/.agents/skills/video-use ~/.claude/skills/video-use
       # Requires: ffmpeg (brew install ffmpeg)
       # Optional: ELEVENLABS_API_KEY in .env for speaker diarization

  □  omnivoice-studio (zero-shot TTS + voice cloning, ~2GB with model weights)
       git clone https://github.com/debpalash/OmniVoice-Studio ~/.agents/skills/omnivoice-studio
       cd ~/.agents/skills/omnivoice-studio
       uv sync   # or: pip install -e .
       # Then register the MCP server in ~/.claude/settings.json:
       # See ~/.claude/skills/omnivoice-studio/SKILL.md for MCP registration JSON
       # Start/stop backend: ~/.agents/skills/omnivoice-studio/bin/omnivoicectl up|down

────────────────────────────────────────────────────────────────────────────────

CHECKLIST
