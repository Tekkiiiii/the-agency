#!/usr/bin/env bash
# check-bash32-parse.sh — parse every shipped shell script with bash 3.2.
#
# WHY THIS EXISTS
#
# macOS ships bash 3.2.57 as /bin/bash and always will (bash moved to GPLv3 in
# 4.0). It is a standing repo constraint: every script here has to parse there.
# CI runs ubuntu (bash 5.x) and Windows (Git Bash, bash 5.x), so a construct
# that ONLY bash 3.2 rejects reaches main completely unopposed.
#
# One such construct has already shipped and broken a hook. hooks/spawn-logger.sh
# embeds a python block in a QUOTED heredoc inside a `$( )` command
# substitution. bash 3.2 pairs backticks while scanning for the closing paren —
# even though the heredoc is quoted and the backticks are inert to it — so an
# ODD number of literal backticks anywhere in that block makes the whole file
# unparseable:
#
#     line 70: unexpected EOF while looking for matching ``'
#
# Wave 15 fixed it by writing the backticks as \x60 escapes and recorded the
# rule in a comment. A comment is not a guard: nothing stopped the next edit
# from typing a literal one straight back in. This is that guard.
#
# WHY A PARSER AND NOT A GREP
#
# The obvious cheap check — "no literal backtick inside a quoted heredoc" —
# is wrong in both directions. It is a false POSITIVE on spawn-logger.sh as it
# stands today (its explanatory comment contains two literal backticks, an even
# count, which parses fine), and a false NEGATIVE for every other bash 3.2
# incompatibility. Running the actual 3.2 parser has neither problem and costs
# about a second.
#
# HOW IT GETS A 3.2 PARSER
#
# 1. docker `bash:3.2` — GNU bash 3.2.57, the same release macOS ships. This is
#    what CI uses (ubuntu runners have docker preinstalled).
# 2. If docker is unavailable, /bin/bash IF it self-reports 3.2 — the macOS dev
#    machine, i.e. exactly the platform at risk.
# 3. Neither available: FAIL loudly. A guard that quietly skips itself is how
#    the defect above shipped in the first place.
#
# Verified red before it was added: reintroducing a single literal backtick into
# spawn-logger.sh's heredoc fails under both bash:3.2 and macOS /bin/bash with
# the identical message, and passes under bash:5.2 — which is why the existing
# CI could not see it.
set -uo pipefail

cd "$(dirname "$0")/../.." || exit 1

files=$(git ls-files '*.sh')
if [ -z "$files" ]; then
  echo "FAIL: no shell scripts found — is this the repo root?"
  exit 1
fi
count=$(printf '%s\n' "$files" | wc -l | tr -d ' ')

if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  echo "parser: docker bash:3.2 ($count files)"
  # One container, all files. `_` fills $0 so the list starts at $1.
  # shellcheck disable=SC2086
  docker run --rm -v "$PWD:/src:ro" --entrypoint bash bash:3.2 -c '
    rc=0
    for f in "$@"; do
      bash -n "/src/$f" || rc=1
    done
    exit $rc
  ' _ $files
  status=$?
elif [ -x /bin/bash ] && /bin/bash --version | head -1 | grep -q 'version 3\.2'; then
  echo "parser: /bin/bash $( /bin/bash --version | head -1 | sed 's/.*version //;s/ .*//' ) ($count files)"
  status=0
  for f in $files; do
    /bin/bash -n "$f" || status=1
  done
else
  cat <<'EOF'
FAIL: no bash 3.2 parser available.

This check needs one of:
  - docker (it runs the `bash:3.2` image — this is what CI does), or
  - a /bin/bash that reports version 3.2 (a macOS machine).

It does not skip. macOS ships bash 3.2 and a script that only fails there
fails for every macOS user, silently, with CI green.
EOF
  exit 1
fi

if [ "$status" -ne 0 ]; then
  cat <<'EOF'

FAIL: the script(s) above do not parse under bash 3.2 (the macOS /bin/bash).

The known trap: a literal backtick inside a quoted heredoc that is itself
inside a `$( )`. bash 3.2 counts backticks while looking for the closing
paren, quoted heredoc or not, so an odd number breaks the entire file. Write
them as \x60 escapes — hooks/spawn-logger.sh shows the idiom.

bash 5 accepts all of it, so neither the ubuntu nor the Windows job will ever
tell you about it.
EOF
  exit 1
fi

echo "OK: all $count shell scripts parse under bash 3.2"
