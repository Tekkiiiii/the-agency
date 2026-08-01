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
# AGENCY_ROOT is deliberately left in whatever string format the environment
# gave it. Under Git Bash that is an MSYS path (/c/Users/me/.claude) and every
# bash consumer handles it natively. It is only at the bash -> python3 boundary
# that the format matters, so that is where it is corrected — see below.
#
# ---------------------------------------------------------------------------
# PYTHON TWIN — the canonical form. Copy it verbatim; do not write a variant.
# ---------------------------------------------------------------------------
#
#   def agency_root(home):
#       root = os.environ.get('AGENCY_HOME') or os.environ.get('CLAUDE_CONFIG_DIR') or os.path.join(home, '.claude')
#       if os.name == 'nt':
#           m = re.fullmatch(r'/(?:cygdrive/)?([A-Za-z])(/.*)?', root)
#           if m:
#               root = m.group(1).upper() + ':' + (m.group(2) or '/')
#       return root
#
# Why the nt branch exists. A Git Bash user who exports
# AGENCY_HOME=/c/Users/me/.claude hands that exact string to python3. The
# python3 first on a Windows PATH is the native build, which reads a leading
# slash as drive-relative-to-the-current-drive, not as an MSYS drive prefix —
# so it happily creates C:\c\Users\me\.claude and writes there, exit code 0,
# and nothing under the real root ever appears. Rewriting /c/... to C:/... at
# this one boundary is the whole fix. The unset (default) case was always fine:
# python computes expanduser("~")/.claude natively.
#
# Why it is guarded on os.name. On macOS and Linux /c/anything is a legitimate
# absolute path and rewriting it would BE the bug. os.name is 'nt' only for a
# native Windows interpreter; an MSYS/Cygwin python reports 'posix' and already
# understands the MSYS form, so the guard selects exactly the broken pairing.
#
# Why it is inlined at every call site rather than imported. Under Git Bash the
# hook's own directory is an MSYS path too, so any sys.path bootstrap would
# have to resolve the same broken string format before the helper that fixes it
# could load. The duplication is forced by the defect, which is why the wording
# above is the single source of truth for it.
#
# Carried by every python block under hooks/. NOT yet carried by scripts/*.py,
# which still use the plain three-line twin: those are user-invoked and have a
# second, larger Windows problem first (python3 cannot load their own script
# path when it is handed to it in MSYS form), so fixing only their env read
# would not make them work. Tracked separately.

AGENCY_ROOT="${AGENCY_HOME:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}}"
export AGENCY_ROOT
