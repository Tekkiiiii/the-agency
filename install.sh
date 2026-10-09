#!/usr/bin/env bash
set -euo pipefail

# The Agency — Install script for macOS/Linux
# Copies skills and agents into ~/.claude/ for Claude Code

# Root precedence must match hooks/lib/resolve-root.sh exactly — otherwise the
# installer writes to one directory and the deployed scripts read from another.
CLAUDE_HOME="${AGENCY_HOME:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# --retired=archive|delete|ask decides what happens to a retired file the user
# EDITED (see "Retired files" below). Parsed FIRST: an invalid value exits 2
# before anything is created or changed. Env AGENCY_RETIRED is the fallback and is
# read by the engine itself (an unknown value there falls back to the default).
RETIRED_FLAG=""
RETIRED_ARG=""
RETIRED_EXPECT=false
for arg in "$@"; do
    if [ "$RETIRED_EXPECT" = true ]; then
        RETIRED_ARG="$arg"; RETIRED_EXPECT=false; continue
    fi
    case "$arg" in
        --retired=*) RETIRED_ARG="${arg#--retired=}"; RETIRED_FLAG="set" ;;
        --retired)   RETIRED_EXPECT=true; RETIRED_FLAG="set" ;;
        *) ;;
    esac
done
if [ "$RETIRED_EXPECT" = true ]; then
    echo "install.sh: --retired needs a value: archive, delete or ask." >&2
    exit 2
fi
if [ -n "$RETIRED_FLAG" ]; then
    case "$RETIRED_ARG" in
        archive|delete|ask) RETIRED_FLAG="--retired=$RETIRED_ARG" ;;
        *)
            echo "install.sh: invalid --retired value '$RETIRED_ARG' (use archive, delete or ask). Nothing was changed." >&2
            exit 2
            ;;
    esac
fi

# Which rung of the ladder above resolved the root (same `:-` emptiness test),
# and whether settings.json existed BEFORE this script runs — it may create one
# below, which would hide the "config lives elsewhere" case on the next run.
# Real case: a Windows user with config on D: synced into the default root,
# which Claude Code never read, and nothing said so.
if [ -n "${AGENCY_HOME:-}" ]; then
    ROOT_SOURCE="AGENCY_HOME"
elif [ -n "${CLAUDE_CONFIG_DIR:-}" ]; then
    ROOT_SOURCE="CLAUDE_CONFIG_DIR"
else
    ROOT_SOURCE="default"
fi
ROOT_WARN=false
if [ "$ROOT_SOURCE" = default ] && [ ! -f "$CLAUDE_HOME/settings.json" ]; then
    ROOT_WARN=true
fi
root_warning() {
    echo "  ⚠ No settings.json at $CLAUDE_HOME, and neither AGENCY_HOME nor CLAUDE_CONFIG_DIR is set."
    echo "    If your Claude Code config lives elsewhere (e.g. D:\\claude or a custom folder),"
    echo "    set CLAUDE_CONFIG_DIR or AGENCY_HOME to that folder and re-run."
}

echo ""
echo "The Agency — Installing to $CLAUDE_HOME"
echo "========================================="
if [ "$ROOT_SOURCE" = default ]; then
    echo "  Sync root: $CLAUDE_HOME (from default — neither AGENCY_HOME nor CLAUDE_CONFIG_DIR is set)"
else
    echo "  Sync root: $CLAUDE_HOME (from $ROOT_SOURCE)"
fi
[ "$ROOT_WARN" = true ] && root_warning
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
        # Python helpers + data the mods call (model-pin.py, claude_pricing.py,
        # exec-model-map.json). Top-level lib/ files only: never __pycache__.
        cp "$HOOKS_SRC"/lib/*.py "$HOOKS_DEST/lib/" 2>/dev/null || true
        cp "$HOOKS_SRC"/lib/*.json "$HOOKS_DEST/lib/" 2>/dev/null || true
        chmod +x "$HOOKS_DEST"/lib/*.sh 2>/dev/null || true
    fi

    # The manifest of wired hooks (read by `agency hooks sync`; deployed so the
    # installed tree matches what `agency upgrade` syncs).
    [ -f "$HOOKS_SRC/hooks.json" ] && cp "$HOOKS_SRC/hooks.json" "$HOOKS_DEST/hooks.json"

    # Install default profile if not already set
    if [ ! -f "$CLAUDE_HOME/.hook-profile" ] && [ -f "$HOOKS_SRC/.hook-profile.template" ]; then
        cp "$HOOKS_SRC/.hook-profile.template" "$CLAUDE_HOME/.hook-profile"
    fi

    echo "  ✓ $hook_count hook scripts installed"
else
    echo "  ⚠ No hooks/ directory found"
fi

# --- Wire hooks into settings.json ---
# hooks/hooks.json is the one list of hooks we wire. cli/lib/hooks-merge.js
# merges it into settings.json on EVERY install: it adds missing hooks, updates
# or prunes only entries it owns, never touches the user's own hooks or other
# keys, backs the file up next to itself before any change, and is a no-op on
# disk when nothing changed. The python block it replaces wired hooks only when
# settings.json did not exist yet, so anyone who already used Claude Code got
# none at all. This step never fails the install: when wiring is skipped or
# errors, the exact command to finish it is printed instead.
# Opt out with AGENCY_NO_HOOKS=1 (same test as hooks-merge.js: set and not 0).
HOOKS_MERGE="$SCRIPT_DIR/cli/lib/hooks-merge.js"
hooks_manual() {
    echo "    agency hooks sync"
    echo "  or, without the agency command:"
    echo "    node \"$HOOKS_MERGE\" sync --root \"$CLAUDE_HOME\""
    echo "  Then: Restart Claude Code to activate the hooks."
}
if [ -n "${AGENCY_NO_HOOKS:-}" ] && [ "${AGENCY_NO_HOOKS}" != 0 ]; then
    echo "  Hooks: NOT wired: AGENCY_NO_HOOKS=1 is set. To set them up, run:"
    hooks_manual
elif ! command -v node >/dev/null 2>&1; then
    echo "  Hooks: NOT wired: Node.js (node) was not found. Install Node.js, then run:"
    hooks_manual
elif [ ! -f "$HOOKS_MERGE" ] || [ ! -f "$HOOKS_SRC/hooks.json" ]; then
    echo "  Hooks: NOT wired: cli/lib/hooks-merge.js or hooks/hooks.json is missing from $SCRIPT_DIR."
else
    node "$HOOKS_MERGE" sync --root "$CLAUDE_HOME" --auto 2>&1 | sed 's/^/  /' || true
fi

# --- Mods ---
# mods/<name>/ are Claude Code mods (plugins of function hooks). The ONE helper
# cli/lib/mods-merge.js copies each to $CLAUDE_HOME/mods/<name> and merges the
# copies into settings.json env.CLAUDE_CODE_PLUGIN_DIRS: after every entry the
# user already had, deduped by plugin name, recorded in the hooks state file so
# `agency mods remove` can undo exactly that. It needs Claude Code 2.1.287+ (on
# older versions it prints a one-line skip note and writes nothing) and never
# fails the install: when skipped or on error, the command to finish is printed.
# Opt out with AGENCY_NO_MODS=1 (same test as mods-merge.js: set and not 0).
MODS_MERGE="$SCRIPT_DIR/cli/lib/mods-merge.js"
mods_manual() {
    echo "    agency mods sync"
    echo "  or, without the agency command:"
    echo "    node \"$MODS_MERGE\" sync --root \"$CLAUDE_HOME\" --repo \"$SCRIPT_DIR\""
    echo "  Then: Restart Claude Code to load the mods."
}
if [ -n "${AGENCY_NO_MODS:-}" ] && [ "${AGENCY_NO_MODS}" != 0 ]; then
    echo "  Mods: NOT wired: AGENCY_NO_MODS=1 is set. To set them up, run:"
    mods_manual
elif ! command -v node >/dev/null 2>&1; then
    echo "  Mods: NOT wired: Node.js (node) was not found. Install Node.js, then run:"
    mods_manual
elif [ ! -f "$MODS_MERGE" ]; then
    echo "  Mods: NOT wired: cli/lib/mods-merge.js is missing from $SCRIPT_DIR."
else
    node "$MODS_MERGE" sync --root "$CLAUDE_HOME" --repo "$SCRIPT_DIR" --auto 2>&1 | sed 's/^/  /' || true
fi
# --- Retired files ---
# Files the repo RETIRED (a skill, agent, runbook or core doc it shipped once and
# deleted since) stay installed forever because the copies above only add. The ONE
# helper cli/lib/retired-prune.js reads retired-manifest.json: an untouched
# retired file is deleted; one you EDITED is listed under "You changed these" and
# archived to <root>/archive/agency-retired-<date>/ (or deleted with
# --retired=delete). On a real terminal it runs directly, so "ask" prompts; when
# piped (CI, `curl | bash`) "ask" degrades to archive. Nothing outside the
# manifest is touched, a git work-tree root is skipped, and it never fails the
# install: when skipped or on error, the command to finish is printed.
RETIRED_PRUNE="$SCRIPT_DIR/cli/lib/retired-prune.js"
retired_manual() {
    echo "    agency prune"
    echo "  or, without the agency command:"
    echo "    node \"$RETIRED_PRUNE\" prune --root \"$CLAUDE_HOME\" --repo \"$SCRIPT_DIR\""
}
if ! command -v node >/dev/null 2>&1; then
    echo "  Retired files: NOT checked: Node.js (node) was not found. Install Node.js, then run:"
    retired_manual
elif [ ! -f "$RETIRED_PRUNE" ]; then
    echo "  Retired files: NOT checked: cli/lib/retired-prune.js is missing from $SCRIPT_DIR."
    retired_manual
else
    # RETIRED_FLAG is empty or one --retired=X word; unquoted on purpose.
    # shellcheck disable=SC2086
    # On a real terminal (stdin AND stdout are ttys) run the engine directly so
    # process.stdout.isTTY is true and "ask" can prompt; otherwise pipe it (indent)
    # and "ask" degrades to archive.
    if [ -t 0 ] && [ -t 1 ]; then
        node "$RETIRED_PRUNE" prune --root "$CLAUDE_HOME" --repo "$SCRIPT_DIR" ${RETIRED_FLAG} || true
    else
        node "$RETIRED_PRUNE" prune --root "$CLAUDE_HOME" --repo "$SCRIPT_DIR" ${RETIRED_FLAG} 2>&1 | sed 's/^/  /' || true
    fi
fi

# --- Core docs ---
# NOT a blind `cp -r`. A few files under core/memory/ ship as empty scaffolds
# that the running system appends rows to AT THEIR INSTALLED PATH — the project
# registry, the delegator route cache, the operator's quality thresholds. A
# recursive overwrite destroyed those rows on every reinstall, silently and with
# exit code 0. core/.preserve lists them; the rule is skip-if-exists, so a fresh
# install still seeds them and everything else still refreshes. That one list is
# also read by install.ps1 and by syncCore() in cli/commands/sync-assets.js —
# add a path there, not here.
CORE_SRC="$SCRIPT_DIR/core"
CORE_DEST="$CLAUDE_HOME/core"
if [ -d "$CORE_SRC" ]; then
    mkdir -p "$CORE_DEST"

    # bash 3.2 (macOS) has no associative arrays, so membership is a fixed-string
    # whole-line grep over a newline-delimited string. Comments and blank lines
    # are stripped once, here.
    core_preserve=""
    if [ -f "$CORE_SRC/.preserve" ]; then
        core_preserve=$(sed -e 's/#.*$//' -e 's/[[:space:]]*$//' "$CORE_SRC/.preserve" | grep -v '^$' || true)
    fi

    core_synced=0
    core_preserved=0
    while IFS= read -r core_rel; do
        [ -n "$core_rel" ] || continue
        case "$core_rel" in
            .DS_Store|*/.DS_Store|__pycache__/*|*/__pycache__/*|*.pyc) continue ;;
        esac
        if [ -e "$CORE_DEST/$core_rel" ] \
           && printf '%s\n' "$core_preserve" | grep -qxF -- "$core_rel"; then
            core_preserved=$((core_preserved + 1))
            continue
        fi
        mkdir -p "$CORE_DEST/$(dirname "$core_rel")"
        cp "$CORE_SRC/$core_rel" "$CORE_DEST/$core_rel"
        core_synced=$((core_synced + 1))
    done < <(cd "$CORE_SRC" && find . -type f | sed 's|^\./||')

    echo "  ✓ Core docs installed ($core_synced synced, $core_preserved preserved)"
fi

# --- Project registry ---
# ONE registry path: $CLAUDE_HOME/memory/medium-term.md. /recall, /pd-resume,
# /pd-spawn and the spawn-log hooks all read it, and `agency new` /
# project-scaffolder write it. Seed it ONLY when absent, never overwrite: it holds
# the user's projects. The seed is the core/ copy, which is the repo stub on a
# fresh install and the user's own accumulated rows on an upgrade from the time
# project-scaffolder wrote there (core/.preserve keeps that copy). Keep in step
# with ensureRegistry() in cli/lib/registry.js and the block in install.ps1.
REGISTRY="$CLAUDE_HOME/memory/medium-term.md"
if [ ! -e "$REGISTRY" ] && [ -f "$CORE_DEST/memory/medium-term.md" ]; then
    mkdir -p "$CLAUDE_HOME/memory"
    cp "$CORE_DEST/memory/medium-term.md" "$REGISTRY"
    echo "  ✓ Project registry created: $REGISTRY"
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

# --- Agents archive ---
# Role files + ROLE-MAP.md for the archived specialist agents (generalist switch).
# Spawners read `{agency-root}/agents-archive/ROLE-MAP.md` and the role files at
# runtime. Copied as plain files to {agency-root}/agents-archive/, NEVER under
# agents/, so nothing here registers as a spawnable agent type. Keep in sync with
# install.ps1, cli/commands/init.js and cli/commands/upgrade.js — see the deploy
# matrix in docs/INSTALL-LAYOUT.md.
ARCHIVE_SRC="$SCRIPT_DIR/agents-archive"
ARCHIVE_DEST="$CLAUDE_HOME/agents-archive"
if [ -d "$ARCHIVE_SRC" ]; then
    mkdir -p "$ARCHIVE_DEST"
    cp -r "$ARCHIVE_SRC"/* "$ARCHIVE_DEST/"
    find "$ARCHIVE_DEST" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
    echo "  ✓ Agents archive installed"
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
    # Recursive: scripts/skill-route/ (and any future subdir) must not ship bytecode either.
    find "$SCRIPTS_DEST" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
    chmod +x "$SCRIPTS_DEST"/*.sh "$SCRIPTS_DEST"/*.py "$SCRIPTS_DEST"/*.js 2>/dev/null || true
    echo "  ✓ Scripts installed"
fi

# --- Design system ---
# Brand-token SSOT. Shipped design skills resolve brand values from
# `{agency-root}/design-system/brands/{name}.json` at generation time. Not
# shipping this tree makes those references dangle SILENTLY — a skill that
# cannot find its brand file falls back to whatever hex it last hardcoded,
# which is the exact drift the tree exists to prevent. Keep in sync with
# install.ps1 and cli/commands/init.js — see docs/INSTALL-LAYOUT.md.
DESIGN_SYSTEM_SRC="$SCRIPT_DIR/design-system"
DESIGN_SYSTEM_DEST="$CLAUDE_HOME/design-system"
if [ -d "$DESIGN_SYSTEM_SRC" ]; then
    mkdir -p "$DESIGN_SYSTEM_DEST"
    cp -r "$DESIGN_SYSTEM_SRC"/* "$DESIGN_SYSTEM_DEST/"
    chmod +x "$DESIGN_SYSTEM_DEST"/*.js 2>/dev/null || true
    ds_repo_brands=$(ls "$DESIGN_SYSTEM_SRC"/brands/*.json 2>/dev/null | wc -l | tr -d ' ')
    ds_dest_brands=$(ls "$DESIGN_SYSTEM_DEST"/brands/*.json 2>/dev/null | wc -l | tr -d ' ')
    echo "  ✓ Design system installed ($ds_dest_brands brand(s), $(ls "$DESIGN_SYSTEM_DEST"/overlays/*.css 2>/dev/null | wc -l | tr -d ' ') overlay(s))"
    if [ "$ds_repo_brands" != "$ds_dest_brands" ]; then
        echo "  ⚠ Brand count mismatch: repo=$ds_repo_brands installed=$ds_dest_brands"
    fi
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
# One line: the optional skill router ships DISABLED. Read-only: cli/lib/skill-router.js
# checks AGENCY_SKILL_ROUTER=1 in this environment and in the "env" block of
# $CLAUDE_HOME/settings.json (where Claude Code users set it; a terminal does not
# inherit that). Without node, only the process environment is checked: a wrong
# "disabled" is safer than a hand-rolled JSON parse. Never creates the Jev key file.
if command -v node >/dev/null 2>&1 && [ -f "$SCRIPT_DIR/cli/lib/skill-router.js" ]; then
    node "$SCRIPT_DIR/cli/lib/skill-router.js" line "$CLAUDE_HOME" 2>/dev/null || true
elif [ "${AGENCY_SKILL_ROUTER:-}" = "1" ]; then
    echo "Skill router: enabled (AGENCY_SKILL_ROUTER=1)"
else
    echo "Skill router: disabled (see $(cd "$CLAUDE_HOME" && pwd)/scripts/skill-route/README.md to enable)"
fi
[ "$ROOT_WARN" = true ] && root_warning
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
