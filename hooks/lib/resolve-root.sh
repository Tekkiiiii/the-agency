#!/usr/bin/env bash
# resolve-root.sh — the single source of truth for "where is the agency root?"
#
# Sourced (never executed) by every shell script under hooks/ and scripts/ that
# needs to address a sibling tree. Exports one variable:
#
#   AGENCY_ROOT   absolute path to the installed agency root
#
# Precedence, highest first:
#
#   1. $AGENCY_HOME        — explicit override. What install.sh, install.ps1 and
#                            cli/bin/agency.js already honour, so a user who
#                            installed with AGENCY_HOME=/opt/agency gets scripts
#                            that address /opt/agency too. Before this file
#                            existed they silently addressed ~/.claude instead —
#                            i.e. a different install than the one they ran.
#   2. $CLAUDE_CONFIG_DIR  — Claude Code's own config-dir override. If a user has
#                            relocated it, that is where Claude Code reads skills,
#                            agents and hooks from, so it is the only root worth
#                            writing to. Honouring it here (and in the three
#                            installers) keeps one idiom across the whole system.
#   3. $HOME/.claude       — the default.
#
# Consumers source this by path relative to their own location, not by absolute
# path — resolving the root is precisely the thing they cannot do yet:
#
#   hooks/foo.sh      . "$(dirname "${BASH_SOURCE[0]:-$0}")/lib/resolve-root.sh"
#   hooks/lib/foo.sh  . "$(dirname "${BASH_SOURCE[0]:-$0}")/resolve-root.sh"
#   scripts/foo.sh    . "$(dirname "${BASH_SOURCE[0]:-$0}")/../hooks/lib/resolve-root.sh"
#
# Each call site appends `2>/dev/null || AGENCY_ROOT="${AGENCY_HOME:-$HOME/.claude}"`
# as a degraded fallback so a partial install cannot hard-fail a hook on Claude
# Code's hot path. That inline expression is a deliberate mirror of rule 1+3
# above; this file remains the place to change precedence.
#
# Python twin: scripts/ use the inline equivalent
#   os.environ.get("AGENCY_HOME") or os.environ.get("CLAUDE_CONFIG_DIR") or ~/.claude
# rather than importing, because several of them are run by absolute path from
# arbitrary working directories where an import would not resolve.

AGENCY_ROOT="${AGENCY_HOME:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}}"
export AGENCY_ROOT
