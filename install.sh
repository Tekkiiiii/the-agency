#!/usr/bin/env bash
set -euo pipefail

# The Agency — Install script for macOS/Linux
# Copies skills and agents into ~/.claude/ for Claude Code

# Root precedence must match hooks/lib/resolve-root.sh exactly — otherwise the
# installer writes to one directory and the deployed scripts read from another.
CLAUDE_HOME="${AGENCY_HOME:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}}"
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
    # Canonical skill layout is directory-only: skills/<name>/SKILL.md, plus any
    # supporting assets alongside it (style.css, scripts/, branches/, ...).
    # This loop previously globbed "$SKILLS_SRC"/*.md — the flat layout the repo
    # abandoned and now fails CI on (scripts/check-flat-skills.js). The result
    # was that install.sh silently installed ZERO skills while still printing a
    # success line. Copy whole skill directories, and never partially: a skill
    # is only counted once its SKILL.md is confirmed present in the source.
    for d in "$SKILLS_SRC"/*/; do
        [ ! -d "$d" ] && continue
        name="$(basename "$d")"
        [ ! -f "$d/SKILL.md" ] && continue

        mkdir -p "$SKILLS_DEST/$name"
        cp -R "$d." "$SKILLS_DEST/$name/"
        rm -rf "$SKILLS_DEST/$name/__pycache__"
        skill_count=$((skill_count + 1))
    done

    # Copy INDEX.md
    [ -f "$SKILLS_SRC/INDEX.md" ] && cp "$SKILLS_SRC/INDEX.md" "$SKILLS_DEST/INDEX.md"
    echo "  ✓ $skill_count skills installed"

    # Loud mismatch check — a silent repo-vs-installed gap is exactly the
    # failure mode that hid the flat-layout bug above for this long.
    repo_skill_count=$(find "$SKILLS_SRC" -mindepth 2 -maxdepth 2 -name SKILL.md | wc -l | tr -d ' ')
    if [ "$skill_count" != "$repo_skill_count" ]; then
        echo "  ⚠ Skill count mismatch: repo has $repo_skill_count, installed $skill_count"
    fi
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

    # Shared helper library sourced by other hooks (hooks/lib/resolve-project.sh
    # is `source`d by spawn-completion.sh). The *.sh loop above is top-level
    # only, so without this the sourced helpers were never on disk.
    if [ -d "$HOOKS_SRC/lib" ]; then
        mkdir -p "$HOOKS_DEST/lib"
        cp "$HOOKS_SRC"/lib/*.sh "$HOOKS_DEST/lib/" 2>/dev/null || true
        chmod +x "$HOOKS_DEST"/lib/*.sh 2>/dev/null || true
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
    # Hook commands are written with the RESOLVED root, not a literal ~/.claude.
    # Under a custom AGENCY_HOME the two are different directories, and a
    # settings.json pointing at ~/.claude/hooks/ would silently run nothing.
    python3 -c "
import json
H = '$CLAUDE_HOME/hooks'
hooks_config = {
    'hooks': {
        'PreToolUse': [
            {'matcher': 'Edit|Write', 'hooks': [
                {'type': 'command', 'command': f'bash {H}/gate-guard.sh'},
                {'type': 'command', 'command': f'bash {H}/config-protection.sh'}
            ]},
            {'matcher': 'Bash', 'hooks': [
                {'type': 'command', 'command': f'bash {H}/secret-scanner.sh'}
            ]}
        ],
        'PostToolUse': [
            {'matcher': 'Edit|Write', 'hooks': [
                {'type': 'command', 'command': f'bash {H}/track-edits.sh'}
            ]}
        ],
        'SessionStart': [
            {'matcher': '', 'hooks': [{'type': 'command', 'command': f'bash {H}/startup-sync.sh'}]},
            {'matcher': '', 'hooks': [{'type': 'command', 'command': f'bash {H}/check-settings-secrets.sh'}]},
            {'matcher': '', 'hooks': [{'type': 'command', 'command': f'bash {H}/check-session-state.sh'}]}
        ],
        'Stop': [
            {'matcher': '', 'hooks': [{'type': 'command', 'command': f'bash {H}/session-end.sh && bash {H}/batch-check.sh && bash {H}/cost-tracker.sh'}]}
        ],
        'UserPromptSubmit': [
            {'hooks': [{'type': 'command', 'command': f'bash {H}/fable-on-opus.sh'}]}
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

# --- Runbooks ---
# Protocol docs that deployed agents/ files reference as `{agency-root}/runbooks/...`.
# Not shipping these makes every one of those references dangle. See the deploy
# matrix in docs/INSTALL-LAYOUT.md — this list must stay in sync with
# cli/commands/init.js and install.ps1.
RUNBOOKS_SRC="$SCRIPT_DIR/runbooks"
RUNBOOKS_DEST="$CLAUDE_HOME/runbooks"
if [ -d "$RUNBOOKS_SRC" ]; then
    mkdir -p "$RUNBOOKS_DEST"
    cp -r "$RUNBOOKS_SRC"/* "$RUNBOOKS_DEST/"
    echo "  ✓ Runbooks installed"
fi

# --- Scripts ---
# Support tooling invoked by shipped skills as `{agency-root}/scripts/...`
# (save-state.py, mem-gardener.sh, ...). The CLI installer already synced these;
# install.sh did not, so a shell-installed user had them missing.
SCRIPTS_SRC="$SCRIPT_DIR/scripts"
SCRIPTS_DEST="$CLAUDE_HOME/scripts"
if [ -d "$SCRIPTS_SRC" ]; then
    mkdir -p "$SCRIPTS_DEST"
    cp -r "$SCRIPTS_SRC"/* "$SCRIPTS_DEST/"
    rm -rf "$SCRIPTS_DEST"/__pycache__
    chmod +x "$SCRIPTS_DEST"/*.sh "$SCRIPTS_DEST"/*.py "$SCRIPTS_DEST"/*.js 2>/dev/null || true
    echo "  ✓ Scripts installed"
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
