#!/usr/bin/env bash
set -euo pipefail

# The Agency — Install script for macOS/Linux
# Copies skills and agents into ~/.claude/ for Claude Code

CLAUDE_HOME="${AGENCY_HOME:-$HOME/.claude}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "The Agency — Installing to $CLAUDE_HOME"
echo "========================================="
echo ""

# Create directories
mkdir -p "$CLAUDE_HOME"/{skills,agents,hooks,projects,sessions,memory}

# --- Skills ---
SKILLS_SRC="$SCRIPT_DIR/skills"
SKILLS_DEST="$CLAUDE_HOME/skills"
skill_count=0

if [ -d "$SKILLS_SRC" ]; then
    for f in "$SKILLS_SRC"/*.md; do
        [ ! -f "$f" ] && continue
        name="$(basename "$f" .md)"
        [ "$name" = "INDEX" ] || [ "$name" = "README" ] && continue

        mkdir -p "$SKILLS_DEST/$name"
        cp "$f" "$SKILLS_DEST/$name/SKILL.md"
        skill_count=$((skill_count + 1))
    done

    # Copy INDEX.md
    [ -f "$SKILLS_SRC/INDEX.md" ] && cp "$SKILLS_SRC/INDEX.md" "$SKILLS_DEST/INDEX.md"
    echo "  ✓ $skill_count skills installed"
else
    echo "  ⚠ No skills/ directory found"
fi

# --- Agents ---
AGENTS_SRC="$SCRIPT_DIR/agents"
AGENTS_DEST="$CLAUDE_HOME/agents"
agent_count=0

copy_agents() {
    local src="$1" dest="$2"
    for entry in "$src"/*; do
        [ ! -e "$entry" ] && continue
        local name="$(basename "$entry")"
        if [ -d "$entry" ]; then
            mkdir -p "$dest/$name"
            copy_agents "$entry" "$dest/$name"
        elif [[ "$name" == *.md ]]; then
            cp "$entry" "$dest/$name"
            agent_count=$((agent_count + 1))
        fi
    done
}

if [ -d "$AGENTS_SRC" ]; then
    copy_agents "$AGENTS_SRC" "$AGENTS_DEST"
    echo "  ✓ $agent_count agents installed"
else
    echo "  ⚠ No agents/ directory found"
fi

# --- Hooks ---
HOOKS_SRC="$SCRIPT_DIR/hooks"
HOOKS_DEST="$CLAUDE_HOME/hooks"
hook_count=0

if [ -d "$HOOKS_SRC" ]; then
    for f in "$HOOKS_SRC"/*.sh; do
        [ ! -f "$f" ] && continue
        cp "$f" "$HOOKS_DEST/$(basename "$f")"
        chmod +x "$HOOKS_DEST/$(basename "$f")"
        hook_count=$((hook_count + 1))
    done

    # Fable playbook modules (not top-level *.sh — a subdirectory read by fable-on-opus.sh)
    if [ -d "$HOOKS_SRC/fable" ]; then
        mkdir -p "$HOOKS_DEST/fable"
        cp "$HOOKS_SRC"/fable/*.md "$HOOKS_DEST/fable/"
    fi

    # Install default profile if not already set
    if [ ! -f "$CLAUDE_HOME/.hook-profile" ] && [ -f "$HOOKS_SRC/.hook-profile.template" ]; then
        cp "$HOOKS_SRC/.hook-profile.template" "$CLAUDE_HOME/.hook-profile"
    fi

    echo "  ✓ $hook_count hook scripts installed"
else
    echo "  ⚠ No hooks/ directory found"
fi

# --- Wire hooks into settings.json ---
SETTINGS="$CLAUDE_HOME/settings.json"
if [ -f "$SETTINGS" ]; then
    # Check if hooks already wired
    if ! grep -q "gate-guard.sh" "$SETTINGS" 2>/dev/null; then
        echo "  ℹ Hook wiring: add the hooks block from docs/HOOKS.md to $SETTINGS"
        echo "    (Automatic wiring skipped — settings.json exists and may have custom config)"
    else
        echo "  ✓ Hooks already wired in settings.json"
    fi
else
    # Create minimal settings.json with hooks wired
    python3 -c "
import json
hooks_config = {
    'hooks': {
        'PreToolUse': [
            {'matcher': 'Edit|Write', 'hooks': [
                {'type': 'command', 'command': 'bash ~/.claude/hooks/gate-guard.sh'},
                {'type': 'command', 'command': 'bash ~/.claude/hooks/config-protection.sh'}
            ]},
            {'matcher': 'Bash', 'hooks': [
                {'type': 'command', 'command': 'bash ~/.claude/hooks/secret-scanner.sh'}
            ]}
        ],
        'PostToolUse': [
            {'matcher': 'Edit|Write', 'hooks': [
                {'type': 'command', 'command': 'bash ~/.claude/hooks/track-edits.sh'}
            ]}
        ],
        'SessionStart': [
            {'matcher': '', 'hooks': [{'type': 'command', 'command': 'bash ~/.claude/hooks/startup-sync.sh'}]},
            {'matcher': '', 'hooks': [{'type': 'command', 'command': 'bash ~/.claude/hooks/check-settings-secrets.sh'}]},
            {'matcher': '', 'hooks': [{'type': 'command', 'command': 'bash ~/.claude/hooks/check-session-state.sh'}]}
        ],
        'Stop': [
            {'matcher': '', 'hooks': [{'type': 'command', 'command': 'bash ~/.claude/hooks/session-end.sh && bash ~/.claude/hooks/batch-check.sh && bash ~/.claude/hooks/cost-tracker.sh'}]}
        ],
        'UserPromptSubmit': [
            {'hooks': [{'type': 'command', 'command': 'bash ~/.claude/hooks/fable-on-opus.sh'}]}
        ]
    }
}
with open('$SETTINGS', 'w') as f:
    json.dump(hooks_config, f, indent=2)
    f.write('\n')
" 2>/dev/null && echo "  ✓ settings.json created with hooks wired" || echo "  ⚠ Could not create settings.json — wire hooks manually (see docs/HOOKS.md)"
fi

# --- Core docs ---
CORE_SRC="$SCRIPT_DIR/core"
CORE_DEST="$CLAUDE_HOME/core"
if [ -d "$CORE_SRC" ]; then
    mkdir -p "$CORE_DEST"
    cp -r "$CORE_SRC"/* "$CORE_DEST/"
    echo "  ✓ Core docs installed"
fi

# --- CLI command ---
CLI_SRC="$SCRIPT_DIR/cli/bin/agency.js"
if [ -f "$CLI_SRC" ]; then
    chmod +x "$CLI_SRC"
    LINKED=false

    # Try /usr/local/bin first (requires sudo on some systems)
    if [ -w /usr/local/bin ] || [ -w "$(dirname /usr/local/bin/agency 2>/dev/null)" ]; then
        ln -sf "$CLI_SRC" /usr/local/bin/agency
        echo "  ✓ CLI linked → /usr/local/bin/agency"
        LINKED=true
    else
        # Fall back to ~/.local/bin (no sudo needed)
        mkdir -p "$HOME/.local/bin"
        ln -sf "$CLI_SRC" "$HOME/.local/bin/agency"
        echo "  ✓ CLI linked → ~/.local/bin/agency"
        LINKED=true

        # Check if ~/.local/bin is on PATH
        if ! echo "$PATH" | tr ':' '\n' | grep -q "$HOME/.local/bin"; then
            echo ""
            echo "  ⚠ ~/.local/bin is not on your PATH. Add it:"
            echo ""
            if [ -f "$HOME/.zshrc" ]; then
                echo "    echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc && source ~/.zshrc"
            else
                echo "    echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc && source ~/.bashrc"
            fi
        fi
    fi
fi

echo ""
echo "✓ The Agency installed to $CLAUDE_HOME"
echo ""
if [ "$LINKED" = true ]; then
    echo "Next steps:"
    echo "  agency onboard                      Interactive setup wizard"
    echo "  agency new my-app \"description\"      Create your first project"
    echo "  agency status                       See all projects"
else
    echo "Next steps:"
    echo "  node $CLI_SRC onboard               Interactive setup wizard"
fi
echo ""
