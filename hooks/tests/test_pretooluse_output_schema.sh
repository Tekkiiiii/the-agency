#!/usr/bin/env bash
# Regression guard: PreToolUse guard hooks must emit the NESTED hookSpecificOutput shape.
#   decision : {"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny|ask",
#                "permissionDecisionReason":"..."}}
#   warning  : {"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"..."}}
#              (NO permissionDecision: the tool call goes ahead)
# A top-level {"permissionDecision":..,"message":..} is silently ignored by Claude Code, so a hook
# that prints it never blocks or asks. This test pins that bug.
# gate-guard is warn-only under the standard profile, deny under strict, and never asks.
# Hermetic: every case runs with a temp HOME and a temp AGENCY_HOME that holds .hook-profile.
# bash 3.2 portable. Fake secrets are generated at random; nothing real is used.
HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0

unset CLAUDE_CONFIG_DIR
mkdir -p "$TMP/home" "$TMP/work"
for p in minimal standard strict; do
  mkdir -p "$TMP/root-$p"
  printf '%s\n' "$p" > "$TMP/root-$p/.hook-profile"
done

# Existing protected config + a filename containing a double quote.
echo '{"semi": true}' > "$TMP/work/.prettierrc"
QUOTED="$TMP/work/.prettierrc.\"x\""
echo 'x' > "$QUOTED"

AKIA="AKIA$(LC_ALL=C tr -dc 'A-Z' </dev/urandom | head -c 16)"
GHP="ghp_$(LC_ALL=C tr -dc 'a-zA-Z0-9' </dev/urandom | head -c 36)"

# payload <tool_name> <key> <value> [content]  -> PreToolUse JSON on stdout
payload() {
  python3 -I -c '
import json,sys
tool,key,val,content,cwd=sys.argv[1:6]
ti={key:val}
if content: ti["content"]=content
print(json.dumps({"session_id":"t","hook_event_name":"PreToolUse","tool_name":tool,"tool_input":ti,"cwd":cwd}))
' "$1" "$2" "$3" "${4:-}" "$TMP/work"
}

# check <label> <hook.sh> <profile> <expected: pass|ask|deny|warn> <payload-json>
check() {
  local label="$1" hook="$2" profile="$3" expect="$4" input="$5"
  local out rc verdict
  out=$(printf '%s' "$input" | HOME="$TMP/home" AGENCY_HOME="$TMP/root-$profile" bash "$HOOKS/$hook" 2>/dev/null); rc=$?
  verdict=$(printf '%s' "$out" | python3 -I -c '
import sys,json
expect=sys.argv[1]
raw=sys.stdin.read().strip()
if raw=="":
    d={}
else:
    try: d=json.loads(raw)
    except Exception as e:
        print("FAIL invalid JSON: %s" % e); sys.exit(0)
if expect=="pass":
    print("OK" if d=={} else "FAIL expected pass, got %s" % raw[:200]); sys.exit(0)
bad=[k for k in ("permissionDecision","message") if k in d]
if bad: print("FAIL top-level keys present: %s" % bad); sys.exit(0)
h=d.get("hookSpecificOutput")
if not isinstance(h,dict): print("FAIL no hookSpecificOutput: %s" % raw[:200]); sys.exit(0)
if h.get("hookEventName")!="PreToolUse": print("FAIL hookEventName=%r" % h.get("hookEventName")); sys.exit(0)
if expect=="warn":
    if "permissionDecision" in h: print("FAIL warn must not carry permissionDecision, got %r" % h.get("permissionDecision")); sys.exit(0)
    c=h.get("additionalContext")
    if not isinstance(c,str) or not c.strip(): print("FAIL empty additionalContext"); sys.exit(0)
    print("OK"); sys.exit(0)
if h.get("permissionDecision")!=expect: print("FAIL permissionDecision=%r want %r" % (h.get("permissionDecision"),expect)); sys.exit(0)
r=h.get("permissionDecisionReason")
if not isinstance(r,str) or not r.strip(): print("FAIL empty permissionDecisionReason"); sys.exit(0)
print("OK")
' "$expect")
  if [ "$verdict" = "OK" ] && [ "$rc" = 0 ]; then
    PASS=$((PASS+1)); echo "PASS  $label"
  else
    FAIL=$((FAIL+1)); echo "FAIL  $label  [rc=$rc] $verdict"
    echo "      output: $(printf '%s' "$out" | head -c 300)"
  fi
}

R="$TMP/root-standard"

# ---- config-protection (Write/Edit): hard deny ----
check "config-protection: existing .prettierrc -> deny" config-protection.sh standard deny \
  "$(payload Write file_path "$TMP/work/.prettierrc" x)"
check "config-protection: Edit existing .prettierrc -> deny" config-protection.sh standard deny \
  "$(payload Edit file_path "$TMP/work/.prettierrc")"
check "config-protection: non-existent .prettierrc -> pass" config-protection.sh standard pass \
  "$(payload Write file_path "$TMP/work/sub/.prettierrc" x)"
check "config-protection: random file -> pass" config-protection.sh standard pass \
  "$(payload Write file_path "$TMP/work/random.txt" x)"
check "config-protection: filename with double quote -> valid JSON deny" config-protection.sh standard deny \
  "$(payload Write file_path "$QUOTED" x)"

# ---- secret-scanner (Bash): ask under standard, deny under strict ----
check "secret-scanner: AKIA key, standard -> ask" secret-scanner.sh standard ask \
  "$(payload Bash command "echo $AKIA")"
check "secret-scanner: AKIA key, strict -> deny" secret-scanner.sh strict deny \
  "$(payload Bash command "echo $AKIA")"
check "secret-scanner: benign command -> pass" secret-scanner.sh standard pass \
  "$(payload Bash command "ls -la")"

# ---- gate-guard (Write/Edit): warn-only under standard, deny under strict, never ask ----
check "gate-guard: settings.json, standard -> warn (no permissionDecision)" gate-guard.sh standard warn \
  "$(payload Write file_path "$R/settings.json" '{}')"
check "gate-guard: settings.json, strict -> deny" gate-guard.sh strict deny \
  "$(payload Write file_path "$TMP/root-strict/settings.json" '{}')"
check "gate-guard: benign path -> pass" gate-guard.sh standard pass \
  "$(payload Write file_path "$TMP/work/notes.txt" hello)"
check "gate-guard: content with ghp_ token, standard -> warn" gate-guard.sh standard warn \
  "$(payload Write file_path "$TMP/work/notes.txt" "$GHP" "token=$GHP")"
check "gate-guard: content with ghp_ token, strict -> deny" gate-guard.sh strict deny \
  "$(payload Write file_path "$TMP/work/notes.txt" "$GHP" "token=$GHP")"
check "gate-guard: agents/specialized/x.md -> warn" gate-guard.sh standard warn \
  "$(payload Write file_path "$R/agents/specialized/x.md" x)"
check "gate-guard: agents/specialized/x.md, strict -> deny" gate-guard.sh strict deny \
  "$(payload Write file_path "$TMP/root-strict/agents/specialized/x.md" x)"
check "gate-guard: core/agents/x.md -> warn" gate-guard.sh standard warn \
  "$(payload Write file_path "$R/core/agents/x.md" x)"
check "gate-guard: projects/foo/memory/agents/scratch.md -> pass (not an agent definition)" gate-guard.sh standard pass \
  "$(payload Write file_path "$R/projects/foo/memory/agents/scratch.md" x)"
check "gate-guard: hook script path -> warn" gate-guard.sh standard warn \
  "$(payload Write file_path "$R/hooks/x.sh" x)"
check "gate-guard: SKILL.md -> warn" gate-guard.sh standard warn \
  "$(payload Write file_path "$R/skills/foo/SKILL.md" x)"

# ---- spawn-gate (Agent): ask on unknown types, pass on structural ones ----
check "spawn-gate: bogus-specialist -> ask" spawn-gate.sh standard ask \
  "$(payload Agent subagent_type bogus-specialist)"
check "spawn-gate: general-purpose -> pass" spawn-gate.sh standard pass \
  "$(payload Agent subagent_type general-purpose)"
check "spawn-gate: council-opus (council seat) -> pass" spawn-gate.sh standard pass \
  "$(payload Agent subagent_type council-opus)"

# ---- minimal profile is a no-op for all four ----
check "config-protection: minimal profile -> pass" config-protection.sh minimal pass \
  "$(payload Write file_path "$TMP/work/.prettierrc" x)"
check "secret-scanner: minimal profile -> pass" secret-scanner.sh minimal pass \
  "$(payload Bash command "echo $AKIA")"
check "gate-guard: minimal profile -> pass" gate-guard.sh minimal pass \
  "$(payload Write file_path "$TMP/root-minimal/settings.json" '{}')"
check "spawn-gate: minimal profile -> pass" spawn-gate.sh minimal pass \
  "$(payload Agent subagent_type bogus-specialist)"

echo "---"; echo "passed=$PASS failed=$FAIL"
[ "$FAIL" = 0 ]
