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
# Why the nt branch exists — and what it is NOT.
#
# If the string /c/Users/me/.claude reaches a native Windows python, that python
# reads the leading slash as drive-relative-to-the-current-drive, not as an MSYS
# drive prefix: it creates C:\c\Users\me\.claude, writes there, exits 0, and
# nothing under the real root ever appears. The nt branch rewrites the value so
# that cannot happen.
#
# What the CI red-check established is that Git Bash normally prevents the
# string from arriving that way at all. Git Bash is MSYS2, and MSYS2 converts
# path-shaped environment variables into Windows form whenever it spawns a
# native binary. So `export AGENCY_HOME=/d/a/x` is already D:\a\x by the time
# python reads os.environ — the rewrite is a no-op on that path, and an earlier
# version of the CI step passed against deliberately un-fixed hooks because of
# it. The step now sets MSYS2_ENV_CONV_EXCL to switch that conversion off and
# assert BOTH cases.
#
# So this branch is a backstop, not a fix for an observed Git Bash failure: it
# covers any caller outside MSYS2's conversion rules (conversion excluded, a
# non-MSYS2 POSIX layer, or a value assembled after the process started). It is
# kept because it is free, provably inert everywhere else, and the alternative
# is a silent wrong-directory write. The unset (default) case was always fine:
# python computes expanduser("~")/.claude natively.
#
# The two earlier variants are genuinely different and remain real: a path
# interpolated into python SOURCE, or embedded inside a larger argument, is
# never touched by MSYS2's conversion. Those are what Waves 13 and 14 fixed.
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
# Carried by every python block under hooks/ AND by every scripts/*.py that
# resolves a root (Wave 16). scripts/*.py could import it — python puts the
# script's own directory on sys.path[0] and mem-graph-build.py already imports
# a sibling that way — but they inline it so that exactly one form of this
# function exists in the repo and check-hardcoded-root.sh can compare them all.
#
# Wave 15 deferred them on the grounds that a native python3 "cannot load its
# own script path when that is handed to it in MSYS form", which would have made
# fixing the env read pointless. That was an inference, and measuring it on
# windows-latest (run 30689704116, Git Bash + python 3.12 win32, invoked as
# `python3 /d/a/_temp/.../scripts/skill-audit.py`) showed:
#
#   plain Git Bash                       loads, resolves the right root  (rc=0)
#   MSYS2_ENV_CONV_EXCL=AGENCY_HOME      loads, FileNotFoundError on
#                                        '\d\a\_temp\...\skills'         (rc=1)
#   MSYS2_ARG_CONV_EXCL='*'              cannot load the script at all   (rc=2)
#
# So the script path is normally fine — MSYS2 converts path-shaped ARGUMENTS to
# native binaries just as it converts path-shaped environment variables — and
# the env read was broken in exactly the way the hooks were. That is what the
# twin now fixes here too.
#
# The third row is real and is NOT fixed, because it cannot be: with argument
# conversion disabled the interpreter never opens the file, so no code inside it
# runs. A caller in that configuration must pass a native path (or `cygpath -w`
# it). Documented rather than papered over.

AGENCY_ROOT="${AGENCY_HOME:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}}"
export AGENCY_ROOT
