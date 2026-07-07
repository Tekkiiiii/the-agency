#!/bin/bash
# fable-on-opus.sh — UserPromptSubmit hook.
# When the active model is an Opus-line model, inject the Fable Thinking discipline:
#   core.md — always, once per session
#   task modules (visual, content, delegation, research, coding, planning, systems)
#     — once per session each, when the prompt matches their keyword profile
# Modules live in ~/.claude/hooks/fable/. Later non-matching prompts get a one-line reminder.
# Model detection order: hook stdin .model → transcript last assistant model → settings.json default.
# Portable for macOS /bin/bash 3.2. Requires jq.

input=$(cat)

session=$(printf '%s' "$input" | jq -r '.session_id // "nosession"')
transcript=$(printf '%s' "$input" | jq -r '.transcript_path // empty')
model=$(printf '%s' "$input" | jq -r '.model // empty')
prompt=$(printf '%s' "$input" | jq -r '.prompt // empty')

if [ -z "$model" ] && [ -n "$transcript" ] && [ -f "$transcript" ]; then
  model=$(grep -o '"model":"claude-[^"]*"' "$transcript" 2>/dev/null | tail -1 | cut -d'"' -f4)
fi
if [ -z "$model" ]; then
  model=$(jq -r '.model // empty' "$HOME/.claude/settings.json" 2>/dev/null)
fi

TMP="${TMPDIR:-/tmp}"

case "$model" in
  *opus*) ;;
  *)
    rm -f "$TMP/fable-"*"-$session" 2>/dev/null
    exit 0
    ;;
esac

FDIR="$HOME/.claude/hooks/fable"
out=""

if [ ! -f "$TMP/fable-core-$session" ] && [ -f "$FDIR/core.md" ]; then
  out=$(cat "$FDIR/core.md")
  touch "$TMP/fable-core-$session"
fi

# ponytail: keyword routing; a false positive costs one ~600-word module once per session
inject() {
  name="$1"; regex="$2"
  [ -f "$TMP/fable-$name-$session" ] && return 0
  [ -f "$FDIR/$name.md" ] || return 0
  printf '%s' "$prompt" | grep -qiE "$regex" || return 0
  out="$out

$(cat "$FDIR/$name.md")"
  touch "$TMP/fable-$name-$session"
}

inject visual     'styl|design|layout|css|dashboard|screenshot|visual|slide|deck|logo|banner|thumbnail|poster|image|graphic|chart|font|color|responsive|figma|mockup|wireframe|icon|landing page|frontend'
inject content    'blog|article|post|caption|copywrit|copy for|email|newsletter|script for|linkedin|tweet|thread|headline|proofread|draft|rewrite|write .{0,20}(about|for|piece)|course|lesson|tutorial'
inject delegation 'spawn|subagent|delegat|orchestr|dispatch|coordinat|agent|-pd|worker|fan.?out'
inject research   'research|compar|evaluat|investigat|competitor|market|deep.?dive|find out|which (tool|library|framework|vendor|model)|options for|state of the art'
inject coding     'code|implement|refactor|debug|bug|fix|function|api|endpoint|feature|test|deploy|migrat|schema|component|module|repo|build'
inject planning   'plan|architect|roadmap|approach|strategy|spec|proposal|milestone|scope|design doc'
inject systems    'system|workflow|process|pipeline|automat|infra|recurring|keeps happening|every time|hook|integration'
inject security   'security|auth|login|password|secret|token|credential|permission|vulnerab|inject|xss|csrf|encrypt|sanitiz|rls|api key|exploit|pentest|attack|database|prod|backup|migrat|drop table|install'
inject efficiency 'optimi|efficien|slow|faster|perform|speed|latency|cost|token|cache|bottleneck|throughput|scal|expensive|reduce|lighter|leaner'

if [ -z "$out" ]; then
  out="FABLE THINKING ACTIVE (Opus) — core discipline loaded earlier this session; keep applying it. Task modules on demand in $FDIR/: visual, content, delegation, research, coding, planning, systems, security, efficiency — Read the matching one if this task needs it and it is not in context."
fi

printf '%s' "$out" | jq -Rs '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":.}}'
